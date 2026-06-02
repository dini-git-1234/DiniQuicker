from models.report_request import PropertyVisit
from integrations.gemini_client import ask_gemini_with_search


async def generate_property_visit_text(visit: PropertyVisit) -> str:
    if not visit:
        return ""

    prompt = f"""
אתה שמאי מקרקעין מקצועי, ענייני ורציני.
בשפה פורמלית, עם היגיון רציף וללא חזרות מיותרות.
אני רוצה שהמשפט הראשון יהיה תאריך הביקור ועל ידי מי,
המשפט השני יהיה מי הציג את הנכס, 
והמשפט השלישי יהיה בבעלות מי הנכס.
אם המציג והבעלים הם אותו אחד- כלומר יש להם אותו שם תאחד את המשפט השני והשלישי.

פרטי הביקור:
- תאריך ביקור: {visit.visit_date or "לא צוין"}
- הביקור בוצע על ידי: {visit.visited_by or "לא צוין"}
- הנכס הוצג על ידי: {visit.presented_by or "לא צוין"}
- המחזיק בנכס: {visit.property_holder or "לא צוין"}

הניסוח צריך להתאים לדוח שמאי רשמי.
"""

    return await ask_gemini_with_search(
        prompt=prompt,
        use_search=False,  # אין צורך בחיפוש חיצוני
    )

