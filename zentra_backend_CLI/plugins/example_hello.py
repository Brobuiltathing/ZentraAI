PLUGIN_NAME = "hello"
PLUGIN_DESCRIPTION = "Example plugin that greets the user"


def handle(data: dict) -> str:
    name = data.get("reply", "").strip() or "world"
    return f"Hello, {name}! This is a ZENTRA plugin."
