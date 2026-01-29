def build_prompt(source, destination, budget, start_date=None):
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
        f"Start Date: {start_date}\n"
        if start_date else
        "Start Date: Not specified\n"
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
    - Budget must be a numeric value.
    - I source is invalid, return ONLY:
    {{"error": "Enter a valid source"}}
    - I destination is invalid, return ONLY:
    {{"error": "Enter a valid destination"}}
    - If any required input (source, destination, budget) is missing, return ONLY:
    {{"error": "Please enter every inputs"}}

    TRAVEL RULES:
    - Include MULTIPLE feasible travel routes.
    - Travel time is mandatory for every route.
    - Cost estimates must be realistic and within the given budget.
    - Exclude any route exceeding the budget.
    - If start date is provided, you MAY consider seasonal pricing.
    - If start date is not provided, assume average pricing.

    OUTPUT RULES:
    - Return ONLY valid JSON.
    - Do NOT include markdown.
    - Do NOT include explanations or extra text.

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

    FINAL ENFORCEMENT:
    - Only return JSON.
    - Travel time must never be missing.
    - All recommendations must fit within the given budget.
    """
    return prompt