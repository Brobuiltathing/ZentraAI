import asyncio

from logger import log

from actions.files import (
    handle_create_file, handle_run_file, handle_read_file,
    handle_edit_file, handle_scaffold_project,
)
from actions.apps import handle_open_app, handle_close_app, handle_vscode_open
from actions.git import handle_github_push
from actions.system import handle_system_stats, handle_shutdown_pc
from actions.screen import handle_screen_action_sync
from actions.gmail import handle_gmail_summary, handle_gmail_send
from actions.calendar import (
    handle_calendar_today, handle_calendar_week, handle_calendar_add,
    handle_calendar_delete, handle_calendar_search,
)
from actions.chat import handle_chat


async def dispatch_action(data: dict) -> tuple[str, str]:
    action = data.get("action", "chat").strip().lower()
    reply  = data.get("reply", "")

    log.info(f"Dispatching action: {action}")

    def combine(status: str) -> str:
        return f"{reply}\n\n{status}" if reply else status

    file_content = ""

    if action == "create_file":
        result = combine(handle_create_file(data))
    elif action == "run_file":
        result = combine(handle_run_file(data))
    elif action == "read_file":
        status, file_content = handle_read_file(data)
        result = combine(status)
    elif action == "edit_file":
        result = combine(handle_edit_file(data))
    elif action == "scaffold_project":
        result = combine(handle_scaffold_project(data))
    elif action == "open_app":
        result = combine(handle_open_app(data))
    elif action == "close_app":
        result = combine(handle_close_app(data))
    elif action == "vscode_open":
        result = combine(handle_vscode_open(data))
    elif action == "github_push":
        result = combine(handle_github_push(data))
    elif action == "system_stats":
        result = combine(await asyncio.to_thread(handle_system_stats, data))
    elif action == "screen_action":
        result = combine(await asyncio.to_thread(handle_screen_action_sync, data))
    elif action == "gmail_summary":
        result = combine(await handle_gmail_summary(data))
    elif action == "gmail_send":
        result = combine(await handle_gmail_send(data))
    elif action == "calendar_today":
        result = combine(await handle_calendar_today(data))
    elif action == "calendar_week":
        result = combine(await handle_calendar_week(data))
    elif action == "calendar_add":
        result = combine(await handle_calendar_add(data))
    elif action == "calendar_delete":
        result = combine(await handle_calendar_delete(data))
    elif action == "calendar_search":
        result = combine(await handle_calendar_search(data))
    elif action == "shutdown_pc":
        result = combine(handle_shutdown_pc(data))
    elif action == "chat":
        result = handle_chat(data)
    else:
        log.warning(f"Unknown action: {action}")
        result = reply or f"Unknown action `{action}`."

    return result, file_content
