import re

from integrations.gemini_client import ask_gemini_with_search


async def generate_location_description(address) -> tuple[str, str]:
    """
    יוצר תיאור אמיתי על בסיס כתובת, כולל חיפוש בגוגל דרך Gemini.
    """
    print(f"Generating description for: {address.street} {address.house_number}, {address.city}")

    prompt = f"""
    הפק תיאור מקצועי לדוח נדל״ן על בסיס חיפוש מידע אמיתי ברשת בלבד (Google Search).
    אני רוצה שתביא לי את המידע כשהוא בנקודות לפי נושאים, כל נקודה בשורה חדשה עם כוכבית בהתחלה
    חלק 1 – תיאור עיר:
    כתוב 5–6 שורות המתארות את מאפייני העיר בה נמצא הנכס:
    אזורים מרכזיים, תחבורה, אוכלוסייה, תשתיות, נקודות עניין.

    חלק 2 – תיאור סביבת הנכס:
    כתוב 5–6 שורות המתארות את הרחוב, כולל את צורתו וקוי המתאר הגאוגרפיים שלו,  שימושי קרקע,
    שירותים עירוניים, תחבורה זמינה, בנייה מקומית ונקודות עניין.
    וכן האם התשתיות המקומיות תקינות 

    הכתובת: {address.street} {address.house_number}, {address.city}

    הפרד בבירור בין:
    "תיאור עיר:"
    "תיאור סביבת הנכס:"
    """

    try:
        print("[generate_location_description] Calling ask_gemini_with_search...")
        full_text = await ask_gemini_with_search(
            prompt=prompt,
            model_name="gemini-2.5-flash",
            use_search=True,
        )

        if not full_text or not isinstance(full_text, str) or full_text.strip() == "":
            return "", ""
        if "Error communicating with Gemini" in full_text:
            return "", ""

    except Exception:
        return "", ""

    city_desc = ""
    area_desc = ""

    if "תיאור עיר:" in full_text:
        try:
            parts = full_text.split("תיאור עיר:")[1].split("תיאור סביבת הנכס:")
            city_desc = parts[0].strip()
            if len(parts) > 1:
                area_desc = parts[1].strip()
        except IndexError:
            pass
    elif "תיאור סביבת הנכס:" in full_text:
        try:
            area_desc = full_text.split("תיאור סביבת הנכס:")[1].strip()
        except IndexError:
            pass

    if not city_desc and not area_desc:
        if full_text and full_text.strip():
            if "חלק 1" in full_text or "חלק 2" in full_text:
                parts = re.split(r"חלק\s+\d+[–-]?\s*", full_text, flags=re.IGNORECASE)
                if len(parts) > 1:
                    city_desc = parts[1].strip() if len(parts) > 1 else ""
                    area_desc = parts[2].strip() if len(parts) > 2 else ""
                else:
                    city_desc = full_text.strip()
            else:
                city_desc = full_text.strip()

    return city_desc, area_desc

