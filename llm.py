import os
import json
import time
import re
import csv
from dotenv import load_dotenv
from pydantic import ValidationError
import google.genai as genai

from prompt_builder import build_prompt
from schema import validate_travel_plan
from providers import GeoapifyProvider, ProviderError


# -----------------------------
# Config
# -----------------------------
load_dotenv()
_api_key = os.getenv("GEMINI_API_KEY")
if not _api_key:
    raise RuntimeError("GEMINI_API_KEY is not set")

client = genai.Client(api_key=_api_key)
MODEL_NAME = "gemini-2.5-flash-lite"


# -----------------------------
# Helpers
# -----------------------------
def _safe_json_parse(text: str):
    """
    Safely parse JSON from model output.
    Supports JSON objects and arrays, including fenced responses.
    """
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        cleaned = text.strip()

        # Handle fenced markdown responses like ```json ... ```
        if cleaned.startswith("```"):
            cleaned = cleaned.strip("`")
            cleaned = cleaned.replace("json", "", 1).strip()

        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            pass

        start_obj = cleaned.find("{")
        end_obj = cleaned.rfind("}")
        start_arr = cleaned.find("[")
        end_arr = cleaned.rfind("]")

        candidates = []
        if start_obj != -1 and end_obj != -1 and end_obj > start_obj:
            candidates.append(cleaned[start_obj:end_obj + 1])
        if start_arr != -1 and end_arr != -1 and end_arr > start_arr:
            candidates.append(cleaned[start_arr:end_arr + 1])

        for candidate in candidates:
            try:
                return json.loads(candidate)
            except json.JSONDecodeError:
                continue

        raise ValueError("No JSON payload found in LLM response")


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


def _friendly_llm_error(exc: Exception) -> str:
    text = str(exc)
    upper = text.upper()
    if "RESOURCE_EXHAUSTED" in upper or "429" in upper:
        return (
            "The AI service rate limit was exceeded. Please try again later."
        )
    if "API KEY" in upper or "INVALID" in upper or "401" in upper or "403" in upper:
        return (
            "The API key appears to be invalid or expired. Please update the API key."
        )
    if "DEADLINE" in upper or "TIMEOUT" in upper or "504" in upper:
        return "The AI service timed out. Please try again in a moment."
    return "The AI service is currently unavailable. Please try again later."


def _norm_place(value: str) -> str:
    cleaned = "".join(ch if ch.isalnum() or ch.isspace() else " " for ch in (value or "").lower())
    return " ".join(cleaned.strip().split())


def _load_curated_places(csv_paths: tuple[str, ...] = (".data/places.csv", "places.csv")) -> list[dict]:
    rows: list[dict] = []
    for csv_path in csv_paths:
        if not os.path.exists(csv_path):
            continue
        with open(csv_path, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                place = (
                    row.get("place")
                    or row.get("Place")
                    or row.get("place_name")
                    or row.get("Place Name")
                    or ""
                ).strip()
                city = (row.get("City") or row.get("city") or "").strip()
                state = (row.get("State") or row.get("state") or "").strip()
                if place:
                    rows.append({"place": place, "city": city, "state": state})
    return rows


def _prioritize_local_places(source: str, llm_places: list[str], limit: int = 6) -> list[str]:
    source_key = _norm_place(source)
    curated = _load_curated_places()

    local: list[str] = []
    seen_local: set[str] = set()
    for row in curated:
        place = row.get("place") or ""
        city = row.get("city") or ""
        state = row.get("state") or ""
        if not place:
            continue

        place_key = _norm_place(place)
        city_key = _norm_place(city)
        state_key = _norm_place(state)

        if source_key and (source_key == city_key or source_key == state_key or source_key in place_key):
            key = _norm_place(place)
            if key not in seen_local:
                seen_local.add(key)
                local.append(place)

    ranked: list[str] = []
    seen: set[str] = set()
    for place in local + llm_places:
        key = _norm_place(place)
        if key and key not in seen:
            seen.add(key)
            ranked.append(place)
        if len(ranked) >= limit:
            break
    return ranked

def suggest_places(source: str) -> list[str]:
    """
    Suggest travel places based on a source location (India-focused).
    Returns a short list of place names.
    """
    prompt = f"""
You are a travel assistant focused on India only.
Suggest 6 travel destinations for someone starting from: {source}.
Rules:
- Prefer nearby or same-state destinations first (biased to the source).
- Include 2 popular India-wide picks.
- Return ONLY a JSON array of place names (strings).
Example: ["Place 1", "Place 2", "Place 3"]
"""
    for attempt in range(2):
        try:
            response = client.models.generate_content(
                model=MODEL_NAME,
                contents=prompt
            )
            text = response.text or "[]"
            data = _safe_json_parse(text)

            if isinstance(data, list):
                places = [str(x).strip() for x in data if str(x).strip()]
                return places[:6]

            if isinstance(data, dict):
                for key in ("places", "suggestions", "destinations"):
                    value = data.get(key)
                    if isinstance(value, list):
                        places = [str(x).strip() for x in value if str(x).strip()]
                        return places[:6]
            return []
        except Exception:
            if attempt == 1:
                return []
            time.sleep(1.5 * (attempt + 1))
            continue


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
        try:
            response = client.models.generate_content(
                model=MODEL_NAME,
                contents=prompt
            )
        except Exception as exc:
            if attempt == 1:
                friendly = _friendly_llm_error(exc)
                raise RuntimeError(friendly) from exc
            time.sleep(1.5 * (attempt + 1))
            continue
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
    Conversational chat using memory context, with direct place suggestion fallback.
    """
    normalized = (user_input or "").strip().lower()

    def _extract_city(text: str) -> str | None:
        patterns = [
            r"(?:in|at|near|around)\s+([a-zA-Z][a-zA-Z\s\-']{2,})",
            r"from\s+([a-zA-Z][a-zA-Z\s\-']{2,})"
        ]
        for p in patterns:
            match = re.search(p, text, re.IGNORECASE)
            if match:
                city = match.group(1).strip(" .,!?")
                if city:
                    return city
        return None

    suggestion_intent = any(k in normalized for k in (
        "suggest", "recommend", "where to go", "places", "visit"
    ))

    if suggestion_intent:
        city = _extract_city(user_input) or (memory.get("last_trip") or {}).get("source")
        if city:
            llm_places = suggest_places(city)
            places = _prioritize_local_places(city, llm_places)
            if places:
                response_text = "Suggested places near {}:\n- {}".format(city, "\n- ".join(places[:6]))
            else:
                response_text = "I could not fetch suggestions right now. Please try again in a moment."
            memory.setdefault("chat_history", []).append(("user", user_input))
            memory["chat_history"].append(("assistant", response_text))
            return response_text

    chat_prompt = f"""
You are a strict India-only travel assistant chatbot.

Scope rules:
- Answer only travel-related questions.
- Support India travel only. For international requests, reply exactly:
  "Sorry, we do not support international travel."
- Use only the memory context provided below.
- Do not invent details.

Memory context:
Last planned trip:
{memory.get("last_trip")}

Conversation history:
{memory.get("chat_history", [])}

User question:
{user_input}

Response rules:
- If answerable from memory and travel-related: respond clearly and briefly.
- If travel-related but not answerable from memory: reply exactly:
  "I don't have enough trip information to answer that."
- If user asks where to go without enough trip context: reply exactly:
  "Use 'Suggest Travel Places' to get destination ideas from your source city."
- If non-travel: reply exactly:
  "I am a travel assistant and can only help with travel-related questions."

Formatting:
- Keep answer concise.
- Do not ask follow-up questions.
- Do not explain reasoning.
"""

    response = None
    for attempt in range(2):
        try:
            response = client.models.generate_content(
                model=MODEL_NAME,
                contents=chat_prompt
            )
            break
        except Exception as exc:
            if attempt == 1:
                friendly = _friendly_llm_error(exc)
                return f"{friendly} Please contact the author."
            time.sleep(1.5 * (attempt + 1))
            continue

    memory.setdefault("chat_history", []).append(("user", user_input))
    if response is None:
        return "The AI service is currently unavailable. Please contact the author."
    memory["chat_history"].append(("assistant", response.text))

    return response.text











