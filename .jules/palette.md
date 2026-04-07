## 2024-05-24 - Real-time Character Limits in Chat Inputs
**Learning:** Users often get frustrated when they spend time typing a long message only to be told it's too long *after* submitting. Streamlit's `st.chat_input` handles this poorly by default if you rely on post-submission validation.
**Action:** Always use the `max_chars` parameter in `st.chat_input` to provide real-time visual feedback and prevent over-typing, rather than relying solely on post-submission validation errors.
