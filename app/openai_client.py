import json
import urllib.error
import urllib.request

from .config import settings
from .schemas import ChatMessage


def _extract_output_text(payload: dict) -> str:
    if payload.get("output_text"):
        return str(payload["output_text"])

    chunks: list[str] = []
    for item in payload.get("output", []):
        for content in item.get("content", []):
            if content.get("type") in {"output_text", "text"} and content.get("text"):
                chunks.append(str(content["text"]))
    return "\n".join(chunks).strip()


def create_chat_response(messages: list[ChatMessage], message: str) -> tuple[str, str | None]:
    if not settings.OPENAI_API_KEY:
        raise RuntimeError("OPENAI_API_KEY is not configured")

    input_items = [
        {
            "role": "developer",
            "content": "You are Project Studio's operations assistant. Keep answers concise and practical.",
        }
    ]
    input_items.extend({"role": item.role, "content": item.content} for item in messages[-12:])
    input_items.append({"role": "user", "content": message})

    body = {
        "model": settings.OPENAI_MODEL,
        "input": input_items,
        "max_output_tokens": 1200,
    }

    request = urllib.request.Request(
        "https://api.openai.com/v1/responses",
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"OpenAI API error {exc.code}: {detail}") from exc

    return _extract_output_text(payload), payload.get("id")
