import asyncio
import json
import re
import time
import threading
from datetime import datetime, timedelta
from collections import defaultdict

from logger import log
from ollama import ollama_raw_sync


_scheduled_tasks: dict[str, dict] = {}
_task_counter = 0
_task_results: list[dict] = []
_results_lock = threading.Lock()


def _parse_schedule_sync(user_text: str) -> dict | None:
    now_str = datetime.now().strftime("%A %d %B %Y %H:%M")
    raw = ollama_raw_sync(
        f"Today is {now_str}. Parse this scheduling request.\n"
        "Reply ONLY with raw JSON, no markdown:\n"
        '{"type": "once", "datetime": "YYYY-MM-DDTHH:MM:SS", '
        '"message": "what to remind/do", "action": "chat"}\n'
        "type can be: once, hourly, daily, weekly\n"
        "For recurring, 'datetime' is the first occurrence.\n"
        "action can be: chat (just remind), shell (run command), gmail_summary, calendar_today\n"
        "Handle relative times like 'in 30 minutes', 'at 5pm', 'every monday at 9am'.",
        user_text,
        max_tokens=200,
    )
    try:
        cleaned = re.sub(r"```(?:json)?\n?", "", raw).replace("```", "").strip()
        return json.loads(cleaned)
    except Exception:
        log.warning(f"Could not parse schedule: {raw[:200]}")
        return None


def handle_schedule_add(data: dict) -> str:
    global _task_counter
    user_text = (data.get("reply") or "").strip()
    if not user_text:
        return "schedule_add: describe what and when."

    parsed = _parse_schedule_sync(user_text)
    if not parsed:
        return "Could not understand the schedule. Try: 'remind me at 5pm to push my code'"

    _task_counter += 1
    task_id = f"task_{_task_counter}"

    task = {
        "id": task_id,
        "type": parsed.get("type", "once"),
        "datetime": parsed.get("datetime", ""),
        "message": parsed.get("message", user_text),
        "action": parsed.get("action", "chat"),
        "created": datetime.now().isoformat(),
        "active": True,
        "last_run": None,
    }

    _scheduled_tasks[task_id] = task

    try:
        dt = datetime.fromisoformat(task["datetime"])
        time_str = dt.strftime("%A %d %B at %I:%M %p")
    except Exception:
        time_str = task["datetime"]

    recur = f" (repeats {task['type']})" if task["type"] != "once" else ""
    return (
        f"Scheduled: **{task['message']}**\n"
        f"When: {time_str}{recur}\n"
        f"ID: {task_id}"
    )


def handle_schedule_list(data: dict) -> str:
    active = {k: v for k, v in _scheduled_tasks.items() if v.get("active")}
    if not active:
        return "No scheduled tasks."

    lines = [f"**Scheduled Tasks** ({len(active)})\n"]
    for tid, task in active.items():
        try:
            dt = datetime.fromisoformat(task["datetime"])
            time_str = dt.strftime("%d %b %H:%M")
        except Exception:
            time_str = task["datetime"]

        recur = f" [{task['type']}]" if task["type"] != "once" else ""
        lines.append(f"  **{tid}**: {task['message']}{recur} @ {time_str}")
    return "\n".join(lines)


def handle_schedule_cancel(data: dict) -> str:
    task_id = (data.get("app") or data.get("reply") or "").strip()
    if not task_id:
        return "schedule_cancel: provide the task ID."

    if task_id in _scheduled_tasks:
        _scheduled_tasks[task_id]["active"] = False
        return f"Cancelled {task_id}: {_scheduled_tasks[task_id]['message']}"

    return f"Task '{task_id}' not found."


def get_due_tasks() -> list[dict]:
    now = datetime.now()
    due = []

    for tid, task in list(_scheduled_tasks.items()):
        if not task.get("active"):
            continue

        try:
            target = datetime.fromisoformat(task["datetime"])
        except Exception:
            continue

        if now >= target:
            due.append(task)

            if task["type"] == "once":
                task["active"] = False
            elif task["type"] == "hourly":
                task["datetime"] = (target + timedelta(hours=1)).isoformat()
            elif task["type"] == "daily":
                task["datetime"] = (target + timedelta(days=1)).isoformat()
            elif task["type"] == "weekly":
                task["datetime"] = (target + timedelta(weeks=1)).isoformat()

            task["last_run"] = now.isoformat()

    return due


def get_task_results() -> list[dict]:
    with _results_lock:
        results = list(_task_results)
        _task_results.clear()
    return results


def add_task_result(task: dict, result: str):
    with _results_lock:
        _task_results.append({
            "task": task,
            "result": result,
            "time": datetime.now().isoformat(),
        })
