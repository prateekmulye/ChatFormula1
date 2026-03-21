## 2024-03-20 - Confirm Destructive Actions
**Learning:** Streamlit's native `@st.dialog` decorator is an effective, accessible way to implement confirmation modals for destructive UI actions (like clearing conversation history) to prevent accidental data loss. It requires no custom CSS and handles focus natively.
**Action:** Use `@st.dialog` for any action that permanently deletes user data or state, and always combine it with conditional `disabled` states for the trigger buttons when the action is invalid (e.g. `disabled=len(st.session_state.messages) == 0`).
