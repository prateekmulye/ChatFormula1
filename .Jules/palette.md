## 2026-03-12 - Context-Aware Disabled States and Confirmation Modals
**Learning:** Preventing invalid actions via visually disabled buttons provides better UX than allowing the action and doing nothing. Similarly, using @st.dialog for confirmation modals before destructive actions (like clearing conversation history) is crucial for preventing accidental data loss.
**Action:** When implementing interactive elements that depend on specific system states (e.g., non-empty history), explicitly add a disabled state. Always use confirmation dialogs for destructive actions.
