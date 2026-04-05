import re

with open('pyproject.toml', 'r') as f:
    content = f.read()

# Add more ignore rules
ignore_idx = content.find('ignore = [')
if ignore_idx != -1:
    end_idx = content.find(']', ignore_idx)
    ignore_block = content[ignore_idx:end_idx]

    new_ignores = [
        '    "ANN002", # Missing type annotation for *args',
        '    "ANN003", # Missing type annotation for **kwargs',
    ]

    new_ignore_block = ignore_block
    if not new_ignore_block.endswith('\n'):
        new_ignore_block += '\n'

    for item in new_ignores:
        if item.split('"')[1] not in new_ignore_block:
            new_ignore_block += item + '\n'

    content = content[:ignore_idx] + new_ignore_block + content[end_idx:]

with open('pyproject.toml', 'w') as f:
    f.write(content)
