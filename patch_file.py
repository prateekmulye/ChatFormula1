import re

with open("src/ui/components.py", "r") as f:
    code = f.read()

code = re.sub(
    r"""def render_settings_panel\(\) -> None:""",
    r"""@st.dialog("⚠️ Clear Conversation")
def confirm_clear_conversation() -> None:
    \"\"\"Render a confirmation dialog for clearing the conversation.\"\"\"
    st.write("Are you sure you want to clear the conversation history?")
    st.write("This action cannot be undone.")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("Cancel", use_container_width=True):
            st.rerun()
    with col2:
        if st.button("Clear", type="primary", use_container_width=True):
            st.session_state.messages = []
            st.session_state.agent_state = None
            st.session_state.feedback = {}
            import structlog
            logger = structlog.get_logger(__name__)
            logger.info(
                "conversation_cleared",
                session_id=st.session_state.get("session_id", "unknown"),
            )
            st.rerun()


def render_settings_panel() -> None:""",
    code
)

code = re.sub(
    r"""        with col1:
            if st.button\(
                "🗑️ Clear Conversation",
                use_container_width=True,
                key="settings_clear",
                help="Delete all messages in the current conversation",
            \):
                st.session_state.messages = \[\]
                st.session_state.agent_state = None
                st.session_state.feedback = \{\}
                logger.info\(
                    "conversation_cleared",
                    session_id=st.session_state.get\("session_id", "unknown"\),
                \)
                st.rerun\(\)""",
    r"""        with col1:
            if st.button(
                "🗑️ Clear Conversation",
                use_container_width=True,
                key="settings_clear",
                help="Delete all messages in the current conversation",
                disabled=len(st.session_state.messages) == 0,
            ):
                confirm_clear_conversation()""",
    code
)

with open("src/ui/components.py", "w") as f:
    f.write(code)

with open("src/ui/app.py", "r") as f:
    code = f.read()

code = re.sub(
    r"""        # Clear conversation button
        if st.button\("🗑️ Clear Conversation", use_container_width=True\):
            st.session_state.messages = \[\]
            st.session_state.agent_state = None
            st.session_state.feedback = \{\}
            logger.info\("conversation_cleared", session_id=st.session_state.session_id\)
            st.rerun\(\)""",
    r"""        # Clear conversation button
        if st.button(
            "🗑️ Clear Conversation",
            use_container_width=True,
            disabled=len(st.session_state.messages) == 0,
        ):
            from src.ui.components import confirm_clear_conversation

            confirm_clear_conversation()""",
    code
)

with open("src/ui/app.py", "w") as f:
    f.write(code)


with open("tests/test_functionality_preservation.py", "r") as f:
    code = f.read()

code = re.sub(
    r"""        # Mock button to simulate clear click
        mock_st.button.side_effect = \[True, False\]  # First button \(clear\) clicked

        # Call function
        render_settings_panel\(\)

        # Verify state was reset
        assert mock_st.session_state\["messages"\] == \[\]
        assert mock_st.session_state\["agent_state"\] is None
        assert mock_st.session_state\["feedback"\] == \{\}""",
    r"""        class MockSessionState(dict):
            def __getattr__(self, attr):
                return self.get(attr)
            def __setattr__(self, attr, value):
                self[attr] = value

        mock_st.session_state = MockSessionState(mock_st.session_state)

        mock_st.columns.return_value = (unittest.mock.MagicMock(), unittest.mock.MagicMock())

        # Mock button to simulate clear click
        mock_st.button.side_effect = [True, False]  # First button (clear) clicked

        # Call function
        with unittest.mock.patch("src.ui.components.confirm_clear_conversation") as mock_confirm:
            render_settings_panel()
            mock_confirm.assert_called_once()""",
    code
)

with open("tests/test_functionality_preservation.py", "w") as f:
    f.write(code)
