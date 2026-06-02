import ast
import fitz
import hashlib
import json
import re
from pathlib import Path

from report_steps.extract_text_with_cloade import extract_text_with_claude, ask_claude_text_only
from utils.temp_paths import temp_dir


def pdf_to_text(path: str) -> str:
    """מחלץ טקסט מכל עמודי ה‑PDF."""
    doc = fitz.open(path)
    text = ""
    for page in doc:
        text += page.get_text()
    return text


def pdf_to_images(path: str, max_pages: int | None = None, dpi: int = 200) -> list[str]:
    """
    ממיר עמודי PDF לתמונות זמניות על הדיסק ומחזיר רשימת נתיבים.
    משמש במיוחד למסמכים שסורקו כתמונה (ללא טקסט).
    """
    doc = fitz.open(path)
    image_paths: list[str] = []
    # Write images only under TEMP, not alongside the source PDF.
    digest = hashlib.sha1(path.encode("utf-8", errors="ignore")).hexdigest()[:10]
    out_dir = temp_dir("pdf_images", f"pdf_{digest}")
    for page_index, page in enumerate(doc):
        if max_pages is not None and page_index >= max_pages:
            break
        pix = page.get_pixmap(dpi=dpi)
        img_path = out_dir / f"page_{page_index + 1}.png"
        pix.save(str(img_path))
        image_paths.append(str(img_path))
    return image_paths


_TABU_PROMPT = """
קרא את קובץ נסח הטאבו המצורף.
אנא בצע שני חלקים:

חלק 1 – JSON  
החזר אובייקט JSON תקין עם השדות הבאים:
- בעלי הנכס
- gush
- helka
- tat_helka
- type (שפה יהיה את סוג הנכס)
- floor (שפה יהיה את קומת הדירה)
- takanon (שדה זה יהיה המילה "מצוי" או "מוסכם" בלבד – לפי מה שכתוב בנסח לגבי תקנון הבתים המשותפים)
- מגרש
- כתובת מלאה
- שטח הדירה במ"ר
- החלק ברכוש המשותף
- העסקה האחרונה (מי קנה, מי מכר, תאריך)
- משכנתאות (רשימה של משכנתאות עם פרטים מלאים) אם יש
- הערות מיוחדות אם יש
חלק 2 – Summary  
סכם בקצרה (5–10 שורות) את עיקרי המידע במסמך.
הסיכום צריך לכלול את כל הפרטים החשובים של הנכס.
הסיכום צריך להיות בשפה מקצועית ונדלנית, ללא מלל נלווה מיותר, כאילו אתה קורא נסח טאבו ומסכם את הדברים הרלוונטיים.
חשוב:  
• החזר את שני החלקים בצורה מאורגנת.  
• אין טקסט נוסף מעבר למה שהתבקשת.  
"""


async def extract_full_data_from_pdf(pdf_path: str) -> dict:
    """
    קורא PDF → שולח ל-Claude → מקבל JSON + Summary.
    """
    output = await extract_text_with_claude(pdf_path, _TABU_PROMPT, max_tokens=4096)
    output = output.strip()
    try:
        json_data, summary_text = parse_gpt_output_to_json_and_summary(output)

        if "error" in json_data:
            # טיפול בשגיאה — תוכלי לשמור debug לשורה/קובץ
            print("Parsing failed, raw output:\n")
        else:
            print("JSON dict:", json_data)
            print("Summary:", summary_text)
            return summary_text, json_data
    except Exception:
        # fallback אם GPT לא שמר פורמט מדויק
        return {"error": "Parsing error", "raw_output": output}, ""


def _cleanup_common_json_issues(text: str) -> str:
    # תיקונים קטנים שבדרך כלל עוזרים ל־json.loads
    # 1. התחלות/סוף של קוד ב־markdown
    text = text.strip()
    # החלפת מרכאות "חכמות"
    text = text.replace("“", '"').replace("”", '"').replace("’", "'").replace("‘", "'")
    # הסרת סימני ``` אם נשארו
    text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s*```$", "", text)
    # הסרת BOM
    text = text.lstrip("\ufeff")
    # הסרת פסיקים מיותרים לפני סוגר (trailing commas)
    text = re.sub(r",\s*([}\]])", r"\1", text)
    return text


def _find_fenced_json(text: str):
    """
    מחפש בלוק ```json ... ``` או ``` ... ``` ומחזיר הטקסט שבתוכו וגם האינדקס שבו מסתיים הבלוק.
    """
    for m in re.finditer(r"```(?:json)?", text, flags=re.IGNORECASE):
        start = m.end()
        end = text.find("```", start)
        if end != -1:
            inner = text[start:end].strip()
            # אם יש מחרוזת שמתחילה עם { נחזיר אותה
            idx = inner.find("{")
            if idx != -1:
                return inner[idx:].strip(), end + 3
            else:
                return inner, end + 3
    return None, None


def _extract_first_brace_json(text: str):
    """
    מוצא את ה־JSON הראשון שמתחיל ב־'{' ומחזיר את הבלוק המלא (עם סגירה מאוזנת)
    מטפל בר־מחרוזות ובעקיפות \"\"
    """
    start = text.find("{")
    if start == -1:
        return None, None
    i = start
    depth = 0
    in_string = False
    esc = False
    while i < len(text):
        ch = text[i]
        if esc:
            esc = False
        elif ch == "\\":
            esc = True
        elif ch == '"':
            in_string = not in_string
        elif not in_string:
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    return text[start : i + 1], i + 1
        i += 1
    return None, None


def parse_gpt_output_to_json_and_summary(output: str):
    """
    מקבל את הטקסט שהתקבל מה־model (response.output_text)
    ומנסה להחזיר:
      (json_dict, summary_str)

    אם לא מצליח לפענח — מחזיר ({ "error": "...", "raw_output": output }, "")
    """
    if not output:
        return {"error": "empty_output"}, ""

    # ניסיון 1: חיפוש בלוק fenced ```json ... ```
    block, end_idx = _find_fenced_json(output)
    candidate = None
    json_obj = None
    summary = ""

    if block:
        cleaned = _cleanup_common_json_issues(block)
        # נסיון ל־json.loads
        try:
            json_obj = json.loads(cleaned)
            # נסה לחלץ summary אחרי הבלוק
            summary = output[end_idx:].strip()
            # חפש מילות מפתח לסיכום אם צריך
            m = re.search(
                r"(##+SUMMARY|Summary:|Summary|סיכום:|סיכום)",
                summary,
                flags=re.IGNORECASE,
            )
            if m:
                summary = summary[m.end() :].strip()
            return json_obj, summary
        except Exception:
            candidate = block  # נמשיך לדרכי חירום

    # ניסיון 2: למצוא JSON ראשון באמצעות bracket-balancing בכל הטקסט
    if json_obj is None:
        block2, end2 = _extract_first_brace_json(output)
        if block2:
            cleaned = _cleanup_common_json_issues(block2)
            try:
                json_obj = json.loads(cleaned)
                # קח טקסט שמופיע אחרי הסוגר של ה־JSON כ־summary
                summary = output[end2:].strip()
                # חפש מילות מפתח
                m = re.search(
                    r"(##+SUMMARY|Summary:|Summary|סיכום:|סיכום)",
                    summary,
                    flags=re.IGNORECASE,
                )
                if m:
                    summary = summary[m.end() :].strip()
                return json_obj, summary
            except Exception:
                candidate = block2

    # ניסיון 3: אם יש קטע ``` שבו יש JSON אבל לא מצליחים ל־json.loads, נסה לתקן עוד בעיות ולהשתמש ב־ast.literal_eval
    if candidate:
        s = _cleanup_common_json_issues(candidate)
        # החלפת single quotes ל־double quotes אם נראה שה־JSON בשימוש ב־single quotes
        if re.search(r"'\w+' *:", s):
            s2 = s.replace("'", '"')
        else:
            s2 = s
        # הסרת שורות של "```json" אם נשארו
        s2 = re.sub(r"^```.*?\n", "", s2, flags=re.DOTALL)
        # נסיון ראשון ל־json.loads
        try:
            json_obj = json.loads(s2)
            return json_obj, output.split("```")[-1].strip()
        except Exception:
            # נסיון עם ast.literal_eval (פחות בטוח אבל עוזר אם בפלט יש single quotes)
            try:
                json_obj = ast.literal_eval(s2)
                return json_obj, output.split("```")[-1].strip()
            except Exception:
                pass

    # ניסיון 4: חיפוש ישיר של תבנית JSON בין ``` ו־``` או בין סימון ```json ו־"Summary:"
    m_sum = re.search(r"(Summary:|##+SUMMARY|סיכום:|Summary)\s*", output, flags=re.IGNORECASE)
    if m_sum:
        before = output[: m_sum.start()].strip()
        # חפש את ה־JSON האחרון בתוך before בעזרת bracket balancing אחורה
        last_brace = before.rfind("{")
        if last_brace != -1:
            block3, _end3 = _extract_first_brace_json(before[last_brace:])
            if block3:
                s = _cleanup_common_json_issues(block3)
                try:
                    json_obj = json.loads(s)
                    summary = output[m_sum.end() :].strip()
                    return json_obj, summary
                except Exception:
                    try:
                        json_obj = ast.literal_eval(s)
                        summary = output[m_sum.end() :].strip()
                        return json_obj, summary
                    except Exception:
                        pass

    # לא הצלחנו לפענח JSON תקין — נחזיר fallback עם ה־raw output
    return {"error": "Parsing error - could not extract valid JSON", "raw_output": output}, ""


_RIGHTS_CONFIRMATION_PROMPT = """
קרא את קובץ אישור הזכויות מרמ"י המצורף.
אנא סכם בקצרה (5–15 שורות) את עיקרי המסמך: סוג האישור, פרטי הנכס/המגרש, הזכויות המאושרות וכל פרט רלוונטי.
הסיכום בשפה מקצועית ונדלנית, ללא מלל מיותר.
כלול: מספר התיק בכותרת, תקופת החכירה, הכתובת כולל גוש וחלקה וכתובת טסקט, התכנית, שטח, על שם מי רשומות הזכויות, רישומים על הערות, פעולות, משכנתאות, תקופת החכירה.
"""


async def extract_rights_confirmation_from_pdf(pdf_path: str) -> str | None:
    """
    קורא PDF של אישור זכויות מרמ"י → שולח ל-Claude → מחזיר סיכום.
    """
    output = await extract_text_with_claude(pdf_path, _RIGHTS_CONFIRMATION_PROMPT)
    return output if output else None


_LEASE_DOCUMENT_PROMPT = """
קרא את קובץ מסמך החכירה המצורף.
אנא סכם בקצרה (5–15 שורות) את עיקרי המסמך: סוג החכירה, פרטי הנכס/המגרש, צדדים לחוזה, תקופת החכירה, תנאים עיקריים וכל פרט רלוונטי.
הסיכום בשפה מקצועית ונדלנית, ללא מלל מיותר.
"""


async def extract_lease_document_from_pdf(pdf_path: str) -> str | None:
    """
    קורא PDF של מסמך חכירה → שולח ל-Claude → מחזיר סיכום.
    """
    output = await extract_text_with_claude(pdf_path, _LEASE_DOCUMENT_PROMPT)
    return output if output else None


# תגובה שמסמנת שלא לכלול סעיף הסכם חכירה בדוח
NO_LEASE_MARKER = "ללא"


async def decide_lease_section_for_report(lease_summary: str) -> str | None:
    """
    מחזיר פסקה קצרה לשילוב בשומה רק אם יש בהסכם שינויים משמעותיים או תוספות חשובות;
    אחרת מחזיר None (ולא יופיע סעיף הסכם חכירה בדוח).
    """
    if not lease_summary:
        return None
    prompt = f"""

להלן תקציר מהסכם החכירה:
-------------------------
{lease_summary}
-------------------------


תן לי תקציר של משפט אחד לכל פסקה במסמך (לא הפסקאות של הטבלאות, אלא הפסקאות שמדברות על התקנות של הבית המשותף)
אני רוצה פסקה של התקנות בבית המשותף. מנוסחת בצורה נדלנית ויפה.

"""
    output = await ask_claude_text_only(prompt)
    out = (output or "").strip()
    if not out:
        return None
    # תשובה "ללא" (כולל עם נקודה/רווח) = לא לכלול סעיף בדוח
    if out.rstrip(".").strip() == NO_LEASE_MARKER or out == NO_LEASE_MARKER:
        return None
    return out


_DOCUMENT_SUMMARY_PROMPT_TEMPLATE = """
קרא את הקובץ המצורף (מסוג "{document_type_label}").
הבא את עקרי הטקסט בצורה מודולרית ומסודרת:
- כותרות משנה ברורות לכל נושא
- סיכומים תמציתיים תחת כל כותרת
- שפה מקצועית ונדלנית, ללא מלל מיותר
"""


async def extract_document_summary_from_pdf(pdf_path: str, document_type_label: str) -> str | None:
    """
    חילוץ עקרי טקסט מ-PDF בצורה מודולרית – לכל סוג מסמך באמצעות Claude.
    """
    prompt = _DOCUMENT_SUMMARY_PROMPT_TEMPLATE.format(document_type_label=document_type_label)
    output = await extract_text_with_claude(pdf_path, prompt)
    return output if output else None


_PREVIOUS_APPRAISAL_PROMPT = """
קרא את קובץ שומת המקרקעין הקודמת לנכס המצורף.
אנא הפק תקציר משפטי קצר, טכני וענייני בלבד של השומה, כאילו אתה כותב סעיף בדוח שומה חדש תחת הכותרת "שומות קודמות שנערכו בנכס".
הסיכום צריך להיות בנוסח נדלני מקצועי, ללא מלל מיותר, ולהתמקד רק בפרטים הטכניים העיקריים: סוג הנכס ומיקומו (כולל גוש/חלקה אם מופיעים), מטרת השומה ומזמין השומה (אם ברור), מועד השומה הקודמת, השווי שנקבע (אם מופיע במפורש).
אורך הסיכום: 1-2 משפטים.
אל תכלול טקסט חופשי לא רלוונטי, סיפורים, נימוקים ארוכים או ציטוטים מלאים מהמסמך. בלי הקדמות ופתיחות. רק את הטקסט עצמו.
"""


async def extract_previous_appraisal_summary_from_pdf(pdf_path: str) -> str | None:
    """
    קורא PDF של שומת מקרקעין קודמת → שולח ל-Claude → מחזיר תקציר טכני וקצר לשילוב בסעיף שומות קודמות.
    """
    output = await extract_text_with_claude(pdf_path, _PREVIOUS_APPRAISAL_PROMPT)
    return output if output else None


# ערכי תקנון מהטאבו – מצוי = תקנון סטנדרטי, מוסכם = יש שינויים
TAKANON_STANDARD = "מצוי"
TAKANON_COMPLEX = "מוסכם"


_BYLAWS_PROMPT = """
קרא את קובץ תקנון הבתים המשותפים המצורף.
הנחיות:
- קרא רק את החלקים הרלוונטיים לתקנון הנוכחי של הבית המשותף.
- השמט כל פרט שאינו רלוונטי להבנת הזכויות והחובות העיקריות של בעלי הדירות.
- החזר פסקה קצרה מאוד, המחולקת למספר משפטים קצרים וברורים.
- אל תוסיף הקדמות, ציטוטים ארוכים או ניסוחים משפטיים מיותרים.
- אל תכלול טבלאות, סעיפים טכניים, הפניות לחוקים או פרטים פרוצדורליים.
- השפה צריכה להיות מקצועית ונדלנית, אבל פשוטה ועניינית.
- קרא את כל המסמך בלי להשמיט פרטים (הטקסט הרלוונטי לא בהכרח בעמודים הראשונים).
"""


async def extract_bylaws_changes_from_pdf(pdf_path: str) -> str | None:
    """
    סריקת קובץ תקנון בתים משותפים כאשר התקנון מורכב/מוסכם – באמצעות Claude.
    """
    output = await extract_text_with_claude(pdf_path, _BYLAWS_PROMPT)
    cleaned = (output or "").strip()

    # אם המודל החזיר הודעה שגוגל/ג׳מיני לא הצליח להוציא טקסט רלוונטי – נעדיף לא להכניס זאת לדוח
    error_markers = [
        "הטקסט שנשלח קצר מדי",
        "לא הצלחתי לזהות טקסט רלוונטי",
        "לא נמצא טקסט מתאים לתקנון",
    ]
    if any(marker in cleaned for marker in error_markers):
        return None

    return cleaned or None

