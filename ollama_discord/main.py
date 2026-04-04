import asyncio
import json
import os
import platform
from pathlib import Path
from datetime import datetime, timedelta, timezone

import discord

from config import (
    DISCORD_BOT_TOKEN, OLLAMA_ENDPOINT, OLLAMA_MODEL,
    OLLAMA_VISION_MODEL, BASE_FOLDER, SCREENSHOT_FOLDER,
    MEMORY_DEPTH, ALLOWED_USER_IDS,
    PSUTIL_AVAILABLE, PYAUTOGUI_AVAILABLE, GOOGLE_AVAILABLE,
    MORNING_DIGEST_HOUR, MORNING_DIGEST_MINUTE,
    EVENT_REMINDER_MINUTES, EMAIL_POLL_INTERVAL_MINUTES,
    APP_NAME, APP_VERSION,
)
from logger import log
from memory import load_memory, save_to_memory, persist_memory, user_locks
from engine import process_message
from utils.seen_emails import load_seen_emails, seen_email_ids, persist_seen_emails
from actions.plugins import load_plugins
from actions.scheduler import get_due_tasks, add_task_result
from actions.watcher import get_pending_events
from dispatcher import dispatch_action

if GOOGLE_AVAILABLE:
    from actions.gmail import fetch_unread_emails_sync, importance_score, _format_email_digest
    from actions.calendar import (
        _fetch_events_sync, _format_calendar_briefing,
        _extract_meeting_link, _fmt_event_time,
    )
    from ollama import ollama_raw_sync


intents = discord.Intents.default()
intents.message_content = True
intents.dm_messages     = True
client = discord.Client(intents=intents)


try:
    from collections import defaultdict
    user_locks = defaultdict(asyncio.Lock)
except Exception:
    pass


class ZentraScheduler:
    def __init__(self, discord_client):
        self.client         = discord_client
        self._reminded_ids: set[str] = set()
        self._tasks: list   = []

    def start(self):
        self._tasks = [
            asyncio.create_task(self._user_schedule_loop()),
            asyncio.create_task(self._watcher_loop()),
        ]
        if GOOGLE_AVAILABLE:
            self._tasks.extend([
                asyncio.create_task(self._morning_digest_loop()),
                asyncio.create_task(self._email_poll_loop()),
                asyncio.create_task(self._event_reminder_loop()),
            ])
        log.info("Scheduler started.")

    def stop(self):
        for t in self._tasks:
            t.cancel()

    async def _dm(self, text: str):
        if not ALLOWED_USER_IDS:
            return
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

    async def _user_schedule_loop(self):
        await asyncio.sleep(30)
        while True:
            try:
                due = get_due_tasks()
                for task in due:
                    msg = f"**Reminder:** {task['message']}"
                    if task.get("action") and task["action"] != "chat":
                        try:
                            data = {"action": task["action"], "reply": "", "app": "",
                                    "filename": "", "folder": "", "content": "",
                                    "patches": [], "files": [], "app_path": "",
                                    "run_args": [], "git_folder": "", "git_message": "",
                                    "screen_goal": "", "screen_actions": []}
                            result, _ = await dispatch_action(data)
                            msg += f"\n\n{result}"
                        except Exception as exc:
                            msg += f"\n\nAction failed: {exc}"
                    add_task_result(task, msg)
                    await self._dm(msg)
            except Exception as exc:
                log.error(f"Schedule loop error: {exc}")
            await asyncio.sleep(30)

    async def _watcher_loop(self):
        await asyncio.sleep(10)
        while True:
            try:
                events = get_pending_events()
                for ev in events:
                    await self._dm(
                        f"**File watcher [{ev['watcher']}]:** "
                        f"{ev['type']} `{ev['name']}`"
                    )
            except Exception as exc:
                log.error(f"Watcher loop error: {exc}")
            await asyncio.sleep(5)

    async def _morning_digest_loop(self):
        while True:
            await self._wait_until(MORNING_DIGEST_HOUR, MORNING_DIGEST_MINUTE)
            try:
                now_str = datetime.now().strftime("%A %d %B %Y")
                header  = f"**Good morning! Briefing for {now_str}**\n\n"
                emails  = await asyncio.to_thread(fetch_unread_emails_sync, 24)
                email_msg = await asyncio.to_thread(_format_email_digest, emails)
                today_events = await asyncio.to_thread(_fetch_events_sync, 1)
                cal_msg = _format_calendar_briefing(today_events, "Today")
                await self._dm(header + email_msg + "\n\n-----------\n\n" + cal_msg)
            except Exception as exc:
                log.error(f"Morning digest error: {exc}")
            await asyncio.sleep(60)

    async def _email_poll_loop(self):
        await asyncio.sleep(30)
        while True:
            try:
                emails = await asyncio.to_thread(fetch_unread_emails_sync, 1)
                for email in emails:
                    if email["id"] in seen_email_ids:
                        continue
                    score = await asyncio.to_thread(
                        importance_score, email["sender"], email["subject"], email["snippet"]
                    )
                    if score >= 2:
                        summary = ollama_raw_sync(
                            "Summarise this important email in 2 sentences.",
                            f"Subject: {email['subject']}\n\n{email['body'] or email['snippet']}",
                            max_tokens=100,
                        )
                        label = "**Critical Email**" if score >= 3 else "**Important Email**"
                        await self._dm(
                            f"{label}\n**From:** {email['sender']}\n"
                            f"**Subject:** {email['subject']}\n**Summary:** {summary}"
                        )
                    seen_email_ids.add(email["id"])
                persist_seen_emails()
            except Exception as exc:
                log.error(f"Email poll error: {exc}")
            await asyncio.sleep(EMAIL_POLL_INTERVAL_MINUTES * 60)

    async def _event_reminder_loop(self):
        await asyncio.sleep(60)
        while True:
            try:
                now = datetime.now(timezone.utc)
                events = await asyncio.to_thread(_fetch_events_sync, 1)
                for ev in events:
                    if ev["id"] in self._reminded_ids or not ev["start"] or ev.get("all_day"):
                        continue
                    try:
                        start = datetime.fromisoformat(ev["start"].replace("Z", "+00:00"))
                    except Exception:
                        continue
                    delta = (start - now).total_seconds()
                    if 0 < delta <= EVENT_REMINDER_MINUTES * 60:
                        mins = int(delta / 60)
                        ts = start.astimezone().strftime("%I:%M %p")
                        loc = f"\nLocation: {ev['location']}" if ev.get("location") else ""
                        link = _extract_meeting_link(ev)
                        link_line = f"\nLink: {link}" if link else ""
                        await self._dm(
                            f"**Starting in {mins} min**\n**{ev['summary']}** at {ts}{loc}{link_line}"
                        )
                        self._reminded_ids.add(ev["id"])
            except Exception as exc:
                log.error(f"Reminder error: {exc}")
            await asyncio.sleep(60)


scheduler = None


async def keep_typing(channel, stop_event: asyncio.Event) -> None:
    while not stop_event.is_set():
        await channel.typing().__aenter__()
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=8)
        except asyncio.TimeoutError:
            pass


async def send_response(channel, text: str) -> None:
    text = text or "Done."
    for chunk in [text[i:i+1990] for i in range(0, len(text), 1990)]:
        await channel.send(chunk)


@client.event
async def on_ready() -> None:
    global scheduler
    log.info("=" * 60)
    log.info(f"  {APP_NAME} v{APP_VERSION} — Discord Bot")
    log.info(f"  Bot user    : {client.user} (ID {client.user.id})")
    log.info(f"  Ollama      : {OLLAMA_ENDPOINT}  model={OLLAMA_MODEL}")
    log.info(f"  Vision      : {OLLAMA_VISION_MODEL}")
    log.info(f"  psutil      : {'yes' if PSUTIL_AVAILABLE else 'no'}")
    log.info(f"  pyautogui   : {'yes' if PYAUTOGUI_AVAILABLE else 'no'}")
    log.info(f"  google      : {'yes' if GOOGLE_AVAILABLE else 'no'}")
    log.info("=" * 60)

    load_memory()
    load_seen_emails()
    Path(BASE_FOLDER).mkdir(parents=True, exist_ok=True)
    Path(SCREENSHOT_FOLDER).mkdir(parents=True, exist_ok=True)

    plugin_count = load_plugins()
    if plugin_count:
        log.info(f"  {plugin_count} plugin(s) loaded")

    scheduler = ZentraScheduler(client)
    scheduler.start()

    log.info("  Ready — waiting for DMs")


@client.event
async def on_message(message: discord.Message) -> None:
    if message.author == client.user:
        return
    if not isinstance(message.channel, discord.DMChannel):
        return
    if ALLOWED_USER_IDS and message.author.id not in ALLOWED_USER_IDS:
        await message.channel.send("Not authorised.")
        return

    user_input = message.content.strip()
    if not user_input:
        return

    user_id = message.author.id
    log.info(f"DM <- {message.author} ({user_id}): {user_input}")

    async with user_locks[user_id]:
        stop_event = asyncio.Event()
        typing_task = asyncio.create_task(keep_typing(message.channel, stop_event))
        try:
            response = await process_message(user_input, user_id=user_id)
        finally:
            stop_event.set()
            typing_task.cancel()
            try:
                await typing_task
            except asyncio.CancelledError:
                pass

    await send_response(message.channel, response)
    log.info(f"DM -> {message.author}: {response[:120]}...")


if __name__ == "__main__":
    if DISCORD_BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        print("Set DISCORD_BOT_TOKEN in .env")
        raise SystemExit(1)
    log.info(f"Starting {APP_NAME} v{APP_VERSION} (Discord)...")
    client.run(DISCORD_BOT_TOKEN)
