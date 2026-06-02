import uuid
from pathlib import Path
from datetime import datetime
from document.word_renderer import render_word_document
from report_steps.report_file_saver import _save_files
from utils.cleanup import schedule_cleanup
from utils.temp_paths import temp_dir
from document.builder import build_document
from report_steps.generate_location_description import generate_location_description
from report_steps.generate_purpose_statement import generate_purpose_statement
from report_steps.parse_tabu_pdf import (
    extract_full_data_from_pdf,
    extract_rights_confirmation_from_pdf,
    extract_lease_document_from_pdf,
    decide_lease_section_for_report,
    extract_bylaws_changes_from_pdf,
    TAKANON_STANDARD,
    TAKANON_COMPLEX,
    extract_previous_appraisal_summary_from_pdf,
)
from models.report_request import ParcelInfo, Data
from report_steps.legal_status_service import extract_legal_documents
from report_steps.describe_apartment_interior import describe_apartment_interior
from report_steps.download_taba import fetch_taba_tables
from report_steps.govmap_screenshot import capture_govmap
from report_steps.visit_text_service import generate_property_visit_text
from report_steps.pollution import check_soil_contamination
from report_steps.comparable_sales import run_nadlan_search
from report_steps.generic_image_to_table import get_table_from_image

ERROR_TEXT_PREFIX = "__QA_ERROR__:"
DEFAULT_SESSION_ERROR_MESSAGE = "אופס, לא הצלחתי למצוא את המידע המבוקש"


def _as_error_text(message: str = DEFAULT_SESSION_ERROR_MESSAGE) -> str:
    # נשמר באותו שדה טקסט, עם prefix פנימי לזיהוי בדוקומנט בילדר.
    return f"{ERROR_TEXT_PREFIX}{message}"


async def create_report_logic(
    background_tasks,
    address,
    meta,
    visit,
    files,
    identification_method: str | None = None,
):
    # 1️⃣ יצירת סביבת עבודה
    report_id = str(uuid.uuid4())
    workdir = temp_dir("reports", f"report_{report_id}")
    input_dir = workdir / "input"
    output_dir = workdir / "output"

    input_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(exist_ok=True)

    # 2️⃣ שמירת קבצים
    saved_files = _save_files(files, input_dir)
    data = Data()

    print("start work")

    visit_text = await generate_property_visit_text(visit)
    data.visit_text = visit_text


    result = ""
    if saved_files["inside"] and len(saved_files["inside"]) > 0:
        try:
            data.apartment_description_text = await describe_apartment_interior(
                image_paths=saved_files["inside"],
                text_segment=meta.apartment_description_text_base
            )
            print(f"Description generated successfully, length: {len(result)} characters")
        except Exception as e:
            print(f"Error generating description: {str(e)}")
            data.apartment_description_text = _as_error_text()
    else:
        print("No inside images provided, skipping description")
        data.apartment_description_text = "לא סופקו תמונות פנים הדירה."


    tabu_result = None
    if saved_files.get("tabu"):
        try:
            tabu_result = await extract_full_data_from_pdf(saved_files["tabu"])
        except Exception as e:
            print(f"[report_service] שגיאה בחילוץ טאבו: {e}")
            tabu_result = None

    if tabu_result:
        # כאן אנחנו מוודאים שקיבלנו טאפל/רשימה עם 2 ערכים
        data.tabu_data, data.tabuJSON = tabu_result
    else:
        # מה קורה אם אין קובץ טאבו או שהחילוץ נכשל
        if saved_files.get("tabu"):
            print("[report_service] Warning: tabu extraction failed")
            data.tabu_data = _as_error_text()
        else:
            # נסח טאבו הוא חובה – גם אם לא הועלה, נסמן שגיאה כדי שיופיע בדוח
            data.tabu_data = _as_error_text()
        data.tabuJSON = {}

    # אוביקט מצב משפטי אחיד (מסמכים + טאבו) – יחליף בהדרגה שדות מפוצלים ב-Data
    data.legal_documents = await extract_legal_documents(
        saved_files=saved_files,
        include_tabu_text=data.tabu_data,
    )

    # סריקת אישור זכויות מרמ"י (אותה שיטה כמו טאבו)
    if saved_files.get("rights_confirmation"):
        try:
            rights_summary = await extract_rights_confirmation_from_pdf(saved_files["rights_confirmation"])
            data.rights_confirmation_data = rights_summary.strip() if rights_summary and rights_summary.strip() else _as_error_text()
            if rights_summary:
                print("[report_service] אישור זכויות מרמ\"י סורק בהצלחה")
        except Exception as e:
            print(f"[report_service] שגיאה בסריקת אישור זכויות: {e}")
            data.rights_confirmation_data = _as_error_text()
    else:
        data.rights_confirmation_data = None

    # סריקת מסמך חכירה (אותה שיטה כמו אישור זכויות)
    if saved_files.get("lease_document"):
        try:
            lease_summary = await extract_lease_document_from_pdf(saved_files["lease_document"])
            data.lease_document_data = lease_summary.strip() if lease_summary and lease_summary.strip() else _as_error_text()
            if lease_summary:
                print("[report_service] מסמך חכירה סורק בהצלחה")
        except Exception as e:
            print(f"[report_service] שגיאה בסריקת מסמך חכירה: {e}")
            data.lease_document_data = _as_error_text()
    else:
        data.lease_document_data = None

    # הסכם חכירה: נכלל בדוח רק אם גמיני קבע שיש שינויים משמעותיים ביחס לאישור הזכויות
    if data.rights_confirmation_data and data.lease_document_data:
        try:
            data.lease_document_data = await decide_lease_section_for_report(
                data.lease_document_data,
            )
            if data.lease_document_data:
                print("[report_service] הסכם חכירה ייכלל בדוח (שינויים משמעותיים)")
            else:
                print("[report_service] הסכם חכירה לא ייכלל בדוח (ללא שינויים משמעותיים)")
        except Exception as e:
            print(f"[report_service] שגיאה בהחלטה על סעיף הסכם חכירה: {e}")
            data.lease_document_data = _as_error_text()

    # תאימות לאחור: מילוי השדות הישנים מתוך ה-dict האחיד (לשימושים קיימים ב-document_builder)
    data.rights_confirmation_data = data.legal_documents.get("אישור זכויות", data.rights_confirmation_data)
    data.lease_document_data = data.legal_documents.get("הסכם חכירה", data.lease_document_data)
    data.civil_admin_data = data.legal_documents.get("מינהל אזרחי", data.civil_admin_data)
    data.mortgage_confirmation_data = data.legal_documents.get("אישור חברה משכנת", data.mortgage_confirmation_data)
    data.sale_agreement_data = data.legal_documents.get("הסכם מכר", data.sale_agreement_data)
    data.rental_agreement_data = data.legal_documents.get("הסכם שכירות", data.rental_agreement_data)
    data.arnona_form_data = data.legal_documents.get("טופס ארנונה", data.arnona_form_data)

    # שומות קודמות – אם המשתמש העלה קובץ שומה קודמת, נסרוק אותה ונפיק תקציר טכני קצר
    data.previous_appraisals_summary = None
    if saved_files.get("previous_appraisals"):
        try:
            prev_summary = await extract_previous_appraisal_summary_from_pdf(
                saved_files["previous_appraisals"]
            )
            data.previous_appraisals_summary = prev_summary or None
            if prev_summary:
                print("[report_service] שומה קודמת סורקה בהצלחה")
        except Exception as e:
            print(f"[report_service] שגיאה בסריקת שומה קודמת: {e}")
            data.previous_appraisals_summary = _as_error_text()

    # תקנון בתים משותפים – מהטאבו (takanon):
    # מצוי  -> לא נכלל סעיף בדוח
    # מוסכם -> נסרוק קובץ תקנון (אם קיים) ונסכם אותו בתמציתיות
    takanon = (data.tabuJSON or {}).get("takanon") or ""
    if isinstance(takanon, str):
        takanon = takanon.strip()
    if takanon == TAKANON_STANDARD:
        # תקנון מצוי – לא מוסיפים כלל סעיף תקנון לדוח
        data.bylaws_text = None
        print("[report_service] תקנון: מצוי – מדלג על סעיף התקנון בדוח")
    elif takanon == TAKANON_COMPLEX:
        if saved_files.get("bylaws"):
            try:
                # תקנון מורכב + יש קובץ: מחלץ פסקה קצרה ותמציתית בלבד על התקנון הנוכחי
                data.bylaws_text = await extract_bylaws_changes_from_pdf(saved_files["bylaws"])
                if data.bylaws_text:
                    print("[report_service] תקנון: סרוק (מוסכם/מורכב) – נוספה פסקה תמציתית")
                else:
                    print("[report_service] תקנון: סרוק (מוסכם/מורכב) – לא התקבלה פסקה, מדלג על הסעיף")
            except Exception as e:
                print(f"[report_service] שגיאה בסריקת תקנון: {e}")
                data.bylaws_text = None
        else:
            # אין קובץ תקנון – לא מוסיפים סעיף לדוח
            data.bylaws_text = None
            print("[report_service] תקנון: מוסכם/מורכב אך ללא קובץ – מדלג על סעיף התקנון בדוח")
    else:
        data.bylaws_text = None

    
    parcel = ParcelInfo(
        gush=data.tabuJSON.get("gush") or "",
        helka=data.tabuJSON.get("helka") or "",
        tat_helka=data.tabuJSON.get("tat_helka") or "",
    )

    try:
        print(f"[report_service] מפעיל govmap_screenshot: gush={parcel.gush}, helka={parcel.helka}, base_path={input_dir}")
        address_str = f"{address.street} {address.house_number}, {address.city}"
        govmap_shot_1, govmap_shot_2 = await capture_govmap(
            address=address_str,
            base_path=str(workdir),
        )
        # תמונה ראשונה: צילום מפה. תמונה שנייה: צילום אויר
        data.govmap_results = govmap_shot_1
        data.googlemap_result = govmap_shot_2
        print(f"[report_service] govmap_screenshot completed: צילום={govmap_shot_1}, צילום אויר={govmap_shot_2}")
    except Exception as e:
        print(f"[report_service] שגיאה בהרצת govmap_screenshot: {str(e)}")
        data.govmap_results = None
        data.googlemap_result = None
    # בדיקת זיהום קרקע (Govmap - Pollution)
    try:
        pollution_address_str = f"{address.street} {address.house_number}, {address.city}"
        print(f"[report_service] מפעיל check_soil_contamination עבור הכתובת: {pollution_address_str}")
        soil_pollution_screenshot = await check_soil_contamination(
            pollution_address_str,
            base_path=workdir,
        )
        data.soil_pollution_screenshot = soil_pollution_screenshot
        if soil_pollution_screenshot:
            print(f"[report_service] נמצא זיהום קרקע, צילום מסך ב: {soil_pollution_screenshot}")
        else:
            print("[report_service] לא נמצא זיהום קרקע לפי govmap")
    except Exception as e:
        print(f"[report_service] שגיאה בבדיקת זיהום קרקע: {e}")
        data.soil_pollution_screenshot = None

    # עסקאות דומות מאתר נדל\"ן + פענוח טבלה עם Gemini
    try:
        nadlan_address = f"{address.street} , {address.city}"
        print(f"[report_service] מפעיל run_nadlan_search עבור הכתובת: {nadlan_address}")
        table_screenshot_path = await run_nadlan_search(
            address=nadlan_address,
            property_type="דירה",
            base_path=str(workdir),
        )
        print("succseed")
        if table_screenshot_path:
            data.comparable_sales_image = table_screenshot_path
            print(f"[report_service] צילום טבלת עסקאות דומות נשמר ב: {table_screenshot_path}")

            EXTRA_COMPARABLE_SALES_INSTRUCTIONS = """
התייחס לטבלה של עסקאות דומות/דירות דומות מאתר נדל\"ן.
וודא שכל שורה מייצגת עסקה אחת, עם עמודות ברורות עבור תאריך עסקה, מחיר, שטח, קומה, כתובת/אזור ופרטים רלוונטיים נוספים אם קיימים.
"""
            comparable_table = await get_table_from_image(
                table_screenshot_path,
                extra_instructions=EXTRA_COMPARABLE_SALES_INSTRUCTIONS,
            )
            if comparable_table:
                data.comparable_sales_table = comparable_table
                rows_count = len(comparable_table.get("rows", [])) if isinstance(comparable_table, dict) else 0
                print(f"[report_service] טבלת עסקאות דומות זוהתה עם {rows_count} שורות")
            else:
                print("[report_service] לא התקבלה טבלת עסקאות דומות מגמיני")
        else:
            print("[report_service] run_nadlan_search לא החזיר נתיב לטבלת עסקאות")
    except Exception as e:
        print(f"[report_service] שגיאה בהרצת עסקאות דומות: {e}")

    # תמונות מפה מתקבלות מ־capture_govmap (צילום + צילום אויר) – לא קוראים ל־Google Maps

    # תב״ע: לוגיקה מרוכזת בקובץ אחד (download_taba.py) – כאן רק מקבלים תוצאה.
    try:
        taba_res = await fetch_taba_tables(
            city=address.city,
            gush=parcel.gush,
            helka=parcel.helka,
            base_path=workdir,
            output_dir=workdir / "taba_documents",
        )
        if taba_res.plans_image_path:
            data.plans = taba_res.plans_image_path
        if taba_res.rights_image_path:
            data.rights = taba_res.rights_image_path

        if taba_res.plans_table:
            data.PLANS_TBL = taba_res.plans_table
        if taba_res.rights_table:
            data.planning_rights_table = taba_res.rights_table
    except Exception as e:
        print(f"[report_service] שגיאה בהבאת טבלאות תב״ע: {e}")
        
    # יצירת נוסח מטרת השומה וזהות מזמין השומה
    data.purpose_statement = ""
    if meta.customer and meta.purpose:
        try:
            data.purpose_statement = await generate_purpose_statement(
                customer=meta.customer,
                purpose=meta.purpose
            )
            print(f"[report_service] Purpose statement generated successfully, length: {len(data.purpose_statement)} characters")
        except Exception as e:
            print(f"[report_service] Error generating purpose statement: {str(e)}")
            data.purpose_statement = f"השומה הוזמנה על ידי {meta.customer}, לצורך הערכת שווי הנכס למטרת {meta.purpose}.\n\nהשומה נועדה למטרה זו בלבד, כל שימוש בשומה זו למטרה אחרת מכל סוג אינו באחריות הח\"מ."
    
    city_desc, area_desc = await generate_location_description(address)

    parts = []
    if city_desc and city_desc.strip():
        parts.append(city_desc.strip())
    if area_desc and area_desc.strip():
        parts.append(area_desc.strip())
    
    data.environmental_description = "\n".join(parts) if parts else ""
    document = await build_document(
        parcel=parcel,
        address=address,
        meta=meta,
        saved_files=saved_files,
        data=data,
    )
    docx_path = output_dir / f"report_{report_id}.docx"

   
    print(f"[report_service] יצירת Word: {docx_path}")
    try:
        render_word_document(document, docx_path)
    except Exception as e:
        print(f"[report_service] שגיאה ביצירת קובץ Word: {e}")
        raise
    
    # וידוא שהקובץ נוצר בהצלחה
    if not docx_path.exists():
        raise FileNotFoundError(f"הקובץ לא נוצר: {docx_path}")
    
    # המרה לנתיב מוחלט
    docx_path_absolute = docx_path.resolve()
    try:
                visit_text = await generate_property_visit_text(visit)
                data.visit_text = visit_text
    except Exception as e:
                print(f"[report_service] שגיאה בחילוץ טקסט ביקור: {e}")
                data.visit_text = _as_error_text()
    print(f"[report_service] קובץ נוצר בהצלחה: {docx_path_absolute} (גודל: {docx_path_absolute.stat().st_size} bytes)")

    # 6️⃣ ניקוי אוטומטי
    schedule_cleanup(background_tasks, workdir)

    return {
        "path": docx_path_absolute,  # נתיב מוחלט
        "filename": docx_path.name,
        "media_type": (
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        ),
    }



