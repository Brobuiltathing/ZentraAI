import asyncio
import shutil
import sys
import os
from datetime import datetime

from config import (
    APP_NAME, APP_VERSION, OLLAMA_ENDPOINT, OLLAMA_MODEL,
    OLLAMA_VISION_MODEL, BASE_FOLDER, SCREENSHOT_FOLDER,
    PSUTIL_AVAILABLE, PYAUTOGUI_AVAILABLE, GOOGLE_AVAILABLE,
    MEMORY_DEPTH,
)
from logger import log
from memory import load_memory, save_to_memory, clear_memory, build_prompt
from engine import process_message
from utils.seen_emails import load_seen_emails
from pathlib import Path

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.text import Text
    from rich.table import Table
    from rich.markdown import Markdown
    from rich.rule import Rule
    from rich.live import Live
    from rich.spinner import Spinner
    from rich.columns import Columns
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False


if RICH_AVAILABLE:
    console = Console()
else:
    console = None


AMBER = "#e4a853"
DIM = "#4a4a58"
CHARCOAL = "#1b1b22"
TEXT = "#d4d0c8"
RED = "#c45050"
GREEN = "#6cc070"


def _term_width() -> int:
    return shutil.get_terminal_size((80, 24)).columns


def print_banner():
    if not RICH_AVAILABLE:
        w = _term_width()
        print("=" * w)
        print(f"  {APP_NAME} v{APP_VERSION}".center(w))
        print("  local ai assistant".center(w))
        print("=" * w)
        return

    banner_text = Text()
    banner_text.append("\n  Z E N T R A\n", style=f"bold {AMBER}")
    banner_text.append(f"  v{APP_VERSION}  //  local ai assistant\n", style=DIM)

    console.print(Panel(
        banner_text,
        border_style=DIM,
        padding=(0, 2),
        expand=True,
    ))

    table = Table(show_header=False, box=None, padding=(0, 2), expand=True)
    table.add_column(style=DIM, width=20)
    table.add_column(style=TEXT)

    table.add_row("ollama", f"{OLLAMA_MODEL} @ {OLLAMA_ENDPOINT}")
    table.add_row("vision", OLLAMA_VISION_MODEL)
    table.add_row("base folder", BASE_FOLDER)
    table.add_row("memory depth", str(MEMORY_DEPTH))
    table.add_row("psutil", f"[{GREEN}]yes[/]" if PSUTIL_AVAILABLE else f"[{RED}]no[/]")
    table.add_row("pyautogui", f"[{GREEN}]yes[/]" if PYAUTOGUI_AVAILABLE else f"[{RED}]no[/]")
    table.add_row("google apis", f"[{GREEN}]yes[/]" if GOOGLE_AVAILABLE else f"[{RED}]no[/]")

    console.print(table)
    console.print()


def print_help():
    if not RICH_AVAILABLE:
        print("\nCommands:")
        print("  /help        show this help")
        print("  /clear       clear conversation memory")
        print("  /status      show ollama connection status")
        print("  /model X     switch ollama model to X")
        print("  /quit        exit zentra")
        print("  anything else is sent to the AI\n")
        return

    console.print()
    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column(style=f"bold {AMBER}", width=16)
    table.add_column(style=TEXT)

    table.add_row("/help", "show this help")
    table.add_row("/clear", "clear conversation memory")
    table.add_row("/status", "show ollama connection status")
    table.add_row("/model <name>", "switch ollama model")
    table.add_row("/quit", "exit zentra")
    table.add_row("anything else", "sent to the AI")

    console.print(Panel(table, title="[bold]commands[/]", title_align="left", border_style=DIM, padding=(1, 2)))
    console.print()


def print_status():
    import requests
    if not RICH_AVAILABLE:
        try:
            r = requests.get(f"{OLLAMA_ENDPOINT}/api/tags", timeout=3)
            if r.status_code == 200:
                models = [m["name"] for m in r.json().get("models", [])]
                print(f"  status: online")
                print(f"  models: {', '.join(models)}")
                has = any(OLLAMA_MODEL in m for m in models)
                print(f"  active: {OLLAMA_MODEL} {'(loaded)' if has else '(not pulled)'}")
            else:
                print("  status: error")
        except Exception:
            print("  status: offline")
        return

    try:
        r = requests.get(f"{OLLAMA_ENDPOINT}/api/tags", timeout=3)
        if r.status_code == 200:
            models = [m["name"] for m in r.json().get("models", [])]
            has = any(OLLAMA_MODEL in m for m in models)

            table = Table(show_header=False, box=None, padding=(0, 2))
            table.add_column(style=DIM, width=16)
            table.add_column(style=TEXT)

            table.add_row("status", f"[{GREEN}]online[/]")
            table.add_row("endpoint", OLLAMA_ENDPOINT)
            table.add_row("active model", f"{OLLAMA_MODEL} {'[' + GREEN + '](loaded)[/]' if has else '[' + RED + '](not pulled)[/]'}")
            table.add_row("available", ", ".join(models[:8]) or "none")

            console.print(Panel(table, title="[bold]ollama status[/]", title_align="left", border_style=DIM, padding=(1, 2)))
        else:
            console.print(f"  [{RED}]ollama returned status {r.status_code}[/]")
    except Exception:
        console.print(f"  [{RED}]ollama is offline[/] at {OLLAMA_ENDPOINT}")

    console.print()


def print_user_message(text: str):
    if not RICH_AVAILABLE:
        print(f"\n  YOU > {text}")
        return

    msg = Text()
    msg.append("YOU", style=f"bold {AMBER}")
    msg.append(f"  {datetime.now().strftime('%H:%M')}", style=DIM)
    msg.append(f"\n{text}", style=TEXT)

    console.print(Panel(
        msg,
        border_style=AMBER,
        padding=(0, 2),
        expand=True,
    ))


def print_bot_message(text: str):
    if not RICH_AVAILABLE:
        print(f"\n  ZENTRA > {text}\n")
        return

    msg = Text()
    msg.append("ZENTRA", style=f"bold {DIM}")
    msg.append(f"  {datetime.now().strftime('%H:%M')}", style=DIM)
    msg.append(f"\n{text}", style=TEXT)

    console.print(Panel(
        msg,
        border_style=DIM,
        padding=(0, 2),
        expand=True,
    ))


def print_error(text: str):
    if not RICH_AVAILABLE:
        print(f"\n  ERROR: {text}\n")
        return
    console.print(f"  [{RED}]error:[/] {text}")
    console.print()


def get_input() -> str:
    if RICH_AVAILABLE:
        try:
            return console.input(f"[{AMBER}] > [/]").strip()
        except (EOFError, KeyboardInterrupt):
            return "/quit"
    else:
        try:
            return input("  > ").strip()
        except (EOFError, KeyboardInterrupt):
            return "/quit"


async def run_with_spinner(user_input: str) -> str:
    if RICH_AVAILABLE:
        with console.status(f"[{AMBER}]thinking ...[/]", spinner="dots", spinner_style=AMBER):
            return await process_message(user_input)
    else:
        print("  thinking ...")
        return await process_message(user_input)


def handle_slash_command(cmd: str) -> bool:
    import config as cfg

    parts = cmd.split(maxsplit=1)
    command = parts[0].lower()

    if command == "/quit" or command == "/exit" or command == "/q":
        if RICH_AVAILABLE:
            console.print(f"\n  [{DIM}]goodbye.[/]\n")
        else:
            print("\n  goodbye.\n")
        return True

    elif command == "/help" or command == "/?":
        print_help()

    elif command == "/clear":
        clear_memory()
        if RICH_AVAILABLE:
            console.print(f"  [{GREEN}]memory cleared.[/]\n")
        else:
            print("  memory cleared.\n")

    elif command == "/status":
        print_status()

    elif command == "/model":
        if len(parts) < 2:
            if RICH_AVAILABLE:
                console.print(f"  current model: [{AMBER}]{cfg.OLLAMA_MODEL}[/]")
                console.print(f"  [{DIM}]usage: /model <name>[/]\n")
            else:
                print(f"  current model: {cfg.OLLAMA_MODEL}")
                print("  usage: /model <name>\n")
        else:
            old = cfg.OLLAMA_MODEL
            cfg.OLLAMA_MODEL = parts[1].strip()
            if RICH_AVAILABLE:
                console.print(f"  [{DIM}]{old}[/] -> [{AMBER}]{cfg.OLLAMA_MODEL}[/]\n")
            else:
                print(f"  {old} -> {cfg.OLLAMA_MODEL}\n")

    else:
        if RICH_AVAILABLE:
            console.print(f"  [{DIM}]unknown command. type /help[/]\n")
        else:
            print("  unknown command. type /help\n")

    return False


async def main_loop():
    Path(BASE_FOLDER).mkdir(parents=True, exist_ok=True)
    Path(SCREENSHOT_FOLDER).mkdir(parents=True, exist_ok=True)
    load_memory()
    load_seen_emails()

    print_banner()

    if RICH_AVAILABLE:
        console.print(f"  [{DIM}]type /help for commands, or just start talking.[/]\n")
    else:
        print("  type /help for commands, or just start talking.\n")

    while True:
        user_input = get_input()

        if not user_input:
            continue

        if user_input.startswith("/"):
            should_quit = handle_slash_command(user_input)
            if should_quit:
                break
            continue

        print_user_message(user_input)

        try:
            response = await run_with_spinner(user_input)
            print_bot_message(response)
        except Exception as exc:
            print_error(str(exc))


def main():
    try:
        asyncio.run(main_loop())
    except KeyboardInterrupt:
        if RICH_AVAILABLE:
            console.print(f"\n  [{DIM}]interrupted. goodbye.[/]\n")
        else:
            print("\n  interrupted. goodbye.\n")


if __name__ == "__main__":
    main()
