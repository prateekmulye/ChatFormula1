## 2024-03-29 - Use modals for destructive actions
**Learning:** Destructive actions like clearing the conversation history or starting a new session can lead to accidental data loss if triggered by a single click. Streamlit's `@st.dialog` decorator is an effective and native way to implement confirmation modals to prevent this.
**Action:** Always wrap destructive UI actions in a confirmation modal using `@st.dialog` to ensure users intentionally confirm their actions before execution.
