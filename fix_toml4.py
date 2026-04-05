with open('pyproject.toml', 'r') as f:
    content = f.read()

# Just literally find the second tool.ruff block and replace it
import re

content = content.replace('''[tool.ruff]
line-length = 88
target-version = "py311"
select = [''', '''[tool.ruff.lint]
select = [''')

content = content.replace('''[tool.ruff.per-file-ignores]''', '''[tool.ruff.lint.per-file-ignores]''')

content = re.sub(r'\s*"ANN10[12]",.*?\n', '\n', content)

with open('pyproject.toml', 'w') as f:
    f.write(content)
