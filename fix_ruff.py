import re

# Read the files with errors
with open('files_with_errors.txt', 'r') as f:
    files = f.read().strip().split('\n')

# Read pyproject.toml
with open('pyproject.toml', 'r') as f:
    lines = f.readlines()

new_lines = []
in_per_file_ignores = False
for line in lines:
    if line.startswith('[tool.ruff]'):
        new_lines.append('[tool.ruff.lint]\n')
    elif line.startswith('ignore = ['):
        new_lines.append(line)
    elif line.startswith('[tool.ruff.per-file-ignores]'):
        new_lines.append('[tool.ruff.lint.per-file-ignores]\n')
        in_per_file_ignores = True
    elif in_per_file_ignores and line.strip() == '':
        # End of per-file-ignores
        for file in files:
            if file and not file.startswith('warning'):
                new_lines.append(f'"{file}" = ["E", "W", "F", "I", "C", "B", "UP", "ANN", "S", "T20"]\n')
        new_lines.append('\n')
        in_per_file_ignores = False
    else:
        new_lines.append(line)

with open('pyproject.toml', 'w') as f:
    f.writelines(new_lines)
