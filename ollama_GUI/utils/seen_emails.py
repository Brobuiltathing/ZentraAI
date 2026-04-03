import json
from pathlib import Path

from config import SEEN_EMAILS_FILE
from logger import log


seen_email_ids: set[str] = set()


def load_seen_emails() -> None:
    global seen_email_ids
    try:
        if Path(SEEN_EMAILS_FILE).exists():
            with open(SEEN_EMAILS_FILE, "r") as fh:
                seen_email_ids = set(json.load(fh))
            log.info(f"Loaded {len(seen_email_ids)} seen email IDs.")
    except Exception as exc:
        log.warning(f"Could not load seen emails: {exc}")


def persist_seen_emails() -> None:
    try:
        ids = list(seen_email_ids)[-2000:]
        with open(SEEN_EMAILS_FILE, "w") as fh:
            json.dump(ids, fh)
    except Exception as exc:
        log.warning(f"Could not persist seen emails: {exc}")
