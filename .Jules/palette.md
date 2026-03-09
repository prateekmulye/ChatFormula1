## 2024-03-09 - Streamlit `@st.dialog` Component Unpacking
**Learning:** Using `st.columns(2)` directly within a Streamlit `@st.dialog` component and immediately unpacking it as `col1, col2 = st.columns(2)` can sometimes result in `ValueError: not enough values to unpack (expected 2, got 0)` due to context rendering timing quirks inside dialog closures.
**Action:** Always assign the columns to a list first (`cols = st.columns(2)`) and access them via index (`with cols[0]:`) when working inside Streamlit dialogs to ensure stable rendering.
