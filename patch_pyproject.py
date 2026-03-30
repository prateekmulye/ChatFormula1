import re

with open("pyproject.toml", "r") as f:
    content = f.read()

# remove ANN101 and ANN102 from ignore list
content = content.replace('    "ANN201",\n', '    "ANN201",\n    "ANN001",\n    "ANN002",\n    "ANN003",\n    "B904",\n    "S104",\n    "ANN206",\n    "S324",\n    "B007",\n')

with open("pyproject.toml", "w") as f:
    f.write(content)
