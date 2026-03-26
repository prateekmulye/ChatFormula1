## 2024-03-26 - Add Confirmation Dialog to Destructive Actions
**Learning:** Destructive actions in Streamlit applications (like clearing conversation history) need explicit `@st.dialog` confirmations because state is easily lost and accidental clicks are common on smaller touch targets.
**Action:** Always wrap destructive actions in an `st.dialog` modal with clear "Cancel" and "Confirm" buttons, and disable the trigger button when the action is invalid (e.g. empty state).
