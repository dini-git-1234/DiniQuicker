import { useState } from "react";
import { createReport } from "../api/reportApi";
// import Gov_Map from "./Govmap";
import "./ReportForm.css";
// import GovMap from "./Govmap";

export default function ReportForm() {
    // כתובת
    const [city, setCity] = useState("");
    const [street, setStreet] = useState("");
    const [houseNumber, setHouseNumber] = useState("");
    const [apartment, setApartment] = useState("");

    // פרטי דוח
    const [customer, setCustomer] = useState("");
    const [notes, setNotes] = useState("");
    const [apartmentDescription, setApartmentDescription] = useState("");

    // --- שדות מטרה חדשים ---
    const [purposeOption, setPurposeOption] = useState("משכנתה לכל מטרה");
    const [customPurpose, setCustomPurpose] = useState("");
    // -----------------------

    const [isLoading, setIsLoading] = useState(false);
    const [submitError, setSubmitError] = useState(null);

    // שיטת זיהוי הנכס: tabu_building_plan | tabu_rights_lease | civil_mortgage
    const [identificationMethod, setIdentificationMethod] = useState(null);

    // קבצים לפי שיטת זיהוי
    const [tabuFile, setTabuFile] = useState(null);
    const [buildingPlanFile, setBuildingPlanFile] = useState(null);
    const [bylawsFile, setBylawsFile] = useState(null);
    const [rightsConfirmationFile, setRightsConfirmationFile] = useState(null);
    const [leaseDocumentFile, setLeaseDocumentFile] = useState(null);
    const [civilAdminFile, setCivilAdminFile] = useState(null);
    const [mortgageConfirmationFile, setMortgageConfirmationFile] = useState(null);
    const [outsideImage, setOutsideImage] = useState(null);
    const [insideImages, setInsideImages] = useState([]);

    // פרטי ביקור בנכס
    const [visitDate, setVisitDate] = useState("");
    const [visitedBy, setVisitedBy] = useState("");
    const [presentedBy, setPresentedBy] = useState("");
    const [propertyHolder, setPropertyHolder] = useState("");

    // פרטי שומה
    const [valuationFor, setValuationFor] = useState("");
    const [valuationNumber, setValuationNumber] = useState("");

    // שומות קודמות
    const [previousAppraisalsText, setPreviousAppraisalsText] = useState("");
    const [previousAppraisalsFile, setPreviousAppraisalsFile] = useState(null);

    // מסמכים נוספים (אופציונלי)
    const [saleAgreementFile, setSaleAgreementFile] = useState(null);
    const [rentalAgreementFile, setRentalAgreementFile] = useState(null);
    const [arnonaFormFile, setArnonaFormFile] = useState(null);

    async function handleSubmit(e) {
        e.preventDefault();

        if (!identificationMethod) {
            alert("נא לבחור שיטת זיהוי נכס (נסח טאבו ותשריט / טאבו ואישור זכויות וחכירה / מינהל אזרחי ואישור משכנת).");
            return;
        }

        const form = new FormData();

        // כתובת
        form.append("city", city);
        form.append("street", street);
        form.append("houseNumber", houseNumber);
        if (apartment) form.append("apartment", apartment);

        form.append("customer", customer);
        form.append("notes", notes);
        form.append("apartment_description_text", apartmentDescription);

        // לוגיקת בחירת מטרה: אם נבחר "אחר", קח את הטקסט מהשדה החופשי
        const finalPurpose = purposeOption === "אחר" ? customPurpose : purposeOption;
        form.append("purpose", finalPurpose);

        form.append("visitDate", visitDate);
        form.append("visitedBy", visitedBy);
        form.append("presentedBy", presentedBy);
        form.append("propertyHolder", propertyHolder);

        form.append("valuationFor", valuationFor);
        form.append("valuationNumber", valuationNumber);

        // שומות קודמות (אופציונלי)
        if (previousAppraisalsText) {
            form.append("previousAppraisalsText", previousAppraisalsText);
        }
        if (previousAppraisalsFile) {
            form.append("previousAppraisalsFile", previousAppraisalsFile);
        }

        // מסמכים נוספים (אופציונלי)
        if (saleAgreementFile) form.append("saleAgreement", saleAgreementFile);
        if (rentalAgreementFile) form.append("rentalAgreement", rentalAgreementFile);
        if (arnonaFormFile) form.append("arnonaForm", arnonaFormFile);

        // שיטת זיהוי והקבצים המתאימים
        form.append("identificationMethod", identificationMethod);
        if (identificationMethod === "tabu_building_plan") {
            if (tabuFile) form.append("tabu", tabuFile);
            if (buildingPlanFile) form.append("buildingPlan", buildingPlanFile);
            if (bylawsFile) form.append("bylaws", bylawsFile);
        } else if (identificationMethod === "tabu_rights_lease") {
            if (tabuFile) form.append("tabu", tabuFile);
            if (rightsConfirmationFile) form.append("rightsConfirmation", rightsConfirmationFile);
            if (leaseDocumentFile) form.append("leaseDocument", leaseDocumentFile);
            if (bylawsFile) form.append("bylaws", bylawsFile);
        } else if (identificationMethod === "civil_mortgage") {
            if (civilAdminFile) form.append("civilAdmin", civilAdminFile);
            if (mortgageConfirmationFile) form.append("mortgageConfirmation", mortgageConfirmationFile);
        }

        // קבצים (תמונות)
        if (outsideImage) form.append("outsideImage", outsideImage);
        insideImages.forEach((img) => form.append("insideImages", img));

        setIsLoading(true);
        setSubmitError(null);
        try {
            const fileBlob = await createReport(form);
            const url = window.URL.createObjectURL(fileBlob);
            const downloadLink = document.createElement("a");
            downloadLink.href = url;
            downloadLink.download = "report.docx";
            downloadLink.click();
            window.URL.revokeObjectURL(url);
        } catch (err) {
            console.error(err);
            setSubmitError("אופס, קרתה תקלה. בבקשה תנסה שוב או פנה למנהל המערכת לבירור התקלה");
        } finally {
            setIsLoading(false);
        }
    }

    return (
        <div className="report-form-container">
            <form onSubmit={handleSubmit} className="report-form">
                <h2>יצירת דוח שומה</h2>

                <div className="form-group">
                    {/* <GovMap address={"אשכולי 106 ירושלים"} /> */}

                    <label>עיר</label>
                    <input
                        type="text"
                        className="form-input"
                        value={city}
                        onChange={(e) => setCity(e.target.value)}
                        required
                        placeholder="תל אביב"
                    />
                </div>

                <div className="form-group">
                    <label>רחוב</label>
                    <input
                        type="text"
                        className="form-input"
                        value={street}
                        onChange={(e) => setStreet(e.target.value)}
                        required
                        placeholder="רוטשילד"
                    />
                </div>

                <div className="form-group">
                    <label>מספר בית</label>
                    <input
                        type="number"
                        className="form-input"
                        value={houseNumber}
                        onChange={(e) => setHouseNumber(e.target.value)}
                        required
                        placeholder="10"
                    />
                </div>

                <div className="form-group">
                    <label>מספר דירה (אופציונלי)</label>
                    <input
                        type="number"
                        className="form-input"
                        value={apartment}
                        onChange={(e) => setApartment(e.target.value)}
                        placeholder="5"
                    />
                </div>

                {/* מעבר ישיר לשאר הפרטים ללא כפתור המעבר */}
                <>
                        <div style={{ marginTop: '20px' }}>
                            {/* <Gov_Map city={city} street={street} houseNumber={houseNumber} /> */}
                        </div>

                        <div className="form-section">
                            <p className="section-title">פרטי הדוח</p>

                            <div className="form-group">
                                <label>שם לקוח</label>
                                <input
                                    type="text"
                                    className="form-input"
                                    value={customer}
                                    onChange={(e) => setCustomer(e.target.value)}
                                    placeholder="ישראל ישראלי"
                                />
                            </div>

                            <div className="form-group">
                                <label>מטרת השומה</label>
                                <select
                                    value={purposeOption}
                                    onChange={(e) => setPurposeOption(e.target.value)}
                                    className="form-select"
                                >
                                    <option value="משכנתה לכל מטרה">משכנתה לכל מטרה</option>
                                    <option value="משכנתה לשיפוצים">משכנתה לשיפוצים</option>
                                    <option value="משכנתה להרחבת בנייה">משכנתה להרחבת בנייה</option>
                                    <option value="משכנתה לרכישה">משכנתה לרכישה</option>
                                    <option value="שווי שוק לקראת מכירה">שווי שוק לקראת מכירה</option>
                                    <option value="שווי שוק לקראת קנייה">שווי שוק לקראת קנייה</option>
                                    <option value="שווי שוק לחלוקה בין בעלי זכויות">שווי שוק לחלוקה בין בעלי זכויות</option>
                                    <option value="אחר">אחר...</option>
                                </select>
                            </div>

                            {purposeOption === "אחר" && (
                                <div className="form-group">
                                    <label>פרט מטרה</label>
                                    <input
                                        type="text"
                                        className="form-input"
                                        placeholder="פרט את המטרה..."
                                        value={customPurpose}
                                        onChange={(e) => setCustomPurpose(e.target.value)}
                                        required={purposeOption === "אחר"}
                                    />
                                </div>
                            )}
                            <div className="form-group">
                                <label>מספר שומה</label>
                                <input
                                    type="text"
                                    className="form-input"
                                    value={valuationNumber}
                                    onChange={(e) => setValuationNumber(e.target.value)}
                                    placeholder="2024-00123"
                                />
                            </div>

                            <div className="form-group">
                                <label>עבור מי השומה</label>
                                <input
                                    type="text"
                                    className="form-input"
                                    value={valuationFor}
                                    onChange={(e) => setValuationFor(e.target.value)}
                                    placeholder="בנק / לקוח פרטי / חברה"
                                />
                            </div>


                            <div className="form-group">
                                <label>תיאור הדירה</label>
                                <textarea
                                    className="form-textarea"
                                    value={apartmentDescription}
                                    onChange={(e) => setApartmentDescription(e.target.value)}
                                    placeholder="דירה מרווחת, משופצת כחדשה..."
                                />
                            </div>

                            <div className="form-group">
                                <label>הערות כלליות</label>
                                <textarea
                                    className="form-textarea"
                                    value={notes}
                                    onChange={(e) => setNotes(e.target.value)}
                                    placeholder="הערות נוספות..."
                                />
                            </div>
                        </div>

                        <div className="form-section">
                            <p className="section-title">זיהוי הנכס – מסמכים</p>
                            <p className="section-hint">בחר שיטת זיהוי אחת. יופיעו שדות להעלאת הקבצים המתאימים.</p>

                            <div className="form-group identification-options">
                                <label className="option-row">
                                    <input
                                        type="radio"
                                        name="identificationMethod"
                                        value="tabu_building_plan"
                                        checked={identificationMethod === "tabu_building_plan"}
                                        onChange={() => setIdentificationMethod("tabu_building_plan")}
                                    />
                                    <span>זיהוי באמצעות נסח טאבו ותשריט בית משותף</span>
                                </label>
                                <label className="option-row">
                                    <input
                                        type="radio"
                                        name="identificationMethod"
                                        value="tabu_rights_lease"
                                        checked={identificationMethod === "tabu_rights_lease"}
                                        onChange={() => setIdentificationMethod("tabu_rights_lease")}
                                    />
                                    <span>זיהוי באמצעות טאבו, אישור זכויות והסכם חכירה</span>
                                </label>
                                <label className="option-row">
                                    <input
                                        type="radio"
                                        name="identificationMethod"
                                        value="civil_mortgage"
                                        checked={identificationMethod === "civil_mortgage"}
                                        onChange={() => setIdentificationMethod("civil_mortgage")}
                                    />
                                    <span>זיהוי בעזרת מינהל אזרחי ואישור חברה משכנת</span>
                                </label>
                            </div>

                            {identificationMethod === "tabu_building_plan" && (
                                <>
                                    <div className="form-group">
                                        <label>נסח טאבו (PDF)</label>
                                        <div className="file-input-wrapper">
                                            <input
                                                type="file"
                                                accept="application/pdf"
                                                onChange={(e) => setTabuFile(e.target.files?.[0] ?? null)}
                                                required
                                            />
                                        </div>
                                    </div>
                                    <div className="form-group">
                                        <label>תשריט בית משותף – יש להעלות תצלום של התשריט, כולל סימון של הנכס הרלוונטי. כרגע המערכת עוד לא יודעת לקרוא תשריטים</label>
                                        <div className="file-input-wrapper">
                                            <input
                                                type="file"
                                                accept="image/*"
                                                onChange={(e) => setBuildingPlanFile(e.target.files?.[0] ?? null)}
                                                required
                                            />
                                        </div>
                                    </div>
                                    <div className="form-group">
                                        <label>תקנון בתים משותפים (PDF, אופציונלי – רק אם התקנון מוסכם)</label>
                                        <div className="file-input-wrapper">
                                            <input
                                                type="file"
                                                accept="application/pdf"
                                                onChange={(e) => setBylawsFile(e.target.files?.[0] ?? null)}
                                            />
                                        </div>
                                    </div>
                                </>
                            )}

                            {identificationMethod === "tabu_rights_lease" && (
                                <>
                                    <div className="form-group">
                                        <label>נסח טאבו (PDF)</label>
                                        <div className="file-input-wrapper">
                                            <input
                                                type="file"
                                                accept="application/pdf"
                                                onChange={(e) => setTabuFile(e.target.files?.[0] ?? null)}
                                                required
                                            />
                                        </div>
                                    </div>
                                    <div className="form-group">
                                        <label>אישור זכויות מרמ"י (PDF)</label>
                                        <div className="file-input-wrapper">
                                            <input
                                                type="file"
                                                accept="application/pdf"
                                                onChange={(e) => setRightsConfirmationFile(e.target.files?.[0] ?? null)}
                                            />
                                        </div>
                                    </div>
                                    <div className="form-group">
                                        <label>הסכם חכירה (PDF, אופציונלי – רלוונטי בעיקר לבית צמוד קרקע)</label>
                                        <div className="file-input-wrapper">
                                            <input
                                                type="file"
                                                accept="application/pdf"
                                                onChange={(e) => setLeaseDocumentFile(e.target.files?.[0] ?? null)}
                                            />
                                        </div>
                                    </div>
                                    <div className="form-group">
                                        <label>תקנון בתים משותפים (PDF, אופציונלי – רק אם התקנון מוסכם)</label>
                                        <div className="file-input-wrapper">
                                            <input
                                                type="file"
                                                accept="application/pdf"
                                                onChange={(e) => setBylawsFile(e.target.files?.[0] ?? null)}
                                            />
                                        </div>
                                    </div>
                                </>
                            )}

                            {identificationMethod === "civil_mortgage" && (
                                <>
                                    <div className="form-group">
                                        <label>מינהל אזרחי (PDF)</label>
                                        <div className="file-input-wrapper">
                                            <input
                                                type="file"
                                                accept="application/pdf"
                                                onChange={(e) => setCivilAdminFile(e.target.files?.[0] ?? null)}
                                                required
                                            />
                                        </div>
                                    </div>
                                    <div className="form-group">
                                        <label>אישור חברה משכנת (PDF)</label>
                                        <div className="file-input-wrapper">
                                            <input
                                                type="file"
                                                accept="application/pdf"
                                                onChange={(e) => setMortgageConfirmationFile(e.target.files?.[0] ?? null)}
                                                required
                                            />
                                        </div>
                                    </div>
                                </>
                            )}
                        </div>

                        <div className="form-section">
                            <p className="section-title">פרטי ביקור בנכס</p>

                            <div className="form-group">
                                <label>תאריך ביקור בנכס</label>
                                <input
                                    type="date"
                                    className="form-input"
                                    value={visitDate}
                                    onChange={(e) => setVisitDate(e.target.value)}
                                />
                            </div>

                            <div className="form-group">
                                <label>הביקור בוצע על ידי</label>
                                <input
                                    type="text"
                                    className="form-input"
                                    value={visitedBy}
                                    onChange={(e) => setVisitedBy(e.target.value)}
                                    placeholder="שם השמאי"
                                />
                            </div>

                            <div className="form-group">
                                <label>מי הציג את הנכס</label>
                                <input
                                    type="text"
                                    className="form-input"
                                    value={presentedBy}
                                    onChange={(e) => setPresentedBy(e.target.value)}
                                    placeholder="בעל הנכס / מתווך"
                                />
                            </div>

                            <div className="form-group">
                                <label>מי מחזיק בנכס</label>
                                <input
                                    type="text"
                                    className="form-input"
                                    value={propertyHolder}
                                    onChange={(e) => setPropertyHolder(e.target.value)}
                                    placeholder="בעלים / שוכר"
                                />
                            </div>
                        </div>

                        <div className="form-group">
                            <label>תמונה חיצונית</label>
                            <div className="file-input-wrapper">
                                <input
                                    type="file"
                                    accept="image/*"
                                    onChange={(e) => setOutsideImage(e.target.files[0])}
                                    required
                                />
                            </div>
                        </div>

                        <div className="form-group">
                            <label>תמונות פנימיות</label>
                            <div className="file-input-wrapper">
                                <input
                                    type="file"
                                    accept="image/*"
                                    multiple
                                    onChange={(e) => setInsideImages(Array.from(e.target.files))}
                                    required
                                />
                            </div>
                        </div>

                        <div className="form-section">
                            <p className="section-title">מסמכים נוספים (אופציונלי)</p>
                            <div className="form-group">
                                <label>הסכם מכר (PDF)</label>
                                <div className="file-input-wrapper">
                                    <input
                                        type="file"
                                        accept="application/pdf"
                                        onChange={(e) => setSaleAgreementFile(e.target.files?.[0] ?? null)}
                                    />
                                </div>
                            </div>
                            <div className="form-group">
                                <label>הסכם שכירות (PDF)</label>
                                <div className="file-input-wrapper">
                                    <input
                                        type="file"
                                        accept="application/pdf"
                                        onChange={(e) => setRentalAgreementFile(e.target.files?.[0] ?? null)}
                                    />
                                </div>
                            </div>
                            <div className="form-group">
                                <label>טופס ארנונה (PDF)</label>
                                <div className="file-input-wrapper">
                                    <input
                                        type="file"
                                        accept="application/pdf"
                                        onChange={(e) => setArnonaFormFile(e.target.files?.[0] ?? null)}
                                    />
                                </div>
                            </div>
                        </div>

                        <div className="form-section">
                            <p className="section-title">שומות קודמות שנערכו בנכס (אם יש)</p>
                            <div className="form-group">
                                <label>תיאור קצר על שומות קודמות (אופציונלי)</label>
                                <textarea
                                    className="form-textarea"
                                    value={previousAppraisalsText}
                                    onChange={(e) => setPreviousAppraisalsText(e.target.value)}
                                    placeholder="פרטים קצרים על שומות קודמות שבוצעו בנכס (אם קיימות)..."
                                />
                            </div>
                            <div className="form-group">
                                <label>העלאת קובץ שומה קודמת (PDF, אופציונלי)</label>
                                <div className="file-input-wrapper">
                                    <input
                                        type="file"
                                        accept="application/pdf"
                                        onChange={(e) => setPreviousAppraisalsFile(e.target.files?.[0] ?? null)}
                                    />
                                </div>
                            </div>
                        </div>

                {isLoading && (
                    <div className="form-status form-status-loading">
                        <span className="form-status-spinner" aria-hidden="true" />
                        <p>מעבד את הבקשה, זה לוקח לי קצת זמן</p>
                    </div>
                )}
                {submitError && (
                    <div className="form-status form-status-error" role="alert">
                        {submitError}
                    </div>
                )}
                <button type="submit" className="form-btn primary" disabled={isLoading}>
                    צור לי דוח
                </button>
                </>
            </form>
        </div >
    );
}
