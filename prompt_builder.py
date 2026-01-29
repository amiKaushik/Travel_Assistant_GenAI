def build_prompt(source: str, destination: str, budget: int, start_date=None) -> str:
    """
    Build a prompt for the LLM to generate a structured travel plan as JSON.

    Args:
        source (str): Starting city/location
        destination (str): Destination city/location
        budget (int): Total budget in INR
        start_date (datetime.date or None): Optional start date for the trip

    Returns:
        str: Formatted prompt string for the LLM
    """
    start_date_section = (
        f"Start Date: {start_date}\n" if start_date
        else "Start Date: Not specified (do NOT assume seasons or weather)\n"
    )

    prompt = f"""
You are a professional travel planning system.

    Your task is to analyze the trip details below and return a structured travel plan.

    INPUT:
    Source: {source}
    Destination: {destination}
    {start_date_section}
    Budget: ₹{budget}

    VALIDATION RULES:
    - Source and destination must be valid real-world place names.
    - Source and destination must be in same country.
    - Budget must be a numeric value.
    - If source is invalid, return ONLY:
    {{"error": "Enter a valid source🙂"}}
    - If destination is invalid, return ONLY:
    {{"error": "Enter a valid destination🙂"}}

    TRAVEL RULES:
    - Include MULTIPLE feasible travel routes.
    - Travel time is mandatory for every route.
    - Cost estimates must be realistic and within the given budget.
    - Exclude any route exceeding the budget.
    - If start date is provided, you MAY consider seasonal pricing.
    - If start date is not provided, assume average pricing.

JSON FORMAT:
{{
  "source": "string",
  "destination": "string",
  "budget": "number",
  "routes": [
    {{
      "route_name": "string",
      "estimated_travel_time": "string",
      "distance_km": "number",
      "available_vehicles": ["string"],
      "estimated_cost": {{
        "min": "number",
        "max": "number",
        "currency": "INR"
      }},
      "route_summary": "string"
    }}
  ],
  "best_route_recommendation": "string",
  "detailed_travel_plan": {{
    "day_1": "string",
    "day_2": "string",
    "day_3": "string"
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
    return prompt
