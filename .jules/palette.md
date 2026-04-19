
## 2024-04-19 - Use max_chars in Streamlit chat_input
**Learning:** Post-submission validation for character limits in chat inputs leads to a frustrating UX because users only find out they exceeded the limit after typing and submitting.
**Action:** When using Streamlit's `st.chat_input` in UI components, utilize the built-in `max_chars` parameter for real-time visual feedback and client-side character limits, rather than relying solely on post-submission Python-side validation.
