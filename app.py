import streamlit as st

from llm import generate_travel_plan_json
from memory import init_memory


# -----------------------------
# Page Config
# -----------------------------
st.set_page_config(
    page_title="AI Travel Assistant ✈️",
    page_icon="🗺️",
    layout="wide",
)

# -----------------------------
# Init Memory
# -----------------------------
init_memory()

# -----------------------------
# Header
# -----------------------------
st.title("✈️ AI Travel Assistant")
st.caption("Structured, smart, and interactive travel planning")

# -----------------------------
# Sidebar Inputs
# -----------------------------
st.sidebar.header("🧳 Trip Details")

source = st.sidebar.text_input("Source")
destination = st.sidebar.text_input("Destination")
start_date = st.sidebar.date_input("Start Date (optional)", value=None, min_value="today")
budget = st.sidebar.number_input("Budget (₹)", min_value=1000, step=500)

generate_btn = st.sidebar.button("✨ Generate Travel Plan")

# -----------------------------
# Generate Travel Plan
# -----------------------------
if generate_btn:
    if not source.strip() or not destination.strip():
        st.error("Please enter both valid source and destination")
        st.stop()
    spinner_placeholder = st.empty()

    with spinner_placeholder:
        st.markdown("⏳ Planning your journey...")

    travel_data = generate_travel_plan_json(
        source=source,
        destination=destination,
        start_date=start_date,
        budget=budget,
        memory=st.session_state.memory
    )

    # Remove spinner immediately
    spinner_placeholder.empty()

    # Handle LLM error response
    if "error" in travel_data:
        st.error(travel_data["error"])
        st.stop()

    st.session_state.travel_data = travel_data




# -----------------------------
# Render Travel Plan (JSON-driven UI)
# -----------------------------
if "travel_data" in st.session_state:
    data = st.session_state.travel_data

    # -------------------------
    # Trip Summary
    # -------------------------
    st.subheader("🧭 Trip Overview")
    st.markdown(
        f"**{data['source']} → {data['destination']}**  \n"
        f"💰 **Budget:** ₹{data['budget']}"
    )

    st.divider()

    # -------------------------
    # Routes Section
    # -------------------------
    st.subheader("🛣️ Available Travel Routes")

    cols = st.columns(len(data["routes"]))

    for idx, route in enumerate(data["routes"]):
        with cols[idx]:
            st.markdown(f"### {route['route_name']}")
            st.markdown(f"⏱ **Time:** {route['estimated_travel_time']}")
            st.markdown(
                f"💰 **Cost:** ₹{route['estimated_cost']['min']} "
                f"- ₹{route['estimated_cost']['max']}"
            )
            st.markdown(
                "🚗 **Vehicles:** " + ", ".join(route["available_vehicles"])
            )
            st.caption(route["route_summary"])

    st.divider()

    # -------------------------
    # Best Route Recommendation
    # -------------------------
    st.subheader("⭐ Best Route Recommendation")
    st.success(data["best_route_recommendation"])

    st.divider()

    # -------------------------
    # Detailed Travel Plan
    # -------------------------
    st.subheader("📅 Detailed Travel Plan")

    day_tabs = st.tabs(list(data["detailed_travel_plan"].keys()))

    for tab, (day, plan) in zip(
        day_tabs, data["detailed_travel_plan"].items()
    ):
        with tab:
            st.markdown(plan)

# -----------------------------
# Chatbot (Optional / Secondary)
# -----------------------------
st.divider()
st.subheader("💬 Travel Assistant Chat")

user_input = st.chat_input("Ask a follow-up question...")

if user_input:
    st.session_state.memory["chat_history"].append(
        ("user", user_input)
    )
    st.info("Chat handling is managed separately.")

for role, msg in st.session_state.memory["chat_history"]:
    with st.chat_message(role):
        st.markdown(msg)
