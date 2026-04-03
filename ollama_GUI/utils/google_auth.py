import pickle
import time
from pathlib import Path

from config import (
    GOOGLE_AVAILABLE, GOOGLE_CREDENTIALS_FILE,
    GOOGLE_TOKEN_FILE, GOOGLE_SCOPES,
)
from logger import log

if GOOGLE_AVAILABLE:
    from google.auth.transport.requests import Request
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build as google_build
    from googleapiclient.errors import HttpError


def get_google_credentials():
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
            log.info("Refreshing Google token...")
            creds.refresh(Request())
        else:
            if not Path(GOOGLE_CREDENTIALS_FILE).exists():
                raise FileNotFoundError(
                    f"credentials.json not found at {GOOGLE_CREDENTIALS_FILE}.\n"
                    "Download from Google Cloud Console -> APIs & Services -> Credentials."
                )
            flow  = InstalledAppFlow.from_client_secrets_file(GOOGLE_CREDENTIALS_FILE, GOOGLE_SCOPES)
            creds = flow.run_local_server(port=0)
            log.info("Google OAuth completed — token saved.")
        with open(GOOGLE_TOKEN_FILE, "wb") as fh:
            pickle.dump(creds, fh)

    return creds


def gmail_service():
    return google_build("gmail", "v1", credentials=get_google_credentials(), cache_discovery=False)


def calendar_service():
    return google_build("calendar", "v3", credentials=get_google_credentials(), cache_discovery=False)


def google_api_call_with_backoff(fn, max_retries: int = 3):
    for attempt in range(max_retries):
        try:
            return fn()
        except HttpError as exc:
            if exc.resp.status in (429, 500, 503) and attempt < max_retries - 1:
                wait = 2 ** attempt
                log.warning(f"Gmail API rate limit / server error, retrying in {wait}s...")
                time.sleep(wait)
            else:
                raise
    return None


def google_not_available() -> str:
    return (
        "Google libraries not installed.\n"
        "Run: `pip install google-auth google-auth-oauthlib "
        "google-auth-httplib2 google-api-python-client`"
    )
