from datetime import datetime
from pathlib import Path
import re

from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Inches

from models.report_request import (
    DocumentRequest,
    ImageBlock,
    ImageGroupBlock,
    TableBlock,
    TextBlock,
)

from document.claude_text_formatter import format_text_with_claude, summarize_contract_text
from document.text_parser import parse_formatted_text


ERROR_TEXT_PREFIX = "__QA_ERROR__:"
DEFAULT_SESSION_ERROR_MESSAGE = "אופס, לא הצלחתי למצוא את המידע המבוקש"


def _extract_error_text(value: object) -> tuple[bool, str]:
    """מחזיר (is_error, clean_text). הסימון נשמר באותו שדה טקסט עם prefix פנימי."""
    if value is None:
        return False, ""
    text = value if isinstance(value, str) else str(value)
    if text.startswith(ERROR_TEXT_PREFIX):
        clean = text[len(ERROR_TEXT_PREFIX) :].strip() or DEFAULT_SESSION_ERROR_MESSAGE
        return True, clean
    return False, text


# סדר וכותרות למסמכים משפטיים בדוח (מתוך data.legal_documents)
# הערה: תשריט בית משותף מטופל בנפרד – תמונה תחת הכותרת (לא טקסט מסריקה)
LEGAL_DOCUMENTS_ORDER = [
    "נתוני טאבו",
    "אישור זכויות",
    "הסכם חכירה",
    "מינהל אזרחי",
    "אישור חברה משכנת",
    "הסכם מכר",
    "הסכם שכירות",
    "טופס ארנונה",
]


async def build_document(parcel, address, meta, saved_files, data):
    blocks = []
    print("Building document...")

 
    # 🔹 לכבוד:
    blocks.append(
        TextBlock(
            text="לכבוד:",
            bold=True,
            underline=True,
            small=True,
            # align="left"
        )
    )

    blocks.append(
        TextBlock(
            text=f"{meta.valuation_for}",  # נתון משתנה
            # align="left",
            spacing_after=12,
        )
    )

    # 🔹 תאריך (שמאל)
    blocks.append(
        TextBlock(
            text=f"תאריך: {datetime.now().strftime('%d/%m/%Y')}",
            align="left",
            spacing_after=12,
        )
    )

    # 🔹 מספר שומה
    blocks.append(
        TextBlock(
            # text=f"מספר שומה: {meta.appraisal_number}",
            text=f"מספר שומה:  {meta.valuation_number}",
            spacing_after=24,
            align="left",
        )
    )

    # 🔷 כותרת מרכזית (עמוד ראשון – גודל 15)
    blocks.append(
        TextBlock(
            text="שומת מקרקעין מלאה",
            bold=True,
            font_size=15,
            underline=True,
            align="center",
            spacing_after=12,
        )
    )
    # יצירת רשימה של חלקי הטקסט רק עבור ערכים שקיימים
    parts = [
        f"{label} {val}"
        for label, val in [
            ("גוש", parcel.gush),
            ("חלקה", parcel.helka),
            ("תת חלקה", parcel.tat_helka),
        ]
        if val
    ]

    # חיבור הכל למחרוזת אחת
    final_text = " ".join(parts)

    if final_text:
        blocks.append(
            TextBlock(
                text=final_text,
                bold=True,
                underline=True,
                font_size=14,
                align="center",
                spacing_after=12,
            )
        )
    blocks.append(
        TextBlock(
            text=f"{address.street} {address.house_number}, {address.city}",
            bold=True,
            underline=True,
            font_size=14,
            align="center",
            spacing_after=24,
        )
    )
    # 🔷 תמונת חוץ
    if saved_files.get("outside"):
        blocks.append(
            ImageBlock(
                path=Path(saved_files["outside"]),
                role="cover",
                bordered=True,
                max_height_inches=4.5,  # מגביל גובה
            )
        )

    # מטרת השומה
    blocks.append(
        TextBlock(
            text=" 1. מטרת השומה וזהות מזמין השומה ",
            underline=True,
            bold=True,
            font_size=12,
            spacing_after=24,
            # align="left"
        )
    )

    # שימוש בנוסח שנוצר על ידי Gemini, או fallback לנוסח סטטי
    if data.purpose_statement and data.purpose_statement.strip():
        is_err, clean = _extract_error_text(data.purpose_statement)
        blocks.append(
            TextBlock(
                text=clean,
                font_size=12,
                spacing_after=24,
                variant="error" if is_err else None,
                # align="left"
            )
        )
    else:
        # Fallback לנוסח סטטי אם לא נוצר נוסח חדש
        blocks.append(
            TextBlock(
                text=(
                    f"השומה הוזמנה על ידי {meta.customer},  לצורך הערכת שווי הנכס "
                    "כאשר הוא פנוי וחופשי מכל חוב, שיעבוד או זכויות כלשהן לצד שלישי בנכס הנדון, "
                    f"למטרת  {meta.purpose} "
                    "השומה נועדה למטרה זו בלבד, וכל שימוש אחר במסמך זה אינו באחריות החותם מטה."
                ),
                font_size=12,
                # align="left",
                spacing_after=24,
            )
        )

    # המועד הקובע לשורה
    blocks.append(
        TextBlock(
            text="2. המועד הקובע לשומה: ",
            underline=True,
            bold=True,
            font_size=12,
            spacing_after=24,
            # align="left"
        )
    )

    blocks.append(
        TextBlock(
            text=f"{datetime.now().strftime('%d/%m/%Y')} ",
            font_size=12,
            spacing_after=24,
            # align="left"
        )
    )
    blocks.append(
        TextBlock(
            text=".3 מועד הביקור בנכס, זהות המבקר וזהות מציג הנכס",
            underline=True,
            bold=True,
            font_size=12,
            spacing_after=24,
            # align="left"
        )
    )
    if data.visit_text:
        is_err, clean = _extract_error_text(data.visit_text)
        if is_err:
            blocks.append(
                TextBlock(text=clean, variant="error", font_size=12, spacing_after=24)
            )
        else:
            # שליחה לקלוד לעיצוב
            formatted_env = await format_text_with_claude(
                text=clean,
                context="תאור ביקור בנכס",
            )
            # פירוק לבלוקים
            env_blocks = parse_formatted_text(formatted_env)
            blocks.extend(env_blocks)

    # 1. שורת סוג הנכס – מהטאבו (TYPE) או ברירת מחדל
    property_type = (getattr(data, "tabuJSON", None) or {}).get("type") or "דירת מגורים"
    if isinstance(property_type, str):
        property_type = property_type.strip() or "דירת מגורים"
    rows = [
        ["סוג הנכס", property_type, ""],
    ]

    # 2. הוספת גוש, חלקה ותת חלקה רק אם יש בהם תוכן
    rows.extend(
        [
            [label, val, ""]
            for label, val in [
                ("גוש", parcel.gush),
                ("חלקה", parcel.helka),
                ("תת חלקה", parcel.tat_helka),
            ]
            if val
        ]
    )

    # 3. שאר השורות – גמישות: רק שורות עם רלוונטיות
    rows.append(["כתובת הנכס", f"{address.street} {address.house_number}, {address.city}", ""])
    rows.append(["איתור הנכס ב-govmap", "אותר" if data.govmap_results else "לא אותר", ""])
    # בית משותף (תשריט) – רק אם הועלתה תמונת תשריט בית משותף
    if saved_files.get("building_plan"):
        rows.append(["בית משותף", "אותר", ""])
    # היתר בניה – מופיע תמיד (ניתן להפוך למותנה בעתיד אם יוגדר מקור)
    rows.append(["היתר בניה", "אותר", ""])

    # הוספה לבלוקים
    blocks.append(
        TextBlock(
            text="4. זיהוי הנכס",
            underline=True,
            bold=True,
            font_size=12,
            spacing_after=24,
            # align="left"
        )
    )

    blocks.append(
        TableBlock(
            headers=["סוג הזיהוי", "זיהוי", "תיאור / הערות"],
            rows=rows,
            column_widths=[2.5, 2.5, 3.0],
        )
    )

    # משפט: איך זיהינו את הנכס (לפי המסמכים שקיימים ב-data.legal_documents)
    identification_labels = []
    legal_docs = getattr(data, "legal_documents", None) or {}

    is_err, tabu_txt = _extract_error_text(legal_docs.get("נתוני טאבו"))
    if (not is_err) and tabu_txt.strip():
        identification_labels.append("נסח טאבו")

    if saved_files.get("building_plan"):
        identification_labels.append("תשריט בית משותף")

    is_err, rights_txt = _extract_error_text(legal_docs.get("אישור זכויות"))
    if (not is_err) and rights_txt.strip():
        identification_labels.append('אישור זכויות מרמ"י')

    is_err, lease_txt = _extract_error_text(legal_docs.get("הסכם חכירה"))
    if (not is_err) and lease_txt.strip():
        identification_labels.append("הסכם חכירה")

    is_err, civil_txt = _extract_error_text(legal_docs.get("מינהל אזרחי"))
    if (not is_err) and civil_txt.strip():
        identification_labels.append("מינהל אזרחי")

    is_err, mort_txt = _extract_error_text(legal_docs.get("אישור חברה משכנת"))
    if (not is_err) and mort_txt.strip():
        identification_labels.append("אישור חברה משכנת")
    if identification_labels:
        identification_sentence = "זיהוי הנכס בוצע באמצעות: " + ", ".join(identification_labels) + "."
        blocks.append(
            TextBlock(
                text=identification_sentence,
                font_size=12,
                spacing_after=24,
                # align="left",
            )
        )

    if data.govmap_results:
        blocks.append(
            TextBlock(
                text="צילום (GOVMAP)",
                font_size=12,
                spacing_after=24,
                # align="left",
            )
        )
        blocks.append(
            ImageBlock(
                path=Path(data.govmap_results),
                max_height_inches=2,
            )
        )
    if data.googlemap_result:
        blocks.append(
            TextBlock(
                text="צילום אויר (GOVMAP)",
                font_size=12,
                spacing_after=24,
                # align="left",
            )
        )
        blocks.append(
            ImageBlock(
                path=Path(data.googlemap_result),
                max_height_inches=2,
            )
        )

    blocks.append(
        TextBlock(
            text="5. תאור הנכס וסביבתו",
            underline=True,
            bold=True,
            font_size=12,
            spacing_after=24,
            # align="left"
        )
    )

    if data.environmental_description:
        is_err, clean = _extract_error_text(data.environmental_description)
        if is_err:
            blocks.append(
                TextBlock(text=clean, variant="error", font_size=12, spacing_after=24)
            )
        else:
            # שליחה לקלוד לעיצוב
            formatted_env = await format_text_with_claude(
                text=clean,
                context="תאור סביבת הנכס",
            )
            # פירוק לבלוקים
            env_blocks = parse_formatted_text(formatted_env)
            blocks.extend(env_blocks)

    inside_images = saved_files.get("inside", [])

    # ✅ תאור הנכס - עם קלוד!
    if data.apartment_description_text:
        is_err, clean = _extract_error_text(data.apartment_description_text)
        if is_err:
            blocks.append(
                TextBlock(text=clean, variant="error", font_size=12, spacing_after=24)
            )
        else:
            formatted_apt = await format_text_with_claude(
                text=clean,
                context="תאור פנים הנכס",
            )
            apt_blocks = parse_formatted_text(formatted_apt)
            blocks.extend(apt_blocks)

        blocks.append(
            TextBlock(
                text="תמונות הנכס",
                font_size=12,
                underline=True,
                # align="left"
            )
        )

        # ארגון תמונות פנימיות בטבלה של 2 עמודות
        if inside_images:
            blocks.append(
                ImageGroupBlock(
                    image_paths=[Path(img) for img in inside_images],
                    max_height_inches=2.5,  # גודל קטן יותר
                    bordered=True,
                )
            )

    # תשריט בית משותף – תמונה בלבד (ללא סריקה)
    if saved_files.get("building_plan"):
        blocks.append(
            TextBlock(
                text="תשריט בית משותף",
                bold=True,
                font_size=12,
                spacing_after=12,
            )
        )
        blocks.append(
            ImageBlock(
                path=Path(saved_files["building_plan"]),
                max_height_inches=4,
                bordered=True,
            )
        )

    # מסמכים משפטיים – ברירת מחדל: אופציונלי (אם אין תוכן, לא מציגים כותרת בכלל)
    # חריג: "נתוני טאבו" הוא חובה, ולכן מציגים שגיאה אם חסר.
    legal_docs = getattr(data, "legal_documents", None) or {}
    for heading in LEGAL_DOCUMENTS_ORDER:
        text = legal_docs.get(heading)
        is_missing = (not text) or (isinstance(text, str) and not text.strip())

        if is_missing:
            if heading == "נתוני טאבו":
                blocks.append(
                    TextBlock(
                        text=heading,
                        bold=True,
                        font_size=12,
                        spacing_after=12,
                    )
                )
                blocks.append(
                    TextBlock(
                        text=DEFAULT_SESSION_ERROR_MESSAGE,
                        variant="error",
                        font_size=12,
                        spacing_after=24,
                    )
                )
            continue

        is_err, text_str = _extract_error_text(text)
        blocks.append(
            TextBlock(
                text=heading,
                bold=True,
                font_size=12,
                spacing_after=12,
            )
        )
        if is_err:
            blocks.append(
                TextBlock(text=text_str, variant="error", font_size=12, spacing_after=24)
            )
        else:
            if heading in ("הסכם מכר", "הסכם שכירות"):
                formatted = await summarize_contract_text(text=text_str, contract_type=heading)
            else:
                formatted = await format_text_with_claude(text=text_str, context=heading)
            blocks.extend(parse_formatted_text(formatted))

    # תקנון בתים משותפים – מופיע רק כשיש טקסט תקנון רלוונטי
    if getattr(data, "bylaws_text", None) and (data.bylaws_text or "").strip():
        blocks.append(
            TextBlock(
                text="תקנון בתים משותפים",
                bold=True,
                font_size=12,
                spacing_after=12,
                # align="left",
            )
        )
        is_err, bylaws_str = _extract_error_text((data.bylaws_text or "").strip())
        # כאן אנו מציגים את התקנון כפי שסוכם כבר בצורה תמציתית,
        # ללא עיבוד נוסף שמסבך את המבנה.
        blocks.append(
            TextBlock(
                text=bylaws_str,
                font_size=12,
                spacing_after=24,
                # align="left",
                variant="error" if is_err else None,
            )
        )

    # ✅ טקסט מקבצי תב"ע שהורדו מהרשת
    if data.plans:
        blocks.append(
            ImageBlock(
                path=Path(data.plans),
                bordered=False,
                max_height_inches=4,  # מגביל גובה
            )
        )
    if data.rights:
        blocks.append(
            ImageBlock(
                path=Path(data.rights),
                bordered=False,
                max_height_inches=4,  # מגביל גובה
            )
        )

    # 6. המצב התכנוני – סעיף אופציונלי: מציגים רק אם יש טבלת תב״ע/זכויות
    has_plans_table = getattr(data, "PLANS_TBL", None) is not None
    has_rights_table = bool(getattr(data, "planning_rights_table", None))

    if has_plans_table or has_rights_table:
        # כותרת ראשית לסעיף
        blocks.append(
            TextBlock(
                text="6. המצב התכנוני",
                underline=True,
                bold=True,
                font_size=12,
                spacing_after=12,
                # align="left"
            )
        )

        # משפט פתיחה לפני טבלת התב"ע
        blocks.append(
            TextBlock(
                text="מידע בדבר תכניות מקומיות: בהתאם למידע תכנוני מאתר הוועדה המקומית, על הנכס חלות בין היתר התכניות הבאות:",
                font_size=12,
                spacing_after=12,
                # align="left"
            )
        )

        # טבלת תכניות תב"ע – טבלה נפרדת עם 3 עמודות בלבד
        if has_plans_table:
            print(data.PLANS_TBL)
            raw_headers = data.PLANS_TBL.get("headers", [])
            raw_rows = data.PLANS_TBL.get("rows", [])

            if not raw_rows:
                blocks.append(
                    TextBlock(
                        text=DEFAULT_SESSION_ERROR_MESSAGE,
                        variant="error",
                        font_size=12,
                        spacing_after=24,
                    )
                )
            else:

                # איתור אינדקסים רלוונטיים לפי שם עמודה
                def find_index(keyword: str) -> int:
                    for i, h in enumerate(raw_headers):
                        h_str = str(h)
                        if all(k in h_str for k in keyword.split()):
                            return i
                    return -1

                idx_plan_num = find_index("מספר תכנית")
                idx_plan_purpose = find_index("מהות")
                idx_plan_date = find_index("תאריך")

                # אם לא נמצא עמודת "מספר תכנית" במפורש – נשתמש כברירת מחדל בעמודה הראשונה ("תוכנית")
                if idx_plan_num == -1 and raw_headers:
                    idx_plan_num = 0

                filtered_rows = []
                for row in raw_rows:
                    # מספר/שם תכנית
                    num_val = (
                        row[idx_plan_num]
                        if 0 <= idx_plan_num < len(row)
                        else (row[0] if row else "")
                    )
                    # מהות תכנית
                    purpose_val = (
                        row[idx_plan_purpose]
                        if 0 <= idx_plan_purpose < len(row)
                        else ""
                    )
                    # תאריך – אם אינדקס "תאריך" מחוץ לטווח אבל יש עמודה אחרונה, נניח שהיא התאריך
                    if 0 <= idx_plan_date < len(row):
                        date_val = row[idx_plan_date]
                    elif row:
                        date_val = row[-1]
                    else:
                        date_val = ""

                    filtered_rows.append(
                        [str(num_val), str(purpose_val), str(date_val)]
                    )

                # כותרת לטבלת תכניות התב"ע
                blocks.append(
                    TextBlock(
                        text='תכניות בניין עיר (תב"ע)',
                        underline=True,
                        bold=True,
                        font_size=12,
                        spacing_after=12,
                        # align="left"
                    )
                )

                blocks.append(
                    TableBlock(
                        headers=["מספר תכנית", "מהות תכנית", "תאריך"],
                        rows=filtered_rows,
                        column_widths=[2.5, 3.0, 2.0],
                    )
                )

        # טבלת זכויות הבניה – רק אם קיימת טבלה
        if has_rights_table:
            print(data.planning_rights_table)
            # כותרת לפני טבלת זכויות הבניה
            blocks.append(
                TextBlock(
                    text="זכויות בניה שחלות על הנכס:",
                    underline=True,
                    bold=True,
                    font_size=12,
                    spacing_after=12,
                    # align="left"
                )
            )

            # חילוץ headers ו-rows מה-dictionary שחזר מגמיני
            raw_headers = data.planning_rights_table.get(
                "headers", ["פרמטר", "ערך", "תכנית מקור", "הערות"]
            )
            raw_rows = data.planning_rights_table.get("rows", [])

            if not raw_rows:
                blocks.append(
                    TextBlock(
                        text=DEFAULT_SESSION_ERROR_MESSAGE,
                        variant="error",
                        font_size=12,
                        spacing_after=24,
                    )
                )
            else:
                # נרמל את השורות כך שיתאימו לאורך הרשימה של הכותרות
                headers = [str(h) for h in raw_headers]
                col_count = (
                    len(headers) if headers else max((len(r) for r in raw_rows), default=0)
                )

                normalized_rows: list[list[str]] = []
                for row in raw_rows or []:
                    row_list = list(row)
                    if len(row_list) < col_count:
                        row_list.extend([""] * (col_count - len(row_list)))
                    elif len(row_list) > col_count:
                        row_list = row_list[:col_count]
                    normalized_rows.append(
                        [str(c) if c is not None else "" for c in row_list]
                    )

                blocks.append(
                    TableBlock(
                        headers=headers,
                        rows=normalized_rows,
                        column_widths=None,  # התאמה אוטומטית לרוחב העמודות לפי מספר הכותרות
                    )
                )

    # עסקאות דומות
    if getattr(data, "comparable_sales_table", None) or getattr(data, "comparable_sales_image", None):
        blocks.append(
            TextBlock(
                text="עסקאות דומות",
                underline=True,
                bold=True,
                font_size=12,
                spacing_after=12,
                # align="left"
            )
        )
        if getattr(data, "comparable_sales_image", None):
            blocks.append(
                ImageBlock(
                    path=Path(data.comparable_sales_image),
                    bordered=False,
                    max_height_inches=4,
                )
            )
        comparable = data.comparable_sales_table or {}
        comp_headers = comparable.get("headers", [])
        comp_rows = comparable.get("rows", [])

        if comp_headers and comp_rows:
            blocks.append(
                TableBlock(
                    headers=comp_headers,
                    rows=comp_rows,
                    column_widths=None,
                )
            )
        else:
            blocks.append(
                TextBlock(
                    text=DEFAULT_SESSION_ERROR_MESSAGE,
                    variant="error",
                    font_size=12,
                    spacing_after=24,
                )
            )

    if data.taba_documents_text:
        blocks.append(
            TextBlock(
                text="מידע תכנוני",
                bold=True,
                underline=True,
                font_size=12,
                spacing_after=12,
            )
        )

    # זיהום קרקע
    blocks.append(
        TextBlock(
            text="9. מידע בדבר זיהום קרקע",
            underline=True,
            bold=True,
            font_size=12,
            spacing_after=12,
            # align="left"
        )
    )

    if getattr(data, "soil_pollution_screenshot", None):
        # יש צילום מסך – נמצא זיהום
        blocks.append(
            TextBlock(
                text='על פי בדיקה במערכת Govmap בשכבת "קרקעות מזוהמות" נמצא זיהום קרקע בסביבת הנכס. להלן צילום מסך מתוצאות הבדיקה:',
                font_size=12,
                spacing_after=12,
                # align="left"
            )
        )
        blocks.append(
            ImageBlock(
                path=Path(data.soil_pollution_screenshot),
                max_height_inches=3.5,
                bordered=True,
            )
        )
    else:
        # אין צילום מסך – אין זיהום
        blocks.append(
            TextBlock(
                text='על פי בדיקה במערכת Govmap בשכבת "קרקעות מזוהמות" לא נמצא זיהום קרקע בסביבת הנכס.',
                font_size=12,
                spacing_after=24,
                # align="left"
            )
        )

    # 10. שומות קודמות שנערכו בנכס
    blocks.append(
        TextBlock(
            text="10. שומות קודמות שנערכו בנכס",
            underline=True,
            bold=True,
            font_size=12,
            spacing_after=12,
            # align="left",
        )
    )

    # תוכן הסעיף:
    # עדיפות 1 – תקציר מגמיני לקובץ שומה קודמת (אם הועלה ונקלט)
    # עדיפות 2 – טקסט חופשי מהמשתמש במטא (previous_appraisals_note)
    # אחרת – ניסוח ברירת מחדל
    previous_text_parts: list[str] = []
    if getattr(data, "previous_appraisals_summary", None):
        previous_text_parts.append(data.previous_appraisals_summary.strip())
    if getattr(meta, "previous_appraisals_note", None):
        note = (meta.previous_appraisals_note or "").strip()
        if note:
            previous_text_parts.append(note)

    if previous_text_parts:
        blocks.append(
            TextBlock(
                text="\n\n".join(previous_text_parts),
                font_size=12,
                spacing_after=24,
                # align="left",
            )
        )
    else:
        blocks.append(
            TextBlock(
                text="לא הוצגו בפנינו שומות קודמות שנערכו בנכס.",
                font_size=12,
                spacing_after=24,
                # align="left",
            )
        )

    # מחזירים DocumentRequest מלא
    return DocumentRequest(title=None, blocks=blocks)

