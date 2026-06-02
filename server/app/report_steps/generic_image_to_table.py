import json
from typing import Any, Dict, List, Optional

from integrations.gemini_client import ask_gemini_with_search


PROMPT_GENERIC_TABLE_BASE = """
משימה: חלץ טבלה מתמונת מסך והמר אותה לפורמט JSON מדויק.

הנחיות:
1. התייחס רק לטבלה המרכזית בתמונה.
2. כל שורה בטבלה צריכה להופיע כרשימה נפרדת במערך rows.
3. שמור על סדר הטקסט בעברית כך שיהיה קריא (לא הפוך).
4. אל תוסיף טקסט הסבר, רק את אובייקט ה-JSON.

{extra_instructions}

פורמט הפלט:
החזר אך ורק אובייקט JSON בפורמט הבא, ללא טקסט נוסף:
{{
  "headers": ["כותרת1", "כותרת2", "..."],
  "rows": [
    ["ערך1", "ערך2", "..."],
    ["ערך1", "ערך2", "..."]
  ]
}}
""".strip()


def build_table_prompt(extra_instructions: str | None = None) -> str:
    extra = extra_instructions or ""
    return PROMPT_GENERIC_TABLE_BASE.format(extra_instructions=extra)


async def get_table_from_image(
    image_path: str,
    extra_instructions: str | None = None,
) -> Optional[Dict[str, Any]]:
    prompt = build_table_prompt(extra_instructions)
    raw_response = await ask_gemini_with_search(
        prompt=prompt,
        images=[image_path],
        use_search=False,
    )

    try:
        clean_json = raw_response.replace("```json", "").replace("```", "").strip()
        data: Dict[str, Any] = json.loads(clean_json)
        return data
    except Exception as e:
        print(f"Error while parsing Gemini response for image {image_path}: {e}")
        return None


async def get_table_from_images(
    image_paths: List[str],
    extra_instructions: str | None = None,
) -> Optional[Dict[str, Any]]:
    prompt = build_table_prompt(extra_instructions)
    """
    מקבל רשימת נתיבי תמונות (למשל כמה מקטעים של אותה טבלה),
    קורא ל-Gemini לכל תמונה ומאחד את השורות לטבלה אחת.
    """
    all_rows: List[List[Any]] = []
    headers: Optional[List[str]] = None

    for image_path in image_paths:
        try:
            raw_response = await ask_gemini_with_search(
                prompt=prompt,
                images=[image_path],
                use_search=False,
            )
            clean_json = raw_response.replace("```json", "").replace("```", "").strip()
            data = json.loads(clean_json)

            if not isinstance(data, dict):
                continue

            img_headers = data.get("headers")
            img_rows = data.get("rows")

            if not img_headers or not img_rows:
                continue

            if headers is None:
                headers = img_headers

            if isinstance(img_rows, list):
                all_rows.extend(img_rows)
        except Exception as e:
            print(f"Error while processing image {image_path}: {e}")
            continue

    if headers is None or not all_rows:
        return None

    return {
        "headers": headers,
        "rows": all_rows,
    }

