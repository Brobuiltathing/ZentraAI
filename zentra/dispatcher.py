import asyncio

from zentra.logger import log

from zentra.actions.files import (
    handle_create_file, handle_run_file, handle_read_file,
    handle_edit_file, handle_scaffold_project,
)
from zentra.actions.apps import handle_open_app, handle_close_app, handle_vscode_open
from zentra.actions.git import handle_github_push
from zentra.actions.system import handle_system_stats, handle_shutdown_pc
from zentra.actions.screen import handle_screen_action_sync
from zentra.actions.gmail import handle_gmail_summary, handle_gmail_send
from zentra.actions.calendar import (
    handle_calendar_today, handle_calendar_week, handle_calendar_add,
    handle_calendar_delete, handle_calendar_search,
)
from zentra.actions.chat import handle_chat
from zentra.actions.shell import handle_shell
from zentra.actions.clipboard import handle_clipboard_read, handle_clipboard_analyze, handle_clipboard_fix
from zentra.actions.context import handle_context_snapshot
from zentra.actions.workflow import (
    handle_workflow_run, handle_workflow_save, handle_workflow_list, handle_workflow_replay,
)
from zentra.actions.watcher import handle_watch_start, handle_watch_stop, handle_watch_list
from zentra.actions.knowledge import handle_kb_add, handle_kb_search, handle_kb_list, handle_kb_clear
from zentra.actions.export import handle_export_chat
from zentra.actions.scheduler import handle_schedule_add, handle_schedule_list, handle_schedule_cancel
from zentra.actions.plugins import handle_plugin_list, handle_plugin_run
from zentra.actions.web import handle_web_search, handle_web_fetch
from zentra.actions.arduino import (
    handle_arduino_boards, handle_arduino_board_info, handle_arduino_ports,
    handle_arduino_library, handle_arduino_generate, handle_arduino_compile,
    handle_arduino_upload, handle_arduino_monitor_start, handle_arduino_monitor_read,
    handle_arduino_monitor_stop, handle_arduino_send,
)


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
    elif action == "shell":
        result = combine(await asyncio.to_thread(handle_shell, data))
    elif action == "clipboard_read":
        result = combine(await asyncio.to_thread(handle_clipboard_read, data))
    elif action == "clipboard_analyze":
        result = combine(await asyncio.to_thread(handle_clipboard_analyze, data))
    elif action == "clipboard_fix":
        result = combine(await asyncio.to_thread(handle_clipboard_fix, data))
    elif action == "context_snapshot":
        result = combine(await asyncio.to_thread(handle_context_snapshot, data))
    elif action == "workflow_run":
        result = combine(await handle_workflow_run(data, dispatch_fn=dispatch_action))
    elif action == "workflow_save":
        result = combine(await asyncio.to_thread(handle_workflow_save, data))
    elif action == "workflow_list":
        result = combine(handle_workflow_list(data))
    elif action == "workflow_replay":
        result = combine(await handle_workflow_replay(data, dispatch_fn=dispatch_action))
    elif action == "watch_start":
        result = combine(handle_watch_start(data))
    elif action == "watch_stop":
        result = combine(handle_watch_stop(data))
    elif action == "watch_list":
        result = combine(handle_watch_list(data))
    elif action == "kb_add":
        result = combine(await asyncio.to_thread(handle_kb_add, data))
    elif action == "kb_search":
        result = combine(await asyncio.to_thread(handle_kb_search, data))
    elif action == "kb_list":
        result = combine(handle_kb_list(data))
    elif action == "kb_clear":
        result = combine(handle_kb_clear(data))
    elif action == "export_chat":
        result = combine(handle_export_chat(data))
    elif action == "schedule_add":
        result = combine(await asyncio.to_thread(handle_schedule_add, data))
    elif action == "schedule_list":
        result = combine(handle_schedule_list(data))
    elif action == "schedule_cancel":
        result = combine(handle_schedule_cancel(data))
    elif action == "plugin_list":
        result = combine(handle_plugin_list(data))
    elif action == "plugin_run":
        result = combine(handle_plugin_run(data))
    elif action == "web_search":
        result = combine(await asyncio.to_thread(handle_web_search, data))
    elif action == "web_fetch":
        result = combine(await asyncio.to_thread(handle_web_fetch, data))
    elif action == "arduino_boards":
        result = combine(handle_arduino_boards(data))
    elif action == "arduino_board_info":
        result = combine(handle_arduino_board_info(data))
    elif action == "arduino_ports":
        result = combine(handle_arduino_ports(data))
    elif action == "arduino_library":
        result = combine(handle_arduino_library(data))
    elif action == "arduino_generate":
        result = combine(await asyncio.to_thread(handle_arduino_generate, data))
    elif action == "arduino_compile":
        result = combine(await asyncio.to_thread(handle_arduino_compile, data))
    elif action == "arduino_upload":
        result = combine(await asyncio.to_thread(handle_arduino_upload, data))
    elif action == "arduino_monitor_start":
        result = combine(handle_arduino_monitor_start(data))
    elif action == "arduino_monitor_read":
        result = combine(handle_arduino_monitor_read(data))
    elif action == "arduino_monitor_stop":
        result = combine(handle_arduino_monitor_stop(data))
    elif action == "arduino_send":
        result = combine(handle_arduino_send(data))
    elif action == "chat":
        result = handle_chat(data)
    else:
        plugin = None
        from zentra.actions.plugins import get_plugin
        plugin = get_plugin(action)
        if plugin:
            try:
                result = combine(plugin["handler"](data))
            except Exception as exc:
                result = f"Plugin '{action}' failed: {exc}"
        else:
            log.warning(f"Unknown action: {action}")
            result = reply or f"Unknown action `{action}`."

    return result, file_content
