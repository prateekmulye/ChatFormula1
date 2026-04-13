## 2024-05-24 - Streamlit Input Character Limits
**Learning:** Utilizing Streamlit's built-in `max_chars` parameter in inputs (like `st.chat_input`) provides real-time visual feedback and prevents user error on the client side, significantly improving UX compared to post-submission Python-side validation.
**Action:** Always check if a Streamlit input component supports `max_chars` when a character limit constraint exists in the backend validation.
