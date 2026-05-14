import json
import uuid
from datetime import datetime
from typing import Any

from .config import settings


def create_audit_id() -> str:
    return "STUDIO-" + uuid.uuid4().hex[:12].upper()


def save_audit_log(payload: dict[str, Any]) -> None:
    event = {**payload, "loggedAt": datetime.utcnow().isoformat() + "Z"}
    with open(settings.AUDIT_LOG_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(event, ensure_ascii=False) + "\n")
