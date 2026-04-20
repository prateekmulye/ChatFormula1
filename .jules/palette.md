## 2024-05-15 - Use max_chars for st.chat_input
**Learning:** Using post-submission Python validation for chat input length creates a frustrating UX, as users only find out their message is too long after typing it all out.
**Action:** Use Streamlit's built-in `max_chars` parameter in `st.chat_input` to provide real-time visual feedback and enforce client-side limits.
