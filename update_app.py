with open('src/ui/app.py', 'r') as f:
    lines = f.readlines()

import_idx = -1
target_start = -1
target_end = -1

for i, line in enumerate(lines):
    if line.startswith("from src.ui.components import ("):
        import_idx = i
    if "if st.button(\"🗑️ Clear Conversation\", use_container_width=True):" in line:
        target_start = i
        # find the end
        for j in range(i, len(lines)):
            if "st.rerun()" in lines[j]:
                target_end = j
                break

if import_idx != -1:
    lines.insert(import_idx + 1, "    confirm_clear_conversation,\n")

if target_start != -1 and target_end != -1:
    new_lines = [
        '        # Clear conversation button\n',
        '        has_messages = len(st.session_state.messages) > 0\n',
        '        if st.button(\n',
        '            "🗑️ Clear Conversation", \n',
        '            use_container_width=True,\n',
        '            disabled=not has_messages,\n',
        '            help="Delete all messages in the current conversation" if has_messages else "No messages to clear"\n',
        '        ):\n',
        '            confirm_clear_conversation()\n'
    ]
    lines = lines[:target_start - 1] + new_lines + lines[target_end + 1:]

with open('src/ui/app.py', 'w') as f:
    f.writelines(lines)
