import re

with open("tests/test_functionality_preservation.py", "r") as f:
    code = f.read()

code = re.sub(
    r"""from unittest.mock import AsyncMock, MagicMock, patch""",
    r"""import unittest.mock\nfrom unittest.mock import AsyncMock, MagicMock, patch""",
    code
)

with open("tests/test_functionality_preservation.py", "w") as f:
    f.write(code)
