import asyncio
import json
import logging
import os
import pickle
import platform
import re
import shutil
import subprocess
import sys
import time
from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone
from pathlib import Path

import discord
import requests


try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False


try:
    from google.auth.transport.requests import Request
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build as google_build
    from googleapiclient.errors import HttpError
    import base64
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart
    GOOGLE_AVAILABLE = True
except ImportError:
    GOOGLE_AVAILABLE = False


try:
    import pyautogui
    import PIL.Image
    import PIL.ImageGrab
    import io
    PYAUTOGUI_AVAILABLE = True
    pyautogui.PAUSE = 0.05
    pyautogui.FAILSAFE = True
except ImportError:
    PYAUTOGUI_AVAILABLE = False

if platform.system() == "Windows":
    try:
        import winreg
        WINREG_AVAILABLE = True
    except ImportError:
        WINREG_AVAILABLE = False
else:
    WINREG_AVAILABLE = False



DISCORD_BOT_TOKEN  = "##################################################################"

OLLAMA_ENDPOINT    = "http://localhost:11434"
OLLAMA_MODEL       = "qwen2.5-coder:7b"
OLLAMA_TEMPERATURE = 0.1


OLLAMA_VISION_MODEL = "llava:13b"

BASE_FOLDER = os.path.join(os.getcwd(), "zentra_files")

MEMORY_DEPTH = 8

RUN_TIMEOUT_SECONDS = 30

ALLOWED_USER_IDS: list = [#########################################]


MEMORY_FILE = os.path.join(os.getcwd(), "zentra_memory.json")


SEEN_EMAILS_FILE = os.path.join(os.getcwd(), "zentra_seen_emails.json")


READ_FILE_MAX_CHARS = 12_000


SCREENSHOT_FOLDER = os.path.join(os.getcwd(), "zentra_screenshots")

MAX_SCREEN_ACTIONS = 20


SCREEN_ACTION_DELAY = 0.4


GOOGLE_CREDENTIALS_FILE = os.path.join(os.getcwd(), "credentials.json")
GOOGLE_TOKEN_FILE       = os.path.join(os.getcwd(), "google_token.pickle")
GOOGLE_SCOPES = [
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/calendar",
]

MORNING_DIGEST_HOUR         = 8
MORNING_DIGEST_MINUTE       = 0
EVENT_REMINDER_MINUTES      = 30
EMAIL_POLL_INTERVAL_MINUTES = 5
MAX_DIGEST_EMAILS           = 20

IMPORTANT_KEYWORDS = [
    "invoice", "payment", "urgent", "deadline", "bill",
    "overdue", "expires", "action required", "verify",
    "security alert", "password", "suspended", "confirm",
    "2fa", "two-factor", "verification", "account locked",
]
IMPORTANT_SENDERS: list[str] = []


LANG_RUNNER: dict = {
    ".py":  [sys.executable],
    ".js":  ["node"],
    ".ts":  ["ts-node"],
    ".sh":  ["bash"],
    ".rb":  ["ruby"],
    ".php": ["php"],
    ".go":  ["go", "run"],
}


logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s — %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("ZENTRA")


memory: dict     = defaultdict(lambda: deque(maxlen=MEMORY_DEPTH * 2))
user_locks: dict = defaultdict(asyncio.Lock)


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


_seen_email_ids: set[str] = set()

def _load_seen_emails() -> None:
    global _seen_email_ids
    try:
        if Path(SEEN_EMAILS_FILE).exists():
            with open(SEEN_EMAILS_FILE, "r") as fh:
                _seen_email_ids = set(json.load(fh))
            log.info(f"Loaded {len(_seen_email_ids)} seen email IDs.")
    except Exception as exc:
        log.warning(f"Could not load seen emails: {exc}")

def _persist_seen_emails() -> None:
    try:

        ids = list(_seen_email_ids)[-2000:]
        with open(SEEN_EMAILS_FILE, "w") as fh:
            json.dump(ids, fh)
    except Exception as exc:
        log.warning(f"Could not persist seen emails: {exc}")


SYSTEM_PROMPT = """You are ZENTRA, an AI developer assistant running locally on the user's PC.
You ONLY respond with a single raw JSON object — no markdown, no code fences, no text before or after.

You have access to these actions:
  create_file      — write a single file to disk
  run_file         — create AND immediately execute a file, return output
  read_file        — read an existing file from disk so you can reason about it
  edit_file        — surgically edit an existing file using search-replace patches
  scaffold_project — generate an entire multi-file project in one shot
  open_app         — launch an application on the user's computer by name
  close_app        — close/kill a running application by name or PID
  vscode_open      — open a file or folder in Visual Studio Code
  github_push      — git add, commit, and push inside a given folder
  system_stats     — show live system information (CPU, RAM, disk, GPU, network, top processes)
  screen_action    — take a screenshot, analyse it, then perform mouse/keyboard actions on screen
  gmail_summary    — summarise unread emails (optional keyword/sender filter in 'app' field)
  gmail_send       — send or reply to an email (put details in 'reply' field)
  calendar_today   — show today's calendar events
  calendar_week    — show this week's calendar events
  calendar_add     — add a calendar event from natural language (put full request in 'reply')
  calendar_delete  — delete a calendar event (put title/time in 'reply')
  calendar_search  — search calendar events by keyword (put keyword in 'app' field)
  chat             — plain conversational reply (no file or system action needed)

ALWAYS return exactly this JSON shape — every field present, no extras, no omissions:
{
  "action":         "create_file",
  "filename":       "example.py",
  "folder":         "",
  "content":        "",
  "patches":        [],
  "files":          [],
  "app":            "",
  "app_path":       "",
  "run_args":       [],
  "git_folder":     "",
  "git_message":    "",
  "screen_goal":    "",
  "screen_actions": [],
  "reply":          "Short friendly message."
}

Field rules:
  action          — one of the eighteen actions listed above
  filename        — full filename WITH correct extension (e.g. server.js, styles.css, main.go)
                    for read_file and edit_file: path relative to base files dir, or absolute
  folder          — optional subfolder inside the base files directory, else ""
  content         — complete file content for create_file/run_file; else ""
  patches         — for edit_file: list of {"old": "exact text to find", "new": "replacement text"} objects
                    IMPORTANT: "old" must be the EXACT text from the file (whitespace included)
  files           — for scaffold_project: list of {"filename": "...", "folder": "...", "content": "..."} objects
                    Each file must have complete, working content. Plan the full project before writing.
  app             — for open_app: common app name (e.g. "steam", "chrome", "spotify")
                    for close_app: name or PID of the app to close (e.g. "chrome", "notepad", "1234")
                    for gmail_summary: optional filter keyword/sender (or "" for all unread)
                    for calendar_search: the keyword to search for
  app_path        — for open_app: full executable path if known, else ""
                    for close_app: full executable name if known (e.g. "chrome.exe"), else ""
  run_args        — for run_file: list of extra CLI arguments, else []
  git_folder      — for github_push: path to the git repo folder, else ""
  git_message     — for github_push: commit message string, else ""
  screen_goal     — for screen_action: a clear description of what you want to achieve on screen
                    e.g. "Open the Start menu and search for Notepad"
                    e.g. "Click the red X button to close the dialog"
                    e.g. "Type 'Hello World' in the text field and press Enter"
  screen_actions  — for screen_action: optional list of pre-planned actions to execute
                    Each action: {"type": "...", ...params...}
                    Leave as [] to let ZENTRA auto-plan from the screenshot
                    Action types and params:
                      {"type": "click",       "x": 500, "y": 300}
                      {"type": "double_click","x": 500, "y": 300}
                      {"type": "right_click", "x": 500, "y": 300}
                      {"type": "move",        "x": 500, "y": 300}
                      {"type": "drag",        "x1": 100, "y1": 100, "x2": 400, "y2": 400}
                      {"type": "scroll",      "x": 500, "y": 300, "clicks": 3}  (positive=up)
                      {"type": "type",        "text": "Hello World"}
                      {"type": "key",         "key": "enter"}  (any pyautogui key name)
                      {"type": "hotkey",      "keys": ["ctrl", "c"]}
                      {"type": "screenshot"}  (take mid-action screenshot for verification)
                      {"type": "wait",        "seconds": 1.0}
                      {"type": "find_and_click", "image": "button_name", "description": "the OK button"}
  reply           — short friendly message (ALWAYS required, never empty)
                    for calendar_add: the full natural language event description goes here
                    for calendar_delete: the event title and/or time to delete
                    for gmail_send: recipient, subject, and body (full details)

Behaviour rules:
  - Use conversation history to understand follow-up requests
  - For run_file, write complete runnable code — never pseudocode
  - For create_file, infer the correct language and extension
  - For read_file, set filename to the path the user mentioned; ZENTRA will inject file contents
  - For edit_file, each patch "old" value must be unique text within the file
  - For scaffold_project, think through the full file structure first, then populate every file completely
  - For close_app, use the most common process name (e.g. "chrome" → looks for "chrome.exe" / "chrome")
  - For screen_action, describe the goal clearly; ZENTRA will take a screenshot, analyse it with vision
    AI, then execute the appropriate actions automatically
  - For gmail_summary, use the app field for any filter the user mentioned (sender name, keyword, etc.)
  - For gmail_send, put all details (to, subject, body) in the reply field
  - For calendar_add/delete, put the complete original request in the reply field
  - For system_stats, no extra fields needed — just set action and reply
  - For chat, set all fields except action and reply to "" or [] or {}
  - Write complete, idiomatic, working code — no TODOs or placeholders
  - NEVER output any text outside the JSON object
  - NEVER use markdown code fences or backticks anywhere
  - Return ONLY the raw JSON starting with { and ending with }
"""


intents = discord.Intents.default()
intents.message_content = True
intents.dm_messages     = True

client = discord.Client(intents=intents)


def build_prompt(user_id: int, new_message: str) -> str:
    history = memory[user_id]
    if not history:
        return new_message
    lines = ["CONVERSATION HISTORY (oldest first):"]
    for turn in history:
        role = "User" if turn["role"] == "user" else "ZENTRA"
        lines.append(f"  {role}: {turn['content']}")
    lines.append("")
    lines.append(f"NEW USER MESSAGE: {new_message}")
    return "\n".join(lines)


def save_to_memory(user_id: int, user_msg: str, bot_reply_summary: str) -> None:
    memory[user_id].append({"role": "user",      "content": user_msg})
    memory[user_id].append({"role": "assistant",  "content": bot_reply_summary})
    persist_memory()


def _query_ollama_sync(prompt: str) -> str:
    """
    Streaming Ollama call — reads chunks as they arrive so the connection
    never times out even for very long code generation.
    """
    payload = {
        "model":      OLLAMA_MODEL,
        "stream":     True,
        "keep_alive": -1,
        "options": {
            "temperature":    OLLAMA_TEMPERATURE,
            "num_predict":    -1,
            "num_ctx":        16384,
            "top_p":          0.9,
            "repeat_penalty": 1.1,
        },
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": prompt},
        ],
    }
    try:
        resp = requests.post(
            f"{OLLAMA_ENDPOINT}/api/chat",
            json=payload,
            timeout=600,
            stream=True,
        )
        resp.raise_for_status()

        full_content = []
        for line in resp.iter_lines():
            if not line:
                continue
            try:
                chunk = json.loads(line.decode("utf-8"))
            except (json.JSONDecodeError, UnicodeDecodeError):
                continue
            delta = chunk.get("message", {}).get("content", "")
            if delta:
                full_content.append(delta)
            if chunk.get("done", False):
                break

        raw = "".join(full_content)
        log.info(f"Ollama raw (first 300 chars): {raw[:300]}")
        return raw

    except requests.exceptions.ConnectionError:
        raise ConnectionError(
            "Cannot connect to Ollama — is it running?\n"
            f"Start it with:  ollama run {OLLAMA_MODEL}"
        )
    except requests.exceptions.Timeout:
        raise TimeoutError("Ollama timed out after 600 s.")
    except requests.exceptions.HTTPError as exc:
        raise RuntimeError(f"Ollama HTTP error: {exc}")


def _ollama_raw_sync(system: str, user: str, max_tokens: int = 300) -> str:
    """Lighter Ollama call for summarisation / classification — no JSON schema."""
    payload = {
        "model":      OLLAMA_MODEL,
        "stream":     False,
        "keep_alive": -1,
        "options": {"temperature": 0.3, "num_predict": max_tokens},
        "messages": [
            {"role": "system", "content": system},
            {"role": "user",   "content": user[:4000]},
        ],
    }
    try:
        r = requests.post(f"{OLLAMA_ENDPOINT}/api/chat", json=payload, timeout=60)
        r.raise_for_status()
        return r.json()["message"]["content"].strip()
    except Exception as exc:
        log.warning(f"_ollama_raw_sync failed: {exc}")
        return user[:200] + "…"


def _ollama_vision_sync(image_b64: str, prompt: str, max_tokens: int = 1000) -> str:
    """
    Call the vision-capable Ollama model with a base64 image.
    Returns the model's description / action plan.
    """
    payload = {
        "model":      OLLAMA_VISION_MODEL,
        "stream":     False,
        "keep_alive": -1,
        "options": {
            "temperature": 0.1,
            "num_predict": max_tokens,
            "num_ctx":     8192,
        },
        "messages": [
            {
                "role":    "user",
                "content": prompt,
                "images":  [image_b64],
            }
        ],
    }
    try:
        r = requests.post(f"{OLLAMA_ENDPOINT}/api/chat", json=payload, timeout=120)
        r.raise_for_status()
        return r.json()["message"]["content"].strip()
    except Exception as exc:
        log.warning(f"Vision model call failed: {exc}")
        return ""


async def query_ollama(prompt: str) -> str:
    return await asyncio.to_thread(_query_ollama_sync, prompt)

def extract_json(raw_text: str) -> dict:
    cleaned = re.sub(r"<think>[\s\S]*?</think>", "", raw_text, flags=re.IGNORECASE).strip()

    for text in [cleaned, raw_text.strip()]:
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        m = re.search(r"\{[\s\S]*?\}", text)
        if m:
            try:
                return json.loads(m.group(0))
            except json.JSONDecodeError:
                pass

        m = re.search(r"\{[\s\S]*\}", text)
        if m:
            try:
                return json.loads(m.group(0))
            except json.JSONDecodeError:
                pass

        no_fences = re.sub(r"```(?:json)?\n?", "", text).replace("```", "").strip()
        try:
            return json.loads(no_fences)
        except json.JSONDecodeError:
            pass

    raise ValueError(f"No valid JSON found in model output:\n{raw_text[:600]}")


def resolve_file_path(data: dict):
    filename = data.get("filename", "").strip() or "generated_output.txt"
    folder   = data.get("folder",   "").strip()
    base_dir = Path(BASE_FOLDER) / folder if folder else Path(BASE_FOLDER)
    return base_dir, base_dir / filename


def resolve_any_path(filename: str) -> Path:
    p = Path(filename)
    if p.is_absolute() and p.exists():
        return p
    rel = Path.cwd() / p
    if rel.exists():
        return rel
    base = Path(BASE_FOLDER) / p
    if base.exists():
        return base
    return base


def ensure_dir(path: Path):
    try:
        path.mkdir(parents=True, exist_ok=True)
        return None
    except OSError as exc:
        return f"❌ Could not create directory `{path}`: {exc}"


def write_file(file_path: Path, content: str):
    try:
        with open(file_path, "w", encoding="utf-8") as fh:
            fh.write(content)
        return None
    except OSError as exc:
        return f"❌ Could not write `{file_path}`: {exc}"


def handle_create_file(data: dict) -> str:
    content = data.get("content", "").strip()
    if not content:
        content = "# ZENTRA generated file\n"

    base_dir, file_path = resolve_file_path(data)

    err = ensure_dir(base_dir)
    if err:
        return err

    err = write_file(file_path, content)
    if err:
        return err

    log.info(f"File created: {file_path}")
    ext = file_path.suffix.lower()
    return f"✅ File created: `{file_path}`\n🔤 Language: `{ext or 'unknown'}`"


def handle_run_file(data: dict) -> str:
    content  = data.get("content", "").strip()
    run_args = data.get("run_args", [])
    if not isinstance(run_args, list):
        run_args = []

    if not content:
        return "❌ run_file requires 'content' — no code was provided."

    base_dir, file_path = resolve_file_path(data)

    err = ensure_dir(base_dir)
    if err:
        return err

    err = write_file(file_path, content)
    if err:
        return err

    log.info(f"File written for run: {file_path}")
    ext = file_path.suffix.lower()

    if ext in (".rs", ".java", ".c", ".cpp"):
        return (
            f"✅ File created: `{file_path}`\n\n"
            f"⚠️ `{ext}` files must be compiled before running."
        )

    if ext == ".bat":
        if platform.system() != "Windows":
            return f"✅ File created: `{file_path}`\n\n⚠️ `.bat` files only run on Windows."
        cmd = [str(file_path)] + run_args
    elif ext in LANG_RUNNER:
        interpreter = LANG_RUNNER[ext][0]
        if not shutil.which(interpreter):
            return (
                f"✅ File created: `{file_path}`\n\n"
                f"⚠️ Cannot run — `{interpreter}` not found on PATH."
            )
        cmd = LANG_RUNNER[ext] + [str(file_path)] + run_args
    else:
        return (
            f"✅ File created: `{file_path}`\n\n"
            f"⚠️ ZENTRA doesn't know how to auto-run `{ext}` files."
        )

    try:
        log.info(f"Running: {' '.join(str(x) for x in cmd)}")
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=RUN_TIMEOUT_SECONDS,
            cwd=str(base_dir),
        )

        stdout = result.stdout.strip()
        stderr = result.stderr.strip()
        code   = result.returncode
        parts  = [f"✅ Created & executed: `{file_path}`"]

        if stdout:
            if len(stdout) > 1200:
                stdout = stdout[:1200] + "\n… (output truncated)"
            parts.append(f"\n📤 Output:\n```\n{stdout}\n```")

        if stderr:
            if len(stderr) > 800:
                stderr = stderr[:800] + "\n… (truncated)"
            parts.append(f"\n⚠️ Stderr:\n```\n{stderr}\n```")

        if code != 0 and not stderr and not stdout:
            parts.append(f"\n⚠️ Process exited with code {code} (no output)")

        return "\n".join(parts)

    except subprocess.TimeoutExpired:
        return (
            f"✅ File created: `{file_path}`\n\n"
            f"⏱️ Execution killed after {RUN_TIMEOUT_SECONDS} s."
        )
    except FileNotFoundError as exc:
        return f"✅ File created: `{file_path}`\n\n❌ Could not run: {exc}"
    except Exception as exc:
        log.error(f"run_file unexpected error: {exc}", exc_info=True)
        return f"✅ File created: `{file_path}`\n\n❌ Unexpected error: {exc}"


def handle_read_file(data: dict) -> tuple[str, str]:
    """Returns (discord_message, file_content_for_prompt)."""
    filename = data.get("filename", "").strip()
    if not filename:
        return "❌ read_file: no filename provided.", ""

    file_path = resolve_any_path(filename)
    if not file_path.exists():
        return f"❌ File not found: `{file_path}`", ""

    try:
        content = file_path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        return f"❌ Could not read `{file_path}`: {exc}", ""

    size      = len(content)
    truncated = False
    if size > READ_FILE_MAX_CHARS:
        content   = content[:READ_FILE_MAX_CHARS]
        truncated = True

    lines     = content.count("\n") + 1
    trunc_msg = f"\n⚠️ File truncated to {READ_FILE_MAX_CHARS:,} chars for context." if truncated else ""
    msg       = f"📂 Read `{file_path}` — {lines} lines, {size:,} chars{trunc_msg}"
    log.info(f"File read: {file_path} ({size} chars)")
    return msg, content


def handle_edit_file(data: dict) -> str:
    filename = data.get("filename", "").strip()
    patches  = data.get("patches", [])

    if not filename:
        return "❌ edit_file: no filename provided."
    if not patches or not isinstance(patches, list):
        return "❌ edit_file: no patches provided."

    file_path = resolve_any_path(filename)
    if not file_path.exists():
        return f"❌ File not found: `{file_path}`"

    try:
        original = file_path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        return f"❌ Could not read `{file_path}`: {exc}"

    content     = original
    applied     = 0
    failed_msgs = []

    for i, patch in enumerate(patches):
        old = patch.get("old", "")
        new = patch.get("new", "")
        if not old:
            failed_msgs.append(f"  Patch {i+1}: empty 'old' field — skipped.")
            continue
        occurrences = content.count(old)
        if occurrences == 0:
            failed_msgs.append(f"  Patch {i+1}: text not found in file — skipped.")
            log.warning(f"edit_file patch {i+1}: text not found: {old[:60]!r}")
            continue
        if occurrences > 1:
            failed_msgs.append(f"  Patch {i+1}: text found {occurrences}× (ambiguous) — skipped.")
            continue
        content = content.replace(old, new, 1)
        applied += 1
        log.info(f"edit_file patch {i+1} applied to {file_path.name}")

    if applied == 0:
        return "❌ No patches could be applied.\n" + "\n".join(failed_msgs)

    err = write_file(file_path, content)
    if err:
        return err

    lines_before = original.count("\n") + 1
    lines_after  = content.count("\n")  + 1
    delta        = lines_after - lines_before
    delta_str    = f"+{delta}" if delta >= 0 else str(delta)

    result = (
        f"✏️ Edited `{file_path}`\n"
        f"   {applied}/{len(patches)} patch(es) applied  |  "
        f"{lines_before}→{lines_after} lines ({delta_str})"
    )
    if failed_msgs:
        result += "\n⚠️ Some patches failed:\n" + "\n".join(failed_msgs)
    return result


def handle_scaffold_project(data: dict) -> str:
    files  = data.get("files", [])
    folder = data.get("folder", "").strip()

    if not files or not isinstance(files, list):
        return "❌ scaffold_project: no files list provided."

    base_dir = Path(BASE_FOLDER) / folder if folder else Path(BASE_FOLDER)
    created  = []
    errors   = []

    for entry in files:
        if not isinstance(entry, dict):
            continue
        fname     = entry.get("filename", "").strip()
        subfolder = entry.get("folder", "").strip()
        content   = entry.get("content", "")

        if not fname:
            errors.append("  ⚠️ An entry had no filename — skipped.")
            continue

        file_dir  = base_dir / subfolder if subfolder else base_dir
        file_path = file_dir / fname

        err = ensure_dir(file_dir)
        if err:
            errors.append(f"  ❌ {fname}: {err}")
            continue

        err = write_file(file_path, content or f"# {fname}\n")
        if err:
            errors.append(f"  ❌ {fname}: {err}")
            continue

        created.append(f"  ✅ `{file_path.relative_to(Path(BASE_FOLDER))}`")
        log.info(f"Scaffolded: {file_path}")

    summary = (
        f"🏗️ Project scaffolded in `{base_dir}`\n"
        f"Created {len(created)} file(s):\n"
        + "\n".join(created)
    )
    if errors:
        summary += "\n\nErrors:\n" + "\n".join(errors)
    return summary


def _fmt_bytes(n: float) -> str:
    """Human-readable byte count."""
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if abs(n) < 1024:
            return f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} PB"


def _fmt_uptime(seconds: float) -> str:
    seconds = int(seconds)
    days    = seconds // 86400
    hours   = (seconds % 86400) // 3600
    mins    = (seconds % 3600)  // 60
    parts   = []
    if days:
        parts.append(f"{days}d")
    if hours:
        parts.append(f"{hours}h")
    parts.append(f"{mins}m")
    return " ".join(parts)


def _gpu_info_sync() -> str:
    """Query nvidia-smi if available; returns formatted string or empty."""
    if not shutil.which("nvidia-smi"):
        return ""
    try:
        r = subprocess.run(
            [
                "nvidia-smi",
                "--query-gpu=name,utilization.gpu,memory.used,memory.total,temperature.gpu",
                "--format=csv,noheader,nounits",
            ],
            capture_output=True, text=True, timeout=5,
        )
        if r.returncode != 0 or not r.stdout.strip():
            return ""
        lines = []
        for i, row in enumerate(r.stdout.strip().splitlines()):
            parts = [p.strip() for p in row.split(",")]
            if len(parts) < 5:
                continue
            name, util, mem_used, mem_total, temp = parts
            lines.append(
                f"  GPU {i}: {name}\n"
                f"    Utilisation : {util}%\n"
                f"    VRAM        : {mem_used} MB / {mem_total} MB\n"
                f"    Temperature : {temp}°C"
            )
        return "\n".join(lines)
    except Exception as exc:
        log.warning(f"nvidia-smi query failed: {exc}")
        return ""


def handle_system_stats(_data: dict) -> str:
    if not PSUTIL_AVAILABLE:
        return (
            "❌ `psutil` is not installed.\n"
            "Run: `pip install psutil` then restart ZENTRA."
        )

    lines: list[str] = []


    boot_time  = datetime.fromtimestamp(psutil.boot_time())
    uptime_sec = time.time() - psutil.boot_time()
    lines.append(
        f"🖥️ **System Stats** — {platform.node()}  |  "
        f"{platform.system()} {platform.release()}\n"
        f"⏱️ Uptime: **{_fmt_uptime(uptime_sec)}**  "
        f"(booted {boot_time.strftime('%d %b %Y %H:%M')})"
    )

   
    cpu_pct_overall = psutil.cpu_percent(interval=0.5)
    cpu_pct_per     = psutil.cpu_percent(interval=None, percpu=True)
    cpu_freq        = psutil.cpu_freq()
    cpu_count_phys  = psutil.cpu_count(logical=False) or "?"
    cpu_count_logic = psutil.cpu_count(logical=True)  or "?"

    freq_str = ""
    if cpu_freq:
        freq_str = f"  |  {cpu_freq.current:.0f} MHz"

    core_bar_parts = []
    for i, pct in enumerate(cpu_pct_per):
        bar_len  = int(pct / 10)
        bar      = "█" * bar_len + "░" * (10 - bar_len)
        core_bar_parts.append(f"    Core {i:<2} [{bar}] {pct:5.1f}%")

    lines.append(
        f"\n**🔲 CPU** — {platform.processor() or 'Unknown'}\n"
        f"  Overall : **{cpu_pct_overall:.1f}%**{freq_str}\n"
        f"  Cores   : {cpu_count_phys} physical / {cpu_count_logic} logical\n"
        + "\n".join(core_bar_parts)
    )


    ram = psutil.virtual_memory()
    swap = psutil.swap_memory()
    ram_bar_len = int(ram.percent / 10)
    ram_bar     = "█" * ram_bar_len + "░" * (10 - ram_bar_len)

    lines.append(
        f"\n**🧠 Memory**\n"
        f"  RAM  [{ram_bar}] **{ram.percent:.1f}%**\n"
        f"       Used : {_fmt_bytes(ram.used)} / {_fmt_bytes(ram.total)}"
        f"  (available: {_fmt_bytes(ram.available)})\n"
        f"  Swap : {_fmt_bytes(swap.used)} / {_fmt_bytes(swap.total)}"
        + (f"  ({swap.percent:.1f}%)" if swap.total else "  (no swap)")
    )


    disk_lines = ["**💾 Disk**"]
    try:
        io_before = psutil.disk_io_counters()
        time.sleep(0.3)
        io_after  = psutil.disk_io_counters()
        read_spd  = (io_after.read_bytes  - io_before.read_bytes)  / 0.3
        write_spd = (io_after.write_bytes - io_before.write_bytes) / 0.3
        disk_lines.append(
            f"  I/O  : ↓ {_fmt_bytes(read_spd)}/s read  |  ↑ {_fmt_bytes(write_spd)}/s write"
        )
    except Exception:
        pass

    for part in psutil.disk_partitions(all=False):
        try:
            usage = psutil.disk_usage(part.mountpoint)
            bar_len = int(usage.percent / 10)
            bar     = "█" * bar_len + "░" * (10 - bar_len)
            disk_lines.append(
                f"  {part.mountpoint:<12} [{bar}] {usage.percent:.1f}%  "
                f"{_fmt_bytes(usage.used)} / {_fmt_bytes(usage.total)}"
            )
        except PermissionError:
            disk_lines.append(f"  {part.mountpoint:<12} (permission denied)")
    lines.append("\n" + "\n".join(disk_lines))


    gpu_str = _gpu_info_sync()
    if gpu_str:
        lines.append(f"\n**🎮 GPU**\n{gpu_str}")


    try:
        net_before = psutil.net_io_counters(pernic=False)
        time.sleep(0.3)
        net_after  = psutil.net_io_counters(pernic=False)
        net_sent   = (net_after.bytes_sent - net_before.bytes_sent) / 0.3
        net_recv   = (net_after.bytes_recv - net_before.bytes_recv) / 0.3

        net_lines = [
            "**🌐 Network**",
            f"  Live  : ↑ {_fmt_bytes(net_sent)}/s  |  ↓ {_fmt_bytes(net_recv)}/s",
            f"  Total : Sent {_fmt_bytes(net_after.bytes_sent)}  |  "
            f"Recv {_fmt_bytes(net_after.bytes_recv)}",
        ]

        # Active interfaces with IP
        addrs = psutil.net_if_addrs()
        stats = psutil.net_if_stats()
        active_ifaces = []
        for iface, stat in stats.items():
            if stat.isup and iface in addrs:
                for addr in addrs[iface]:
                    if addr.family.name in ("AF_INET", "2"):  # IPv4
                        active_ifaces.append(f"    {iface}: {addr.address}")
        if active_ifaces:
            net_lines.append("  Interfaces:")
            net_lines.extend(active_ifaces)

        lines.append("\n" + "\n".join(net_lines))
    except Exception as exc:
        log.warning(f"Network stats error: {exc}")


    try:
        procs = []
        for p in psutil.process_iter(["pid", "name", "cpu_percent", "memory_info", "status"]):
            try:
                if p.info["status"] != "zombie":
                    procs.append(p.info)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass

        # Warm up CPU measurements
        psutil.cpu_percent(interval=0.2)

        top_cpu = sorted(procs, key=lambda x: x.get("cpu_percent") or 0, reverse=True)[:5]
        top_ram = sorted(procs, key=lambda x: (x.get("memory_info") or psutil._common.pmem(0, 0)).rss, reverse=True)[:5]

        cpu_proc_lines = ["**📊 Top 5 by CPU**"]
        for p in top_cpu:
            cpu_pct = p.get("cpu_percent") or 0
            mem_mb  = ((p.get("memory_info") or psutil._common.pmem(0, 0)).rss) / (1024 ** 2)
            cpu_proc_lines.append(
                f"  [{p['pid']:>6}] {p['name'][:28]:<28}  CPU {cpu_pct:5.1f}%  RAM {mem_mb:6.1f} MB"
            )

        ram_proc_lines = ["**📊 Top 5 by RAM**"]
        for p in top_ram:
            cpu_pct = p.get("cpu_percent") or 0
            mem_mb  = ((p.get("memory_info") or psutil._common.pmem(0, 0)).rss) / (1024 ** 2)
            ram_proc_lines.append(
                f"  [{p['pid']:>6}] {p['name'][:28]:<28}  RAM {mem_mb:6.1f} MB  CPU {cpu_pct:5.1f}%"
            )

        lines.append("\n" + "\n".join(cpu_proc_lines))
        lines.append("\n" + "\n".join(ram_proc_lines))
    except Exception as exc:
        log.warning(f"Process stats error: {exc}")

    return "\n".join(lines)




def _normalize_proc_name(name: str) -> list[str]:
    """
    Given a user-friendly name like "chrome", return a list of possible
    process names to search for across Windows / macOS / Linux.
    """
    name = name.strip().lower()
    # Strip .exe suffix for matching
    base = name.removesuffix(".exe")

    candidates = {name, base}

    # Common aliases
    _PROC_ALIASES: dict[str, list[str]] = {
        "chrome":        ["chrome", "chrome.exe", "google chrome", "googlechrome"],
        "firefox":       ["firefox", "firefox.exe"],
        "edge":          ["msedge", "msedge.exe", "microsoft edge"],
        "brave":         ["brave", "brave.exe", "brave-browser"],
        "opera":         ["opera", "opera.exe"],
        "discord":       ["discord", "discord.exe"],
        "spotify":       ["spotify", "spotify.exe"],
        "steam":         ["steam", "steam.exe"],
        "notepad":       ["notepad", "notepad.exe"],
        "notepad++":     ["notepad++", "notepad++.exe"],
        "vscode":        ["code", "code.exe", "visual studio code"],
        "vs code":       ["code", "code.exe"],
        "code":          ["code", "code.exe"],
        "explorer":      ["explorer", "explorer.exe"],
        "obs":           ["obs64", "obs32", "obs.exe", "obs64.exe"],
        "vlc":           ["vlc", "vlc.exe"],
        "slack":         ["slack", "slack.exe"],
        "teams":         ["teams", "teams.exe"],
        "zoom":          ["zoom", "zoom.exe"],
        "telegram":      ["telegram", "telegram.exe", "telegramdesktop"],
        "word":          ["winword", "winword.exe"],
        "excel":         ["excel", "excel.exe"],
        "powerpoint":    ["powerpnt", "powerpnt.exe"],
        "outlook":       ["outlook", "outlook.exe"],
        "photoshop":     ["photoshop", "photoshop.exe"],
        "blender":       ["blender", "blender.exe"],
        "task manager":  ["taskmgr", "taskmgr.exe"],
        "cmd":           ["cmd", "cmd.exe"],
        "powershell":    ["powershell", "powershell.exe", "pwsh", "pwsh.exe"],
        "terminal":      ["wt", "wt.exe", "terminal"],
        "pycharm":       ["pycharm64", "pycharm64.exe", "pycharm"],
        "intellij":      ["idea64", "idea64.exe"],
        "postman":       ["postman", "postman.exe"],
        "docker":        ["docker", "docker desktop", "dockerdesktop"],
    }

    if base in _PROC_ALIASES:
        candidates.update(_PROC_ALIASES[base])
    if name in _PROC_ALIASES:
        candidates.update(_PROC_ALIASES[name])

    return list(candidates)


def _find_processes_by_name(name_or_pid: str) -> list:
    """
    Return a list of psutil.Process objects matching name_or_pid.
    Accepts process name (fuzzy), exact exe name, or PID.
    """
    if not PSUTIL_AVAILABLE:
        return []

    # Try PID first
    try:
        pid = int(name_or_pid)
        p   = psutil.Process(pid)
        return [p]
    except (ValueError, psutil.NoSuchProcess, psutil.AccessDenied):
        pass

    candidates = _normalize_proc_name(name_or_pid)
    matches    = []

    for proc in psutil.process_iter(["pid", "name", "exe", "cmdline"]):
        try:
            proc_name = (proc.info.get("name") or "").lower()
            proc_exe  = (proc.info.get("exe")  or "").lower()

            for candidate in candidates:
                if candidate in proc_name or candidate in proc_exe:
                    matches.append(proc)
                    break
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass

    return matches


def handle_close_app(data: dict) -> str:
    """
    Close a running application gracefully (SIGTERM), then forcefully (SIGKILL)
    if it doesn't exit within 3 seconds. Works on Windows, macOS, Linux.
    """
    if not PSUTIL_AVAILABLE:
        return (
            "❌ `psutil` is not installed — required for close_app.\n"
            "Run: `pip install psutil` then restart ZENTRA."
        )

    app_name = (data.get("app") or data.get("app_path") or "").strip()
    if not app_name:
        return "❌ close_app: no app name or PID provided."

    procs = _find_processes_by_name(app_name)

    if not procs:
        # Last resort on Windows: use taskkill
        if platform.system() == "Windows":
            # Try taskkill with the raw name
            exe_name = app_name if app_name.endswith(".exe") else f"{app_name}.exe"
            r = subprocess.run(
                ["taskkill", "/F", "/IM", exe_name],
                capture_output=True, text=True,
            )
            if r.returncode == 0:
                return f"✅ Closed **{app_name}** via taskkill."
            # Also try without .exe
            r2 = subprocess.run(
                ["taskkill", "/F", "/IM", app_name],
                capture_output=True, text=True,
            )
            if r2.returncode == 0:
                return f"✅ Closed **{app_name}** via taskkill."
        return f"❌ No running process found matching **{app_name}**."

    killed  = []
    failed  = []
    skipped = [] 

    PROTECTED = {
        "system", "smss.exe", "csrss.exe", "wininit.exe", "winlogon.exe",
        "lsass.exe", "services.exe", "svchost.exe", "dwm.exe",
        "kernel_task", "launchd", "systemd", "init",
    }

    for proc in procs:
        try:
            pname = proc.name().lower()
            if pname in PROTECTED:
                skipped.append(f"{proc.name()} (PID {proc.pid}) — system process, skipped")
                continue

            log.info(f"Terminating {proc.name()} (PID {proc.pid})")
            proc.terminate()

            try:
                proc.wait(timeout=3)
                killed.append(f"{proc.name()} (PID {proc.pid})")
            except psutil.TimeoutExpired:
                log.warning(f"Process {proc.name()} didn't exit — killing forcefully")
                proc.kill()
                proc.wait(timeout=2)
                killed.append(f"{proc.name()} (PID {proc.pid}) [force-killed]")

        except psutil.NoSuchProcess:
            killed.append(f"(already gone, PID {proc.pid})")
        except psutil.AccessDenied:
            failed.append(f"{proc.name()} (PID {proc.pid}) — access denied")
        except Exception as exc:
            failed.append(f"{proc.name()} (PID {proc.pid}) — {exc}")

    parts = []
    if killed:
        parts.append(f"✅ Closed {len(killed)} process(es):\n" + "\n".join(f"  • {k}" for k in killed))
    if skipped:
        parts.append("⚠️ Skipped (protected):\n" + "\n".join(f"  • {s}" for s in skipped))
    if failed:
        parts.append("❌ Failed:\n" + "\n".join(f"  • {f}" for f in failed))

    return "\n\n".join(parts) or "⚠️ Nothing was closed."




def _take_screenshot_sync() -> tuple[str, str]:
    """
    Take a full-screen screenshot.
    Returns (base64_png_string, saved_file_path).
    """
    Path(SCREENSHOT_FOLDER).mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    save_path = os.path.join(SCREENSHOT_FOLDER, f"screen_{timestamp}.png")

    if PYAUTOGUI_AVAILABLE:
        screenshot = pyautogui.screenshot()
    else:
        # Fallback: PIL ImageGrab (Windows/macOS only)
        screenshot = PIL.ImageGrab.grab()

    # Downscale for vision model if very large (keeps tokens manageable)
    w, h = screenshot.size
    max_dim = 1280
    if w > max_dim or h > max_dim:
        ratio = min(max_dim / w, max_dim / h)
        screenshot = screenshot.resize(
            (int(w * ratio), int(h * ratio)),
            PIL.Image.LANCZOS,
        )

    screenshot.save(save_path, "PNG")

    buf = io.BytesIO()
    screenshot.save(buf, format="PNG")
    b64 = base64.b64encode(buf.getvalue()).decode("utf-8")

    log.info(f"Screenshot taken: {save_path} ({w}x{h} → {screenshot.size})")
    return b64, save_path


def _vision_plan_actions_sync(
    image_b64: str,
    goal: str,
    screen_w: int,
    screen_h: int,
    previous_actions: list[dict] | None = None,
) -> list[dict]:
    """
    Send a screenshot to the vision model and ask it to plan a sequence
    of UI actions to achieve `goal`.
    Returns a list of action dicts.
    """
    prev_str = ""
    if previous_actions:
        prev_str = (
            "\n\nActions already performed:\n"
            + json.dumps(previous_actions, indent=2)
            + "\n\nLook at the current screenshot and decide what to do next."
        )

    prompt = f"""You are a precise screen automation assistant.
Screen resolution: {screen_w}x{screen_h} pixels.
Goal: {goal}{prev_str}

Analyse this screenshot carefully. Return ONLY a raw JSON array of actions — no explanation, no markdown.

Available action types:
  {{"type":"click",        "x":<int>, "y":<int>}}
  {{"type":"double_click", "x":<int>, "y":<int>}}
  {{"type":"right_click",  "x":<int>, "y":<int>}}
  {{"type":"move",         "x":<int>, "y":<int>}}
  {{"type":"drag",         "x1":<int>,"y1":<int>,"x2":<int>,"y2":<int>}}
  {{"type":"scroll",       "x":<int>, "y":<int>, "clicks":<int>}}
  {{"type":"type",         "text":"<string>"}}
  {{"type":"key",          "key":"<pyautogui key>"}}
  {{"type":"hotkey",       "keys":["<key1>","<key2>"]}}
  {{"type":"wait",         "seconds":<float>}}
  {{"type":"screenshot"}}
  {{"type":"done",         "message":"<what was accomplished>"}}

Rules:
- Be precise with coordinates — click the centre of UI elements
- Use "screenshot" to verify state before and after important actions
- Use "wait" after clicks that open menus/dialogs (0.3–1.0 seconds)
- Use "key":"escape" to dismiss unintended popups
- Include "done" as the last action with a description of what was accomplished
- If the goal is already achieved in the screenshot, return [{{"type":"done","message":"Already done: <reason>"}}]
- ONLY return the JSON array, nothing else"""

    raw = _ollama_vision_sync(image_b64, prompt, max_tokens=800)
    log.info(f"Vision plan (raw): {raw[:400]}")

    # Extract JSON array
    raw_clean = re.sub(r"<think>[\s\S]*?</think>", "", raw, flags=re.IGNORECASE).strip()
    for text in [raw_clean, raw]:
        # Try direct parse
        try:
            parsed = json.loads(text.strip())
            if isinstance(parsed, list):
                return parsed
        except json.JSONDecodeError:
            pass
        # Try extracting array
        m = re.search(r"\[[\s\S]*\]", text)
        if m:
            try:
                parsed = json.loads(m.group(0))
                if isinstance(parsed, list):
                    return parsed
            except json.JSONDecodeError:
                pass

    log.warning("Vision model returned no parsable action list.")
    return [{"type": "done", "message": "Could not plan actions from screenshot."}]


def _execute_screen_actions_sync(
    actions: list[dict],
    screen_w: int,
    screen_h: int,
    goal: str,
    use_vision: bool = True,
) -> dict:
    """
    Execute a list of screen actions.
    Returns a dict with keys: actions_taken, screenshots, final_message, error
    """
    if not PYAUTOGUI_AVAILABLE:
        return {
            "actions_taken": [],
            "screenshots":   [],
            "final_message": "",
            "error": (
                "❌ `pyautogui` is not installed.\n"
                "Run: `pip install pyautogui pillow` then restart ZENTRA."
            ),
        }

    result = {
        "actions_taken": [],
        "screenshots":   [],
        "final_message": "",
        "error":         "",
    }

    def clamp(val: int, lo: int, hi: int) -> int:
        return max(lo, min(hi, val))

    executed_count = 0

    for i, action in enumerate(actions[:MAX_SCREEN_ACTIONS]):
        atype = action.get("type", "").lower()
        log.info(f"Screen action [{i+1}]: {action}")

        try:
            if atype == "done":
                result["final_message"] = action.get("message", "Task completed.")
                result["actions_taken"].append({"type": "done", "message": result["final_message"]})
                break

            elif atype == "click":
                x = clamp(int(action["x"]), 0, screen_w - 1)
                y = clamp(int(action["y"]), 0, screen_h - 1)
                pyautogui.click(x, y)
                result["actions_taken"].append({"type": "click", "x": x, "y": y})
                time.sleep(SCREEN_ACTION_DELAY)

            elif atype == "double_click":
                x = clamp(int(action["x"]), 0, screen_w - 1)
                y = clamp(int(action["y"]), 0, screen_h - 1)
                pyautogui.doubleClick(x, y)
                result["actions_taken"].append({"type": "double_click", "x": x, "y": y})
                time.sleep(SCREEN_ACTION_DELAY)

            elif atype == "right_click":
                x = clamp(int(action["x"]), 0, screen_w - 1)
                y = clamp(int(action["y"]), 0, screen_h - 1)
                pyautogui.rightClick(x, y)
                result["actions_taken"].append({"type": "right_click", "x": x, "y": y})
                time.sleep(SCREEN_ACTION_DELAY)

            elif atype == "move":
                x = clamp(int(action["x"]), 0, screen_w - 1)
                y = clamp(int(action["y"]), 0, screen_h - 1)
                pyautogui.moveTo(x, y, duration=0.2)
                result["actions_taken"].append({"type": "move", "x": x, "y": y})

            elif atype == "drag":
                x1 = clamp(int(action["x1"]), 0, screen_w - 1)
                y1 = clamp(int(action["y1"]), 0, screen_h - 1)
                x2 = clamp(int(action["x2"]), 0, screen_w - 1)
                y2 = clamp(int(action["y2"]), 0, screen_h - 1)
                pyautogui.moveTo(x1, y1, duration=0.15)
                pyautogui.dragTo(x2, y2, duration=0.4, button="left")
                result["actions_taken"].append({"type": "drag", "x1": x1, "y1": y1, "x2": x2, "y2": y2})
                time.sleep(SCREEN_ACTION_DELAY)

            elif atype == "scroll":
                x      = clamp(int(action.get("x", screen_w // 2)), 0, screen_w - 1)
                y      = clamp(int(action.get("y", screen_h // 2)), 0, screen_h - 1)
                clicks = int(action.get("clicks", 3))
                pyautogui.scroll(clicks, x=x, y=y)
                result["actions_taken"].append({"type": "scroll", "x": x, "y": y, "clicks": clicks})
                time.sleep(0.2)

            elif atype == "type":
                text = str(action.get("text", ""))
                pyautogui.typewrite(text, interval=0.03)
                result["actions_taken"].append({"type": "type", "text": text})
                time.sleep(0.1)

            elif atype == "key":
                key = str(action.get("key", ""))
                if key:
                    pyautogui.press(key)
                    result["actions_taken"].append({"type": "key", "key": key})
                    time.sleep(0.1)

            elif atype == "hotkey":
                keys = action.get("keys", [])
                if keys:
                    pyautogui.hotkey(*keys)
                    result["actions_taken"].append({"type": "hotkey", "keys": keys})
                    time.sleep(0.15)

            elif atype == "wait":
                secs = float(action.get("seconds", 0.5))
                secs = min(secs, 10.0)  # Cap at 10s for safety
                time.sleep(secs)
                result["actions_taken"].append({"type": "wait", "seconds": secs})

            elif atype == "screenshot":
                b64, path = _take_screenshot_sync()
                result["screenshots"].append(path)
                result["actions_taken"].append({"type": "screenshot", "path": path})
                log.info(f"Mid-action screenshot: {path}")

                # If vision is available, re-evaluate after screenshot
                if use_vision and i < len(actions) - 1:
                    remaining_goal = f"Continue: {goal}"
                    new_plan = _vision_plan_actions_sync(
                        b64, remaining_goal, screen_w, screen_h,
                        previous_actions=result["actions_taken"]
                    )
                    if new_plan:
                        # Replace remaining actions with updated plan
                        actions = result["actions_taken"] + new_plan
                        log.info(f"Re-planned after screenshot: {len(new_plan)} new action(s)")

            else:
                log.warning(f"Unknown screen action type: {atype}")

            executed_count += 1

        except pyautogui.FailSafeException:
            result["error"] = (
                "🛑 PyAutoGUI failsafe triggered — mouse moved to screen corner.\n"
                "Move mouse away from the corner to resume."
            )
            break
        except Exception as exc:
            log.error(f"Screen action error ({atype}): {exc}", exc_info=True)
            result["error"] = f"❌ Action `{atype}` failed: {exc}"
            break

    if not result["final_message"] and not result["error"]:
        result["final_message"] = f"Executed {executed_count} screen action(s)."

    return result


def handle_screen_action_sync(data: dict) -> str:
    """
    Full screen_action pipeline:
    1. Take a screenshot
    2. If no actions provided, use vision model to plan them
    3. Execute the actions
    4. Take a final screenshot for verification
    5. Return a rich summary
    """
    if not PYAUTOGUI_AVAILABLE:
        return (
            "❌ Screen automation libraries not installed.\n"
            "Run: `pip install pyautogui pillow` then restart ZENTRA.\n"
            "On Linux you may also need: `sudo apt install python3-tk python3-dev`"
        )

    goal           = (data.get("screen_goal") or data.get("reply") or "").strip()
    preset_actions = data.get("screen_actions", [])
    if not isinstance(preset_actions, list):
        preset_actions = []

    if not goal and not preset_actions:
        return "❌ screen_action: provide a goal or action list."

    # Get screen dimensions
    screen_w, screen_h = pyautogui.size()
    log.info(f"Screen resolution: {screen_w}x{screen_h}")

    # 1. Take initial screenshot
    try:
        b64, initial_path = _take_screenshot_sync()
    except Exception as exc:
        return f"❌ Could not take screenshot: {exc}"

    # 2. Plan actions via vision model if none provided
    actions = preset_actions
    if not actions and goal:
        log.info("No preset actions — planning via vision model...")
        actions = _vision_plan_actions_sync(b64, goal, screen_w, screen_h)
        if not actions:
            return (
                "❌ Vision model could not plan actions from the screenshot.\n"
                f"Make sure `{OLLAMA_VISION_MODEL}` is pulled: "
                f"`ollama pull {OLLAMA_VISION_MODEL}`"
            )

    log.info(f"Executing {len(actions)} screen action(s) for goal: {goal}")

    # 3. Execute actions
    exec_result = _execute_screen_actions_sync(
        actions, screen_w, screen_h, goal, use_vision=(not preset_actions)
    )

    # 4. Take final screenshot
    try:
        _, final_path = _take_screenshot_sync()
        exec_result["screenshots"].append(final_path)
    except Exception:
        pass

    # 5. Build report
    parts = []

    if goal:
        parts.append(f"🖥️ **Screen Action** — *{goal}*")
    else:
        parts.append("🖥️ **Screen Action**")

    parts.append(f"📐 Screen: {screen_w}×{screen_h}")
    parts.append(f"📸 Initial screenshot: `{initial_path}`")

    if exec_result["actions_taken"]:
        action_lines = []
        for act in exec_result["actions_taken"]:
            atype = act.get("type", "?")
            if atype == "click":
                action_lines.append(f"  🖱️ Click ({act['x']}, {act['y']})")
            elif atype == "double_click":
                action_lines.append(f"  🖱️ Double-click ({act['x']}, {act['y']})")
            elif atype == "right_click":
                action_lines.append(f"  🖱️ Right-click ({act['x']}, {act['y']})")
            elif atype == "move":
                action_lines.append(f"  🖱️ Move → ({act['x']}, {act['y']})")
            elif atype == "drag":
                action_lines.append(f"  🖱️ Drag ({act['x1']},{act['y1']}) → ({act['x2']},{act['y2']})")
            elif atype == "scroll":
                direction = "↑" if act["clicks"] > 0 else "↓"
                action_lines.append(f"  🖱️ Scroll {direction} {abs(act['clicks'])}× at ({act['x']},{act['y']})")
            elif atype == "type":
                text_preview = act["text"][:40] + ("…" if len(act["text"]) > 40 else "")
                action_lines.append(f"  ⌨️ Type: `{text_preview}`")
            elif atype == "key":
                action_lines.append(f"  ⌨️ Key: `{act['key']}`")
            elif atype == "hotkey":
                action_lines.append(f"  ⌨️ Hotkey: `{'+'.join(act['keys'])}`")
            elif atype == "wait":
                action_lines.append(f"  ⏱️ Wait {act['seconds']}s")
            elif atype == "screenshot":
                action_lines.append(f"  📸 Screenshot → `{act.get('path', '?')}`")
            elif atype == "done":
                action_lines.append(f"  ✅ Done: {act.get('message', '')}")
        parts.append("**Actions executed:**\n" + "\n".join(action_lines))

    if exec_result["screenshots"]:
        last_ss = exec_result["screenshots"][-1]
        parts.append(f"📸 Final screenshot: `{last_ss}`")

    if exec_result["final_message"]:
        parts.append(f"✅ **Result:** {exec_result['final_message']}")

    if exec_result["error"]:
        parts.append(exec_result["error"])

    return "\n".join(parts)


_APP_ALIASES: dict[str, str] = {
    # Browsers
    "chrome": "chrome", "google chrome": "chrome",
    "firefox": "firefox",
    "edge": "msedge", "microsoft edge": "msedge",
    "brave": "brave", "opera": "opera", "opera gx": "opera",
    "vivaldi": "vivaldi", "tor": "tor browser",
    # Gaming / launchers
    "steam": "steam",
    "epic": "epicgameslauncher", "epic games": "epicgameslauncher",
    "epic games launcher": "epicgameslauncher",
    "gog": "goggalaxy", "gog galaxy": "goggalaxy",
    "origin": "origin", "ea app": "eadesktop",
    "ubisoft": "ubisoftconnect", "uplay": "ubisoftconnect",
    "ubisoft connect": "ubisoftconnect",
    "battle.net": "battle.net", "battlenet": "battle.net",
    "riot": "riotclientservices", "riot games": "riotclientservices",
    "league": "riotclientservices",
    "minecraft": "minecraftlauncher",
    "xbox": "xboxapp", "xbox app": "xboxapp",
    # Media
    "spotify": "spotify", "vlc": "vlc", "mpv": "mpv", "plex": "plex",
    "obs": "obs64", "obs studio": "obs64",
    "audacity": "audacity", "winamp": "winamp",
    "foobar": "foobar2000", "foobar2000": "foobar2000",
    # Communication
    "discord": "discord", "slack": "slack",
    "teams": "teams", "microsoft teams": "teams",
    "zoom": "zoom", "telegram": "telegram",
    "signal": "signal", "whatsapp": "whatsapp", "skype": "skype",
    # Dev tools
    "vscode": "code", "visual studio code": "code",
    "vs code": "code", "code": "code",
    "visual studio": "devenv",
    "pycharm": "pycharm64", "intellij": "idea64",
    "webstorm": "webstorm64", "clion": "clion64",
    "rider": "rider64", "datagrip": "datagrip64",
    "android studio": "studio64", "cursor": "cursor",
    "sublime": "sublime_text", "sublime text": "sublime_text",
    "notepad++": "notepad++", "atom": "atom",
    "vim": "vim", "neovim": "nvim",
    "terminal": "wt", "windows terminal": "wt",
    "powershell": "powershell", "cmd": "cmd",
    "command prompt": "cmd", "git bash": "git-bash", "wsl": "wsl",
    "postman": "postman", "insomnia": "insomnia",
    "docker": "docker desktop", "docker desktop": "docker desktop",
    "dbeaver": "dbeaver", "tableplus": "tableplus",
    # Productivity / Office
    "notepad": "notepad", "wordpad": "wordpad",
    "word": "winword", "excel": "excel",
    "powerpoint": "powerpnt", "outlook": "outlook",
    "onenote": "onenote", "access": "msaccess",
    "libreoffice": "soffice", "libreoffice writer": "swriter",
    "libreoffice calc": "scalc",
    "notion": "notion", "obsidian": "obsidian", "todoist": "todoist",
    # Creative
    "photoshop": "photoshop", "illustrator": "illustrator",
    "premiere": "premiere", "after effects": "afterfx",
    "lightroom": "lightroom", "gimp": "gimp",
    "inkscape": "inkscape", "blender": "blender",
    "figma": "figma", "davinci": "resolve", "davinci resolve": "resolve",
    # System
    "task manager": "taskmgr", "file explorer": "explorer",
    "explorer": "explorer", "calculator": "calc",
    "paint": "mspaint", "snipping tool": "snippingtool",
    "settings": "ms-settings:", "control panel": "control",
    "registry editor": "regedit",
    "device manager": "devmgmt.msc",
    "event viewer": "eventvwr.msc",
    "disk management": "diskmgmt.msc",
}

_WIN_SEARCH_ROOTS: list[str] = [
    r"C:\Program Files",
    r"C:\Program Files (x86)",
    os.path.expandvars(r"%LOCALAPPDATA%"),
    os.path.expandvars(r"%APPDATA%"),
    os.path.expandvars(r"%LOCALAPPDATA%\Programs"),
]

_WIN_KNOWN_PATHS: dict[str, list[str]] = {
    "steam": [
        r"C:\Program Files (x86)\Steam\steam.exe",
        r"C:\Program Files\Steam\steam.exe",
        os.path.expandvars(r"%PROGRAMFILES(X86)%\Steam\steam.exe"),
    ],
    "epicgameslauncher": [
        r"C:\Program Files (x86)\Epic Games\Launcher\Portal\Binaries\Win32\EpicGamesLauncher.exe",
        r"C:\Program Files\Epic Games\Launcher\Portal\Binaries\Win64\EpicGamesLauncher.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\EpicGamesLauncher\Portal\Binaries\Win32\EpicGamesLauncher.exe"),
    ],
    "goggalaxy": [
        r"C:\Program Files (x86)\GOG Galaxy\GalaxyClient.exe",
        r"C:\Program Files\GOG Galaxy\GalaxyClient.exe",
    ],
    "origin": [
        r"C:\Program Files (x86)\Origin\Origin.exe",
        r"C:\Program Files\Origin\Origin.exe",
    ],
    "eadesktop": [
        os.path.expandvars(r"%LOCALAPPDATA%\Electronic Arts\EA Desktop\EA Desktop\EADesktop.exe"),
    ],
    "ubisoftconnect": [
        r"C:\Program Files (x86)\Ubisoft\Ubisoft Game Launcher\UbisoftConnect.exe",
        r"C:\Program Files\Ubisoft\Ubisoft Game Launcher\UbisoftConnect.exe",
    ],
    "battle.net": [
        r"C:\Program Files (x86)\Battle.net\Battle.net.exe",
        r"C:\Program Files\Battle.net\Battle.net.exe",
    ],
    "riotclientservices": [
        os.path.expandvars(r"%LOCALAPPDATA%\Riot Games\Riot Client\RiotClientServices.exe"),
    ],
    "discord": [
        os.path.expandvars(r"%LOCALAPPDATA%\Discord\Update.exe"),
        os.path.expandvars(r"%LOCALAPPDATA%\Discord\app-*\Discord.exe"),
    ],
    "spotify": [
        os.path.expandvars(r"%APPDATA%\Spotify\Spotify.exe"),
        os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\WindowsApps\Spotify.exe"),
    ],
    "telegram": [
        os.path.expandvars(r"%APPDATA%\Telegram Desktop\Telegram.exe"),
        os.path.expandvars(r"%LOCALAPPDATA%\Telegram Desktop\Telegram.exe"),
    ],
    "obs64": [
        r"C:\Program Files\obs-studio\bin\64bit\obs64.exe",
        r"C:\Program Files (x86)\obs-studio\bin\64bit\obs64.exe",
    ],
    "postman": [
        os.path.expandvars(r"%LOCALAPPDATA%\Postman\Postman.exe"),
        os.path.expandvars(r"%APPDATA%\Postman\Postman.exe"),
    ],
}


def _registry_lookup_windows(app_name: str) -> str | None:
    if not WINREG_AVAILABLE:
        return None
    search    = app_name.lower().replace(".exe", "")
    reg_paths = [
        r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall",
        r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall",
    ]
    hives = [winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER]
    for hive in hives:
        for reg_path in reg_paths:
            try:
                key   = winreg.OpenKey(hive, reg_path)
                count = winreg.QueryInfoKey(key)[0]
            except OSError:
                continue
            for i in range(count):
                try:
                    sub_name = winreg.EnumKey(key, i)
                    sub_key  = winreg.OpenKey(key, sub_name)
                except OSError:
                    continue
                try:
                    display_name, _ = winreg.QueryValueEx(sub_key, "DisplayName")
                    if search not in display_name.lower():
                        continue
                    for value_name in ("DisplayIcon", "InstallLocation"):
                        try:
                            val, _ = winreg.QueryValueEx(sub_key, value_name)
                            val    = val.split(",")[0].strip().strip('"')
                            if val.lower().endswith(".exe") and Path(val).exists():
                                log.info(f"Registry found: {display_name} → {val}")
                                return val
                            folder = Path(val)
                            if folder.is_dir():
                                for exe in folder.glob("*.exe"):
                                    return str(exe)
                        except OSError:
                            pass
                except OSError:
                    pass
                finally:
                    sub_key.Close()
            key.Close()
    return None


def _glob_known_path(pattern: str) -> str | None:
    if "*" not in pattern:
        p = Path(pattern)
        return str(p) if p.exists() else None
    parent = Path(pattern).parent
    name   = Path(pattern).name
    try:
        matches = sorted(parent.glob(name), reverse=True)
        return str(matches[0]) if matches else None
    except OSError:
        return None


def _find_app_windows(canonical: str, original: str) -> str | None:
    found = shutil.which(canonical) or shutil.which(original)
    if found:
        return found
    for key in (canonical, original):
        for path_pattern in _WIN_KNOWN_PATHS.get(key, []):
            result = _glob_known_path(path_pattern)
            if result:
                return result
    reg = _registry_lookup_windows(canonical) or _registry_lookup_windows(original)
    if reg:
        return reg
    search_terms = {canonical.lower(), original.lower()}
    search_terms.discard("")
    for root in _WIN_SEARCH_ROOTS:
        root_path = Path(root)
        if not root_path.is_dir():
            continue
        try:
            for sub in root_path.iterdir():
                if not sub.is_dir():
                    continue
                if any(term in sub.name.lower() for term in search_terms):
                    exes = sorted(sub.glob("*.exe"))
                    if exes:
                        log.info(f"Folder scan found: {exes[0]}")
                        return str(exes[0])
        except PermissionError:
            pass
    return None


def _find_app_macos(canonical: str, original: str) -> str | None:
    for name in [original, canonical, original.title(), canonical.title()]:
        try:
            result = subprocess.run(
                ["mdfind", f"kMDItemCFBundleIdentifier == '*{name.lower()}*'"],
                capture_output=True, text=True, timeout=5,
            )
            lines = [l.strip() for l in result.stdout.splitlines() if l.strip()]
            if lines:
                return lines[0]
        except Exception:
            pass
    return None


def _find_app_linux(canonical: str, original: str) -> str | None:
    found = shutil.which(canonical) or shutil.which(original)
    if found:
        return found
    desktop_dirs = [
        Path("/usr/share/applications"),
        Path("/usr/local/share/applications"),
        Path.home() / ".local/share/applications",
    ]
    search = {canonical.lower(), original.lower()}
    for d in desktop_dirs:
        if not d.is_dir():
            continue
        for desktop in d.glob("*.desktop"):
            text = desktop.read_text(errors="replace").lower()
            if any(s in text for s in search):
                for line in desktop.read_text(errors="replace").splitlines():
                    if line.startswith("Exec="):
                        return line[5:].split()[0].strip()
    return None


def _platform_launch(target: str, system: str) -> None:
    if system == "Windows":
        os.startfile(target)              # type: ignore[attr-defined]
    elif system == "Darwin":
        subprocess.Popen(["open", target])
    else:
        subprocess.Popen([target])


def handle_open_app(data: dict) -> str:
    app_raw  = data.get("app", "").strip()
    app_path = data.get("app_path", "").strip()
    system   = platform.system()

    if not app_raw and not app_path:
        return "❌ open_app: no app name or path was provided."

    if app_path:
        p = Path(app_path)
        if not p.exists():
            return f"❌ Path not found: `{app_path}`"
        try:
            _platform_launch(str(p), system)
            return f"✅ Opened: `{app_path}`"
        except Exception as exc:
            return f"❌ Could not open `{app_path}`: {exc}"

    app_lower = app_raw.lower().strip()
    canonical = _APP_ALIASES.get(app_lower, app_lower)
    log.info(f"open_app: raw='{app_raw}' → canonical='{canonical}'")

    if system == "Windows":
        exe = _find_app_windows(canonical, app_lower)
        if exe:
            try:
                _platform_launch(exe, system)
                return f"✅ Launched **{app_raw}**."
            except Exception as exc:
                return f"❌ Found `{exe}` but couldn't launch it: {exc}"
        try:
            os.startfile(canonical)       # type: ignore[attr-defined]
            return f"✅ Launched **{app_raw}**."
        except Exception:
            pass

    elif system == "Darwin":
        exe = _find_app_macos(canonical, app_lower)
        if exe:
            try:
                subprocess.Popen(["open", exe])
                return f"✅ Launched **{app_raw}**."
            except Exception as exc:
                return f"❌ Found `{exe}` but couldn't launch it: {exc}"
        for name in [app_raw, app_raw.title(), canonical, canonical.title()]:
            try:
                r = subprocess.run(["open", "-a", name], capture_output=True, text=True)
                if r.returncode == 0:
                    return f"✅ Launched **{name}**."
            except Exception:
                pass

    else:
        exe = _find_app_linux(canonical, app_lower)
        if exe:
            try:
                subprocess.Popen([exe])
                return f"✅ Launched **{app_raw}**."
            except Exception as exc:
                return f"❌ Found `{exe}` but couldn't launch it: {exc}"
        try:
            subprocess.Popen(["xdg-open", app_lower])
            return f"✅ Launched **{app_raw}** via xdg-open."
        except Exception:
            pass

    return (
        f"❌ Couldn't find **{app_raw}** on your system.\n"
        f"💡 Try telling me the full path and I'll open it directly."
    )

def handle_vscode_open(data: dict) -> str:
    target = (
        data.get("app_path", "").strip()
        or data.get("folder", "").strip()
        or BASE_FOLDER
    )
    target = str(Path(target).expanduser())
    if not shutil.which("code"):
        return (
            "❌ `code` command not found.\n"
            "Install VSCode and enable 'Add to PATH' during setup."
        )
    try:
        subprocess.Popen(["code", target])
        return f"✅ Opened in VSCode: `{target}`"
    except Exception as exc:
        return f"❌ Could not open VSCode: {exc}"


def handle_github_push(data: dict) -> str:
    git_folder = data.get("git_folder", "").strip() or BASE_FOLDER
    commit_msg = data.get("git_message", "").strip() or "ZENTRA auto-commit"

    repo_path = Path(git_folder)
    if not repo_path.exists():
        return f"❌ git folder not found: `{git_folder}`"
    if not shutil.which("git"):
        return "❌ `git` is not installed or not on PATH."

    def run_git(*args):
        r = subprocess.run(
            ["git", *args],
            capture_output=True, text=True, cwd=str(repo_path),
        )
        return r.returncode, r.stdout.strip(), r.stderr.strip()

    steps = []

    code, out, err = run_git("add", ".")
    if code != 0:
        return f"❌ `git add` failed:\n```\n{err or out}\n```"
    steps.append("✅ `git add .`")

    code, out, err = run_git("commit", "-m", commit_msg)
    if code != 0:
        msg = (out + err).lower()
        if "nothing to commit" in msg:
            return "ℹ️ Nothing to commit — working tree is already clean."
        return f"❌ `git commit` failed:\n```\n{err or out}\n```"
    steps.append(f"✅ `git commit` — \"{commit_msg}\"")

    code, out, err = run_git("push")
    if code != 0:
        return "\n".join(steps) + f"\n❌ `git push` failed:\n```\n{err or out}\n```"
    steps.append("✅ `git push`")

    return "\n".join(steps) + "\n\n🎉 Code pushed successfully!"


def handle_chat(data: dict) -> str:
    return data.get("reply") or "I'm not sure how to respond to that."


def _get_google_credentials():
    if not GOOGLE_AVAILABLE:
        raise RuntimeError(
            "Google libraries not installed.\n"
            "Run: pip install google-auth google-auth-oauthlib "
            "google-auth-httplib2 google-api-python-client"
        )
    creds = None
    if Path(GOOGLE_TOKEN_FILE).exists():
        with open(GOOGLE_TOKEN_FILE, "rb") as fh:
            creds = pickle.load(fh)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            log.info("Refreshing Google token…")
            creds.refresh(Request())
        else:
            if not Path(GOOGLE_CREDENTIALS_FILE).exists():
                raise FileNotFoundError(
                    f"credentials.json not found at {GOOGLE_CREDENTIALS_FILE}.\n"
                    "Download from Google Cloud Console → APIs & Services → Credentials."
                )
            flow  = InstalledAppFlow.from_client_secrets_file(GOOGLE_CREDENTIALS_FILE, GOOGLE_SCOPES)
            creds = flow.run_local_server(port=0)
            log.info("Google OAuth completed — token saved.")
        with open(GOOGLE_TOKEN_FILE, "wb") as fh:
            pickle.dump(creds, fh)

    return creds


def _gmail_service():
    return google_build("gmail", "v1", credentials=_get_google_credentials(), cache_discovery=False)


def _calendar_service():
    return google_build("calendar", "v3", credentials=_get_google_credentials(), cache_discovery=False)


def _get_header(headers: list, name: str) -> str:
    for h in headers:
        if h["name"].lower() == name.lower():
            return h["value"]
    return ""


def _clean_sender(raw: str) -> str:
    """Extract 'Name' from 'Name <email@domain.com>' or return the raw address."""
    m = re.match(r'^"?([^"<]+?)"?\s*<[^>]+>$', raw.strip())
    if m:
        return m.group(1).strip()
    return raw.strip()


def _decode_email_body(msg: dict) -> str:
    def _extract(part):
        mime = part.get("mimeType", "")
        if mime == "text/plain":
            data = part.get("body", {}).get("data", "")
            if data:
                return base64.urlsafe_b64decode(data + "==").decode("utf-8", errors="replace")
        if mime == "text/html" and not part.get("parts"):
            # Fallback: strip HTML tags for plain text
            data = part.get("body", {}).get("data", "")
            if data:
                html = base64.urlsafe_b64decode(data + "==").decode("utf-8", errors="replace")
                return re.sub(r"<[^>]+>", " ", html)
        for sub in part.get("parts", []):
            result = _extract(sub)
            if result:
                return result
        return ""

    text = _extract(msg.get("payload", {}))
    return text.strip() or msg.get("snippet", "")


def _gmail_api_call_with_backoff(fn, max_retries: int = 3):
    """Execute a Google API call with exponential backoff on rate-limit errors."""
    for attempt in range(max_retries):
        try:
            return fn()
        except HttpError as exc:
            if exc.resp.status in (429, 500, 503) and attempt < max_retries - 1:
                wait = 2 ** attempt
                log.warning(f"Gmail API rate limit / server error, retrying in {wait}s…")
                time.sleep(wait)
            else:
                raise
    return None


def _fetch_unread_emails_sync(since_hours: int = 24, query_extra: str = "") -> list[dict]:
    try:
        service  = _gmail_service()
        after_ts = int((datetime.now(timezone.utc) - timedelta(hours=since_hours)).timestamp())
        q = f"is:unread after:{after_ts}"
        if query_extra:
            q += f" {query_extra}"

        results = _gmail_api_call_with_backoff(
            lambda: service.users().messages().list(
                userId="me", q=q, maxResults=MAX_DIGEST_EMAILS
            ).execute()
        )

        emails = []
        for m in (results or {}).get("messages", []):
            try:
                msg = _gmail_api_call_with_backoff(
                    lambda mid=m["id"]: service.users().messages().get(
                        userId="me", id=mid, format="full"
                    ).execute()
                )
                if not msg:
                    continue
                headers  = msg.get("payload", {}).get("headers", [])
                raw_from = _get_header(headers, "From")
                body_text = _decode_email_body(msg)

                emails.append({
                    "id":        m["id"],
                    "thread_id": msg.get("threadId", ""),
                    "sender":    _clean_sender(raw_from),
                    "sender_raw": raw_from,
                    "subject":   _get_header(headers, "Subject"),
                    "snippet":   msg.get("snippet", ""),
                    "body":      body_text[:3000],
                    "date":      _get_header(headers, "Date"),
                    "labels":    msg.get("labelIds", []),
                })
            except Exception as exc:
                log.warning(f"Failed to fetch email {m['id']}: {exc}")
                continue

        log.info(f"Fetched {len(emails)} unread emails (q='{q}').")
        return emails
    except Exception as exc:
        log.error(f"Gmail fetch error: {exc}")
        return []


def _importance_score(sender: str, subject: str, snippet: str) -> int:
    """
    Returns an integer 0–3:
      0 = not important
      1 = mildly important (keyword match)
      2 = important (sender list or strong keyword)
      3 = critical (AI confirmed + keyword)
    """
    combined = f"{sender} {subject} {snippet}".lower()
    score = 0


    if any(s.lower() in combined for s in IMPORTANT_SENDERS):
        score += 2


    keyword_hits = sum(1 for kw in IMPORTANT_KEYWORDS if kw in combined)
    if keyword_hits >= 2:
        score += 2
    elif keyword_hits == 1:
        score += 1


    if score == 1:
        answer = _ollama_raw_sync(
            "You are a strict email triage assistant. Reply only YES or NO.",
            f"From: {sender}\nSubject: {subject}\nPreview: {snippet}\n\n"
            "Is this email time-sensitive or requires action today?",
            max_tokens=5,
        )
        if answer.strip().upper().startswith("Y"):
            score += 1

    return score


def _format_email_digest(emails: list[dict]) -> str:
    if not emails:
        return "📭 No unread emails in the last 24 hours."


    def email_sort_key(e):
        return _importance_score(e["sender"], e["subject"], e["snippet"])

    emails_sorted = sorted(emails, key=email_sort_key, reverse=True)

    lines = [f"📧 **Email Digest** — {len(emails)} unread\n"]
    for i, email in enumerate(emails_sorted, 1):
        score = email_sort_key(email)
        urgency = "🔴 " if score >= 2 else ("🟡 " if score == 1 else "")

        summary = _ollama_raw_sync(
            "Summarise this email in one clear sentence. No preamble.",
            f"Subject: {email['subject']}\n\n{email['body'] or email['snippet']}",
            max_tokens=80,
        )

        date_str = ""
        try:
            from email.utils import parsedate_to_datetime
            dt = parsedate_to_datetime(email["date"])
            date_str = f"  ·  {dt.strftime('%d %b %H:%M')}"
        except Exception:
            pass

        lines.append(
            f"**{i}.** {urgency}**{email['sender']}**{date_str}\n"
            f"   📌 {email['subject'] or '(no subject)'}\n"
            f"   💬 {summary}\n"
        )

    return "\n".join(lines)


def _fetch_email_search_sync(query: str, max_results: int = 10) -> list[dict]:
    """Search emails with a natural language query converted to Gmail search syntax."""
    
    gmail_q = query
    if "from:" not in query.lower() and "subject:" not in query.lower():
  
        gmail_q = query

    try:
        service = _gmail_service()
        results = _gmail_api_call_with_backoff(
            lambda: service.users().messages().list(
                userId="me", q=gmail_q, maxResults=max_results
            ).execute()
        )
        emails = []
        for m in (results or {}).get("messages", []):
            try:
                msg     = _gmail_api_call_with_backoff(
                    lambda mid=m["id"]: service.users().messages().get(
                        userId="me", id=mid, format="full"
                    ).execute()
                )
                headers = msg.get("payload", {}).get("headers", [])
                emails.append({
                    "id":       m["id"],
                    "sender":   _clean_sender(_get_header(headers, "From")),
                    "subject":  _get_header(headers, "Subject"),
                    "snippet":  msg.get("snippet", ""),
                    "body":     _decode_email_body(msg)[:2000],
                    "date":     _get_header(headers, "Date"),
                })
            except Exception:
                continue
        return emails
    except Exception as exc:
        log.error(f"Email search error: {exc}")
        return []


def _parse_send_request_sync(user_text: str) -> dict | None:
    """Use AI to extract recipient, subject, and body from natural language."""
    raw = _ollama_raw_sync(
        "Extract email send details from the user's request. "
        "Reply ONLY with raw JSON, no markdown:\n"
        '{"to":"email@example.com","subject":"Subject here","body":"Email body here"}\n'
        "If no email address given, put the name in 'to'. If no subject, infer one.",
        user_text,
        max_tokens=300,
    )
    try:
        cleaned = re.sub(r"```(?:json)?\n?", "", raw).replace("```", "").strip()
        return json.loads(cleaned)
    except Exception:
        log.warning(f"Could not parse send JSON: {raw[:200]}")
        return None


def _send_email_sync(to: str, subject: str, body: str, reply_to_thread: str = "") -> str:
    try:
        service = _gmail_service()
        msg     = MIMEMultipart("alternative")
        msg["To"]      = to
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))

        raw_bytes = base64.urlsafe_b64encode(msg.as_bytes()).decode("utf-8")
        body_payload: dict = {"raw": raw_bytes}
        if reply_to_thread:
            body_payload["threadId"] = reply_to_thread

        sent = _gmail_api_call_with_backoff(
            lambda: service.users().messages().send(
                userId="me", body=body_payload
            ).execute()
        )
        log.info(f"Email sent to {to}: {subject}")
        return f"✅ Email sent to **{to}**\n📌 Subject: {subject}"
    except Exception as exc:
        log.error(f"Gmail send error: {exc}")
        return f"❌ Failed to send email: {exc}"


async def handle_gmail_summary(data: dict) -> str:
    if not GOOGLE_AVAILABLE:
        return _google_not_available()
    query  = data.get("app", "").strip()
    if query:
        emails = await asyncio.to_thread(_fetch_email_search_sync, query, 15)
    else:
        emails = await asyncio.to_thread(_fetch_unread_emails_sync, 48)
    return await asyncio.to_thread(_format_email_digest, emails)


async def handle_gmail_send(data: dict) -> str:
    if not GOOGLE_AVAILABLE:
        return _google_not_available()
    user_text = data.get("reply", "").strip()
    if not user_text:
        return "❌ No send details provided."
    parsed = await asyncio.to_thread(_parse_send_request_sync, user_text)
    if not parsed:
        return "❌ Couldn't parse send request. Try: *'Send an email to john@example.com saying…'*"
    to      = parsed.get("to", "")
    subject = parsed.get("subject", "(no subject)")
    body    = parsed.get("body", "")
    if not to:
        return "❌ No recipient found in your request."
    if not body:
        return "❌ No email body found in your request."
    return await asyncio.to_thread(_send_email_sync, to, subject, body)


def _fmt_event_time(iso_str: str) -> str:
    try:
        dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
        return dt.astimezone().strftime("%I:%M %p")
    except Exception:
        return iso_str


def _fmt_event_duration(start: str, end: str) -> str:
    try:
        s = datetime.fromisoformat(start.replace("Z", "+00:00"))
        e = datetime.fromisoformat(end.replace("Z", "+00:00"))
        mins = int((e - s).total_seconds() / 60)
        if mins < 60:
            return f"{mins}m"
        h, m = divmod(mins, 60)
        return f"{h}h {m}m" if m else f"{h}h"
    except Exception:
        return ""


def _extract_meeting_link(event: dict) -> str:
    """Pull Zoom / Meet / Teams link from description or conferenceData."""
    # Google Meet
    conf = event.get("conferenceData", {})
    for ep in conf.get("entryPoints", []):
        if ep.get("entryPointType") == "video":
            return ep.get("uri", "")
    # Fallback: scan description
    desc = event.get("description", "") or ""
    m = re.search(
        r"https?://(?:meet\.google\.com|zoom\.us|teams\.microsoft\.com)/\S+",
        desc,
    )
    return m.group(0) if m else ""


def _detect_conflicts(events: list[dict]) -> list[str]:
    """Return list of conflict description strings."""
    conflicts = []
    timed = []
    for ev in events:
        start = ev.get("start", "")
        end   = ev.get("end",   "")
        if start and end and "T" in start:
            try:
                s = datetime.fromisoformat(start.replace("Z", "+00:00"))
                e = datetime.fromisoformat(end.replace("Z", "+00:00"))
                timed.append((s, e, ev.get("summary", "(no title)")))
            except Exception:
                pass

    timed.sort(key=lambda x: x[0])
    for i in range(len(timed) - 1):
        _, end_i, name_i = timed[i]
        start_j, _, name_j = timed[i + 1]
        if start_j < end_i:
            conflicts.append(f"⚠️ **Conflict**: *{name_i}* overlaps with *{name_j}*")
    return conflicts


def _fetch_events_sync(days_ahead: int = 1) -> list[dict]:
    try:
        service  = _calendar_service()
        now      = datetime.now(timezone.utc)
        time_max = now + timedelta(days=days_ahead)
        result   = _gmail_api_call_with_backoff(
            lambda: service.events().list(
                calendarId="primary",
                timeMin=now.isoformat(),
                timeMax=time_max.isoformat(),
                maxResults=50,
                singleEvents=True,
                orderBy="startTime",
            ).execute()
        )
        events = []
        for item in (result or {}).get("items", []):
            start = item.get("start", {})
            end   = item.get("end",   {})
            events.append({
                "id":              item.get("id"),
                "summary":         item.get("summary", "(No title)"),
                "start":           start.get("dateTime") or start.get("date"),
                "end":             end.get("dateTime")   or end.get("date"),
                "description":     item.get("description", ""),
                "location":        item.get("location",    ""),
                "conferenceData":  item.get("conferenceData", {}),
                "all_day":         "dateTime" not in start,
            })
        log.info(f"Fetched {len(events)} calendar events.")
        return events
    except Exception as exc:
        log.error(f"Calendar fetch error: {exc}")
        return []


def _render_event_card(ev: dict, show_date: bool = False) -> str:
    """Render a rich single-event card string."""
    start_str = ev.get("start", "")
    end_str   = ev.get("end", "")

    if ev.get("all_day"):
        time_str = "All day"
        dur_str  = ""
    else:
        time_str = _fmt_event_time(start_str) if start_str else "?"
        end_time = _fmt_event_time(end_str)   if end_str   else ""
        dur_str  = _fmt_event_duration(start_str, end_str)
        if end_time:
            time_str = f"{time_str} → {end_time}"
        if dur_str:
            time_str += f"  ({dur_str})"

    if show_date and start_str:
        try:
            dt = datetime.fromisoformat(start_str.replace("Z", "+00:00"))
            date_label = dt.astimezone().strftime("%A %d %b")
            time_str = f"{date_label} · {time_str}"
        except Exception:
            pass

    lines = [f"🔹 **{ev['summary']}**  —  {time_str}"]
    if ev.get("location"):
        lines.append(f"   📍 {ev['location']}")
    link = _extract_meeting_link(ev)
    if link:
        lines.append(f"   🔗 {link}")
    if ev.get("description"):
        desc = ev["description"].strip()
        if len(desc) > 100:
            desc = desc[:100] + "…"
        lines.append(f"   📝 {desc}")
    return "\n".join(lines)


def _format_calendar_briefing(events: list[dict], label: str = "Today") -> str:
    if not events:
        return f"📅 Nothing on the calendar {label.lower()}."

    lines = [f"📅 **{label}'s Calendar** — {len(events)} event(s)\n"]
    for ev in events:
        lines.append(_render_event_card(ev))
        lines.append("")

    conflicts = _detect_conflicts(events)
    if conflicts:
        lines.append("")
        lines.extend(conflicts)

    return "\n".join(lines).strip()


def _format_weekly_agenda(events: list[dict]) -> str:
    if not events:
        return "📅 Nothing on the calendar this week."

    days: dict = defaultdict(list)
    day_order: list[str] = []
    for ev in events:
        start = ev.get("start", "")
        if not start:
            continue
        try:
            if "T" in start:
                dt = datetime.fromisoformat(start.replace("Z", "+00:00")).astimezone()
            else:
                dt = datetime.fromisoformat(start)
            day = dt.strftime("%A %d %B")
        except Exception:
            day = start[:10]
        if day not in days:
            day_order.append(day)
        days[day].append(ev)

    lines = ["📅 **Weekly Agenda**\n"]
    for day in day_order:
        day_events = days[day]
        lines.append(f"**── {day} ──**")
        for ev in day_events:
            lines.append(_render_event_card(ev))
        conflicts = _detect_conflicts(day_events)
        lines.extend(conflicts)
        lines.append("")

    return "\n".join(lines).strip()


def _parse_event_from_text_sync(user_text: str) -> dict | None:
    now_str = datetime.now().strftime("%A %d %B %Y %H:%M")
    raw = _ollama_raw_sync(
        f"Today is {now_str}. Extract calendar event details from the user's request.\n"
        "Handle relative dates like 'next Monday', 'tomorrow', 'in 2 hours', 'this Friday'.\n"
        "Reply ONLY with raw JSON, no markdown:\n"
        '{"summary":"event title","start":"YYYY-MM-DDTHH:MM:SS","end":"YYYY-MM-DDTHH:MM:SS",'
        '"description":"","location":""}\n'
        "If no end time, assume 1 hour after start. If no date, assume today.",
        user_text,
        max_tokens=200,
    )
    try:
        cleaned = re.sub(r"```(?:json)?\n?", "", raw).replace("```", "").strip()
        return json.loads(cleaned)
    except Exception:
        log.warning(f"Could not parse event JSON: {raw[:200]}")
        return None


def _create_event_sync(
    summary: str, start_dt: str, end_dt: str,
    description: str = "", location: str = ""
) -> str:
    try:
        service = _calendar_service()
        tz_str  = str(datetime.now().astimezone().tzinfo)
        body    = {
            "summary":     summary,
            "description": description,
            "location":    location,
            "start": {"dateTime": start_dt, "timeZone": tz_str},
            "end":   {"dateTime": end_dt,   "timeZone": tz_str},
        }
        created = _gmail_api_call_with_backoff(
            lambda: service.events().insert(calendarId="primary", body=body).execute()
        )
        link = (created or {}).get("htmlLink", "")
        try:
            s = datetime.fromisoformat(start_dt)
            time_display = s.strftime("%A %d %B at %I:%M %p")
        except Exception:
            time_display = start_dt

        result = f"✅ **{summary}** added to your calendar\n📆 {time_display}"
        if location:
            result += f"\n📍 {location}"
        if link:
            result += f"\n🔗 {link}"
        log.info(f"Calendar event created: {summary} @ {start_dt}")
        return result
    except Exception as exc:
        log.error(f"Calendar create error: {exc}")
        return f"❌ Could not create event: {exc}"


def _search_events_sync(keyword: str, days_range: int = 30) -> list[dict]:
    try:
        service  = _calendar_service()
        now      = datetime.now(timezone.utc)
        time_max = now + timedelta(days=days_range)
        result   = _gmail_api_call_with_backoff(
            lambda: service.events().list(
                calendarId="primary",
                timeMin=now.isoformat(),
                timeMax=time_max.isoformat(),
                maxResults=50,
                singleEvents=True,
                orderBy="startTime",
                q=keyword,
            ).execute()
        )
        events = []
        for item in (result or {}).get("items", []):
            start = item.get("start", {})
            end   = item.get("end",   {})
            events.append({
                "id":          item.get("id"),
                "summary":     item.get("summary", "(No title)"),
                "start":       start.get("dateTime") or start.get("date"),
                "end":         end.get("dateTime")   or end.get("date"),
                "description": item.get("description", ""),
                "location":    item.get("location",    ""),
                "all_day":     "dateTime" not in start,
            })
        return events
    except Exception as exc:
        log.error(f"Calendar search error: {exc}")
        return []


def _delete_event_sync(query_text: str) -> str:
    """Find and delete an event matching the query (title + optional time)."""
    try:
        service = _calendar_service()
        # Extract a keyword for the search
        keyword = _ollama_raw_sync(
            "Extract just the event title keywords (2-4 words max) from this deletion request. "
            "Reply with ONLY the keywords, nothing else.",
            query_text,
            max_tokens=20,
        ).strip()

        events = _search_events_sync(keyword, days_range=60)
        if not events:
            return f"❌ No upcoming events found matching **{keyword}**."

        if len(events) == 1:
            ev = events[0]
            _gmail_api_call_with_backoff(
                lambda: service.events().delete(calendarId="primary", eventId=ev["id"]).execute()
            )
            start_str = _fmt_event_time(ev["start"]) if ev.get("start") and "T" in ev["start"] else ev.get("start", "")
            log.info(f"Deleted event: {ev['summary']}")
            return f"🗑️ Deleted **{ev['summary']}** ({start_str})"

        # Multiple matches — show list and ask user to be specific
        lines = [f"Found {len(events)} matching events — which one did you mean?\n"]
        for i, ev in enumerate(events[:5], 1):
            time_str = _fmt_event_time(ev["start"]) if ev.get("start") and "T" in ev["start"] else ev.get("start", "")[:10]
            lines.append(f"  {i}. **{ev['summary']}**  —  {time_str}")
        lines.append("\nTry being more specific, e.g. *'delete the 3pm dentist on Friday'*.")
        return "\n".join(lines)

    except Exception as exc:
        log.error(f"Calendar delete error: {exc}")
        return f"❌ Could not delete event: {exc}"




async def handle_calendar_today(data: dict) -> str:
    if not GOOGLE_AVAILABLE:
        return _google_not_available()
    events = await asyncio.to_thread(_fetch_events_sync, 1)
    return _format_calendar_briefing(events, "Today")


async def handle_calendar_week(data: dict) -> str:
    if not GOOGLE_AVAILABLE:
        return _google_not_available()
    events = await asyncio.to_thread(_fetch_events_sync, 7)
    return _format_weekly_agenda(events)


async def handle_calendar_add(data: dict) -> str:
    if not GOOGLE_AVAILABLE:
        return _google_not_available()
    user_text = data.get("reply", "").strip()
    if not user_text:
        return "❌ No event details provided."
    parsed = await asyncio.to_thread(_parse_event_from_text_sync, user_text)
    if not parsed:
        return "❌ Couldn't understand the event. Try: *'Add a meeting with John on Friday at 2pm'*"
    summary  = parsed.get("summary",     "New Event")
    start_dt = parsed.get("start",       "")
    end_dt   = parsed.get("end",         "")
    desc     = parsed.get("description", "")
    location = parsed.get("location",    "")
    if not start_dt:
        return "❌ Couldn't determine a start time from your request."
    return await asyncio.to_thread(_create_event_sync, summary, start_dt, end_dt, desc, location)


async def handle_calendar_delete(data: dict) -> str:
    if not GOOGLE_AVAILABLE:
        return _google_not_available()
    query = data.get("reply", "").strip()
    if not query:
        return "❌ No event name/time provided."
    return await asyncio.to_thread(_delete_event_sync, query)


async def handle_calendar_search(data: dict) -> str:
    if not GOOGLE_AVAILABLE:
        return _google_not_available()
    keyword = data.get("app", "").strip()
    if not keyword:
        return "❌ No search keyword provided."
    events = await asyncio.to_thread(_search_events_sync, keyword, 30)
    if not events:
        return f"📅 No upcoming events found matching **{keyword}**."
    lines = [f"📅 **Events matching '{keyword}'** — {len(events)} found\n"]
    for ev in events:
        lines.append(_render_event_card(ev, show_date=True))
        lines.append("")
    return "\n".join(lines).strip()


def _google_not_available() -> str:
    return (
        "❌ Google libraries not installed.\n"
        "Run: `pip install google-auth google-auth-oauthlib "
        "google-auth-httplib2 google-api-python-client`"
    )


class ZentraScheduler:
    def __init__(self, discord_client):
        self.client         = discord_client
        self._reminded_ids: set[str] = set()
        self._tasks:        list     = []

    def start(self):
        if not GOOGLE_AVAILABLE:
            log.warning("Google libraries not installed — scheduler disabled.")
            return
        self._tasks = [
            asyncio.create_task(self._morning_digest_loop()),
            asyncio.create_task(self._email_poll_loop()),
            asyncio.create_task(self._event_reminder_loop()),
        ]
        log.info("Scheduler started — morning digest, email poll, event reminders active.")

    def stop(self):
        for t in self._tasks:
            t.cancel()

    async def _dm(self, text: str):
        try:
            user = await self.client.fetch_user(ALLOWED_USER_IDS[0])
            for chunk in [text[i:i+1990] for i in range(0, len(text), 1990)]:
                await user.send(chunk)
        except Exception as exc:
            log.error(f"Scheduler DM failed: {exc}")

    @staticmethod
    async def _wait_until(hour: int, minute: int):
        now    = datetime.now()
        target = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if target <= now:
            target += timedelta(days=1)
        await asyncio.sleep((target - now).total_seconds())


    async def _morning_digest_loop(self):
        while True:
            await self._wait_until(MORNING_DIGEST_HOUR, MORNING_DIGEST_MINUTE)
            try:
                await self._send_morning_digest()
            except Exception as exc:
                log.error(f"Morning digest error: {exc}")
            await asyncio.sleep(60)

    async def _send_morning_digest(self):
        log.info("Sending morning digest…")
        now_str      = datetime.now().strftime("%A %d %B %Y")
        header       = f"☀️ **Good morning! Here's your briefing for {now_str}**\n\n"

        emails       = await asyncio.to_thread(_fetch_unread_emails_sync, 24)
        email_msg    = await asyncio.to_thread(_format_email_digest, emails)

        today_events = await asyncio.to_thread(_fetch_events_sync, 1)
        cal_msg      = _format_calendar_briefing(today_events, "Today")

        await self._dm(header + email_msg + "\n\n──────────────\n\n" + cal_msg)


    async def _email_poll_loop(self):
        await asyncio.sleep(30)
        while True:
            try:
                emails = await asyncio.to_thread(_fetch_unread_emails_sync, 1)
                for email in emails:
                    if email["id"] in _seen_email_ids:
                        continue
                    score = await asyncio.to_thread(
                        _importance_score,
                        email["sender"], email["subject"], email["snippet"]
                    )
                    if score >= 2:
                        summary = _ollama_raw_sync(
                            "Summarise this important email in 2 sentences. Be direct and brief.",
                            f"Subject: {email['subject']}\n\n{email['body'] or email['snippet']}",
                            max_tokens=100,
                        )
                        urgency_label = "🚨 **Critical Email**" if score >= 3 else "⚠️ **Important Email**"
                        await self._dm(
                            f"{urgency_label}\n"
                            f"**From:** {email['sender']}\n"
                            f"**Subject:** {email['subject']}\n"
                            f"**Summary:** {summary}"
                        )
                        log.info(f"Alert sent (score={score}): {email['subject']}")
                    _seen_email_ids.add(email["id"])
                _persist_seen_emails()
            except Exception as exc:
                log.error(f"Email poll error: {exc}")
            await asyncio.sleep(EMAIL_POLL_INTERVAL_MINUTES * 60)


    async def _event_reminder_loop(self):
        await asyncio.sleep(60)
        while True:
            try:
                now    = datetime.now(timezone.utc)
                events = await asyncio.to_thread(_fetch_events_sync, 1)
                for ev in events:
                    if ev["id"] in self._reminded_ids or not ev["start"]:
                        continue
                    if ev.get("all_day"):
                        continue
                    try:
                        start = datetime.fromisoformat(ev["start"].replace("Z", "+00:00"))
                    except Exception:
                        continue
                    delta = (start - now).total_seconds()
                    if 0 < delta <= EVENT_REMINDER_MINUTES * 60:
                        mins_away = int(delta / 60)
                        ts        = start.astimezone().strftime("%I:%M %p")
                        loc_line  = f"\n📍 {ev['location']}"         if ev.get("location")    else ""
                        link      = _extract_meeting_link(ev)
                        link_line = f"\n🔗 {link}"                    if link                  else ""
                        desc      = (ev.get("description") or "")[:100]
                        desc_line = f"\n📝 {desc}"                    if desc                  else ""
                        await self._dm(
                            f"⏰ **Starting in {mins_away} min**\n"
                            f"**{ev['summary']}** at {ts}"
                            f"{loc_line}{link_line}{desc_line}"
                        )
                        self._reminded_ids.add(ev["id"])
                        log.info(f"Reminder sent: {ev['summary']} in {mins_away}m")
            except Exception as exc:
                log.error(f"Event reminder error: {exc}")
            await asyncio.sleep(60)


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
    elif action == "chat":
        result = handle_chat(data)
    else:
        log.warning(f"Unknown action: {action}")
        result = reply or f"⚠️ Unknown action `{action}`."

    return result, file_content


async def keep_typing(channel: discord.DMChannel, stop_event: asyncio.Event) -> None:
    while not stop_event.is_set():
        await channel.typing().__aenter__()
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=8)
        except asyncio.TimeoutError:
            pass


async def process_message(user_id: int, user_input: str) -> str:
    prompt = build_prompt(user_id, user_input)

    try:
        raw_output = await query_ollama(prompt)
    except (ConnectionError, TimeoutError, RuntimeError) as exc:
        log.error(f"Ollama error: {exc}")
        return f"⚠️ AI Error: {exc}"

    try:
        parsed = extract_json(raw_output)
        log.info(f"Parsed JSON:\n{json.dumps(parsed, indent=2)[:500]}")
    except ValueError as exc:
        log.error(f"JSON parse failure: {exc}")
        preview = raw_output[:800]
        return (
            f"⚠️ Couldn't parse the AI's response as JSON.\n"
            f"Raw output:\n```\n{preview}\n```"
        )

    try:
        result, file_content = await dispatch_action(parsed)
    except Exception as exc:
        log.error(f"Dispatch error: {exc}", exc_info=True)
        return f"⚠️ Action failed: {exc}"


    if file_content:
        filename = parsed.get("filename", "file")
        followup_prompt = (
            f"{user_input}\n\n"
            f"[ZENTRA NOTE: The file '{filename}' was read successfully. "
            f"Here is its content for you to reason about:]\n\n"
            f"```\n{file_content}\n```\n\n"
            f"Now answer the user's question about this file."
        )
        try:
            raw2    = await query_ollama(followup_prompt)
            parsed2 = extract_json(raw2)
            result2, _ = await dispatch_action(parsed2)
            result  = result + "\n\n" + result2
        except Exception as exc:
            log.warning(f"read_file follow-up failed: {exc}")
            result += "\n\n📄 File contents loaded into context."

    summary = (parsed.get("reply") or result)[:300]
    save_to_memory(user_id, user_input, summary)
    return result


async def send_response(channel: discord.DMChannel, text: str) -> None:
    text = text or "✅ Done."
    for chunk in [text[i:i+1990] for i in range(0, len(text), 1990)]:
        await channel.send(chunk)


scheduler: ZentraScheduler | None = None


@client.event
async def on_ready() -> None:
    global scheduler
    log.info("=" * 60)
    log.info("  ZENTRA v7.0 — AI Developer Assistant")
    log.info(f"  Bot user    : {client.user} (ID {client.user.id})")
    log.info(f"  Ollama      : {OLLAMA_ENDPOINT}  model={OLLAMA_MODEL}")
    log.info(f"  Vision model: {OLLAMA_VISION_MODEL}")
    log.info(f"  Base folder : {BASE_FOLDER}")
    log.info(f"  Screenshots : {SCREENSHOT_FOLDER}")
    log.info(f"  Memory depth: {MEMORY_DEPTH} exchanges per user")
    log.info(f"  Generation  : unlimited (num_predict=-1)")
    log.info(f"  Context     : 16384 tokens")
    log.info(f"  Actions     : create_file, run_file, read_file, edit_file,")
    log.info(f"                scaffold_project, open_app, close_app,")
    log.info(f"                vscode_open, github_push, system_stats,")
    log.info(f"                screen_action,")
    log.info(f"                gmail_summary, gmail_send,")
    log.info(f"                calendar_today, calendar_week,")
    log.info(f"                calendar_add, calendar_delete, calendar_search, chat")
    log.info(f"  psutil      : {'✅ available' if PSUTIL_AVAILABLE else '❌ not installed (pip install psutil)'}")
    log.info(f"  pyautogui   : {'✅ available' if PYAUTOGUI_AVAILABLE else '❌ not installed (pip install pyautogui pillow)'}")
    log.info(f"  Google APIs : {'✅ available' if GOOGLE_AVAILABLE else '❌ not installed'}")
    if GOOGLE_AVAILABLE:
        log.info(f"  Morning digest  : {MORNING_DIGEST_HOUR:02d}:{MORNING_DIGEST_MINUTE:02d} daily")
        log.info(f"  Event reminders : {EVENT_REMINDER_MINUTES} min before")
        log.info(f"  Email polling   : every {EMAIL_POLL_INTERVAL_MINUTES} min")
    if ALLOWED_USER_IDS:
        log.info(f"  Whitelist   : {ALLOWED_USER_IDS}")
    else:
        log.info("  Whitelist   : open (anyone can DM)")
    log.info("  Ready — waiting for DMs")
    log.info("=" * 60)

    load_memory()
    _load_seen_emails()
    Path(BASE_FOLDER).mkdir(parents=True, exist_ok=True)
    Path(SCREENSHOT_FOLDER).mkdir(parents=True, exist_ok=True)

    scheduler = ZentraScheduler(client)
    scheduler.start()


@client.event
async def on_message(message: discord.Message) -> None:
    if message.author == client.user:
        return
    if not isinstance(message.channel, discord.DMChannel):
        return
    if ALLOWED_USER_IDS and message.author.id not in ALLOWED_USER_IDS:
        await message.channel.send("⛔ You're not authorised to use ZENTRA.")
        return

    user_input = message.content.strip()
    if not user_input:
        return

    user_id = message.author.id
    log.info(f"DM ← {message.author} ({user_id}): {user_input}")

    async with user_locks[user_id]:
        stop_event  = asyncio.Event()
        typing_task = asyncio.create_task(keep_typing(message.channel, stop_event))

        try:
            response = await process_message(user_id, user_input)
        finally:
            stop_event.set()
            typing_task.cancel()
            try:
                await typing_task
            except asyncio.CancelledError:
                pass

    await send_response(message.channel, response)
    log.info(f"DM → {message.author}: {response[:120]}…")


if __name__ == "__main__":
    if DISCORD_BOT_TOKEN == "########################################################":
        print("=" * 60)
        print("  ❌  No Discord bot token found!")
        print()
        print("  Open zentra_bot.py and replace the placeholder on")
        print("  the DISCORD_BOT_TOKEN line with your real token from:")
        print("  https://discord.com/developers/applications")
        print("=" * 60)
        raise SystemExit(1)

    if not PSUTIL_AVAILABLE:
        print("⚠️  psutil not found — system_stats and close_app will be unavailable.")
        print("    To enable: pip install psutil")

    if not PYAUTOGUI_AVAILABLE:
        print("⚠️  pyautogui not found — screen_action will be unavailable.")
        print("    To enable: pip install pyautogui pillow")
        print("    On Linux:  sudo apt install python3-tk python3-dev scrot")

    if not GOOGLE_AVAILABLE:
        print("⚠️  Google libraries not found — Gmail/Calendar features disabled.")
        print("    To enable: pip install google-auth google-auth-oauthlib")
        print("               google-auth-httplib2 google-api-python-client")

    log.info("Starting ZENTRA v7.0…")
    client.run(DISCORD_BOT_TOKEN)