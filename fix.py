with open("src/api/routes/chat.py", "r") as f:
    content = f.read()

content = content.replace("async def event_generator() -> AsyncGenerator[str, None]:", "async def event_generator():  # noqa: ANN202")

with open("src/api/routes/chat.py", "w") as f:
    f.write(content)
