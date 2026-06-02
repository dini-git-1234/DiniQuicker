import os
import json
import asyncio
import mimetypes
import fitz  # PyMuPDF
from PIL import Image, ImageDraw, ImageColor
from typing import List, Optional
from integrations.gemini_client import ask_gemini_with_search

from utils.temp_paths import temp_dir
# הגדרת מפתח ה-API


# --- פונקציית העיבוד הגרפי ---
def process_graphics(pdf_path: str, ai_data: List[dict], output_folder: str = "output") -> List[str]:
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)
        
    doc = fitz.open(pdf_path)
    page = doc.load_page(0)
    
    # המרה לתמונה איכותית לצורך החיתוך
    zoom = 3 
    pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom))
    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
    w, h = img.size
    
    results = []
    
    for i, item in enumerate(ai_data):
        temp_img = img.copy()
        draw = ImageDraw.Draw(temp_img)
        
        # המרת קואורדינטות מנורמלות (0‑1000) לפיקסלים
        # הצורה המצופה מהמודל: [ymin, xmin, ymax, xmax]
        def to_p(box):
            ymin, xmin, ymax, xmax = box
            y_min_px = ymin * h / 1000.0
            x_min_px = xmin * w / 1000.0
            y_max_px = ymax * h / 1000.0
            x_max_px = xmax * w / 1000.0
            # נחזיר באותו פורמט לוגי, רק בפיקסלים
            return [y_min_px, x_min_px, y_max_px, x_max_px]
        
        # m = to_p(item['marker_box'])
        c = to_p(item['crop_box'])
        
        # ציור ריבוע צהוב על המיקום שסומן לדירה
        # draw.rectangle([m[1], m[0], m[3], m[2]], outline="yellow", width=10)
        
        # חיתוך ושמירה
        cropped = temp_img.crop((c[1], c[0], c[3], c[2]))
        file_path = os.path.join(output_folder, f"result_{item['type']}_{i}.png")
        cropped.save(file_path)
        results.append(file_path)
    
    doc.close()
    return results


async def identify_apartment(
    pdf_path: str,
    floor: str,
    apartment: str,
    attachments: Optional[str] = None,
    output_folder: str | None = None,
) -> List[str]:
    """
    מאתר דירה בתשריט, מסמן אותה ומחזיר נתיבי קבצי התמונות שנוצרו.

    :param pdf_path: מיקום קובץ ה‑PDF של התשריט.
    :param floor: מספר קומה (כטקסט, למשל "3").
    :param apartment: מספר דירה (כטקסט, למשל "26").
    :param attachments: תיאור ההצמדות (חניות, מחסנים וכו') במילים חופשיות, או None.
    :param output_folder: תיקיית היעד לשמירת התמונות החתוכות.
    :return: רשימת נתיבי קבצי PNG שנוצרו.
    """

    # 1. הפיכת ה-PDF לתמונה בזיכרון כדי ש-Gemini יוכל "לראות"
    doc = fitz.open(pdf_path)
    page = doc.load_page(0)
    pix = page.get_pixmap(matrix=fitz.Matrix(1, 1))  # רזולוציה רגילה ל-AI
    img_bytes = pix.tobytes("jpeg")
    doc.close()

    # 2. פנייה ל-Gemini עם פרמטרים של קומה, דירה והצמדות
    attachments_text = f" וההצמדות שלה: {attachments}" if attachments else " וההצמדות שלה (חניות, מחסנים וכו')."
    prompt = f"""
   אני רוצה שתסרוק את הצילום הבא, הוא קצת מבולגן אבל בכל אופן. תחפש את דירה מספר {apartment} בקומה {floor} 
   ותמצא באיזה צבע היא מוקפת. זה אמור להיות פוליגון כזה בצורה מוזרה. 
   חוץ מזה, אני רוצה לעשות צילום מסך בשביל כל הקומה שבה נמצאת הדירה. לכן אני צריכה שתחזיר לי את הקורדינטות של הפוליגון שבה נמצאת הדירה. 
   קרוב לאזור הזה אמור להיות כתוב המילה קומה {floor}.

    הנחיות קריטיות לקואורדינטות:
    - השתמש במערכת צירים מנורמלת של 0-1000.
    - ה-crop_box חייב להיות רחב מספיק כדי לראות את כל הקומה (לפחות 200-300 יחידות גובה/רוחב).

    החזר אך ורק מערך JSON תקין במבנה הבא, ללא מילים נוספות:
    [
    {{
        "type": "apartment",
        "description": "קומה {floor} דירה {apartment}",
        "crop_box": [ymin, xmin, ymax, xmax],
        "color":(צבע שהדירה מוקפת בו)
    }}
    ]

    אם לא מצאת את הקומה או הדירה בוודאות של 100%, החזר רשימה ריקה [].
    """
    print("מנתח תשריט...")
    # כתיבת התמונה לקובץ זמני ואז שליחתה דרך ה-wrappper הכללי
    tmp_dir = temp_dir("identify_apartment", ensure=True)
    img_path = os.path.join(tmp_dir, "identify_input.jpg")
    with open(img_path, "wb") as f:
        f.write(img_bytes)
    raw_json = await ask_gemini_with_search(prompt, images=[img_path])
    # הדפסה לצורך דיבוג – תוכל לראות בדיוק מה חזר מהמודל
    print("RAW JSON FROM GEMINI:")
    print(raw_json)

    try:
        ai_results = json.loads(raw_json)
        if not isinstance(ai_results, list):
            raise ValueError("Gemini did not return a JSON list.")
    except Exception as e:
        raise ValueError(f"Failed to parse Gemini JSON response: {e}\nRaw response: {raw_json}") from e

    # 3. יצירת התמונות החתוכות
    print(f"יוצר {len(ai_results)} תמונות...")
    if output_folder is None:
        output_folder = str(temp_dir("screenshots", "identify_apartment", ensure=True))

    final_files = process_graphics(pdf_path, ai_results, output_folder=output_folder)

    print("בוצע! הקבצים מוכנים:")
    for f in final_files:
        print(f"- {f}")

    return final_files


if __name__ == "__main__":
    """
    זימון לדוגמה להרצת הפונקציה ישירות מהקובץ.
    עדכן את pdf_path / floor / apartment / attachments לפי הצורך.
    """

    async def _demo():
        files = await identify_apartment(
            pdf_path="תשריט בית משותף (1).pdf",
            floor="שלישית",
            apartment="26",
            attachments="גג שמעל הדירה- באותו מיקום",
            output_folder="output_apartment_26",
        )
        print("קבצים שנוצרו:")
        for f in files:
            print(f"- {f}")

    asyncio.run(_demo())
