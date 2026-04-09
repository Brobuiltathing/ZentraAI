import asyncio
import json
import re
import base64
from datetime import datetime, timedelta, timezone
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from zentra.config import (
    GOOGLE_AVAILABLE, MAX_DIGEST_EMAILS,
    IMPORTANT_KEYWORDS, IMPORTANT_SENDERS,
)
from zentra.logger import log
from zentra.ollama import ollama_raw_sync
from zentra.utils.google_auth import (
    gmail_service, google_api_call_with_backoff, google_not_available,
)


def _get_header(headers: list, name: str) -> str:
    for h in headers:
        if h["name"].lower() == name.lower():
            return h["value"]
    return ""


def _clean_sender(raw: str) -> str:
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


def importance_score(sender: str, subject: str, snippet: str) -> int:
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
        answer = ollama_raw_sync(
            "You are a strict email triage assistant. Reply only YES or NO.",
            f"From: {sender}\nSubject: {subject}\nPreview: {snippet}\n\n"
            "Is this email time-sensitive or requires action today?",
            max_tokens=5,
        )
        if answer.strip().upper().startswith("Y"):
            score += 1

    return score


def fetch_unread_emails_sync(since_hours: int = 24, query_extra: str = "") -> list[dict]:
    try:
        service  = gmail_service()
        after_ts = int((datetime.now(timezone.utc) - timedelta(hours=since_hours)).timestamp())
        q = f"is:unread after:{after_ts}"
        if query_extra:
            q += f" {query_extra}"

        results = google_api_call_with_backoff(
            lambda: service.users().messages().list(
                userId="me", q=q, maxResults=MAX_DIGEST_EMAILS
            ).execute()
        )

        emails = []
        for m in (results or {}).get("messages", []):
            try:
                msg = google_api_call_with_backoff(
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


def _format_email_digest(emails: list[dict]) -> str:
    if not emails:
        return "No unread emails in the last 24 hours."

    def email_sort_key(e):
        return importance_score(e["sender"], e["subject"], e["snippet"])

    emails_sorted = sorted(emails, key=email_sort_key, reverse=True)

    lines = [f"**Email Digest** — {len(emails)} unread\n"]
    for i, email in enumerate(emails_sorted, 1):
        score = email_sort_key(email)
        urgency = "CRITICAL " if score >= 2 else ("IMPORTANT " if score == 1 else "")

        summary = ollama_raw_sync(
            "Summarise this email in one clear sentence. No preamble.",
            f"Subject: {email['subject']}\n\n{email['body'] or email['snippet']}",
            max_tokens=80,
        )

        date_str = ""
        try:
            from email.utils import parsedate_to_datetime
            dt = parsedate_to_datetime(email["date"])
            date_str = f"  |  {dt.strftime('%d %b %H:%M')}"
        except Exception:
            pass

        lines.append(
            f"**{i}.** {urgency}**{email['sender']}**{date_str}\n"
            f"   Subject: {email['subject'] or '(no subject)'}\n"
            f"   Summary: {summary}\n"
        )

    return "\n".join(lines)


def _fetch_email_search_sync(query: str, max_results: int = 10) -> list[dict]:
    try:
        service = gmail_service()
        results = google_api_call_with_backoff(
            lambda: service.users().messages().list(
                userId="me", q=query, maxResults=max_results
            ).execute()
        )
        emails = []
        for m in (results or {}).get("messages", []):
            try:
                msg     = google_api_call_with_backoff(
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
    raw = ollama_raw_sync(
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
        service = gmail_service()
        msg     = MIMEMultipart("alternative")
        msg["To"]      = to
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))

        raw_bytes = base64.urlsafe_b64encode(msg.as_bytes()).decode("utf-8")
        body_payload: dict = {"raw": raw_bytes}
        if reply_to_thread:
            body_payload["threadId"] = reply_to_thread

        sent = google_api_call_with_backoff(
            lambda: service.users().messages().send(
                userId="me", body=body_payload
            ).execute()
        )
        log.info(f"Email sent to {to}: {subject}")
        return f"Email sent to **{to}**\nSubject: {subject}"
    except Exception as exc:
        log.error(f"Gmail send error: {exc}")
        return f"Failed to send email: {exc}"


async def handle_gmail_summary(data: dict) -> str:
    if not GOOGLE_AVAILABLE:
        return google_not_available()
    query  = data.get("app", "").strip()
    if query:
        emails = await asyncio.to_thread(_fetch_email_search_sync, query, 15)
    else:
        emails = await asyncio.to_thread(fetch_unread_emails_sync, 48)
    return await asyncio.to_thread(_format_email_digest, emails)


async def handle_gmail_send(data: dict) -> str:
    if not GOOGLE_AVAILABLE:
        return google_not_available()
    user_text = data.get("reply", "").strip()
    if not user_text:
        return "No send details provided."
    parsed = await asyncio.to_thread(_parse_send_request_sync, user_text)
    if not parsed:
        return "Couldn't parse send request. Try: *'Send an email to john@example.com saying...'*"
    to      = parsed.get("to", "")
    subject = parsed.get("subject", "(no subject)")
    body    = parsed.get("body", "")
    if not to:
        return "No recipient found in your request."
    if not body:
        return "No email body found in your request."
    return await asyncio.to_thread(_send_email_sync, to, subject, body)
