import re

with open("src/ui/app.py", "r") as f:
    content = f.read()

# Add import
import_pattern = r'''from src\.ui\.components import \('''
replace_import = r'''from src.ui.components import (
    confirm_clear_conversation,'''
content = re.sub(import_pattern, replace_import, content)

# Update sidebar Clear Conversation button
search_sidebar_clear = r'''        # Clear conversation button\s+if st\.button\("🗑️ Clear Conversation", use_container_width=True\):\s+st\.session_state\.messages = \[\]\s+st\.session_state\.agent_state = None\s+st\.session_state\.feedback = \{\}\s+logger\.info\("conversation_cleared", session_id=st\.session_state\.session_id\)\s+st\.rerun\(\)'''

replace_sidebar_clear = r'''        # Clear conversation button
        has_messages = len(st.session_state.messages) > 0
        if st.button(
            "🗑️ Clear Conversation",
            use_container_width=True,
            disabled=not has_messages,
            help="Delete all messages in the current conversation" if has_messages else "No messages to clear"
        ):
            confirm_clear_conversation()'''

content = re.sub(search_sidebar_clear, replace_sidebar_clear, content)

with open("src/ui/app.py", "w") as f:
    f.write(content)
