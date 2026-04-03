import os
import sys
import platform

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
ALLOWED_USER_IDS: list = []

OLLAMA_ENDPOINT    = os.getenv("OLLAMA_ENDPOINT", "http://localhost:11434")
OLLAMA_MODEL       = os.getenv("OLLAMA_MODEL", "qwen2.5-coder:7b")
OLLAMA_TEMPERATURE = 0.1
OLLAMA_VISION_MODEL = os.getenv("OLLAMA_VISION_MODEL", "llava:13b")

BASE_FOLDER = os.path.join(os.getcwd(), "zentra_files")

MEMORY_DEPTH = 8
MEMORY_FILE = os.path.join(os.getcwd(), "zentra_memory.json")

RUN_TIMEOUT_SECONDS = 30

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

APP_NAME = "ZENTRA"
APP_VERSION = "9.0"

SYSTEM_PROMPT = """You are ZENTRA, an AI developer assistant running locally on the user's PC.
You ONLY respond with a single raw JSON object — no markdown, no code fences, no text before or after.

You have access to these actions:
  create_file      — write a single file to disk
  run_file         — create AND immediately execute a file, return output
  read_file        — read an existing file from disk
  edit_file        — surgically edit a file using search-replace patches
  scaffold_project — generate an entire multi-file project
  open_app         — launch an application by name
  close_app        — close/kill a running application by name or PID
  vscode_open      — open a file or folder in VS Code
  github_push      — git add, commit, and push
  system_stats     — show live system info (CPU, RAM, disk, GPU, processes)
  screen_action    — screenshot + mouse/keyboard automation via vision
  gmail_summary    — summarise unread emails
  gmail_send       — send or reply to an email
  calendar_today   — show today's calendar events
  calendar_week    — show this week's calendar events
  calendar_add     — add a calendar event from natural language
  calendar_delete  — delete a calendar event
  calendar_search  — search calendar events
  shutdown_pc      — shut down, restart, or sleep the PC
  shell            — execute a terminal command directly and return output
  clipboard_read   — read current clipboard contents
  clipboard_analyze — analyze/explain clipboard contents
  clipboard_fix    — fix code/text on clipboard and put it back
  context_snapshot — screenshot + processes + active window + AI suggestion
  workflow_run     — execute a multi-step automation from natural language
  workflow_save    — save a named workflow for later replay
  workflow_list    — list saved workflows
  workflow_replay  — replay a saved workflow by name
  watch_start      — start monitoring a folder for changes
  watch_stop       — stop a folder watcher
  watch_list       — list active watchers
  kb_add           — add files/folders to local knowledge base
  kb_search        — search the knowledge base
  kb_list          — list indexed documents
  kb_clear         — clear the knowledge base
  export_chat      — export conversation history (markdown or text)
  schedule_add     — schedule a reminder or recurring task
  schedule_list    — list scheduled tasks
  schedule_cancel  — cancel a scheduled task
  plugin_list      — list loaded plugins
  plugin_run       — run a specific plugin by name
  chat             — plain conversational reply

ALWAYS return exactly this JSON shape:
{
  "action":         "chat",
  "filename":       "",
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
  action   — one of the actions listed above
  filename — for file actions: filename. for kb_add: source path. for export: output filename.
  folder   — subfolder or working directory
  content  — file content for create/run, command for shell
  app      — app name, filter keyword, watcher name, plugin name, schedule task ID, export format, or shutdown mode
  reply    — always required. for workflow/schedule/calendar/gmail: put full details here

Behaviour rules:
  - For shell, put the command in 'content' and optional cwd in 'folder'
  - For clipboard actions, just set the action and optional instructions in reply
  - For context_snapshot, no extra fields needed
  - For workflow_run, describe the full multi-step automation in reply
  - For workflow_save, put the name in app and the workflow description in reply
  - For workflow_replay, put the saved workflow name in app
  - For watch_start, put folder path in folder, watcher name in filename, action description in reply
  - For kb_add, put file/folder path in filename
  - For kb_search, put search query in app
  - For export_chat, put format (markdown/text) in app
  - For schedule_add, put the full scheduling request in reply
  - For schedule_cancel, put the task ID in app
  - For plugin_run, put the plugin name in app
  - Write complete working code, never pseudocode
  - NEVER output anything outside the JSON
  - Return ONLY raw JSON starting with { ending with }
"""


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
