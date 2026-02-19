# AI Travel Assistant

## Overview
This is a Streamlit travel planning app focused on **India‑only** trips. It generates structured, budget‑aware itineraries and shows **real routing distance/time** using Geoapify. The UI is a dashboard with route comparison, interactive map, and a right‑side chat panel.

This version also includes a **"Suggest Travel Places"** flow for users who **don’t know where to go**. Suggestions are **source‑biased** and can display **curated Cloudinary images** via a CSV mapping.

---

## What We Implemented (So Far)

### Core travel planning
* Multi‑destination input (comma‑separated): builds **legs** like `Kolkata -> Digha -> Puri`.
* Single destination: **one leg** with multiple transport options.
* Exact **date tabs** if a start date is provided (e.g., `29 JAN THU`).
* Strict **schema validation** with backward‑compat normalizers.
* **Geoapify routing** for distance/time with graceful fallback.

### India‑only enforcement
* Source/destination geocoded.
* If any stop is outside India: show a large, friendly message:
  * “Sorry, we don't support international travels 👀”
  * “We encourage you to visit our beautiful India 😋”

### UI / UX updates
* Dashboard layout with KPIs, route table, and map.
* Right‑side chat panel.
* Colored section headers using `:color[]`.
* Map showing straight‑line legs + stop markers (PyDeck).

### Suggestions (No destination case)
* **Suggest Travel Places** button only when destination is empty or international.
* Suggestions are biased to the source + a few all‑India picks.
* Each suggestion opens in a tab with a **curated image** from Cloudinary (CSV mapping).

### Reliability & errors
* Friendly error messages for rate limit, invalid key, and timeouts.
* No crashes on LLM failure—clean UI feedback.

---

## What We Removed
* Unsplash and Wikimedia image fetches (replaced by curated Cloudinary URLs).
* Unreliable public image search sources.

---

## Current Design Decisions
* **India‑only** travel.
* **Curated images** via CSV mapping to Cloudinary public URLs.
* **Model**: Gemini 2.5 Flash Lite via `google-genai`.
* **Transport options** per leg; not individual LLM routes.

---

## Setup

### 1) Install dependencies
```bash
pip install -r requirements.txt
```

### 2) Environment variables
Create a `.env` file:
```bash
GEMINI_API_KEY=your_gemini_key
GEOAPIFY_API_KEY=your_geoapify_key
```

### 3) Curated images (Cloudinary)
Create or edit `places.csv` with **public** Cloudinary links:
```
place,image_url,characteristics
Kolkata,https://res.cloudinary.com/<cloud>/image/upload/v1/TravelPlacesIndia/kolkata.jpg,city culture food heritage
Darjeeling,https://res.cloudinary.com/<cloud>/image/upload/v1/TravelPlacesIndia/darjeeling.jpg,tea hills mountain view sunrise
```

### 4) Run
```bash
streamlit run app.py
```

---

## Key Files
* `app.py` — UI, map, suggestions, and India‑only checks
* `llm.py` — LLM calls, retries, and suggestion generation
* `schema.py` — validation + normalization
* `providers.py` — Geoapify routing + geocoding
* `places.csv` — curated image mapping for suggestions

---

## Current Behavior (Quick Summary)
* If destination is empty → Suggest button appears.
* If destination is outside India → big friendly message + Suggest button.
* If Geoapify fails → LLM still returns routes.
* If LLM rate‑limited → clean UI message (no crash).

---

## Future Improvements
* Road‑geometry map lines (not straight‑line legs)
* User preference filters (temples, food, mountains, nightlife)
* Multiple images per place (carousel)
* PDF export for itineraries
* Persistent saved trips
* FastAPI backend separation
* Tests + CI pipeline

---

## Author (This Branch)
Kaushik Das  
Email: kaushikdas.at@gmail.com
