import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional


_PRINT_TOKENS: dict[str, dict] = {}


def generate_print_token(
    report_id: int,
    session_id: int,
    user_id: int,
    *,
    purpose: str = "pdf_export",
    ttl_minutes: int = 2,
) -> str:
    token = secrets.token_urlsafe(32)
    _PRINT_TOKENS[token] = {
        "token": token,
        "report_id": report_id,
        "session_id": session_id,
        "user_id": user_id,
        "purpose": purpose,
        "expires_at": datetime.now(timezone.utc) + timedelta(minutes=ttl_minutes),
        "read_count": 0,
    }
    return token


def validate_print_token(
    token: str,
    *,
    expected_session_id: int,
    expected_purpose: str = "pdf_export",
) -> Optional[dict]:
    record = _PRINT_TOKENS.get(token)
    if not record:
        return None
    if record["session_id"] != expected_session_id:
        return None
    if record["purpose"] != expected_purpose:
        return None
    if record["expires_at"] < datetime.now(timezone.utc):
        return None
    record["read_count"] += 1
    return record


def consume_print_token(token: str) -> None:
    _PRINT_TOKENS.pop(token, None)
