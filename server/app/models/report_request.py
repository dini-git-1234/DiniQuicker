from pydantic import BaseModel ,field_validator
from dataclasses import dataclass, field
from typing import List, Optional, Literal
from pathlib import Path
from pydantic import Field
class PropertyAddress(BaseModel):
    city: str
    street: str
    house_number: str
    apartment: Optional[str]

class ReportMeta(BaseModel):
    customer: Optional[str]
    purpose: Optional[str]

    valuation_for: Optional[str] = None     # עבור מי השומה
    valuation_number: Optional[str] = None  # מספר השומה

    notes: Optional[str]
    apartment_description_text_base: Optional[str] = None
    # תיאור חופשי של שומות קודמות (אם ניתן ע"י המשתמש)
    previous_appraisals_note: Optional[str] = None

class PropertyVisit(BaseModel):
    visit_date: Optional[str] = None        # תאריך ביקור בנכס
    visited_by: Optional[str] = None        # מי ביצע את הביקור
    presented_by: Optional[str] = None      # מי הציג את הנכס
    property_holder: Optional[str] = None   # מי מחזיק בנכס

    
class Data(BaseModel):
    apartment_description_text: Optional[str] = None  # טקסט נוסף לשילוב בתיאור התמונות
    # בפועל tabu_data משמש כטקסט מסוכם/מעוצב (ולא JSON). ה-JSON נשמר ב-tabuJSON.
    tabu_data: Optional[str] = None
    tabuJSON: dict = Field(default_factory=dict)
    environmental_description: Optional[str] = None
    purpose_statement: Optional[str]=None
    tabu_screenshots: Optional[List[str]] = None
    taba_documents_text: Optional[str] = None  
    govmap_results: Optional[str] = None  
    googlemap_result: Optional[str]=None
    visit_text: Optional[str]=None
    rights: Optional[str]=None
    plans: Optional[str]=None
    rights_confirmation_data: Optional[str] = None  # טקסט מחולץ מאישור זכויות מרמ"י
    lease_document_data: Optional[str] = None  # טקסט מחולץ מהסכם חכירה
    building_plan_data: Optional[str] = None  # תשריט בית משותף
    bylaws_text: Optional[str] = None  # תקנון: "התקנון מצוי" או סיכום שינויים כשמורכב
    civil_admin_data: Optional[str] = None  # מינהל אזרחי
    mortgage_confirmation_data: Optional[str] = None  # אישור חברה משכנת
    # מסמכים משפטיים / מצב משפטי במבנה אחיד: label -> תוכן
    legal_documents: dict = Field(default_factory=dict)
    planning_rights_table: Optional[List[List[str]]] = Field(default=None)
    PLANS_TBL: Optional[dict] = Field(default=None)
    # נתוני בדיקת זיהום קרקע
    soil_pollution_screenshot: Optional[str] = None  # נתיב לצילום מסך אם נמצא זיהום, אחרת None
    # טבלת עסקאות דומות ותמונת המקור שלה
    comparable_sales_table: Optional[dict] = Field(default=None)
    comparable_sales_image: Optional[str] = None
    # טקסט מחולץ מקבצי התב"ע שהורדו
    # תקציר שומות קודמות שנשלחו כקובץ PDF
    previous_appraisals_summary: Optional[str] = None
    # מסמכים נוספים (אופציונלי) – סריקה ועיצוב דרך קלוד
    sale_agreement_data: Optional[str] = None      # הסכם מכר
    rental_agreement_data: Optional[str] = None     # הסכם שכירות
    arnona_form_data: Optional[str] = None          # טופס ארנונה
class ParcelInfo(BaseModel):
    gush: str
    helka: str
    tat_helka: str

    @field_validator("gush", "helka", "tat_helka", mode="before")
    @classmethod
    def cast_to_str(cls, v):
        return str(v)
@dataclass
class DocumentRequest:
    title: Optional[str] = None
    blocks: List[object] = field(default_factory=list)
class ImageBlock:
    type = "image"

    def __init__(
        self,
        path: Path,
        role: str = "default",
        caption: str | None = None,
        max_height_inches: float | None = None,
        bordered: bool = False
    ):
        self.path = path
        self.role = role
        self.caption = caption
        self.max_height_inches = max_height_inches
        self.bordered = bordered

class ImageGroupBlock:
    """קבוצת תמונות שתוצג בטבלה (2 תמונות בשורה)"""
    type = "image_group"
    
    def __init__(
        self,
        image_paths: List[Path],
        max_height_inches: float = 2.5,
        bordered: bool = True
    ):
        self.image_paths = image_paths
        self.max_height_inches = max_height_inches
        self.bordered = bordered

class TextBlock:
    type = "text"

    def __init__(
        self,
        text: str,
        bold: bool = False,
        font_size: int | None = None,
        align: str | None = None,   # "right" | "left" | "center"
        underline: bool = False,
        small: bool = False,
        spacing_after: int | None = None,
        use_bullets: bool = False,  # אם True, הטקסט יוצג כ-bullet list
        variant: str | None = None,  # למשל "error" לצביעה/הדגשה מיוחדת במסמך
    ):
        self.text = text
        self.bold = bold
        self.font_size = font_size
        self.align = align
        self.underline = underline
        self.small = small
        self.spacing_after = spacing_after
        self.use_bullets = use_bullets
        self.variant = variant
class TableBlock:
    type = "table"

    def __init__(
        self,
        headers: list[str],
        rows: list[list[str]],
        column_widths: list[float] | None = None,  # באינצ'ים
        bordered: bool = True
    ):
        self.headers = headers
        self.rows = rows
        self.column_widths = column_widths
        self.bordered = bordered

