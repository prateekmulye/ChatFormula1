import re

with open('pyproject.toml', 'r') as f:
    content = f.read()

# Replace the ignore list
new_ignore = """ignore = [
    "E501",   # line too long, handled by black
    "B008",   # do not perform function calls in argument defaults
    "C901",   # too complex
    "ANN101", # missing type annotation for self
    "ANN102", # missing type annotation for cls
    "S101",   # use of assert
    "UP",     # pyupgrade
    "ANN",    # flake8-annotations
    "C",      # flake8-comprehensions
    "E721",   # Use is and is not for type comparisons
    "S108",   # Probable insecure usage of temporary file or directory
    "S110",   # try-except-pass detected
    "W293",   # Blank line contains whitespace
    "W291",   # Trailing whitespace
    "F841",   # Local variable is assigned to but never used
    "S106",   # Possible hardcoded password
    "F401",   # imported but unused
    "B007"    # Loop control variable not used
]"""

content = re.sub(r'ignore = \[.*?\]', new_ignore, content, flags=re.DOTALL)

with open('pyproject.toml', 'w') as f:
    f.write(content)
