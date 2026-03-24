## 2024-03-24 - Prevent Accidental Data Loss
**Learning:** Destructive UI actions (like clearing conversation history) need confirmation modals to prevent accidental data loss. Furthermore, buttons for actions that are currently invalid (e.g., clearing an empty conversation) should be disabled to provide accurate visual feedback and prevent unnecessary state updates.
**Action:** Use `st.button(..., disabled=True)` when actions are invalid, and use Streamlit's `@st.dialog` to implement confirmation modals for destructive actions.
