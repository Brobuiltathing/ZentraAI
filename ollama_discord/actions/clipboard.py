import asyncio

from logger import log
from ollama import ollama_raw_sync

try:
    import pyperclip
    PYPERCLIP_AVAILABLE = True
except ImportError:
    PYPERCLIP_AVAILABLE = False


def _get_clipboard() -> str:
    if PYPERCLIP_AVAILABLE:
        return pyperclip.paste() or ""
    try:
        import subprocess, platform
        if platform.system() == "Windows":
            r = subprocess.run(["powershell", "-Command", "Get-Clipboard"], capture_output=True, text=True, timeout=5)
            return r.stdout.strip()
        elif platform.system() == "Darwin":
            r = subprocess.run(["pbpaste"], capture_output=True, text=True, timeout=5)
            return r.stdout.strip()
        else:
            r = subprocess.run(["xclip", "-selection", "clipboard", "-o"], capture_output=True, text=True, timeout=5)
            return r.stdout.strip()
    except Exception as exc:
        log.warning(f"Clipboard read failed: {exc}")
        return ""


def _set_clipboard(text: str) -> bool:
    if PYPERCLIP_AVAILABLE:
        pyperclip.copy(text)
        return True
    try:
        import subprocess, platform
        if platform.system() == "Windows":
            subprocess.run(["powershell", "-Command", f"Set-Clipboard -Value '{text}'"], timeout=5)
        elif platform.system() == "Darwin":
            subprocess.run(["pbcopy"], input=text, text=True, timeout=5)
        else:
            subprocess.run(["xclip", "-selection", "clipboard"], input=text, text=True, timeout=5)
        return True
    except Exception as exc:
        log.warning(f"Clipboard write failed: {exc}")
        return False


def handle_clipboard_read(data: dict) -> str:
    content = _get_clipboard()
    if not content:
        return "Clipboard is empty."

    preview = content[:500]
    if len(content) > 500:
        preview += "..."

    return f"**Clipboard contents** ({len(content)} chars):\n```\n{preview}\n```"


def handle_clipboard_analyze(data: dict) -> str:
    content = _get_clipboard()
    if not content:
        return "Clipboard is empty, nothing to analyze."

    instruction = (data.get("reply") or "").strip()
    if not instruction:
        instruction = "Analyze this content. If it's code, explain what it does. If it's text, summarize it."

    analysis = ollama_raw_sync(
        "You are a helpful assistant. Analyze the following clipboard content as requested. Be concise and direct.",
        f"User request: {instruction}\n\nClipboard content:\n{content[:3000]}",
        max_tokens=500,
    )

    return f"**Clipboard analysis:**\n{analysis}"


def handle_clipboard_fix(data: dict) -> str:
    content = _get_clipboard()
    if not content:
        return "Clipboard is empty, nothing to fix."

    instruction = (data.get("reply") or "").strip()
    if not instruction:
        instruction = "Fix any errors in this code/text and return only the corrected version."

    fixed = ollama_raw_sync(
        "You are a code/text fixer. Return ONLY the fixed version with no explanation, no markdown fences, no preamble.",
        f"Instruction: {instruction}\n\nContent to fix:\n{content[:4000]}",
        max_tokens=2000,
    )

    if _set_clipboard(fixed):
        preview = fixed[:300]
        if len(fixed) > 300:
            preview += "..."
        return f"Fixed and copied back to clipboard ({len(fixed)} chars):\n```\n{preview}\n```"
    else:
        return f"Fixed content (couldn't write to clipboard):\n```\n{fixed[:500]}\n```"
