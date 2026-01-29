import streamlit as st


def init_memory():
    if "memory" not in st.session_state:
        st.session_state.memory = {
            "chat_history": [],
            "last_destination": None,
            "preferences": {}
        }
