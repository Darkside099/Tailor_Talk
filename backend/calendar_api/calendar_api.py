import os
import pickle
import datetime
from typing import List, Dict, Optional, Tuple

from dotenv import load_dotenv
from fastapi import HTTPException
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

load_dotenv()

SCOPES = [
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/calendar",
]

CREDENTIALS_PATH = os.getenv("GOOGLE_CREDENTIALS_PATH", "calendar_api/credentials.json")
TOKEN_DIR = os.getenv("GOOGLE_TOKEN_DIR", "tokens/")
TIMEZONE = os.getenv("GOOGLE_CALENDAR_TIMEZONE", "UTC")

os.makedirs(TOKEN_DIR, exist_ok=True)


def _get_token_path(email: str) -> str:
    return os.path.join(TOKEN_DIR, f"{email}.pickle")


def _load_credentials(email: str):
    token_path = _get_token_path(email)
    if os.path.exists(token_path):
        with open(token_path, "rb") as f:
            return pickle.load(f)
    return None


def _save_credentials(email: str, creds):
    with open(_get_token_path(email), "wb") as f:
        pickle.dump(creds, f)


def _refresh_credentials_if_needed(creds, email: str):
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
        _save_credentials(email, creds)
    return creds


def _ensure_authenticated(email: str):
    creds = _load_credentials(email)
    if creds is None or not creds.valid:
        creds = _refresh_credentials_if_needed(creds, email)
        if not creds or not creds.valid:
            raise HTTPException(status_code=403, detail="User not authenticated.")
    return creds


def get_calendar_service(email: str):
    creds = _ensure_authenticated(email)
    return build("calendar", "v3", credentials=creds)


def get_upcoming_events(email: str, max_results: int = 10) -> List[Dict]:
    try:
        service = get_calendar_service(email)
        now = datetime.datetime.utcnow().isoformat() + "Z"
        result = (
            service.events()
            .list(
                calendarId="primary",
                timeMin=now,
                maxResults=max_results,
                singleEvents=True,
                orderBy="startTime",
            )
            .execute()
        )
        return result.get("items", [])
    except HttpError as e:
        raise HTTPException(status_code=500, detail=f"Google Calendar error: {e}")


def create_event(
    email: str,
    summary: str,
    start_time: str,
    end_time: str,
    description: Optional[str] = None,
) -> Dict:
    try:
        service = get_calendar_service(email)
        event = {
            "summary": summary,
            "start": {"dateTime": start_time, "timeZone": TIMEZONE},
            "end": {"dateTime": end_time, "timeZone": TIMEZONE},
        }
        if description:
            event["description"] = description
        return service.events().insert(calendarId="primary", body=event).execute()
    except HttpError as e:
        raise HTTPException(status_code=500, detail=f"Event creation error: {e}")


def start_google_auth() -> str:
    try:
        flow = Flow.from_client_secrets_file(
            CREDENTIALS_PATH,
            scopes=SCOPES,
            redirect_uri="https://tailor-talk-n81b.onrender.com/oauth2callback",
        )
        auth_url, _ = flow.authorization_url(
            access_type="offline",
            include_granted_scopes="true",
            prompt="consent",
        )
        return auth_url
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Login link error: {e}")


def finish_google_auth(code: str) -> Tuple[str, str]:
    try:
        flow = Flow.from_client_secrets_file(
            CREDENTIALS_PATH,
            scopes=SCOPES,
            redirect_uri="https://tailor-talk-n81b.onrender.com/oauth2callback",
        )

        flow.fetch_token(code=code)
        creds = flow.credentials

        if not creds or not creds.valid:
            raise HTTPException(status_code=401, detail="Invalid OAuth credentials.")

        user_service = build("oauth2", "v2", credentials=creds)
        user_info = user_service.userinfo().get().execute()
        email = user_info.get("email")
        name = user_info.get("name", "Unknown User")

        if not email:
            raise HTTPException(status_code=401, detail="Email not found.")

        _save_credentials(email, creds)
        return email, name

    except Exception as e:
        print("[OAuth ERROR]", str(e))
        raise HTTPException(status_code=401, detail=f"OAuth error: {e}")


def is_user_authenticated(email: str) -> bool:
    creds = _load_credentials(email)
    return creds is not None and creds.valid
