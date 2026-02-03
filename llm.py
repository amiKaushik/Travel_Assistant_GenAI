import os
import json
import google.generativeai as genai
from dotenv import load_dotenv
from pydantic import ValidationError

from prompt_builder import build_prompt
from schema import validate_travel_plan
from providers import GeoapifyProvider, ProviderError


# -----------------------------
# Config
# -----------------------------
load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

model = genai.GenerativeModel("gemini-2.5-flash-lite")


# -----------------------------
# Helpers
# -----------------------------
def _safe_json_parse(text: str) -> dict:
    """
    Safely extract and parse JSON from LLM output.
    Handles cases where the model adds stray text.
    """
    try:
        # Fast path: already valid JSON
        return json.loads(text)
    except json.JSONDecodeError:
        # Fallback: extract JSON substring
        start = text.find("{")
        end = text.rfind("}") + 1
        if start == -1 or end == -1:
            raise ValueError("No JSON object found in LLM response")

        json_str = text[start:end]
        return json.loads(json_str)


def _build_routes_context(routes_by_leg: list[dict]) -> str:
    lines = []
    for leg in routes_by_leg:
        lines.append(f"Leg: {leg['leg_name']}")
        for opt in leg["transport_options"]:
            cost = opt["estimated_cost"]
            lines.append(
                f"- {opt['mode']}: time {opt['estimated_travel_time']}, "
                f"distance {opt['distance_km']} km, vehicles "
                f"{', '.join(opt['available_vehicles'])}, cost INR "
                f"{cost['min']}-{cost['max']}"
            )
    return "\n".join(lines)


def _repair_prompt(invalid_text: str, error: Exception) -> str:
    return f"""
The previous output was invalid JSON for the required schema.
Error: {error}

Fix the JSON to match the required schema exactly.
Return ONLY the corrected JSON object.

INVALID OUTPUT:
{invalid_text}
"""


# -----------------------------
# Travel Plan (JSON)
# -----------------------------
def generate_travel_plan_json(
    source: str,
    destinations: list[str],
    start_date,
    budget: int,
    memory: dict
) -> dict:
    """
    Generates a structured travel plan as JSON (Python dict).
    """
    routes_from_provider = None
    data_source = None
    provider_error = None
    try:
        provider = GeoapifyProvider()
        routes_from_provider = []
        leg_source = source
        for dest in destinations:
            options = provider.get_transport_options(leg_source, dest)
            routes_from_provider.append({
                "leg_name": f"{leg_source} -> {dest}",
                "transport_options": options
            })
            leg_source = dest
        data_source = "Geoapify routing"
    except ProviderError as exc:
        provider_error = str(exc)
        routes_from_provider = None

    routes_context = _build_routes_context(routes_from_provider) if routes_from_provider else None

    prompt = build_prompt(
        source=source,
        destinations=destinations,
        budget=budget,
        start_date=start_date,
        routes_context=routes_context
    )

    travel_data = None
    last_error = None
    for attempt in range(2):
        response = model.generate_content(prompt)
        raw_text = response.text or ""
        try:
            parsed = _safe_json_parse(raw_text)
            travel_data = validate_travel_plan(parsed)
            break
        except (ValueError, ValidationError) as exc:
            last_error = exc
            prompt = _repair_prompt(raw_text, exc)
            continue

    if travel_data is None:
        raise ValueError(f"LLM output invalid: {last_error}")

    if routes_from_provider:
        travel_data["routes"] = routes_from_provider
        travel_data["destinations"] = destinations
        if "best_route_recommendation" in travel_data:
            pass

    if data_source:
        travel_data["data_source"] = data_source
    elif provider_error:
        travel_data["data_source"] = "LLM estimates"
        travel_data["data_source_error"] = provider_error

    # -------------------------
    # Update Memory
    # -------------------------
    memory["last_trip"] = {
        "source": source,
        "destinations": destinations,
        "budget": budget,
        "start_date": str(start_date) if start_date else None,
    }

    memory.setdefault("generated_trips", []).append(travel_data)

    return travel_data


def chat_with_memory(user_input: str, memory: dict) -> str:
    """
    Simple conversational chat using memory context.
    Only answers travel-related questions based on stored memory.
    """
    chat_prompt = f"""
You are a STRICT travel assistant chatbot.

ROLE:
- You ONLY answer questions related to travel, journeys, routes, transportation, budgets, or trip planning.
- You MUST rely ONLY on the information available in memory.
- You MUST NOT invent, assume, or hallucinate details.

MEMORY CONTEXT:
Last planned trip:
{memory.get("last_trip")}

Conversation history:
{memory.get("chat_history", [])}

USER QUESTION:
{user_input}

RESPONSE RULES:
- If the question is related to travel AND can be answered using the memory context: Answer clearly and concisely.
- If the question is travel-related BUT memory does not contain enough information: Reply exactly:
      "I don't have enough trip information to answer that."
- If the question is NOT related to travel or journeys: Reply exactly:
      "I am a travel assistant and can only help with travel-related questions."

- Do NOT ask follow-up questions.
- Do NOT provide general knowledge.
- Do NOT explain your reasoning.
- Keep the response short and helpful.
"""

    response = model.generate_content(chat_prompt)

    memory.setdefault("chat_history", []).append(("user", user_input))
    memory["chat_history"].append(("assistant", response.text))

    return response.text
