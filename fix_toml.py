import re

with open('pyproject.toml', 'r') as f:
    content = f.read()

# Replace deprecated ruff settings with tool.ruff.lint
content = re.sub(r'\[tool\.ruff\]\nline-length = 88\ntarget-version = "py311"\nselect = \[', r'[tool.ruff]\nline-length = 88\ntarget-version = "py311"\n\n[tool.ruff.lint]\nselect = [', content)
content = re.sub(r'\[tool\.ruff\.per-file-ignores\]', r'[tool.ruff.lint.per-file-ignores]', content)

# Remove ANN101 and ANN102 from ignore list
content = re.sub(r'\s*"ANN10[12]",.*?\n', '\n', content)

with open('pyproject.toml', 'w') as f:
    f.write(content)
