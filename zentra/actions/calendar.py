import asyncio
import re
from collections import defaultdict
from datetime import datetime, timedelta, timezone

from zentra.config import GOOGLE_AVAILABLE
from zentra.logger import log
from zentra.ollama import ollama_raw_sync
from zentra.utils.google_auth import (
    calendar_service, google_api_call_with_backoff, google_not_available,
)


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
    conf = event.get("conferenceData", {})
    for ep in conf.get("entryPoints", []):
        if ep.get("entryPointType") == "video":
            return ep.get("uri", "")
    desc = event.get("description", "") or ""
    m = re.search(
        r"https?://(?:meet\.google\.com|zoom\.us|teams\.microsoft\.com)/\S+",
        desc,
    )
    return m.group(0) if m else ""


def _detect_conflicts(events: list[dict]) -> list[str]:
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
            conflicts.append(f"**Conflict**: *{name_i}* overlaps with *{name_j}*")
    return conflicts


def _fetch_events_sync(days_ahead: int = 1) -> list[dict]:
    try:
        service  = calendar_service()
        now      = datetime.now(timezone.utc)
        time_max = now + timedelta(days=days_ahead)
        result   = google_api_call_with_backoff(
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
    start_str = ev.get("start", "")
    end_str   = ev.get("end",   "")

    if ev.get("all_day"):
        time_str = "All day"
        dur_str  = ""
    else:
        time_str = _fmt_event_time(start_str) if start_str else "?"
        end_time = _fmt_event_time(end_str)   if end_str   else ""
        dur_str  = _fmt_event_duration(start_str, end_str)
        if end_time:
            time_str = f"{time_str} -> {end_time}"
        if dur_str:
            time_str += f"  ({dur_str})"

    if show_date and start_str:
        try:
            dt = datetime.fromisoformat(start_str.replace("Z", "+00:00"))
            date_label = dt.astimezone().strftime("%A %d %b")
            time_str = f"{date_label} | {time_str}"
        except Exception:
            pass

    lines = [f"**{ev['summary']}**  —  {time_str}"]
    if ev.get("location"):
        lines.append(f"   Location: {ev['location']}")
    link = _extract_meeting_link(ev)
    if link:
        lines.append(f"   Link: {link}")
    if ev.get("description"):
        desc = ev["description"].strip()
        if len(desc) > 100:
            desc = desc[:100] + "..."
        lines.append(f"   Note: {desc}")
    return "\n".join(lines)


def _format_calendar_briefing(events: list[dict], label: str = "Today") -> str:
    if not events:
        return f"Nothing on the calendar {label.lower()}."

    lines = [f"**{label}'s Calendar** — {len(events)} event(s)\n"]
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
        return "Nothing on the calendar this week."

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

    lines = ["**Weekly Agenda**\n"]
    for day in day_order:
        day_events = days[day]
        lines.append(f"**-- {day} --**")
        for ev in day_events:
            lines.append(_render_event_card(ev))
        conflicts = _detect_conflicts(day_events)
        lines.extend(conflicts)
        lines.append("")

    return "\n".join(lines).strip()


def _parse_event_from_text_sync(user_text: str) -> dict | None:
    now_str = datetime.now().strftime("%A %d %B %Y %H:%M")
    raw = ollama_raw_sync(
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


import json


def _create_event_sync(
    summary: str, start_dt: str, end_dt: str,
    description: str = "", location: str = ""
) -> str:
    try:
        service = calendar_service()
        tz_str  = str(datetime.now().astimezone().tzinfo)
        body    = {
            "summary":     summary,
            "description": description,
            "location":    location,
            "start": {"dateTime": start_dt, "timeZone": tz_str},
            "end":   {"dateTime": end_dt,   "timeZone": tz_str},
        }
        created = google_api_call_with_backoff(
            lambda: service.events().insert(calendarId="primary", body=body).execute()
        )
        link = (created or {}).get("htmlLink", "")
        try:
            s = datetime.fromisoformat(start_dt)
            time_display = s.strftime("%A %d %B at %I:%M %p")
        except Exception:
            time_display = start_dt

        result = f"**{summary}** added to your calendar\n{time_display}"
        if location:
            result += f"\nLocation: {location}"
        if link:
            result += f"\nLink: {link}"
        log.info(f"Calendar event created: {summary} @ {start_dt}")
        return result
    except Exception as exc:
        log.error(f"Calendar create error: {exc}")
        return f"Could not create event: {exc}"


def _search_events_sync(keyword: str, days_range: int = 30) -> list[dict]:
    try:
        service  = calendar_service()
        now      = datetime.now(timezone.utc)
        time_max = now + timedelta(days=days_range)
        result   = google_api_call_with_backoff(
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
    try:
        service = calendar_service()
        keyword = ollama_raw_sync(
            "Extract just the event title keywords (2-4 words max) from this deletion request. "
            "Reply with ONLY the keywords, nothing else.",
            query_text,
            max_tokens=20,
        ).strip()

        events = _search_events_sync(keyword, days_range=60)
        if not events:
            return f"No upcoming events found matching **{keyword}**."

        if len(events) == 1:
            ev = events[0]
            google_api_call_with_backoff(
                lambda: service.events().delete(calendarId="primary", eventId=ev["id"]).execute()
            )
            start_str = _fmt_event_time(ev["start"]) if ev.get("start") and "T" in ev["start"] else ev.get("start", "")
            log.info(f"Deleted event: {ev['summary']}")
            return f"Deleted **{ev['summary']}** ({start_str})"

        lines = [f"Found {len(events)} matching events — which one did you mean?\n"]
        for i, ev in enumerate(events[:5], 1):
            time_str = _fmt_event_time(ev["start"]) if ev.get("start") and "T" in ev["start"] else ev.get("start", "")[:10]
            lines.append(f"  {i}. **{ev['summary']}**  —  {time_str}")
        lines.append("\nTry being more specific, e.g. *'delete the 3pm dentist on Friday'*.")
        return "\n".join(lines)

    except Exception as exc:
        log.error(f"Calendar delete error: {exc}")
        return f"Could not delete event: {exc}"


async def handle_calendar_today(data: dict) -> str:
    if not GOOGLE_AVAILABLE:
        return google_not_available()
    events = await asyncio.to_thread(_fetch_events_sync, 1)
    return _format_calendar_briefing(events, "Today")


async def handle_calendar_week(data: dict) -> str:
    if not GOOGLE_AVAILABLE:
        return google_not_available()
    events = await asyncio.to_thread(_fetch_events_sync, 7)
    return _format_weekly_agenda(events)


async def handle_calendar_add(data: dict) -> str:
    if not GOOGLE_AVAILABLE:
        return google_not_available()
    user_text = data.get("reply", "").strip()
    if not user_text:
        return "No event details provided."
    parsed = await asyncio.to_thread(_parse_event_from_text_sync, user_text)
    if not parsed:
        return "Couldn't understand the event. Try: *'Add a meeting with John on Friday at 2pm'*"
    summary  = parsed.get("summary",     "New Event")
    start_dt = parsed.get("start",       "")
    end_dt   = parsed.get("end",         "")
    desc     = parsed.get("description", "")
    location = parsed.get("location",    "")
    if not start_dt:
        return "Couldn't determine a start time from your request."
    return await asyncio.to_thread(_create_event_sync, summary, start_dt, end_dt, desc, location)


async def handle_calendar_delete(data: dict) -> str:
    if not GOOGLE_AVAILABLE:
        return google_not_available()
    query = data.get("reply", "").strip()
    if not query:
        return "No event name/time provided."
    return await asyncio.to_thread(_delete_event_sync, query)


async def handle_calendar_search(data: dict) -> str:
    if not GOOGLE_AVAILABLE:
        return google_not_available()
    keyword = data.get("app", "").strip()
    if not keyword:
        return "No search keyword provided."
    events = await asyncio.to_thread(_search_events_sync, keyword, 30)
    if not events:
        return f"No upcoming events found matching **{keyword}**."
    lines = [f"**Events matching '{keyword}'** — {len(events)} found\n"]
    for ev in events:
        lines.append(_render_event_card(ev, show_date=True))
        lines.append("")
    return "\n".join(lines).strip()
