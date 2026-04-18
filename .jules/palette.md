## 2025-04-18 - Improve Streamlit Chat Input UX
**Learning:** Adding client-side length constraints to `st.chat_input` via `max_chars` provides immediate user feedback and improves overall input UX before backend validation.
**Action:** When using `st.chat_input`, always utilize the built-in `max_chars` parameter for real-time visual feedback, rather than relying exclusively on post-submission backend validation.
