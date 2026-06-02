from integrations.gemini_client import ask_gemini_with_search


async def generate_purpose_statement(customer: str, purpose: str) -> str:
    """
    יוצר נוסח מקצועי בשפה של עורכי דין על מטרת השומה וזהות מזמין השומה.
    """
    print(
        f"[generate_purpose_statement] Generating purpose statement for customer: {customer}, purpose: {purpose}"
    )

    prompt = f"""כתוב נוסח מקצועי מאוד בשפה של עורכי דין על:

1. זהות מזמין השומה: {customer}
2. מטרת השומה: {purpose}
3. המשפט הבא: "השומה נועדה למטרה זו בלבד, כל שימוש בשומה זו למטרה אחרת מכל סוג אינו באחריות החתום מטה."

הנוסח צריך להיות:
- מקצועי ומדויק בשפה משפטית
- ברור וחד משמעי
- מתאים למסמך שומה מקצועי
- כולל את כל הפרטים הנדרשים
-באורך של 4-6 שורות
כתוב את הנוסח בפורמט רציף, ללא כותרות או רשימות."""

    try:
        result = await ask_gemini_with_search(
            prompt=prompt,
            model_name="gemini-2.5-flash",
            use_search=False,  # לא צריך חיפוש - זה טקסט משפטי סטנדרטי
        )

        if not result or not isinstance(result, str) or result.strip() == "":
            return _get_fallback_statement(customer, purpose)
        if "Error communicating with Gemini" in result:
            return _get_fallback_statement(customer, purpose)

        return result

    except Exception:
        return _get_fallback_statement(customer, purpose)


def _get_fallback_statement(customer: str, purpose: str) -> str:
    return f"""השומה הוזמנה על ידי {customer}, לצורך הערכת שווי הנכס למטרת {purpose}.

השומה נועדה למטרה זו בלבד, כל שימוש בשומה זו למטרה אחרת מכל סוג אינו באחריות הח"מ."""

