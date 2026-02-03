# AI Travel Assistant Bot

## Overview

The AI Travel Assistant Bot is a web-based travel planning system powered by the Gemini 2.5 Flash Lite model. It generates structured, budget-aware travel plans and includes a travel-only chatbot for follow-up questions.

This version integrates real routing data (distance and travel time) via Geoapify to improve reliability.

---

## Key Features

* Uses a pre-trained LLM (no fine-tuning required)
* Accepts user inputs:
  * Source
  * Destination
  * Budget
  * Optional start date
* Fetches real routing distance/time for India routes (Geoapify)
* Produces multiple route options with vehicles, time, and costs
* Validates model output with schema checks and retries on errors
* Includes a travel-only chatbot with session memory

---

## Tech Stack

* Python
* Streamlit
* Google Generative AI (Gemini 2.5 Flash Lite)
* Geoapify Routing + Geocoding
* Pydantic (schema validation)

---

## Setup

1. Install dependencies:

```bash
pip install -r requirements.txt
```

2. Create a `.env` file with:

```bash
GEMINI_API_KEY=your_gemini_key
GEOAPIFY_API_KEY=your_geoapify_key
```

3. Run the app:

```bash
streamlit run app.py
```

---

## Notes

* Route distance and travel time come from Geoapify.
* Cost estimates are distance-based heuristics and may vary.

---

## Future Enhancements

* Real-time pricing integrations
* Multi-city and round-trip planning
* User profile and preference memory
* Exportable itineraries

---

## Authors

Kaushik Das  
Python | SQL | AI and ML Enthusiast  
Email: kaushikdas.at@gmail.com
