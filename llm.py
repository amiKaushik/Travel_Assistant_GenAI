import os
import json
import google.generativeai as genai
from dotenv import load_dotenv

from prompt_builder import build_prompt


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


# -----------------------------
# Travel Plan (JSON)
# -----------------------------
def generate_travel_plan_json(
    source: str,
    destination: str,
    start_date,
    budget: int,
    memory: dict
) -> dict:
    """
    Generates a structured travel plan as JSON (Python dict).
    """

    prompt = build_prompt(
        source=source,
        destination=destination,
        budget=budget,
        start_date=start_date
    )

    response = model.generate_content(prompt)

    travel_data = _safe_json_parse(response.text)

    # -------------------------
    # Update Memory
    # -------------------------
    memory["last_trip"] = {
        "source": source,
        "destination": destination,
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
- If the question is related to "Suggest Some Places at The Destination": Answer relevant places.
- If the question is travel-related BUT memory does not contain enough information: Reply exactly:
      "I don't have enough trip information to answer that."
- If the question is NOT related to travel or journeys: Reply exactly:
      "I am a travel assistant and can only help with travel-related questions.🥲"

- Do NOT ask follow-up questions.
- Do NOT provide general knowledge.
- Do NOT explain your reasoning.
- Keep the response short and helpful.
"""

    response = model.generate_content(chat_prompt)

    memory.setdefault("chat_history", []).append(("user", user_input))
    memory["chat_history"].append(("assistant", response.text))

    return response.text
