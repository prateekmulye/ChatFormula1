## 2024-03-01 - Add confirmation dialogs for destructive actions
**Learning:** Destructive actions like clearing the conversation history or starting a new session can easily lead to accidental data loss, frustrating users.
**Action:** Always use Streamlit's `@st.dialog` decorator to wrap destructive actions in a confirmation modal that requires explicit user consent before proceeding.
