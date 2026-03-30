import sys
import os

with open("tests/conftest.py", "r") as f:
    content = f.read()

prefix = """
import os
import sys
from unittest.mock import MagicMock

# Set dummy environment variables to pass validation
os.environ["ENVIRONMENT"] = "development"
os.environ.setdefault("OPENAI_API_KEY", "dummy")
os.environ.setdefault("PINECONE_API_KEY", "dummy")
os.environ.setdefault("TAVILY_API_KEY", "dummy")

"""

if "import os" in content and not "os.environ[\"ENVIRONMENT\"]" in content:
    content = prefix + content
    with open("tests/conftest.py", "w") as f:
        f.write(content)
