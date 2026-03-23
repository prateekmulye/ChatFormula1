import os
content = ""
with open("tests/test_integration_api.py", "r") as f:
    content = f.read()

# Before importing app, we need to mock env vars
mock_vars = """
import os
os.environ["OPENAI_API_KEY"] = "dummy"
os.environ["PINECONE_API_KEY"] = "dummy"
os.environ["TAVILY_API_KEY"] = "dummy"
os.environ["ENVIRONMENT"] = "development"

"""
if "os.environ" not in content:
    content = content.replace("from src.api.main import app", mock_vars + "from src.api.main import app")
    with open("tests/test_integration_api.py", "w") as f:
        f.write(content)
