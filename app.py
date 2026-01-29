import streamlit as st
import google.generativeai as genai
import os
from dotenv import load_dotenv

# -----------------------------
# Config
# -----------------------------
load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

model = genai.GenerativeModel("gemini-2.5-flash")

st.set_page_config(
    page_title="AI Travel Assistant ✈️",
    page_icon="🗺️",
    layout="wide"
)

# -----------------------------
# UI Header
# -----------------------------
st.title("✈️ AI Travel Assistant")
st.caption("Plan trips with AI-powered recommendations")

# -----------------------------
# Sidebar Inputs
# -----------------------------
st.sidebar.header("🧳 Travel Preferences")

destination = st.sidebar.text_input("Destination (optional)")
days = st.sidebar.slider("Trip Duration (days)", 1, 14, 5)
budget = st.sidebar.selectbox("Budget", ["Low", "Medium", "Luxury"])
interest = st.sidebar.multiselect(
    "Interests",
    ["Beach", "Mountains", "Food", "History", "Adventure", "Nightlife"]
)

generate_btn = st.sidebar.button("✨ Generate Travel Plan")

# -----------------------------
# Prompt Builder
# -----------------------------
def build_prompt(destination, days, budget, interest):
    return f"""
You are an AI travel assistant.

Create a detailed travel plan with:
1. Destination suggestions (if destination not provided)
2. Hotel recommendations (budget-wise)
3. Local food recommendations
4. Must-visit attractions
5. Day-wise itinerary for {days} days
6. Travel tips (best season, safety, culture, budget)

User Preferences:
- Destination: {destination if destination else "Suggest best options"}
- Duration: {days} days
- Budget: {budget}
- Interests: {", ".join(interest) if interest else "General"}

Respond in a clean, well-structured format.
"""

# -----------------------------
# Generate Travel Plan
# -----------------------------
if generate_btn:
    with st.spinner("✈️ Planning your trip..."):
        prompt = build_prompt(destination, days, budget, interest)
        response = model.generate_content(prompt)
        st.markdown(response.text)

# -----------------------------
# Chatbot Section
# -----------------------------
st.divider()
st.subheader("💬 Travel Chatbot")

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

user_input = st.chat_input("Ask me anything about travel...")

if user_input:
    st.session_state.chat_history.append(("user", user_input))

    chat_prompt = f"""
You are a friendly AI travel assistant.
Answer the user's question concisely and helpfully.

User question: {user_input}
"""
    reply = model.generate_content(chat_prompt)
    st.session_state.chat_history.append(("assistant", reply.text))

# Display chat
for role, msg in st.session_state.chat_history:
    with st.chat_message(role):
        st.markdown(msg)
