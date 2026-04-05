with open('src/agent/graph.py', 'r') as f:
    content = f.read()

import re
if 'import asyncio' not in content:
    content = re.sub(r'import json\n', 'import json\nimport asyncio\n', content)

with open('src/agent/graph.py', 'w') as f:
    f.write(content)
