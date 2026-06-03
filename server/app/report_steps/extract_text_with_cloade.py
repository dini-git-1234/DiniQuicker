#!/usr/bin/env python3
"""
סריקה/סיכום קבצים (PDF או תמונה) באמצעות Claude API.
פונקציות קריאות: extract_text_with_claude (קובץ + פרומפט), ask_claude_text_only (טקסט בלבד).
"""

import asyncio
import base64
import os
import sys
from pathlib import Path
from typing import Optional

import anthropic

SUPPORTED_IMAGES = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
SUPPORTED_DOCS = {".pdf"}

IMAGE_MIME = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".gif": "image/gif",
    ".webp": "image/webp",
}

# מפתח API חייב להגיע מהסביבה
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")

DEFAULT_SUMMARY_PROMPT = (
    "הנחיה: קרא בעיון את תוכן הקובץ והחזר את המידע בצורה של טקסט טבעי בעברית, כפי שייכתב על ידי שמאי/עורך מקצועי.\n"
    "החזר רק את הטקסט עצמו — אל תכלול סימוני מערכת, כותרות מיותרות, או התייחסות לכך שהטקסט נוצר על ידי מודל.\n"
    "אם הקובץ מכיל פרטים פורמליים (מספרי טאבו, תאריכים, סכומים, כתובות) — ציין אותם בדיוק כפי שהם מופיעים בקובץ.\n"
    "אם יש הרבה מידע חופף, המר בקצרה אך שמור על הדיוק; אל תמציא פרטים שאינם מופיעים.\n"
    "השתמש בשפה טבעית, תקנית וקריאה; אל תוסיף תגיות או תוויות כמו <BULLET> אלא אם נדרש במפורש.\n"
    "אל תתחיל במילים כמו 'סיכום' או 'להלן' — החזר טקסט רציף, נייטרלי ובעל ניסוח אנושי.\n"
    "אם משהו לא ברור בקובץ, החזר את הטקסט כפי שהוא והצביע בקצרה על חוסר בהירות כמסקנה אחת בלבד.\n"
)


def load_file_as_base64(path: Path) -> str:
    with open(path, "rb") as f:
        return base64.standard_b64encode(f.read()).decode("utf-8")


def build_content(file_path: Path, prompt: str) -> list:
    """בונה תוכן לשליחה ל-Claude: קובץ (PDF/תמונה) + בלוק טקסט (פרומפט)."""
    ext = file_path.suffix.lower()
    data = load_file_as_base64(file_path)

    if ext in SUPPORTED_DOCS:
        file_block = {
            "type": "document",
            "source": {
                "type": "base64",
                "media_type": "application/pdf",
                "data": data,
            },
        }
    elif ext in SUPPORTED_IMAGES:
        file_block = {
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": IMAGE_MIME[ext],
                "data": data,
            },
        }
    else:
        raise ValueError(
            f"סוג קובץ לא נתמך: {ext}\n"
            f"נתמך: {SUPPORTED_DOCS | SUPPORTED_IMAGES}"
        )

    text_block = {"type": "text", "text": prompt}
    return [file_block, text_block]


def _call_claude_messages_create(content: list, max_tokens: int = 4096) -> str:
    """קריאה סינכרונית ל-API של Claude (לשימוש מתוך asyncio.to_thread)."""
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=max_tokens,
        messages=[{"role": "user", "content": content}],
    )
    return message.content[0].text


async def extract_text_with_claude(
    file_path: str,
    prompt: str,
    prompt_addition: Optional[str] = None,
    max_tokens: int = 4096,
) -> str:
    """
    סריקה/סיכום קובץ (PDF או תמונה) באמצעות Claude.
    - file_path: נתיב לקובץ.
    - prompt: הפרומפט הבסיסי (הוראות מה לעשות עם הקובץ).
    - prompt_addition: טקסט אופציונלי שמצורף לפרומפט (לאחר הפרומפט הקיים).
    מחזיר את טקסט התגובה מ-Claude.
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"הקובץ לא נמצא: {file_path}")

    full_prompt = prompt
    if prompt_addition and prompt_addition.strip():
        full_prompt = f"{prompt}\n\n{prompt_addition.strip()}"

    content = build_content(path, full_prompt)
    result = await asyncio.to_thread(_call_claude_messages_create, content, max_tokens)
    return result.strip() if result else ""


async def ask_claude_text_only(
    prompt: str,
    max_tokens: int = 4096,
) -> str:
    """
    שליחת פרומפט טקסטואלי בלבד ל-Claude (ללא קבצים).
    מתאים להחלטות על בסיס טקסט (למשל החלטה אם לכלול סעיף בדוח).
    """
    text_block = {"type": "text", "text": prompt}
    content = [text_block]
    result = await asyncio.to_thread(_call_claude_messages_create, content, max_tokens)
    return result.strip() if result else ""


def summarize(file_path: str, prompt_addition: Optional[str] = None) -> str:
    """
    סיכום קובץ עם הפרומפט ברירת המחדל (לשימוש סקריפט/CLI).
    לא async – לשימוש ישיר מסקריפט.
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"הקובץ לא נמצא: {file_path}")

    full_prompt = DEFAULT_SUMMARY_PROMPT
    if prompt_addition and prompt_addition.strip():
        full_prompt = f"{full_prompt}\n\n{prompt_addition.strip()}"

    content = build_content(path, full_prompt)
    return _call_claude_messages_create(content)


def main():
    if len(sys.argv) < 2:
        print("שימוש: python extract_text_with_cloade.py <path_to_file> [prompt_addition]")
        print("קבצים נתמכים: PDF, JPG, PNG, GIF, WEBP")
        sys.exit(1)

    file_path = sys.argv[1]
    prompt_addition = sys.argv[2] if len(sys.argv) > 2 else None

    try:
        summary = summarize(file_path, prompt_addition)
        print("\n" + "=" * 50)
        print("📝 סיכום:")
        print("=" * 50)
        print(summary)
    except (FileNotFoundError, ValueError) as e:
        print(f"❌ שגיאה: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

