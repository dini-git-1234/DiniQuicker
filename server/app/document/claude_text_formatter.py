import os
import anthropic


# System Prompt לקלוד
FORMATTER_SYSTEM_PROMPT = """
אתה עורך טקסטים מומחה המתמחה בעיצוב וארגון טקסטים בעברית לדוחות מקצועיים.

תפקידך: לקבל טקסט גולמי ולהחזיר אותו מעוצב ומסודר עם סימונים מיוחדים.

## סימונים זמינים:
- <HEADING1>טקסט</HEADING1> - כותרת ראשית (רק אם באמת צריך, נדיר)
- <HEADING2>טקסט</HEADING2> - כותרת משנה
- <HEADING3>טקסט</HEADING3> - כותרת משנה קטנה
- <BULLET>טקסט - נקודה ברשימה (השתמש הרבה!)
- <BOLD>טקסט</BOLD> - הדגשה (רק לדברים חשובים,מידי פעם לשים)
- <UNDERLINE>טקסט</UNDERLINE> - קו תחתון (רק לדברים מאוד חשובים )
- <BR> - ירידת שורה (אם צריך להפריד בין קטעים)

## עקרונות חשובים:
1. **חלוקה לנקודות:** כל רעיון/משפט עצמאי = נקודה נפרדת
2. **נקודות ברורות:** כל נקודה צריכה להיות 10-30 מילים (לא יותר!)
3. **קיבוץ הגיוני:** אם 2-3 משפטים מדברים על אותו נושא, שים אותם בנקודה אחת
4. **הדגשות במשורה:** רק מילות מפתח חשובות (שמות מקומות, מספרים, מונחים מקצועיים)
5. **לא להמציא:** השתמש רק במידע שניתן לך, אל תוסיף דברים
6. **שמור על הטון:** טון מקצועי ופורמלי

## דוגמה:
טקסט קלט:
"ירושלים היא בירת ישראל והינה העיר הגדולה במדינה. שוכנת על הרי יהודה. השכונה יוקרתית ודתית עם בתי כנסת רבים."

פלט נכון:
<BULLET>ירושלים היא בירת ישראל והינה העיר הגדולה במדינה, שוכנת על <BOLD>הרי יהודה</BOLD>.
<BULLET>השכונה <BOLD>יוקרתית ודתית</BOLD> עם בתי כנסת רבים ומוסדות חינוך תורניים.

## הנחיות לפי סוג תוכן:
###
תאור ביקור בנכס
-הדגש שמות של השמאי המבקר, של המציג ושל הבעלים
-הדגש את התאריך
-שים נקודות בתחילת כל משפט בצורה הגיונית

### תאור סביבה:
- התחל ב-HEADING3 אם יש כותרת
- חלק לנקודות לפי נושאים: מיקום → אופי השכונה → שירותים → פיתוח
- הדגש: שמות מקומות, מאפיינים ייחודיים


### תאור נכס פנימי:
- חלק לנקודות לפי חדרים/אזורים
- הדגש: מספרי חדרים, שטחים, רמת גימור
- פרט טכני חשוב = הדגשה
-לא כל פרט צריך להיות נקודה נפרדת! אפשר לשים כמה ביחד

### נתוני טאבו:
- כל פרט = נקודה נפרדת
- הדגש: מספרים, תאריכים, סכומים
- שמור פורמליות גבוהה

### מידע תכנוני:
- חלק לפי תכניות/תקנות
- הדגש: מספרי תכניות, תאריכים, זכויות בנייה

## חשוב:
- אל תוסיף כותרות אם לא ניתנו לך
- אל תשנה עובדות או מספרים
- שמור על השפה המקורית (אם פורמלי - תישאר פורמלי)
- אם הטקסט קצר (1-2 משפטים), אפשר להחזיר בלי נקודות
- כל התוכן שתחזיר יוצג במסמך בגודל גופן 12 – התאם את אורך המשפטים והפסקאות בהתאם.

החזר **רק** את הטקסט המעוצב, בלי הסברים נוספים.
"""


async def format_text_with_claude(
    text: str,
    context: str | None = None,
) -> str:
    """
    שולח טקסט ל-Claude לעיצוב וארגון

    Args:
        text: הטקסט הגולמי לעיצוב
        context: הקשר אופציונלי (למשל: "תאור סביבה", "נתוני טאבו")

    Returns:
        טקסט מעוצב עם סימונים מיוחדים
    """
    if not text or not text.strip():
        return ""

    # לוג קלט לקלוד (מקוצר)
    try:
        preview = text.strip().replace("\n", " ")[:500]
        print(f"[claude_text_formatter] INPUT ({context or 'no-context'}): {preview}")
    except Exception:
        pass

    api_key = os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("CLAUDE_API_KEY")
    if not api_key:
        raise ValueError("[claude_text_formatter] Missing ANTHROPIC_API_KEY or CLAUDE_API_KEY")

    client = anthropic.Anthropic(api_key=api_key)

    # בניית הפרומפט
    prompt = f"""עצב את הטקסט הבא בצורה מסודרת ומקצועית.

{f"הקשר: {context}" if context else ""}

טקסט לעיצוב:
{text}

החזר את הטקסט מעוצב עם הסימונים המתאימים.
"""

    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2000,
            system=FORMATTER_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}],
        )
        # content יכול להכיל TextBlock, ThinkingBlock וכו' – לוקחים את הטקסט מהבלוק הראשון שמכיל text
        first_text = ""
        for block in response.content:
            part = getattr(block, "text", None)
            if part:
                first_text = part
                break
        formatted_text = (first_text or "").strip()

        # לוג פלט מקלוד (מקוצר)
        try:
            preview_out = formatted_text.replace("\n", " ")[:500]
            print(f"[claude_text_formatter] OUTPUT ({context or 'no-context'}): {preview_out}")
        except Exception:
            pass

        return formatted_text

    except Exception as e:
        print(f"[claude_text_formatter] שגיאה: {str(e)}")
        return text


async def summarize_contract_text(
    text: str,
    contract_type: str,
) -> str:
    """
    מסכם חוזה קצר ומדויק: 2–3 משפטים בלבד, רק פרטים מהותיים מאוד.
    """
    if not text or not text.strip():
        return ""

    api_key = os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("CLAUDE_API_KEY")
    if not api_key:
        raise ValueError("[claude_text_formatter] Missing ANTHROPIC_API_KEY or CLAUDE_API_KEY")

    prompt = f"""
אנא כתוב תקציר תמציתי מאוד של המסמך הבא מסוג {contract_type}.
התקציר צריך להכיל רק את הפרטים היותר חשובים בלבד:
- מי הצדדים לחוזה
- תאריך החתימה
- סכום העסקה או דמי השכירות המרכזיים
- תנאים מהותיים מאוד בלבד

כתוב רק 2–3 משפטים, בלי פתיחים ארוכים, בלי בלבול ובלי סיכום כללי.
אם אין מידע רלוונטי, כתוב משפט אחד קצר שמתמקד במה שיש.

{ text }
"""

    try:
        response = anthropic.Anthropic(api_key=api_key).messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=400,
            messages=[{"role": "user", "content": prompt}],
        )

        first_text = ""
        for block in response.content:
            part = getattr(block, "text", None)
            if part:
                first_text = part
                break

        summary = (first_text or "").strip()
        if summary:
            return summary
        return text
    except Exception as e:
        print(f"[claude_text_formatter] שגיאת תקציר חוזה: {e}")
        return text


async def format_multiple_texts(texts_dict: dict[str, str]) -> dict[str, str]:
    """
    מעצב מספר טקסטים בבת אחת (יעיל יותר)

    Args:
        texts_dict: מילון של {context: text}

    Returns:
        מילון של {context: formatted_text}
    """
    results: dict[str, str] = {}

    for context, text in texts_dict.items():
        if text and text.strip():
            results[context] = await format_text_with_claude(text, context)
        else:
            results[context] = ""

    return results

