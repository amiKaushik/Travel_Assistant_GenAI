def build_prompt(
    source: str,
    destinations: list[str],
    budget: int,
    start_date=None,
    routes_context: str | None = None
) -> str:
    """
    Build a prompt for the LLM to generate a structured travel plan as JSON.

    Args:
        source (str): Starting city/location
        destinations (list[str]): Destination city/location(s)
        budget (int): Total budget in INR
        start_date (datetime.date or None): Optional start date for the trip
        routes_context (str or None): Optional authoritative routing data

    Returns:
        str: Formatted prompt string for the LLM
    """
    start_date_section = (
        f"Start Date: {start_date}\n" if start_date
        else "Start Date: Not specified (do NOT assume seasons or weather)\n"
    )

    routes_section = (
        f"ROUTE DATA (authoritative, use exactly):\n{routes_context}\n"
        if routes_context
        else "ROUTE DATA: Not available (you may estimate travel time and distance).\n"
    )

    destinations_line = " -> ".join(destinations)

    prompt = f"""
You are a professional travel planning system.

    Your task is to analyze the trip details below and return a structured travel plan.

    INPUT:
    Source: {source}
    Destinations: {destinations_line}
    {start_date_section}
    Budget: INR {budget}
    {routes_section}

    VALIDATION RULES:
    - Source and destinations must be valid real-world place names.
    - Source and destinations must be in same country.
    - Budget must be a numeric value.
    - If source is invalid, return ONLY:
    {{"error": "Enter a valid source"}}
    - If destination is invalid, return ONLY:
    {{"error": "Enter a valid destination"}}

    TRAVEL RULES:
    - For a single destination, include ONE route with MULTIPLE transport options.
    - For multiple destinations, include ONE route per leg with MULTIPLE transport options.
    - Travel time is mandatory for every transport option.
    - Cost estimates must be realistic and within the given budget.
    - Exclude any route exceeding the budget.
    - If start date is provided, you MAY consider seasonal pricing.
    - If start date is not provided, assume average pricing.
    - If ROUTE DATA is provided, use those values exactly for time, distance, and vehicles.

JSON FORMAT:
{{
  "source": "string",
  "destinations": ["string"],
  "budget": "number",
  "routes": [
    {{
      "leg_name": "string",
      "transport_options": [
        {{
          "mode": "string",
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
      ]
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
1. Single destination: ONE route with MULTIPLE transport options
2. Multiple destinations: ONE route per leg with MULTIPLE transport options
3. Clearly mention travel time for each transport option
4. Include cost estimates per transport option
5. List commonly available vehicles
6. Provide a realistic, detailed day-wise travel plan
7. Keep all suggestions within the given budget

Return ONLY the JSON object.
"""
    return prompt
