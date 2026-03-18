## 2024-05-24 - Prevent Accidental Data Loss with Dialogs
**Learning:** Destructive actions like clearing conversation history should not be triggered directly by a single click, especially in Streamlit where state updates are immediate.
**Action:** Use Streamlit's `@st.dialog` component to implement a confirmation modal for destructive actions to prevent accidental data loss.

## 2024-05-24 - Accurate Visual Feedback for State
**Learning:** Interactive elements should provide accurate visual feedback on the system's state to prevent invalid actions and confusion.
**Action:** Conditionally disable interactive elements (e.g., `disabled=len(st.session_state.messages) == 0`) when their action is not applicable to the current state.
