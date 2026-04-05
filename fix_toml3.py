with open('pyproject.toml', 'r') as f:
    content = f.read()

import re

# We just want to replace the deprecated tool.ruff settings with tool.ruff.lint, and remove ANN101/ANN102
# Currently pyproject.toml has this for tool.ruff:
# [tool.ruff]
# line-length = 88
# target-version = ['py311', 'py312', 'py313']
# include = '\.pyi?$'
# extend-exclude = ''' ... '''
#
# [tool.ruff]
# line-length = 88
# target-version = "py311"
# select = [...]
# ignore = [...]
#
# [tool.ruff.per-file-ignores]
# ...

# Let's cleanly replace the second [tool.ruff] and [tool.ruff.per-file-ignores]
# wait, looking at git restore, it has:
# [tool.ruff]
# line-length = 88
# target-version = ['py311', 'py312', 'py313']
# ...

content = content.replace('''[tool.ruff]
line-length = 88
target-version = "py311"

[tool.ruff.lint]
select = [''', '''[tool.ruff.lint]
select = [''')

content = content.replace('''[tool.ruff]
line-length = 88
target-version = "py311"
select = [''', '''[tool.ruff.lint]
select = [''')

content = content.replace('''[tool.ruff.per-file-ignores]''', '''[tool.ruff.lint.per-file-ignores]''')

content = re.sub(r'\s*"ANN10[12]",.*?\n', '\n', content)

with open('pyproject.toml', 'w') as f:
    f.write(content)
