## 2024-05-24 - Confirmation dialogs for destructive actions
**Learning:** Streamlit's `@st.dialog` decorator is the preferred approach for implementing confirmation modals for destructive UI actions (such as clearing conversation history) to prevent accidental data loss. Conditionally disabling elements based on state (like a clear button when history is empty) provides accurate visual feedback.
**Action:** Use `@st.dialog` for actions that wipe data, and always disable buttons when their action is invalid.
