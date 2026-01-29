import streamlit as st

def init_memory():
    """
    Initialize application-wide memory in Streamlit session_state.
    This memory persists across user interactions in the same session.
    """
    if "memory" not in st.session_state:
        st.session_state.memory = {
            "chat_history": [],
            "last_trip": None,
            "generated_trips": [],
            "preferences": {}
        }
