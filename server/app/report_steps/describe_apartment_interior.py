from typing import List, Optional
import os

from integrations.gemini_client import ask_gemini_with_search


async def describe_apartment_interior(
    image_paths: List[str],
    text_segment: Optional[str] = None,
    model: str = "gemini-2.5-flash",
) -> str:
    """
    מקבל רשימת נתיבים של תמונות פנים דירה וקטע טקסט,
    ומחזיר תיאור מקצועי ומפורט של פנים הדירה שמשולב בו הטקסט.
    משתמש ב-Gemini.
    """
    if not image_paths:
        raise ValueError("חובה לספק לפחות תמונה אחת")

    for path in image_paths:
        if not os.path.exists(path):
            raise FileNotFoundError(f"התמונה לא נמצאה: {path}")

    # יצירת prompt מקצועי לתיאור נדל"ן
    text_context = f"\nמידע נוסף: {text_segment}\n" if text_segment else ""

    user_prompt = f"""נתח את התמונות של פנים הדירה וכתוב תיאור מקצועי של הנכס.

{text_context}

כתוב תיאור מפורט שכולל:
- סוג הנכס וחלוקה לחדרים
- מצב פיזי ושיפוץ
- חומרי גמר (ריצוף, קירות, חלונות, דלתות)
- מטבח ושירותים (אם נראים)
- מערכות טכניות (מיזוג, תאורה, חשמל)
- נקודות ייחודיות

כללים:
-תכתוב כאילו אתה שמאי מקרקעין שבא לדירה, וכותב תאור מקצועי ואוביקטיבי על מצב הנכס על סמך מראה עיניו. (כאילו זה לא מתמונות אלא מביקור בדירה)
- תאר רק מה שנראה בתמונות, מה שלא רואים- תדלג ותתעלם
- השתמש במונחים מקצועיים של נדל"ן
- , ותתעלם אם לא קיימים ציין גם ליקויים בולטים וחמורים בלבד אם קיימים
- התאור שלך אמור להיות כאילו אתה שמאי שמבקר בדירה ואתה מתאר אותה בצורה מקצועית ומפורטת
- אין צורך לכתוב סיכום סופי בתיאור
-, וכן להתעלם מחפצים אישיים ומרהיטים אישיים, כאלה שעוברים איתם דירה. תתייחס רק לדברים קבועים ולא ניידים! לא ארונות, לא שולחנות או דברים דומים. שלא משמעותיים לשווי הנכס. יש להתעלם מבלגן ומפרטים חסרי משמעות
- כתוב 400-700 מילים במבנה מאורגן
"""

    # שימוש ב-Gemini דרך הקליינט המרכזי
    try:
        print("[describe_apartment_interior] Calling ask_gemini_with_search...")
        response_text = await ask_gemini_with_search(
            prompt=user_prompt,
            model_name=model,
            images=image_paths,
            use_search=False,  # בלי חיפוש - מתמקדים בתמונות בלבד
        )

        # בדיקה שהתגובה תקינה
        if not response_text:
            raise Exception("Gemini החזיר תגובה ריקה (None)")
        if not isinstance(response_text, str):
            raise Exception(f"Gemini החזיר תגובה מסוג לא תקין: {type(response_text)}")
        if response_text.strip() == "":
            raise Exception("Gemini החזיר תגובה ריקה (string ריק)")
        if "Error communicating with Gemini" in response_text:
            raise Exception(f"Gemini החזיר שגיאה: {response_text}")

        return response_text

    except Exception as e:
        raise Exception(f"שגיאה ביצירת תיאור הנכס: {str(e)}")

