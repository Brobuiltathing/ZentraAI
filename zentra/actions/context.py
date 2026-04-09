import platform
import subprocess

from zentra.config import PSUTIL_AVAILABLE, PYAUTOGUI_AVAILABLE
from zentra.logger import log
from zentra.ollama import ollama_raw_sync, ollama_vision_sync

if PSUTIL_AVAILABLE:
    import psutil

if PYAUTOGUI_AVAILABLE:
    from zentra.actions.screen import _take_screenshot_sync


def _get_active_window() -> str:
    system = platform.system()
    try:
        if system == "Windows":
            import ctypes
            user32 = ctypes.windll.user32
            hwnd = user32.GetForegroundWindow()
            length = user32.GetWindowTextLengthW(hwnd)
            buf = ctypes.create_unicode_buffer(length + 1)
            user32.GetWindowTextW(hwnd, buf, length + 1)
            return buf.value or "Unknown"
        elif system == "Darwin":
            r = subprocess.run(
                ["osascript", "-e", 'tell application "System Events" to get name of first application process whose frontmost is true'],
                capture_output=True, text=True, timeout=5,
            )
            return r.stdout.strip() or "Unknown"
        else:
            r = subprocess.run(["xdotool", "getactivewindow", "getwindowname"], capture_output=True, text=True, timeout=5)
            return r.stdout.strip() or "Unknown"
    except Exception as exc:
        log.warning(f"Active window detection failed: {exc}")
        return "Unknown"


def _get_top_processes(n: int = 8) -> list[dict]:
    if not PSUTIL_AVAILABLE:
        return []
    procs = []
    for p in psutil.process_iter(["pid", "name", "cpu_percent", "memory_info"]):
        try:
            info = p.info
            mem = (info.get("memory_info") or psutil._common.pmem(0, 0)).rss
            procs.append({
                "name": info["name"],
                "pid": info["pid"],
                "cpu": info.get("cpu_percent") or 0,
                "mem_mb": round(mem / (1024 * 1024), 1),
            })
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    procs.sort(key=lambda x: x["cpu"], reverse=True)
    return procs[:n]


def handle_context_snapshot(data: dict) -> str:
    parts = ["**Context Snapshot**\n"]

    active = _get_active_window()
    parts.append(f"**Active window:** {active}")

    procs = _get_top_processes(8)
    if procs:
        proc_lines = []
        for p in procs:
            proc_lines.append(f"  {p['name']:<28} CPU {p['cpu']:5.1f}%  RAM {p['mem_mb']:6.1f} MB")
        parts.append(f"\n**Top processes:**\n" + "\n".join(proc_lines))

    screen_analysis = ""
    if PYAUTOGUI_AVAILABLE:
        try:
            b64, path = _take_screenshot_sync()
            parts.append(f"\n**Screenshot:** `{path}`")

            screen_analysis = ollama_vision_sync(
                b64,
                "Describe what the user is currently doing on their screen in 2-3 sentences. "
                "Mention the active application, what content is visible, and what task they appear to be working on.",
                max_tokens=200,
            )
        except Exception as exc:
            log.warning(f"Screenshot for context failed: {exc}")

    context_summary = f"Active window: {active}\n"
    if procs:
        running_apps = ", ".join(p["name"] for p in procs[:5])
        context_summary += f"Running: {running_apps}\n"
    if screen_analysis:
        context_summary += f"Screen: {screen_analysis}\n"

    suggestion = ollama_raw_sync(
        "You are a productivity assistant. Based on the user's current context, "
        "give 1-2 brief, actionable suggestions for what they should focus on or do next. Be concise.",
        context_summary,
        max_tokens=150,
    )

    if screen_analysis:
        parts.append(f"\n**What you're doing:** {screen_analysis}")

    parts.append(f"\n**Suggestion:** {suggestion}")

    return "\n".join(parts)
