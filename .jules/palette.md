## 2024-04-02 - Add Confirmation Dialog for Destructive Actions
**Learning:** Users can easily lose context if they accidentally click the clear conversation button without a confirmation dialog. It's crucial to prevent accidental data loss in chat interfaces.
**Action:** Add an `@st.dialog` confirmation step for any action that deletes history or user data.