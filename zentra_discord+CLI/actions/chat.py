def handle_chat(data: dict) -> str:
    return data.get("reply") or "I'm not sure how to respond to that."
