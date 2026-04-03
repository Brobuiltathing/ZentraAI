import json
import os
from collections import defaultdict, deque

from config import MEMORY_DEPTH, MEMORY_FILE
from logger import log


memory: dict = defaultdict(lambda: deque(maxlen=MEMORY_DEPTH * 2))

USER_ID = 0


def load_memory() -> None:
    if not os.path.exists(MEMORY_FILE):
        log.info("No memory file found — starting fresh.")
        return
    try:
        with open(MEMORY_FILE, "r", encoding="utf-8") as fh:
            raw: dict = json.load(fh)
        for uid_str, turns in raw.items():
            uid = int(uid_str)
            q: deque = deque(maxlen=MEMORY_DEPTH * 2)
            for turn in turns:
                q.append(turn)
            memory[uid] = q
        log.info(f"Memory loaded — {len(raw)} user(s) restored.")
    except Exception as exc:
        log.warning(f"Could not load memory: {exc} — starting fresh.")


def persist_memory() -> None:
    try:
        serialisable = {
            str(uid): list(turns)
            for uid, turns in memory.items()
            if turns
        }
        with open(MEMORY_FILE, "w", encoding="utf-8") as fh:
            json.dump(serialisable, fh, indent=2, ensure_ascii=False)
    except Exception as exc:
        log.warning(f"Could not persist memory: {exc}")


def build_prompt(new_message: str) -> str:
    history = memory[USER_ID]
    if not history:
        return new_message
    lines = ["CONVERSATION HISTORY (oldest first):"]
    for turn in history:
        role = "User" if turn["role"] == "user" else "ZENTRA"
        lines.append(f"  {role}: {turn['content']}")
    lines.append("")
    lines.append(f"NEW USER MESSAGE: {new_message}")
    return "\n".join(lines)


def save_to_memory(user_msg: str, bot_reply_summary: str) -> None:
    memory[USER_ID].append({"role": "user",      "content": user_msg})
    memory[USER_ID].append({"role": "assistant",  "content": bot_reply_summary})
    persist_memory()


def clear_memory() -> None:
    memory[USER_ID].clear()
    persist_memory()
