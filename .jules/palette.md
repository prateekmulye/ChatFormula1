## 2024-05-24 - Streamlit Chat Input Validation UX
**Learning:** Native client-side validation using `max_chars` on Streamlit's `st.chat_input` component provides immediate visual feedback (a character counter) and blocks submission, offering a vastly superior UX compared to accepting long input and rejecting it via a post-submission backend warning.
**Action:** When implementing constraints on user input in Streamlit applications, prioritize native component parameters (like `max_chars`) over custom Python-side validation checks whenever the API supports it.
