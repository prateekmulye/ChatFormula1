## 2024-04-06 - Confirmation Dialogs for Destructive Actions
**Learning:** Single-click destructive actions (like clearing the chat history) easily lead to accidental data loss in a reactive environment like Streamlit where buttons might trigger unexpectedly or due to accidental misclicks.
**Action:** Always wrap destructive UI actions with a confirmation step (such as `st.dialog`) to give users a chance to opt out.
