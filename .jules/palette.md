## 2026-03-02 - Streamlit st.chat_input character limit UX
**Learning:** Relying solely on server-side validation for character limits in chat interfaces leads to a poor user experience, as users can type indefinitely before receiving an error.
**Action:** When using Streamlit UI components like `st.chat_input`, always utilize built-in parameters like `max_chars` to provide real-time visual feedback and client-side limits before submission.
