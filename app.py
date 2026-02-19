import csv
import datetime
import os
import streamlit as st
import pydeck as pdk

from llm import generate_travel_plan_json, chat_with_memory, suggest_places
from providers import GeoapifyProvider, ProviderError
from memory import init_memory


def _pick_best_option(routes: list[dict]) -> dict | None:
    if not routes:
        return None
    options = []
    for leg in routes:
        options.extend(leg.get("transport_options", []))
    if not options:
        return None
    return sorted(options, key=lambda r: r["estimated_cost"]["min"])[0]


@st.cache_data(show_spinner=False)
def _geocode_stops(source: str, destinations: list[str]) -> list[dict]:
    provider = GeoapifyProvider()
    stops = []
    start = provider.geocode_place(source)
    stops.append({
        "name": source,
        "lat": start["lat"],
        "lon": start["lon"]
    })
    for dest in destinations:
        item = provider.geocode_place(dest)
        stops.append({
            "name": dest,
            "lat": item["lat"],
            "lon": item["lon"]
        })
    return stops


@st.cache_data(show_spinner=False)
def _normalize_place(value: str) -> str:
    cleaned = "".join(ch if ch.isalnum() or ch.isspace() else " " for ch in value.lower())
    return " ".join(cleaned.strip().split())


def _place_aliases(row: dict, place: str) -> list[str]:
    aliases: list[str] = [place]
    for key in ("City", "city", "State", "state", "Place Name", "place_name"):
        value = (row.get(key) or "").strip()
        if value:
            aliases.append(value)
    return aliases


@st.cache_data(show_spinner=False)
def _load_places_index(csv_paths: tuple[str, ...] = (".data/places.csv", "places.csv")) -> dict[str, list[dict]]:
    index: dict[str, list[dict]] = {}
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
                    or row.get("City")
                    or ""
                ).strip()
                if not place:
                    continue

                image_url = (
                    row.get("image_url")
                    or row.get("Image Link")
                    or row.get("image_link")
                    or ""
                ).strip()
                characteristics = (
                    row.get("characteristics")
                    or row.get("Image Scenery")
                    or row.get("Description")
                    or ""
                ).strip()
                entry = {
                    "place": place,
                    "image_url": image_url,
                    "characteristics": characteristics,
                    "city": (row.get("City") or row.get("city") or "").strip(),
                    "state": (row.get("State") or row.get("state") or "").strip(),
                    "country": (row.get("Country") or row.get("country") or "").strip(),
                    "image_source": (row.get("Image Source") or row.get("image_source") or "").strip(),
                    "actual_link": (row.get("Actual Link") or row.get("actual_link") or "").strip()
                }

                for alias in _place_aliases(row, place):
                    key = _normalize_place(alias)
                    if key:
                        index.setdefault(key, []).append(entry)
    return index


def _find_place_entries(places_index: dict[str, list[dict]], place: str) -> list[dict]:
    key = _normalize_place(place)
    exact = places_index.get(key, [])
    if exact:
        return exact

    matches: list[dict] = []
    for candidate_key, items in places_index.items():
        if key in candidate_key or candidate_key in key:
            matches.extend(items)
    return matches


def _prioritize_suggestions(source: str, llm_places: list[str], places_index: dict[str, list[dict]], limit: int = 6) -> list[str]:
    src = _normalize_place(source)
    local: list[str] = []
    seen_local: set[str] = set()

    for items in places_index.values():
        for entry in items:
            place_name = (entry.get("place") or "").strip()
            if not place_name:
                continue
            city_key = _normalize_place(entry.get("city") or "")
            place_key = _normalize_place(place_name)
            state_key = _normalize_place(entry.get("state") or "")
            if src and (src == city_key or src in place_key or src == state_key):
                dedupe = _normalize_place(place_name)
                if dedupe not in seen_local:
                    seen_local.add(dedupe)
                    local.append(place_name)

    ranked: list[str] = []
    seen_ranked: set[str] = set()
    for place in local + llm_places:
        key = _normalize_place(place)
        if key and key not in seen_ranked:
            seen_ranked.add(key)
            ranked.append(place)
        if len(ranked) >= limit:
            break
    return ranked
# -----------------------------
# Page Config
# -----------------------------
st.set_page_config(
    page_title="AI Travel Assistant",
    page_icon="AI",
    layout="wide",
    initial_sidebar_state="expanded"
)


# -----------------------------
# Initialize Memory
# -----------------------------
init_memory()
memory = st.session_state.memory

# -----------------------------
# Header
# -----------------------------
st.title("AI Travel Assistant")
st.caption(":blue[Structured], :green[smart], and :orange[interactive] travel planning")

# -----------------------------
# Sidebar Inputs
# -----------------------------
st.sidebar.header("Trip Details")

source = st.sidebar.text_input("Source")
destination_input = st.sidebar.text_input("Destination(s) - comma separated")

if os.getenv("GEOAPIFY_API_KEY"):
    st.sidebar.success("Geoapify key detected")
else:
    st.sidebar.warning("Geoapify key not detected")

use_start_date = st.sidebar.checkbox("I have a start date", value=False)
start_date = None
if use_start_date:
    start_date = st.sidebar.date_input(
        "Start Date",
        min_value=datetime.date.today()
    )

budget = st.sidebar.number_input("Budget (INR)", min_value=1000, step=500)

generate_btn = st.sidebar.button("Generate Travel Plan")

destinations = [d.strip() for d in destination_input.split(",") if d.strip()]
international_block = False
if destinations and source.strip():
    try:
        provider = GeoapifyProvider()
        source_info = provider.geocode_place(source)
        dest_infos = [provider.geocode_place(d) for d in destinations]
        all_places = [source_info] + dest_infos
        if any((p.get("country_code") or "").lower() != "in" for p in all_places):
            international_block = True
    except ProviderError:
        st.error("Unable to validate location. Please try a more specific place name.")
        st.stop()

# -----------------------------
# Generate Travel Plan
# -----------------------------
if generate_btn:
    if not source.strip() or not destinations:
        st.error("Please enter a valid source and at least one destination.")
        st.stop()

    if international_block:
        st.markdown(
            """
<div style="padding: 16px 20px; border: 2px dashed #f59e0b; border-radius: 16px; text-align: center;">
  <div style="font-size: 28px; font-weight: 700; color: #b45309;">
    Sorry, we don't support international travels &#128064;
  </div>
  <div style="font-size: 20px; margin-top: 6px; color: #92400e;">
    We encourage you to visit our beautiful India &#128523;
  </div>
</div>
            """,
            unsafe_allow_html=True
        )
        st.stop()

    spinner_placeholder = st.empty()
    with spinner_placeholder:
        st.markdown("Planning your journey...")

    try:
        travel_data = generate_travel_plan_json(
            source=source,
            destinations=destinations,
            start_date=start_date,
            budget=budget,
            memory=st.session_state.memory
        )
    except Exception as exc:
        spinner_placeholder.empty()
        st.error(f"Failed to generate plan: {exc}")
        st.caption("If this keeps happening, please contact the author.")
        st.stop()

    spinner_placeholder.empty()

    if "error" in travel_data:
        st.error(travel_data["error"])
        st.caption("If this keeps happening, please contact the author.")
        st.stop()

    st.session_state.travel_data = travel_data
main_col, chat_col = st.columns([3.2, 1.3])

with main_col:
    show_suggest = (not destinations) or international_block
    if show_suggest:
        st.subheader(":yellow[Suggest Travel Places]")
        if international_block:
            st.markdown(
                """
<div style="padding: 16px 20px; border: 2px dashed #f59e0b; border-radius: 16px; text-align: center;">
  <div style="font-size: 28px; font-weight: 700; color: #b45309;">
    Sorry, we don't support international travels &#128064;
  </div>
  <div style="font-size: 20px; margin-top: 6px; color: #92400e;">
    We encourage you to visit our beautiful India &#128523;
  </div>
</div>
                """,
                unsafe_allow_html=True
            )
        else:
            st.markdown("Not sure where to go? Get India-focused suggestions based on your source.")

        places_index = _load_places_index()
        if not places_index:
            st.info("Add .data/places.csv (or places.csv) to enable Cloudinary images for suggestions.")

        if "suggested_places" not in st.session_state:
            st.session_state.suggested_places = []
            st.session_state.suggest_source = ""

        if st.button("Suggest Travel Places"):
            if not source.strip():
                st.error("Please enter a source first.")
            else:
                llm_places = suggest_places(source)
                st.session_state.suggested_places = _prioritize_suggestions(source, llm_places, places_index)
                st.session_state.suggest_source = source
                if not st.session_state.suggested_places:
                    st.warning("Could not generate suggestions right now. Try again in a moment.")

        if st.session_state.suggested_places:
            st.caption(f"Suggestions based on: {st.session_state.suggest_source}")
            tabs = st.tabs(st.session_state.suggested_places)
            for tab, place in zip(tabs, st.session_state.suggested_places):
                with tab:
                    entries = _find_place_entries(places_index, place)
                    if entries:
                        entry = entries[0]
                        if entry.get("image_url"):
                            st.image(entry["image_url"], use_container_width=True)
                        if entry.get("characteristics"):
                            st.caption(f"Tags: {entry['characteristics']}")
                        source_name = (entry.get("image_source") or "").strip()
                        source_link = (entry.get("actual_link") or "").strip()
                        if source_name and source_link:
                            st.markdown(f"Source: [{source_name}]({source_link})")
                        elif source_link:
                            st.markdown(f"Source: [Original Image Link]({source_link})")
                        elif source_name:
                            st.caption(f"Source: {source_name}")
                    else:
                        st.info("No curated image found for this place yet.")

    # -----------------------------
    # Render Travel Plan
    # -----------------------------
    if "travel_data" in st.session_state:
        data = st.session_state.travel_data

        header_left, header_right = st.columns([3, 2])
        with header_left:
            st.subheader(":violet[Trip Overview]")
            dest_line = " -> ".join(data.get("destinations", [])) or "N/A"
            st.markdown(
                f"**{data['source']} -> {dest_line}**  \n"
                f"**Budget:** INR {data['budget']}"
            )
        with header_right:
            if "data_source" in data:
                if data["data_source"] == "Geoapify routing":
                    st.success(f"Data Source: {data['data_source']}")
                else:
                    st.warning(f"Data Source: {data['data_source']}")
                    if "data_source_error" in data:
                        st.caption(f"Geoapify issue: {data['data_source_error']}")
            else:
                st.warning("Data Source: LLM estimates")

        st.divider()

        best_option = _pick_best_option(data["routes"])
        if best_option:
            kpi_cols = st.columns(4)
            kpi_cols[0].metric("Best Option", best_option["mode"])
            kpi_cols[1].metric("Time", best_option["estimated_travel_time"])
            kpi_cols[2].metric("Distance (km)", best_option["distance_km"])
            kpi_cols[3].metric(
                "Cost (INR)",
                f"{best_option['estimated_cost']['min']} - {best_option['estimated_cost']['max']}"
            )

        st.divider()

        st.subheader(":yellow[Interactive Route Map]")
        try:
            stops = _geocode_stops(data["source"], data.get("destinations", []))
            lines = []
            for i in range(len(stops) - 1):
                lines.append({
                    "from": [stops[i]["lon"], stops[i]["lat"]],
                    "to": [stops[i + 1]["lon"], stops[i + 1]["lat"]]
                })

            line_layer = pdk.Layer(
                "LineLayer",
                data=lines,
                get_source_position="from",
                get_target_position="to",
                get_color=[14, 116, 144],
                get_width=4
            )
            point_layer = pdk.Layer(
                "ScatterplotLayer",
                data=stops,
                get_position=["lon", "lat"],
                get_radius=6000,
                get_fill_color=[37, 99, 235],
                pickable=True
            )
            view_state = pdk.ViewState(
                latitude=stops[0]["lat"],
                longitude=stops[0]["lon"],
                zoom=5
            )
            st.pydeck_chart(
                pdk.Deck(
                    layers=[line_layer, point_layer],
                    initial_view_state=view_state,
                    tooltip={"text": "{name}"}
                ),
                use_container_width=True
            )
        except (ProviderError, Exception):
            st.info("Map could not be loaded for these locations.")

        st.divider()

        st.subheader(":blue[Route Comparison]")
        default_leg_names = []
        if data.get("destinations"):
            leg_source = data["source"]
            for dest in data["destinations"]:
                default_leg_names.append(f"{leg_source} -> {dest}")
                leg_source = dest

        for idx, leg in enumerate(data["routes"]):
            leg_name = leg.get("leg_name")
            if not leg_name and idx < len(default_leg_names):
                leg_name = default_leg_names[idx]
            if not leg_name:
                leg_name = f"Leg {idx + 1}"
            st.markdown(f"**{leg_name}**")

            rows = []
            options = leg.get("transport_options")
            if options is None:
                options = [leg]
            for opt in options:
                rows.append({
                    "Mode": opt.get("mode", opt.get("route_name", "Unknown")),
                    "Time": opt.get("estimated_travel_time", "N/A"),
                    "Distance (km)": opt.get("distance_km", "N/A"),
                    "Cost Min (INR)": opt.get("estimated_cost", {}).get("min", "N/A"),
                    "Cost Max (INR)": opt.get("estimated_cost", {}).get("max", "N/A"),
                    "Vehicles": ", ".join(opt.get("available_vehicles", [])) or "N/A"
                })
            st.dataframe(rows, use_container_width=True, hide_index=True)

        st.divider()

        st.subheader(":green[Best Route Recommendation]")
        st.success(data["best_route_recommendation"])

        st.divider()

        st.subheader(":orange[Detailed Travel Plan]")
        plan_items = list(data["detailed_travel_plan"].items())

        def _day_key(item):
            key = item[0]
            parts = key.split("_")
            if len(parts) == 2 and parts[1].isdigit():
                return int(parts[1])
            return 0

        plan_items.sort(key=_day_key)
        tab_labels = []
        for idx, (day, _plan) in enumerate(plan_items):
            if start_date:
                current_date = start_date + datetime.timedelta(days=idx)
                tab_labels.append(current_date.strftime("%d %b %a").upper())
            else:
                tab_labels.append(day.replace("_", " ").title())
        day_tabs = st.tabs(tab_labels)
        for tab, (_day, plan) in zip(day_tabs, plan_items):
            with tab:
                st.markdown(plan)

        with st.expander("Raw JSON (Debug)"):
            st.json(data)

with chat_col:
    # -----------------------------
    # Chatbot (Right Panel)
    # -----------------------------
    st.subheader(":orange[Travel Assistant Chat]")
    st.caption("Ask follow-up questions about your trip.")

    for role, msg in memory.get("chat_history", []):
        with st.chat_message(role):
            st.markdown(msg)

    user_input = st.chat_input("Ask a follow-up question...")
    if user_input:
        response = chat_with_memory(user_input, memory)
        st.session_state.memory = memory
        st.info(response)

st.markdown(
    """
<style>
.footer {
    background-color: #2c2c2c;
    color: #f1f1f1;
    padding: 10px;
    text-align: center;
    position: relative;
    width: 100%;
    bottom: 0;
}
.content {
    min-height: calc(100vh - 100px);
    display: flex;
    flex-direction: column;
    justify-content: space-between;
}
.footer a {
    color: #64b5f6;
}
.footer a:hover {
    text-decoration: underline;
}
</style>
<div class="content">
    <div></div>
    <div class="footer">
        <p><b>Contact Us</b></p>
        <p>Ping me on GitHub: <a href="https://github.com/amiKaushik" target="_blank">https://github.com/amiKaushik</a></p>
    </div>
</div>
    """,
    unsafe_allow_html=True
)








