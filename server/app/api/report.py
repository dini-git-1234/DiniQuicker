from fastapi import APIRouter, BackgroundTasks, File, Form, UploadFile, HTTPException
from fastapi.responses import FileResponse
from typing import Optional, List
from types import SimpleNamespace
import os

from services.report_service import create_report_logic
from models.report_request import (
    PropertyAddress,
    ReportMeta,
    ParcelInfo,
    PropertyVisit
)

router = APIRouter()


@router.post("/create")
async def create_report(
    background_tasks: BackgroundTasks,

    # --- כתובת ---
    city: str = Form(...),
    street: str = Form(...),
    houseNumber: str = Form(...),
    apartment: Optional[str] = Form(None),

    # --- פרטי דוח / שומה ---
    customer: Optional[str] = Form(None),
    purpose: Optional[str] = Form(None),
    valuationFor: Optional[str] = Form(None),
    valuationNumber: Optional[str] = Form(None),
    notes: Optional[str] = Form(None),
    apartment_description_text: Optional[str] = Form(None),
    # --- שומות קודמות ---
    previousAppraisalsText: Optional[str] = Form(None),

    # --- פרטי ביקור בנכס ---
    visitDate: Optional[str] = Form(None),
    visitedBy: Optional[str] = Form(None),
    presentedBy: Optional[str] = Form(None),
    propertyHolder: Optional[str] = Form(None),

    # --- שיטת זיהוי (מהקליינט) ---
    identificationMethod: Optional[str] = Form(None),

    # --- קבצים ---
    tabu: Optional[UploadFile] = File(None),
    buildingPlan: Optional[UploadFile] = File(None),
    rightsConfirmation: Optional[UploadFile] = File(None),
    leaseDocument: Optional[UploadFile] = File(None),
    bylaws: Optional[UploadFile] = File(None),
    civilAdmin: Optional[UploadFile] = File(None),
    mortgageConfirmation: Optional[UploadFile] = File(None),
    outsideImage: Optional[UploadFile] = File(None),
    insideImages: Optional[List[UploadFile]] = File(None),
    previousAppraisalsFile: Optional[UploadFile] = File(None),
    # מסמכים נוספים (אופציונלי)
    saleAgreement: Optional[UploadFile] = File(None),
    rentalAgreement: Optional[UploadFile] = File(None),
    arnonaForm: Optional[UploadFile] = File(None),
):
    # ---------------- כתובת ----------------
    address = PropertyAddress(
        city=city,
        street=street,
        house_number=houseNumber,
        apartment=apartment
    )

    # ---------------- מטא־דאטה לדוח ----------------
    meta = ReportMeta(
        customer=customer,
        purpose=purpose,
        valuation_for=valuationFor,
        valuation_number=valuationNumber,
        notes=notes,
        apartment_description_text_base=apartment_description_text,
        previous_appraisals_note=previousAppraisalsText,
    )

    # ---------------- פרטי ביקור ----------------
    visit = PropertyVisit(
        visit_date=visitDate,
        visited_by=visitedBy,
        presented_by=presentedBy,
        property_holder=propertyHolder
    )

    # ---------------- קבצים ----------------
    files = SimpleNamespace(
        tabu=tabu,
        building_plan=buildingPlan,
        rights_confirmation=rightsConfirmation,
        lease_document=leaseDocument,
        bylaws=bylaws,
        civil_admin=civilAdmin,
        mortgage_confirmation=mortgageConfirmation,
        outside_image=outsideImage,
        inside_images=insideImages,
        previous_appraisals=previousAppraisalsFile,
        sale_agreement=saleAgreement,
        rental_agreement=rentalAgreement,
        arnona_form=arnonaForm,
    )

    try:
        # ---------------- לוגיקה ----------------
        result = await create_report_logic(
            background_tasks=background_tasks,
            address=address,
            meta=meta,
            visit=visit,
            files=files,
            identification_method=identificationMethod,
        )

        file_path = str(result["path"])

        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="הקובץ לא נמצא לאחר יצירת הדוח")

        print(f"[report API] מחזיר קובץ: {file_path}, filename: {result['filename']}")

        return FileResponse(
            path=file_path,
            filename=result["filename"],
            media_type=result["media_type"]
        )
    except HTTPException:
        raise
    except Exception as e:
        # לא “בולעים” את הבעיה — מחזירים 500 עקבי, והלוג המלא יופיע בשרת (דרך handler גלובלי)
        print(f"[report API] שגיאה ביצירת דוח: {e}")
        raise HTTPException(status_code=500, detail="שגיאה פנימית ביצירת הדוח")
