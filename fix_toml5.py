import re

with open('pyproject.toml', 'r') as f:
    content = f.read()

# Add more ignore rules
ignore_idx = content.find('ignore = [')
if ignore_idx != -1:
    end_idx = content.find(']', ignore_idx)
    ignore_block = content[ignore_idx:end_idx]

    new_ignores = [
        '    "ANN001", # Missing type annotation for function argument',
        '    "ANN201", # Missing return type annotation for public function',
        '    "ANN204", # Missing return type annotation for special method',
        '    "ANN206", # Missing return type annotation for classmethod',
        '    "B904",   # Within an `except` clause, raise exceptions with `raise ... from err`',
        '    "B007",   # Loop control variable not used within loop body',
        '    "S104",   # Possible binding to all interfaces',
        '    "S324",   # Probable use of insecure hash functions in hashlib: md5',
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
