from __future__ import annotations

from collections.abc import Mapping

from report_steps.parse_tabu_pdf import (
    decide_lease_section_for_report,
    extract_document_summary_from_pdf,
)


ERROR_TEXT_PREFIX = "__QA_ERROR__:"
DEFAULT_SESSION_ERROR_MESSAGE = "אופס, לא הצלחתי למצוא את המידע המבוקש"


def _as_error_text(message: str = DEFAULT_SESSION_ERROR_MESSAGE) -> str:
    return f"{ERROR_TEXT_PREFIX}{message}"


# מיפוי: key ב-saved_files -> label שיופיע ב-dict
LEGAL_DOCUMENTS_MAP: list[tuple[str, str]] = [
    ("rights_confirmation", "אישור זכויות"),
    ("lease_document", "הסכם חכירה"),
    ("civil_admin", "מינהל אזרחי"),
    ("mortgage_confirmation", "אישור חברה משכנת"),
    ("sale_agreement", "הסכם מכר"),
    ("rental_agreement", "הסכם שכירות"),
    ("arnona_form", "טופס ארנונה"),
]


async def extract_legal_documents(
    *,
    saved_files: Mapping[str, object],
    include_tabu_text: str | None = None,
) -> dict[str, str]:
    """
    מחזיר dict אחיד של מסמכים משפטיים:
    { "אישור זכויות": "...", "הסכם מכר": "...", ... }
    """
    out: dict[str, str] = {}

    if include_tabu_text is not None:
        out["נתוני טאבו"] = include_tabu_text

    # 1) סריקה "רגילה" למסמכים
    for file_key, label in LEGAL_DOCUMENTS_MAP:
        path = saved_files.get(file_key)
        if not path:
            continue
        try:
            summary = await extract_document_summary_from_pdf(path, label)
            out[label] = summary.strip() if summary and summary.strip() else _as_error_text()
        except Exception:
            out[label] = _as_error_text()

    # 2) התאמה ייחודית: הסכם חכירה תלוי באישור זכויות
    if out.get("אישור זכויות") and out.get("הסכם חכירה"):
        try:
            decided = await decide_lease_section_for_report(out["הסכם חכירה"])
            if decided:
                out["הסכם חכירה"] = decided
            else:
                # אם הוחלט לא להציג – נסיר לגמרי מהתוצרים כדי ש-document_builder לא יציג סעיף
                out.pop("הסכם חכירה", None)
        except Exception:
            out["הסכם חכירה"] = _as_error_text()

    return out

