# Palette's Journal

## UX/Accessibility Learnings

## 2026-03-07 - Conditional Disabling and Modals for Destructive Actions
**Learning:** Destructive actions like clearing chat history should have an explicit confirmation step (like `@st.dialog` in Streamlit) to avoid accidental data loss. Furthermore, buttons for actions that cannot be performed in the current state (like clearing an already empty chat) should be conditionally disabled (`disabled=len(st.session_state.messages) == 0`) to provide immediate visual feedback on the system's state and prevent user confusion or invalid actions.
**Action:** Always implement a confirmation dialog for destructive actions. Always evaluate if a button can be disabled based on the current state and disable it proactively instead of failing silently or doing a no-op when clicked.
