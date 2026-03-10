## 2024-05-15 - Streamlit duplicate buttons\n**Learning:** When automating Streamlit UI interactions via Playwright, component locators (like `page.locator('button')`) may resolve to multiple duplicate DOM elements due to Streamlit's internal rendering. Always append `.first` or use `.nth()` alongside text filters to prevent strict mode violations during `.click()` actions.\n**Action:** Always append `.first` or use `.nth()` alongside text filters.

## 2024-05-15 - Conditionally disable interactive elements
**Learning:** A preferred micro-UX pattern in Streamlit applications is conditionally disabling interactive elements (like buttons) when their corresponding action is invalid based on the current system state, such as checking `len(st.session_state.messages) == 0`.
**Action:** Always provide accurate visual feedback on system state and prevent invalid user actions by conditionally disabling UI elements and providing contextual help messages.
