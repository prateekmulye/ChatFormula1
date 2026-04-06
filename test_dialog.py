import streamlit as st
import structlog
logger = structlog.get_logger(__name__)

if "messages" not in st.session_state:
    st.session_state.messages = ["hello"]

@st.dialog("Clear Conversation")
def show_clear_confirmation() -> None:
    st.warning("Are you sure you want to delete all messages? This action cannot be undone.")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Cancel", use_container_width=True):
            st.rerun()
    with col2:
        if st.button("Yes, Clear", type="primary", use_container_width=True):
            st.session_state.messages = []
            st.rerun()

if st.button("🗑️ Clear Conversation"):
    show_clear_confirmation()

st.write("Messages: ", st.session_state.messages)
