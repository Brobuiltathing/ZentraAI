import json
import os
from datetime import datetime
from pathlib import Path

from zentra.config import BASE_FOLDER
from zentra.logger import log
from zentra.memory import memory, USER_ID


def handle_export_chat(data: dict) -> str:
    fmt = (data.get("app") or "markdown").strip().lower()
    filename = (data.get("filename") or "").strip()

    uid = USER_ID
    all_memory = dict(memory)

    if uid in all_memory:
        turns = list(all_memory[uid])
    else:
        for k, v in all_memory.items():
            if v:
                turns = list(v)
                break
        else:
            return "No conversation history to export."

    if not turns:
        return "No conversation history to export."

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    if fmt in ("md", "markdown"):
        if not filename:
            filename = f"zentra_chat_{timestamp}.md"
        content = _format_markdown(turns, timestamp)
    else:
        if not filename:
            filename = f"zentra_chat_{timestamp}.txt"
        content = _format_plaintext(turns, timestamp)

    export_dir = Path(BASE_FOLDER)
    export_dir.mkdir(parents=True, exist_ok=True)
    export_path = export_dir / filename

    try:
        export_path.write_text(content, encoding="utf-8")
        log.info(f"Chat exported to {export_path}")
        return f"Exported {len(turns)} messages to `{export_path}`"
    except Exception as exc:
        return f"Export failed: {exc}"


def _format_markdown(turns: list, timestamp: str) -> str:
    lines = [
        f"# ZENTRA Conversation",
        f"Exported: {datetime.now().strftime('%A %d %B %Y at %H:%M')}",
        f"Messages: {len(turns)}",
        "",
        "---",
        "",
    ]
    for turn in turns:
        role = turn.get("role", "unknown")
        content = turn.get("content", "")
        if role == "user":
            lines.append(f"### You")
            lines.append(content)
        else:
            lines.append(f"### ZENTRA")
            lines.append(content)
        lines.append("")

    return "\n".join(lines)


def _format_plaintext(turns: list, timestamp: str) -> str:
    lines = [
        f"ZENTRA Conversation Export",
        f"Date: {datetime.now().strftime('%A %d %B %Y at %H:%M')}",
        f"Messages: {len(turns)}",
        "=" * 60,
        "",
    ]
    for turn in turns:
        role = "YOU" if turn.get("role") == "user" else "ZENTRA"
        content = turn.get("content", "")
        lines.append(f"[{role}]")
        lines.append(content)
        lines.append("")

    return "\n".join(lines)
