## 2024-03-20 - Adding destructive action confirmation
**Learning:** Destructive actions like clearing the conversation should have a confirmation dialog to prevent accidental data loss. This improves user experience and prevents frustration.
**Action:** Use Streamlit's `@st.dialog` feature to create a confirmation modal before executing destructive actions.
