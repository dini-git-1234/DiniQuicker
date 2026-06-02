import os
import base64
import asyncio
from typing import List, Optional

import anthropic

SUPPORTED_IMAGES = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
IMAGE_MIME = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".gif": "image/gif",
    ".webp": "image/webp",
}


def get_anthropic_api_key() -> Optional[str]:
    return os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("CLAUDE_API_KEY")


def _build_claude_content(prompt: str, images: Optional[List[str]] = None) -> list:
    content: list = []

    # תמונות/קבצים
    if images:
        for path in images:
            try:
                ext = os.path.splitext(path)[1].lower()
                if ext in SUPPORTED_IMAGES and os.path.exists(path):
                    with open(path, "rb") as f:
                        data_b64 = base64.standard_b64encode(f.read()).decode("utf-8")
                    content.append(
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": IMAGE_MIME.get(ext, "image/jpeg"),
                                "data": data_b64,
                            },
                        }
                    )
                else:
                    print(f"[claude_client] קובץ תמונה לא נתמך או לא נמצא: {path}")
            except Exception as e:
                print(f"[claude_client] שגיאה בקריאת תמונה {path}: {e}")
                continue

    # בלוק טקסט עם הפרומפט
    content.append({"type": "text", "text": prompt})
    return content


def _call_claude_messages_create(content: list, model: str = "claude-sonnet-4-6", max_tokens: int = 4000) -> str:
    api_key = get_anthropic_api_key()
    if not api_key:
        raise Exception("[Claude] API key missing: set ANTHROPIC_API_KEY or CLAUDE_API_KEY")

    client = anthropic.Anthropic(api_key=api_key)
    message = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        messages=[{"role": "user", "content": content}],
    )

    # חיפוש הטקסט בבלוקים
    out = ""
    for block in message.content:
        part = getattr(block, "text", None)
        if part:
            out += part

    return out.strip()


async def ask_gemini_with_search(
    prompt: str,
    model_name: str = "claude-sonnet-4-6",
    images: Optional[List[str]] = None,
    use_search: bool = True,
) -> str:
    """Compatibility wrapper that previously called Gemini.

    Now sends the prompt (and optional images) to Claude (Anthropic).
    Keeps the same signature so existing callers don't need changes.
    """

    content = _build_claude_content(prompt, images)

    # Normalize model_name in case callers pass Gemini model names
    if model_name and "gemini" in model_name.lower():
        model_name = "claude-sonnet-4-6"

    try:
        # run the blocking SDK call in a thread, with timeout
        result = await asyncio.wait_for(
            asyncio.to_thread(_call_claude_messages_create, content, model_name, 4000),
            timeout=120,
        )
        return result
    except asyncio.TimeoutError:
        raise Exception("[Claude] TIMEOUT - Claude לקח יותר מדי זמן לענות")
    except Exception as e:
        raise Exception(f"[Claude] שגיאה בתקשורת עם Claude: {e}")
