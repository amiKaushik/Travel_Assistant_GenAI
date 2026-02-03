import datetime
import os
import streamlit as st

from llm import generate_travel_plan_json, chat_with_memory
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
st.caption("Structured, smart, and interactive travel planning")

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

# -----------------------------
# Generate Travel Plan
# -----------------------------
if generate_btn:
    destinations = [d.strip() for d in destination_input.split(",") if d.strip()]
    if not source.strip() or not destinations:
        st.error("Please enter a valid source and at least one destination.")
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
        st.stop()

    spinner_placeholder.empty()

    if "error" in travel_data:
        st.error(travel_data["error"])
        st.stop()

    st.session_state.travel_data = travel_data

main_col, chat_col = st.columns([3.2, 1.3])

with main_col:
    # -----------------------------
    # Render Travel Plan
    # -----------------------------
    if "travel_data" in st.session_state:
        data = st.session_state.travel_data

        header_left, header_right = st.columns([3, 2])
        with header_left:
            st.subheader("Trip Overview")
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

        st.subheader("Route Comparison")
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

        st.subheader("Best Route Recommendation")
        st.success(data["best_route_recommendation"])

        st.divider()

        st.subheader("Detailed Travel Plan")
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
    st.subheader("Travel Assistant Chat")
    st.caption("Ask follow-up questions about your trip.")

    for role, msg in memory.get("chat_history", []):
        with st.chat_message(role):
            st.markdown(msg)

    user_input = st.chat_input("Ask a follow-up question...")
    if user_input:
        response = chat_with_memory(user_input, memory)
        st.session_state.memory = memory
        st.info(response)
