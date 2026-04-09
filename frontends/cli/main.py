import asyncio
import shutil
import sys
import os
from datetime import datetime
from pathlib import Path

from zentra.config import (
    APP_NAME, APP_VERSION, OLLAMA_ENDPOINT, OLLAMA_MODEL,
    OLLAMA_VISION_MODEL, BASE_FOLDER, SCREENSHOT_FOLDER,
    PSUTIL_AVAILABLE, PYAUTOGUI_AVAILABLE, GOOGLE_AVAILABLE,
    MEMORY_DEPTH,
)
from zentra.logger import log
from zentra.memory import load_memory, clear_memory, USER_ID
from zentra.engine import process_message
from zentra.utils.seen_emails import load_seen_emails
from zentra.actions.plugins import load_plugins, reload_plugins, handle_plugin_list
from zentra.actions.scheduler import get_due_tasks, add_task_result
from zentra.actions.watcher import get_pending_events
from zentra.dispatcher import dispatch_action

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.text import Text
    from rich.table import Table
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

if RICH_AVAILABLE:
    console = Console()
else:
    console = None

AMBER = "#e4a853"
DIM = "#4a4a58"
TEXT = "#d4d0c8"
RED = "#c45050"
GREEN = "#6cc070"


def print_banner():
    if not RICH_AVAILABLE:
        w = shutil.get_terminal_size((80, 24)).columns
        print("=" * w)
        print(f"  {APP_NAME} v{APP_VERSION}".center(w))
        print("  local ai assistant".center(w))
        print("=" * w)
        return

    banner = Text()
    banner.append("\n  Z E N T R A\n", style=f"bold {AMBER}")
    banner.append(f"  v{APP_VERSION}  //  local ai assistant\n", style=DIM)

    console.print(Panel(banner, border_style=DIM, padding=(0, 2), expand=True))

    t = Table(show_header=False, box=None, padding=(0, 2), expand=True)
    t.add_column(style=DIM, width=20)
    t.add_column(style=TEXT)
    t.add_row("ollama", f"{OLLAMA_MODEL} @ {OLLAMA_ENDPOINT}")
    t.add_row("vision", OLLAMA_VISION_MODEL)
    t.add_row("base folder", BASE_FOLDER)
    t.add_row("memory depth", str(MEMORY_DEPTH))
    t.add_row("psutil", f"[{GREEN}]yes[/]" if PSUTIL_AVAILABLE else f"[{RED}]no[/]")
    t.add_row("pyautogui", f"[{GREEN}]yes[/]" if PYAUTOGUI_AVAILABLE else f"[{RED}]no[/]")
    t.add_row("google apis", f"[{GREEN}]yes[/]" if GOOGLE_AVAILABLE else f"[{RED}]no[/]")
    console.print(t)
    console.print()


def print_help():
    if not RICH_AVAILABLE:
        print("\nCommands:")
        print("  /help           show this help")
        print("  /clear          clear conversation memory")
        print("  /status         check ollama connection")
        print("  /model X        switch model")
        print("  /clipboard      read clipboard")
        print("  /fix            fix clipboard contents")
        print("  /snapshot       context snapshot")
        print("  /export [md|txt] export chat history")
        print("  /kb list|add|search  knowledge base")
        print("  /schedule       list scheduled tasks")
        print("  /watch          list active file watchers")
        print("  /workflows      list saved workflows")
        print("  /plugins        list loaded plugins")
        print("  /reload         reload plugins")
        print("  /quit           exit zentra")
        print("  anything else   sent to the AI\n")
        return

    t = Table(show_header=False, box=None, padding=(0, 2))
    t.add_column(style=f"bold {AMBER}", width=24)
    t.add_column(style=TEXT)
    t.add_row("/help", "this help")
    t.add_row("/clear", "clear memory")
    t.add_row("/status", "check ollama")
    t.add_row("/model <n>", "switch model")
    t.add_row("/clipboard", "read clipboard")
    t.add_row("/fix", "fix clipboard + put back")
    t.add_row("/snapshot", "screen + processes + suggestion")
    t.add_row("/export [md|txt]", "export chat history")
    t.add_row("/kb list", "list knowledge base")
    t.add_row("/kb add <path>", "index files into KB")
    t.add_row("/kb search <query>", "search knowledge base")
    t.add_row("/schedule", "list scheduled tasks")
    t.add_row("/watch", "list file watchers")
    t.add_row("/workflows", "list saved workflows")
    t.add_row("/plugins", "list plugins")
    t.add_row("/reload", "reload plugins")
    t.add_row("/quit", "exit")
    t.add_row("anything else", "sent to the AI")
    console.print(Panel(t, title="[bold]commands[/]", title_align="left", border_style=DIM, padding=(1, 2)))
    console.print()


def print_status():
    import requests
    try:
        r = requests.get(f"{OLLAMA_ENDPOINT}/api/tags", timeout=3)
        if r.status_code == 200:
            models = [m["name"] for m in r.json().get("models", [])]
            has = any(OLLAMA_MODEL in m for m in models)
            if RICH_AVAILABLE:
                console.print(f"  [{GREEN}]online[/] | {OLLAMA_MODEL} {'[' + GREEN + '](loaded)[/]' if has else '[' + RED + '](not pulled)[/]'}")
                console.print(f"  [{DIM}]models: {', '.join(models[:6])}[/]")
            else:
                print(f"  online | {OLLAMA_MODEL} {'(loaded)' if has else '(not pulled)'}")
        else:
            _print_msg("ollama error", RED)
    except Exception:
        _print_msg(f"ollama offline at {OLLAMA_ENDPOINT}", RED)
    _print_nl()


def _print_msg(text, style=None):
    if RICH_AVAILABLE:
        console.print(f"  [{style or TEXT}]{text}[/]")
    else:
        print(f"  {text}")

def _print_nl():
    if RICH_AVAILABLE:
        console.print()
    else:
        print()


def print_user_message(text: str):
    if not RICH_AVAILABLE:
        print(f"\n  YOU > {text}")
        return
    msg = Text()
    msg.append("YOU", style=f"bold {AMBER}")
    msg.append(f"  {datetime.now().strftime('%H:%M')}", style=DIM)
    msg.append(f"\n{text}", style=TEXT)
    console.print(Panel(msg, border_style=AMBER, padding=(0, 2), expand=True))


def print_bot_message(text: str):
    if not RICH_AVAILABLE:
        print(f"\n  ZENTRA > {text}\n")
        return
    msg = Text()
    msg.append("ZENTRA", style=f"bold {DIM}")
    msg.append(f"  {datetime.now().strftime('%H:%M')}", style=DIM)
    msg.append(f"\n{text}", style=TEXT)
    console.print(Panel(msg, border_style=DIM, padding=(0, 2), expand=True))


def get_input() -> str:
    try:
        if RICH_AVAILABLE:
            return console.input(f"[{AMBER}] > [/]").strip()
        return input("  > ").strip()
    except (EOFError, KeyboardInterrupt):
        return "/quit"


async def run_with_spinner(user_input: str) -> str:
    if RICH_AVAILABLE:
        with console.status(f"[{AMBER}]thinking ...[/]", spinner="dots", spinner_style=AMBER):
            return await process_message(user_input, user_id=USER_ID)
    else:
        print("  thinking ...")
        return await process_message(user_input, user_id=USER_ID)


async def run_action_direct(action: str, **kwargs) -> str:
    data = {
        "action": action, "filename": "", "folder": "", "content": "",
        "patches": [], "files": [], "app": "", "app_path": "",
        "run_args": [], "git_folder": "", "git_message": "",
        "screen_goal": "", "screen_actions": [], "reply": "",
    }
    data.update(kwargs)
    result, _ = await dispatch_action(data)
    return result


async def check_background_tasks():
    due = get_due_tasks()
    for task in due:
        msg = f"**Reminder:** {task['message']}"
        if task.get("action") and task["action"] != "chat":
            try:
                result = await run_action_direct(task["action"])
                msg += f"\n\n{result}"
            except Exception as exc:
                msg += f"\n\nAction failed: {exc}"
        add_task_result(task, msg)
        print_bot_message(msg)

    events = get_pending_events()
    for ev in events:
        print_bot_message(f"**File watcher [{ev['watcher']}]:** {ev['type']} {ev['name']}")


def handle_slash_command(cmd: str) -> bool:
    import zentra.config as cfg
    parts = cmd.split(maxsplit=1)
    command = parts[0].lower()
    arg = parts[1].strip() if len(parts) > 1 else ""

    if command in ("/quit", "/exit", "/q"):
        _print_msg("goodbye.", DIM)
        _print_nl()
        return True

    elif command in ("/help", "/?"):
        print_help()

    elif command == "/clear":
        clear_memory(USER_ID)
        _print_msg("memory cleared.", GREEN)
        _print_nl()

    elif command == "/status":
        print_status()

    elif command == "/model":
        if not arg:
            _print_msg(f"current: {cfg.OLLAMA_MODEL}", AMBER)
        else:
            old = cfg.OLLAMA_MODEL
            cfg.OLLAMA_MODEL = arg
            _print_msg(f"{old} -> {cfg.OLLAMA_MODEL}", AMBER)
        _print_nl()

    elif command == "/clipboard":
        result = asyncio.get_event_loop().run_until_complete(run_action_direct("clipboard_read"))
        print_bot_message(result)

    elif command == "/fix":
        result = asyncio.get_event_loop().run_until_complete(run_action_direct("clipboard_fix", reply=arg))
        print_bot_message(result)

    elif command == "/snapshot":
        result = asyncio.get_event_loop().run_until_complete(run_action_direct("context_snapshot"))
        print_bot_message(result)

    elif command == "/export":
        result = asyncio.get_event_loop().run_until_complete(run_action_direct("export_chat", app=arg or "markdown"))
        print_bot_message(result)

    elif command == "/kb":
        sub_parts = arg.split(maxsplit=1)
        sub = sub_parts[0].lower() if sub_parts else "list"
        sub_arg = sub_parts[1] if len(sub_parts) > 1 else ""
        action_map = {"list": "kb_list", "add": "kb_add", "search": "kb_search", "clear": "kb_clear"}
        if sub in action_map:
            kw = {"filename": sub_arg} if sub == "add" else {"app": sub_arg}
            result = asyncio.get_event_loop().run_until_complete(run_action_direct(action_map[sub], **kw))
        else:
            result = "Usage: /kb list | add <path> | search <query> | clear"
        print_bot_message(result)

    elif command == "/schedule":
        result = asyncio.get_event_loop().run_until_complete(run_action_direct("schedule_list"))
        print_bot_message(result)

    elif command == "/watch":
        result = asyncio.get_event_loop().run_until_complete(run_action_direct("watch_list"))
        print_bot_message(result)

    elif command == "/workflows":
        result = asyncio.get_event_loop().run_until_complete(run_action_direct("workflow_list"))
        print_bot_message(result)

    elif command == "/plugins":
        print_bot_message(handle_plugin_list({}))

    elif command == "/reload":
        _print_msg(reload_plugins(), GREEN)
        _print_nl()

    else:
        _print_msg("unknown command. type /help", DIM)
        _print_nl()

    return False


async def main_loop():
    Path(BASE_FOLDER).mkdir(parents=True, exist_ok=True)
    Path(SCREENSHOT_FOLDER).mkdir(parents=True, exist_ok=True)
    load_memory()
    load_seen_emails()
    plugin_count = load_plugins()

    print_banner()
    if plugin_count:
        _print_msg(f"  {plugin_count} plugin(s) loaded", GREEN)
    _print_msg("type /help for commands, or just start talking.", DIM)
    _print_nl()

    bg_counter = 0
    while True:
        user_input = get_input()
        if not user_input:
            continue

        if user_input.startswith("/"):
            if handle_slash_command(user_input):
                break
            continue

        print_user_message(user_input)
        try:
            response = await run_with_spinner(user_input)
            print_bot_message(response)
        except Exception as exc:
            _print_msg(f"error: {exc}", RED)

        bg_counter += 1
        if bg_counter % 3 == 0:
            await check_background_tasks()


def main():
    try:
        asyncio.run(main_loop())
    except KeyboardInterrupt:
        _print_msg("\ninterrupted. goodbye.", DIM)
        _print_nl()


if __name__ == "__main__":
    main()
