import re

with open('pyproject.toml', 'r') as f:
    content = f.read()

# Fix the duplicate [tool.ruff.lint] headers
lines = content.split('\n')
new_lines = []
in_ruff = False
in_ruff_lint = False

for line in lines:
    if line == '[tool.ruff]':
        if not in_ruff:
            new_lines.append(line)
            in_ruff = True
    elif line == '[tool.ruff.lint]':
        if not in_ruff_lint:
            new_lines.append(line)
            in_ruff_lint = True
    elif line == 'line-length = 88' and in_ruff:
        if new_lines[-1] != 'line-length = 88':
            new_lines.append(line)
    elif line == 'target-version = "py311"' and in_ruff:
        if new_lines[-1] != 'target-version = "py311"':
            new_lines.append(line)
    else:
        new_lines.append(line)

content = '\n'.join(new_lines)

# One more pass to fix [tool.ruff.lint] properly
content = re.sub(r'\[tool\.ruff\]\nline-length = 88\ntarget-version = "py311"\n\n\[tool\.ruff\.lint\]', r'[tool.ruff]\nline-length = 88\ntarget-version = "py311"\n\n[tool.ruff.lint]', content)

with open('pyproject.toml', 'w') as f:
    f.write(content)
