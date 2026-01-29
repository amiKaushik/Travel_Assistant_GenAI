def build_prompt(source, destination, budget, start_date=None):
    start_date_section = (
        f"Start Date: {start_date}\n"
        if start_date else
        "Start Date: Not specified (do NOT assume seasons or weather)\n"
    )

    return f"""
You are a professional travel planning system.

Your task is to analyze the following trip details and return a structured travel plan.

INPUT:
Source: {source}
Destination: {destination}
{start_date_section}
Budget: ₹{budget}

IMPORTANT CONTEXT RULES:
- Travel time is CRITICAL and must be included for every route
- Cost estimates must be realistic and within the provided budget
- If start date is specified, you MAY consider seasonal pricing
- If start date is not specified, assume average pricing

OUTPUT REQUIREMENTS:
- You MUST return a valid JSON object
- Do NOT include markdown
- Do NOT include explanations
- Do NOT include extra text
- JSON must be directly parseable

JSON FORMAT:
{{
  "source": string,
  "destination": string,
  "budget": number,
  "routes": [
    {{
      "route_name": string,
      "estimated_travel_time": string,
      "distance_km": number,
      "available_vehicles": array of strings,
      "estimated_cost": {{
        "min": number,
        "max": number,
        "currency": "INR"
      }},
      "route_summary": string
    }}
  ],
  "best_route_recommendation": string,
  "detailed_travel_plan": {{
    "day_1": string,
    "day_2": string,
    "day_3": string
  }}
}}

CONTENT RULES:
1. Include MULTIPLE realistic travel routes
2. Clearly mention travel time for each route
3. Include cost estimates per route
4. List commonly available vehicles
5. Provide a realistic, detailed day-wise travel plan
6. Keep all suggestions within the given budget

Return ONLY the JSON object.
"""
