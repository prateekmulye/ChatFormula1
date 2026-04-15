## 2026-04-15 - Add real-time character limit feedback
**Learning:** When using Streamlit's st.chat_input in UI components, utilize the built-in max_chars parameter for real-time visual feedback and client-side character limits, rather than relying solely on post-submission Python-side validation to improve UX.
**Action:** Use max_chars=N in st.chat_input whenever there is a length limit.
