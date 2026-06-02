from pathlib import Path
import re

from docx import Document
from docx.enum.style import WD_STYLE_TYPE
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT, WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_COLOR_INDEX
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor
from PIL import Image

from models.report_request import (
    DocumentRequest,
    ImageBlock,
    ImageGroupBlock,
    TableBlock,
    TextBlock,
)


def render_word_document(document: DocumentRequest, out_path: Path):
    # doc = Document("templates/base_report.docx")
    doc = Document()

    print("Rendering document to:")
    # force_document_rtl(doc)

    # ✅ כותרת כללית (אם קיימת)
    if document.title:
        doc.add_heading(document.title, level=1)

    for block in document.blocks:
        if block.type == "text":
            _render_text_block(doc, block)

        elif block.type == "image":
            _render_image_block(doc, block)

        elif block.type == "image_group":
            _render_image_group_block(doc, block)

        elif block.type == "table":
            _render_table_block(doc, block)

    doc.save(out_path)


def _render_table_block(doc: Document, block):
    rows_count = len(block.rows) + 1
    cols_count = len(block.headers)

    table = doc.add_table(rows=rows_count, cols=cols_count)
    table.style = "Table Grid"
    table.alignment = WD_TABLE_ALIGNMENT.RIGHT

    # --- RTL לטבלה --- (חזרה להתנהגות הקודמת עם bidiVisual)
    tbl = table._tbl
    tblPr = tbl.tblPr
    if tblPr is None:
        tblPr = OxmlElement("w:tblPr")
        tbl.insert(0, tblPr)

    bidi = OxmlElement("w:bidiVisual")
    bidi.set(qn("w:val"), "1")
    tblPr.append(bidi)

    # --- כותרות ---
    for col, header in enumerate(block.headers):
        cell = table.rows[0].cells[col]
        p = cell.paragraphs[0]
        set_paragraph_rtl(p)
        p.alignment = WD_ALIGN_PARAGRAPH.RIGHT

        run = p.add_run(header)
        run.bold = True
        run.font.size = Pt(11)
        set_run_rtl(run)

    # --- שורות ---
    for row_idx, row in enumerate(block.rows, start=1):
        for col_idx, value in enumerate(row):
            # בדיקת הגנה - שלא נחרוג מגבולות הטבלה
            if row_idx < len(table.rows) and col_idx < len(table.columns):
                cell = table.rows[row_idx].cells[col_idx]

                # מנקים את התא (למקרה שיש בו תוכן ברירת מחדל)
                cell.text = ""

                # מוסיפים את התוכן עם עיצוב RTL
                p = cell.paragraphs[0]
                set_paragraph_rtl(p)
                p.alignment = WD_ALIGN_PARAGRAPH.RIGHT

                run = p.add_run(str(value))
                run.font.size = Pt(11)
                set_run_rtl(run)
            else:
                print(
                    f"Warning: Skipping cell at {row_idx}:{col_idx} - out of table bounds"
                )
    # --- רוחבי עמודות ---
    if block.column_widths:
        for i, width in enumerate(block.column_widths):
            for row in table.rows:
                row.cells[i].width = Inches(width)


def set_paragraph_rtl(p):
    """מגדיר paragraph כ-RTL (מימין לשמאל)"""
    pPr = p._p.get_or_add_pPr()
    bidi = OxmlElement("w:bidi")
    bidi.set(qn("w:val"), "1")
    # מחיקה אם כבר קיים
    for child in pPr.findall(qn("w:bidi")):
        pPr.remove(child)
    pPr.append(bidi)


def set_run_rtl(run):
    """מגדיר run (טקסט) כ-RTL (מימין לשמאל)"""
    rPr = run._r.get_or_add_rPr()
    rtl = OxmlElement("w:rtl")
    rtl.set(qn("w:val"), "1")
    # מחיקה אם כבר קיים
    for child in rPr.findall(qn("w:rtl")):
        rPr.remove(child)
    rPr.append(rtl)


def force_document_rtl(doc):
    # Normal style
    try:
        normal = doc.styles["Normal"]
        pPr = normal.element.get_or_add_pPr()

        # כיוון RTL
        bidi = OxmlElement("w:bidi")
        bidi.set(qn("w:val"), "1")
        for c in pPr.findall(qn("w:bidi")):
            pPr.remove(c)
        pPr.append(bidi)

        # יישור לימין כברירת מחדל
        jc = OxmlElement("w:jc")
        jc.set(qn("w:val"), "right")
        for c in pPr.findall(qn("w:jc")):
            pPr.remove(c)
        pPr.append(jc)

    except Exception as e:
        print(f"Could not set Normal style RTL: {e}")

    # הופך גם את Heading 1/2/3 ל־RTL
    for style_name in ["Heading 1", "Heading 2", "Heading 3"]:
        try:
            s = doc.styles[style_name]
            pPr = s.element.get_or_add_pPr()

            bidi = OxmlElement("w:bidi")
            bidi.set(qn("w:val"), "1")
            pPr.append(bidi)

            jc = OxmlElement("w:jc")
            jc.set(qn("w:val"), "right")
            pPr.append(jc)

        except Exception:
            pass


def set_paragraph_alignment(p, align):
    """
    מיישר פסקה לימין, שמאל או מרכז.
    בוורד במסמך RTL לפעמים החוויה של המשתמש הפוכה,
    לכן כאן אנחנו בכוונה הופכים את המשמעות:
    align="right" → ויזואלית שמאל, align="left" → ויזואלית ימין.
    """
    if align == "right":
        # משתמש מבקש "ימין" → בוורד RTL זה מתנהג כשמאל, לכן נהפוך
        p.alignment = WD_ALIGN_PARAGRAPH.LEFT
    elif align == "left":
        # משתמש מבקש "שמאל" → ניישר לימין
        p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    elif align == "center":
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    else:
        p.alignment = WD_ALIGN_PARAGRAPH.LEFT


def fix_rtl_text(text: str) -> str:
    RLM = "\u200F"
    text = re.sub(r"([,.])\s", f"\\1{RLM} ", text)
    text = re.sub(r"(^|\n)(\d)", f"\\1{RLM}\\2", text)
    return text


INLINE_TAG_PATTERN = re.compile(r"(<BOLD>|</BOLD>|<UNDERLINE>|</UNDERLINE>)")


def _add_runs_from_tagged_text(
    p,
    text: str,
    base_bold: bool,
    base_underline: bool,
    font_size_pt: int,
    highlight: bool = False,
):
    """
    מקבל טקסט שיכול להכיל תגיות <BOLD>/<UNDERLINE> ויוצר runs בהתאם,
    תוך שימוש ב-build_rpr_in_order בלי לשנות את סדר הפעולות שם.
    """
    bold_on = False
    underline_on = False

    for part in INLINE_TAG_PATTERN.split(text or ""):
        if not part:
            continue

        if part == "<BOLD>":
            bold_on = True
            continue
        if part == "</BOLD>":
            bold_on = False
            continue
        if part == "<UNDERLINE>":
            underline_on = True
            continue
        if part == "</UNDERLINE>":
            underline_on = False
            continue

        segment = fix_rtl_text(part)
        if not segment:
            continue

        run = p.add_run(segment)
        build_rpr_in_order(
            run,
            bold=bool(base_bold or bold_on),
            underline=bool(base_underline or underline_on),
            font_size_pt=font_size_pt,
        )
        if highlight:
            run.font.highlight_color = WD_COLOR_INDEX.YELLOW


def _render_text_block(doc: Document, block: TextBlock):
    """
    רינדור טקסט כולל:
    - תמיכה ב-use_bullets (מקבל שורות מפרסור קלוד)
    - זיהוי שורות שמתחילות ב-* כמו בוורד והפיכתן לנקודות
    - פירוק תגיות <BOLD>/<UNDERLINE> לריצות מודגשות / עם קו תחתי
    """
    print("Rendering text block:")

    text = block.text or ""
    use_bullets = bool(getattr(block, "use_bullets", False))
    is_error = getattr(block, "variant", None) == "error"

    # חישוב גודל פונט
    if getattr(block, "small", False):
        font_size_pt = 9
    elif getattr(block, "font_size", None):
        font_size_pt = block.font_size  # type: ignore[attr-defined]
    else:
        font_size_pt = 12

    def _create_paragraph():
        p = doc.add_paragraph()
        set_paragraph_rtl(p)

        align = getattr(block, "align", None)
        if align:
            set_paragraph_alignment(p, align)
        else:
            set_paragraph_alignment(p, "right")
        return p

    def _render_line(line_text: str, is_last: bool, force_bullet: bool = False):
        p = _create_paragraph()

        # תמיכה ב-* בתחילת השורה כמו בוורד
        star_bullet_match = re.match(r"^\s*\*\s+", line_text)
        content = line_text
        if star_bullet_match:
            content = line_text[star_bullet_match.end() :]
            force_bullet = True

        bullet = use_bullets or force_bullet
        prefix = "• " if bullet else ""

        full_text = f"{prefix}{content.lstrip()}"
        _add_runs_from_tagged_text(
            p,
            full_text,
            base_bold=bool(getattr(block, "bold", False)),
            base_underline=bool(getattr(block, "underline", False)),
            font_size_pt=font_size_pt,
            highlight=is_error,
        )

        if is_last and getattr(block, "spacing_after", None):
            p.paragraph_format.space_after = Pt(block.spacing_after)  # type: ignore[attr-defined]

    lines = text.split("\n")

    # אם זה בלוק נקודות מקלוד – כל שורה משמעותית הופכת לנקודה
    if use_bullets:
        bullet_lines = [ln for ln in lines if ln.strip()]
        for i, ln in enumerate(bullet_lines):
            _render_line(ln, is_last=i == len(bullet_lines) - 1)
        return

    # לא מוגדר use_bullets, אבל הטקסט מתחיל ב-* → נתייחס אליו כנקודה אחת
    if re.match(r"^\s*\*\s+", text):
        _render_line(text, is_last=True, force_bullet=True)
        return

    # טקסט רגיל – פסקה אחת, עם תגיות פנימיות
    _render_line(text, is_last=True)


def build_rpr_in_order(run, bold=False, underline=False, font_size_pt=12):
    r = run._r
    for existing in r.findall(qn("w:rPr")):
        r.remove(existing)

    rPr = OxmlElement("w:rPr")

    # 1. bold — ראשון לפי סכמת OOXML!
    if bold:
        rPr.append(OxmlElement("w:b"))
        b_cs = OxmlElement("w:bCs")  # חשוב ל-RTL
        rPr.append(b_cs)

    # 2. rFonts
    rFonts = OxmlElement("w:rFonts")
    rFonts.set(qn("w:ascii"), "Arial")
    rFonts.set(qn("w:hAnsi"), "Arial")
    rFonts.set(qn("w:cs"), "Arial")
    rPr.append(rFonts)

    # 3. underline
    if underline:
        u = OxmlElement("w:u")
        u.set(qn("w:val"), "single")
        rPr.append(u)

    # 4. size
    half_points = str(int(font_size_pt * 2))
    sz = OxmlElement("w:sz")
    sz.set(qn("w:val"), half_points)
    rPr.append(sz)
    szCs = OxmlElement("w:szCs")
    szCs.set(qn("w:val"), half_points)
    rPr.append(szCs)

    # 5. rtl — אחרון
    rPr.append(OxmlElement("w:rtl"))

    r.insert(0, rPr)


def _add_border_to_picture(pic):
    try:
        inline = pic._inline
        pic_elem = inline.graphic.graphicData.pic
        spPr = pic_elem.spPr

        # הסרת מסגרת קודמת אם יש
        for ln in spPr.findall(
            "{http://schemas.openxmlformats.org/drawingml/2006/main}ln"
        ):
            spPr.remove(ln)

        # ---- מסגרת ----
        ln = OxmlElement("a:ln")
        ln.set("w", "38100")  # בערך 3pt (יותר עבה)

        solidFill = OxmlElement("a:solidFill")
        srgbClr = OxmlElement("a:srgbClr")
        srgbClr.set("val", "FFFFFF")  # לבן
        solidFill.append(srgbClr)
        ln.append(solidFill)

        spPr.append(ln)

        # ---- צל ----
        effectLst = spPr.find(
            "{http://schemas.openxmlformats.org/drawingml/2006/main}effectLst"
        )
        if effectLst is None:
            effectLst = OxmlElement("a:effectLst")
            spPr.append(effectLst)

        outerShdw = OxmlElement("a:outerShdw")
        outerShdw.set("blurRad", "40000")  # טשטוש
        outerShdw.set("dist", "20000")  # מרחק
        outerShdw.set("dir", "5400000")  # זווית
        outerShdw.set("algn", "ctr")
        outerShdw.set("rotWithShape", "0")

        shadow_color = OxmlElement("a:srgbClr")
        shadow_color.set("val", "888888")  # אפור
        shadow_alpha = OxmlElement("a:alpha")
        shadow_alpha.set("val", "50000")  # שקיפות 50%

        shadow_color.append(shadow_alpha)
        outerShdw.append(shadow_color)

        effectLst.append(outerShdw)

    except Exception as e:
        print(f"Warning: Could not add styled border: {e}")


def _render_image_block(doc: Document, block: ImageBlock):
    section = doc.sections[0]
    page_width = section.page_width - section.left_margin - section.right_margin

    # המרה ל-Inches
    page_width_inches = page_width / 914400  # המרה מ-EMU ל-Inches

    # גודל תמונה - תלוי ב-role
    if block.role == "cover":
        width_inches = page_width_inches * 0.8  # תמונה חיצונית - גדולה יותר
        max_height = Inches(block.max_height_inches or 4.5)
    else:
        width_inches = page_width_inches * 0.66  # תמונה רגילה
        max_height = Inches(block.max_height_inches or 3.5)

    # חישוב גודל סופי
    if block.max_height_inches:
        try:
            img = Image.open(block.path)
            height_ratio = img.height / img.width
            calc_height_inches = width_inches * height_ratio
            if calc_height_inches > max_height.inches:
                width_inches = max_height.inches / height_ratio
        except Exception as e:
            print(f"Warning: Could not open image {block.path}: {e}")

    width = Inches(width_inches)

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    set_paragraph_rtl(p)

    run = p.add_run()
    pic = run.add_picture(str(block.path), width=width)

    if block.bordered:
        _add_border_to_picture(pic)


def _render_image_group_block(doc: Document, block: ImageGroupBlock):
    """מציג קבוצת תמונות בטבלה מסודרת, אחידה, עם רווחים מסביב"""

    section = doc.sections[0]
    page_width = section.page_width - section.left_margin - section.right_margin

    # המרה לאינצ'ים
    page_width_inches = page_width / 914400

    # כמה המקום לתמונות
    available_width = page_width_inches * 0.85  # לא צמוד לשוליים
    cell_width_inches = available_width / 2  # שתי עמודות
    image_width_inches = cell_width_inches * 0.75  # משאיר רווח יפה מסביב

    image_width = Inches(image_width_inches)
    max_height = Inches(block.max_height_inches)

    num_images = len(block.image_paths)
    if num_images == 0:
        return

    num_rows = (num_images + 1) // 2

    table = doc.add_table(rows=num_rows, cols=2)
    table.alignment = WD_ALIGN_PARAGRAPH.CENTER
    table.autofit = False

    # קובע רוחב אחיד לעמודות
    col_width = Inches(cell_width_inches)
    for row in table.rows:
        for cell in row.cells:
            cell.width = col_width

            # ⭐⭐ רווח פנימי בתוך התא ⭐⭐
            tcPr = cell._tc.get_or_add_tcPr()
            tcMar = OxmlElement("w:tcMar")

            for side in ["top", "bottom", "left", "right"]:
                mar = OxmlElement(f"w:{side}")
                mar.set(qn("w:w"), "360")  # padding ≈ 0.25cm
                mar.set(qn("w:type"), "dxa")
                tcMar.append(mar)

            tcPr.append(tcMar)

    # הוספת תמונות
    for idx, img_path in enumerate(block.image_paths):
        row_idx = idx // 2
        col_idx = idx % 2

        cell = table.rows[row_idx].cells[col_idx]

        # חישוב גודל קבוע לכל התמונות
        try:
            img = Image.open(img_path)
            ratio = img.height / img.width
            calc_height = image_width_inches * ratio

            final_width = image_width
            if calc_height > max_height.inches:
                final_width = Inches(max_height.inches / ratio)

        except Exception:
            final_width = image_width

        p = cell.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER

        run = p.add_run()
        pic = run.add_picture(str(img_path), width=final_width)

        if block.bordered:
            _add_border_to_picture(pic)

    # ⭐⭐ רווח בין שורות ⭐⭐
    for row in table.rows:
        for p in row.cells[0].paragraphs:
            p.paragraph_format.space_after = Pt(10)

