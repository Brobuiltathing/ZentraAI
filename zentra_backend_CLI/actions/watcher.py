import asyncio
import os
import time
import threading
from pathlib import Path
from collections import defaultdict

from logger import log
from ollama import ollama_raw_sync


_active_watchers: dict[str, dict] = {}
_watcher_callbacks: dict[str, callable] = {}


class FolderWatcher:
    def __init__(self, path: str, name: str, action_desc: str, callback=None):
        self.path = Path(path)
        self.name = name
        self.action_desc = action_desc
        self.callback = callback
        self._running = False
        self._thread = None
        self._known_files: dict[str, float] = {}

    def start(self):
        if not self.path.is_dir():
            return False
        self._running = True
        self._scan_initial()
        self._thread = threading.Thread(target=self._watch_loop, daemon=True)
        self._thread.start()
        log.info(f"Watcher '{self.name}' started on {self.path}")
        return True

    def stop(self):
        self._running = False
        log.info(f"Watcher '{self.name}' stopped")

    def _scan_initial(self):
        try:
            for f in self.path.iterdir():
                if f.is_file():
                    self._known_files[str(f)] = f.stat().st_mtime
        except Exception as exc:
            log.warning(f"Watcher initial scan failed: {exc}")

    def _watch_loop(self):
        while self._running:
            try:
                current_files = {}
                for f in self.path.iterdir():
                    if f.is_file():
                        current_files[str(f)] = f.stat().st_mtime

                new_files = set(current_files.keys()) - set(self._known_files.keys())
                modified_files = []
                for fp, mtime in current_files.items():
                    if fp in self._known_files and mtime > self._known_files[fp]:
                        modified_files.append(fp)

                deleted_files = set(self._known_files.keys()) - set(current_files.keys())

                for fp in new_files:
                    event = {"type": "created", "path": fp, "name": Path(fp).name}
                    log.info(f"Watcher '{self.name}': new file {Path(fp).name}")
                    if self.callback:
                        self.callback(self.name, event)

                for fp in modified_files:
                    event = {"type": "modified", "path": fp, "name": Path(fp).name}
                    if self.callback:
                        self.callback(self.name, event)

                for fp in deleted_files:
                    event = {"type": "deleted", "path": fp, "name": Path(fp).name}
                    if self.callback:
                        self.callback(self.name, event)

                self._known_files = current_files

            except Exception as exc:
                log.warning(f"Watcher '{self.name}' error: {exc}")

            time.sleep(2)


_pending_events: list[dict] = []
_event_lock = threading.Lock()


def _default_callback(watcher_name: str, event: dict):
    with _event_lock:
        _pending_events.append({
            "watcher": watcher_name,
            "type": event["type"],
            "path": event["path"],
            "name": event["name"],
            "time": time.time(),
        })


def get_pending_events() -> list[dict]:
    with _event_lock:
        events = list(_pending_events)
        _pending_events.clear()
    return events


def handle_watch_start(data: dict) -> str:
    folder = (data.get("folder") or data.get("app") or "").strip()
    name = (data.get("filename") or "").strip() or f"watch_{len(_active_watchers)}"
    action_desc = (data.get("reply") or "").strip() or "notify on changes"

    if not folder:
        return "watch_start: provide a folder path."

    path = Path(folder).expanduser()
    if not path.is_dir():
        return f"Folder not found: `{path}`"

    if name in _active_watchers:
        return f"Watcher '{name}' already running. Stop it first with watch_stop."

    watcher = FolderWatcher(str(path), name, action_desc, callback=_default_callback)
    if watcher.start():
        _active_watchers[name] = {
            "watcher": watcher,
            "path": str(path),
            "action": action_desc,
        }
        return f"Watching **{path}** as '{name}'\nAction on change: {action_desc}"
    else:
        return f"Could not start watcher on `{path}`"


def handle_watch_stop(data: dict) -> str:
    name = (data.get("app") or data.get("filename") or "").strip()

    if not name:
        if len(_active_watchers) == 1:
            name = list(_active_watchers.keys())[0]
        else:
            return "watch_stop: provide the watcher name."

    if name not in _active_watchers:
        available = ", ".join(_active_watchers.keys()) if _active_watchers else "none"
        return f"No watcher named '{name}'. Active: {available}"

    _active_watchers[name]["watcher"].stop()
    del _active_watchers[name]
    return f"Stopped watcher '{name}'."


def handle_watch_list(data: dict) -> str:
    if not _active_watchers:
        return "No active file watchers."

    lines = ["**Active Watchers:**\n"]
    for name, info in _active_watchers.items():
        lines.append(f"  **{name}** -> `{info['path']}`\n    Action: {info['action']}")
    return "\n".join(lines)
