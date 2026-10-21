
import json
import os
import uuid
import fcntl
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

GROUP_NAME = os.getenv("GROUP_NAME", "gruppeX")

BASE_DIR = Path(__file__).resolve().parent.parent
DUMP_DIR = Path.home() / "Pictures" / "dumps"
SESSION_FILE = DUMP_DIR / "counter.txt" 
DUMP_DIR.mkdir(parents=True, exist_ok=True, mode=0o700)


def new_session_id() -> int:
    """Increment session ID on every agent startup."""
    with open(SESSION_FILE, "a+") as file:
        fcntl.flock(file, fcntl.LOCK_EX)

        try:
            file.seek(0)
            content = file.read().strip()
            current = int(content) if content else 0

            session_id = current + 1

            file.seek(0)
            file.truncate()
            file.write(str(session_id))
            file.flush()
            os.fsync(file.fileno())

            return session_id
        finally:
            fcntl.flock(file, fcntl.LOCK_UN)


def new_request_id() -> str:
    return str(uuid.uuid4())


def dump(
    request_id: str,
    thread_id: str,
    session_id: int,
    event: str,
    **data,
) -> None:
    timestamp = datetime.now(timezone.utc)

    entry = {
        "timestamp": timestamp.isoformat(),
        "group": GROUP_NAME,
        "session_id": session_id,
        "request_id": request_id,
        "thread_id": thread_id,
        "event": event,
        **data,
    }

    filename = DUMP_DIR / f"dumps-{timestamp:%Y-%m-%d}.jsonl"

    payload = (
        json.dumps(entry, ensure_ascii=False, default=str)
        + "\n"
    ).encode("utf-8")

    fd = os.open(
        filename,
        os.O_WRONLY | os.O_CREAT | os.O_APPEND,
        0o600,
    )

    with os.fdopen(fd, "ab") as file:
        file.write(payload)
