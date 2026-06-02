from typing import List

from models.report_request import TextBlock


def parse_formatted_text(formatted_text: str, default_align: str = "right") -> List[TextBlock]:
    """
    מפרק טקסט מעוצב (עם סימונים) לרשימת TextBlock

    Args:
        formatted_text: הטקסט המעוצב מקלוד
        default_align: יישור ברירת מחדל

    Returns:
        רשימת TextBlock מוכנה ל-document builder
    """
    if not formatted_text or not formatted_text.strip():
        return []

    blocks = []
    lines = formatted_text.strip().split("\n")

    current_bullets = []  # אוסף נקודות רצופות

    for line in lines:
        line = line.strip()

        if not line:
            # שורה ריקה - אם יש נקודות שנצברו, נוסיף אותן
            if current_bullets:
                blocks.append(
                    TextBlock(
                        text="\n".join(current_bullets),
                        use_bullets=True,
                        align=default_align,
                        font_size=12,
                        spacing_after=12,
                    )
                )
                current_bullets = []
            continue

        # זיהוי כותרת 1
        if line.startswith("<HEADING1>"):
            # סיום נקודות אם יש
            if current_bullets:
                blocks.append(
                    TextBlock(
                        text="\n".join(current_bullets),
                        use_bullets=True,
                        align=default_align,
                        font_size=12,
                        spacing_after=12,
                    )
                )
                current_bullets = []

            title = line.replace("<HEADING1>", "").replace("</HEADING1>", "").strip()
            title = _process_inline_formatting(title)
            blocks.append(
                TextBlock(
                    text=title,
                    bold=True,
                    underline=True,
                    font_size=12,
                    align="center",
                    spacing_after=24,
                )
            )

        # זיהוי כותרת 2
        elif line.startswith("<HEADING2>"):
            if current_bullets:
                blocks.append(
                    TextBlock(
                        text="\n".join(current_bullets),
                        use_bullets=True,
                        align=default_align,
                        font_size=12,
                        spacing_after=12,
                    )
                )
                current_bullets = []

            title = line.replace("<HEADING2>", "").replace("</HEADING2>", "").strip()
            title = _process_inline_formatting(title)
            blocks.append(
                TextBlock(
                    text=title,
                    bold=True,
                    underline=True,
                    font_size=12,
                    align=default_align,
                    spacing_after=24,
                )
            )

        # זיהוי כותרת 3
        elif line.startswith("<HEADING3>"):
            if current_bullets:
                blocks.append(
                    TextBlock(
                        text="\n".join(current_bullets),
                        use_bullets=True,
                        align=default_align,
                        font_size=12,
                        spacing_after=12,
                    )
                )
                current_bullets = []

            title = line.replace("<HEADING3>", "").replace("</HEADING3>", "").strip()
            title = _process_inline_formatting(title)
            blocks.append(
                TextBlock(
                    text=title,
                    bold=True,
                    underline=True,
                    font_size=12,
                    align=default_align,
                    spacing_after=12,
                )
            )

        # זיהוי נקודה
        elif line.startswith("<BULLET>"):
            bullet_text = line.replace("<BULLET>", "").strip()
            bullet_text = _process_inline_formatting(bullet_text)
            current_bullets.append(bullet_text)

        # זיהוי <BR> - ירידת שורה
        elif line == "<BR>":
            if current_bullets:
                blocks.append(
                    TextBlock(
                        text="\n".join(current_bullets),
                        use_bullets=True,
                        align=default_align,
                        font_size=12,
                        spacing_after=12,
                    )
                )
                current_bullets = []
            # הוספת שורה ריקה
            blocks.append(TextBlock(text="", spacing_after=12))

        # טקסט רגיל (ללא סימון)
        else:
            if current_bullets:
                blocks.append(
                    TextBlock(
                        text="\n".join(current_bullets),
                        use_bullets=True,
                        align=default_align,
                        font_size=12,
                        spacing_after=12,
                    )
                )
                current_bullets = []

            text = _process_inline_formatting(line)
            blocks.append(
                TextBlock(
                    text=text,
                    align=default_align,
                    font_size=12,
                    spacing_after=12,
                )
            )

    # אם נשארו נקודות בסוף
    if current_bullets:
        blocks.append(
            TextBlock(
                text="\n".join(current_bullets),
                use_bullets=True,
                align=default_align,
                font_size=12,
                spacing_after=12,
            )
        )

    return blocks


def _process_inline_formatting(text: str) -> str:
    """
    משאיר תגיות BOLD/UNDERLINE בטקסט כדי שמנוע הרינדור (word_renderer)
    יוכל להפוך אותן ל-runs מודגשים / עם קו תחתי בתוך אותה פסקה.
    """
    return text

