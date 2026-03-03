import re

with open("src/ui/components.py", "r") as f:
    content = f.read()

search_pattern = r'''        with col1:
            if st\.button\(
                "🗑️ Clear Conversation",
                use_container_width=True,
                key="settings_clear",
                help="Delete all messages in the current conversation",
            \):
                st\.session_state\.messages = \[\]
                st\.session_state\.agent_state = None
                st\.session_state\.feedback = \{\}
                logger\.info\(
                    "conversation_cleared",
                    session_id=st\.session_state\.get\("session_id", "unknown"\),
                \)
                st\.rerun\(\)'''

replace_pattern = r'''        with col1:
            has_messages = len(st.session_state.messages) > 0
            if st.button(
                "🗑️ Clear Conversation",
                use_container_width=True,
                key="settings_clear",
                disabled=not has_messages,
                help="Delete all messages in the current conversation" if has_messages else "No messages to clear",
            ):
                confirm_clear_conversation()'''

new_content = re.sub(search_pattern, replace_pattern, content)

with open("src/ui/components.py", "w") as f:
    f.write(new_content)
