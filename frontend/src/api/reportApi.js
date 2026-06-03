// src/api/reportApi.js

// שליפת כתובת השרת ממשתני הסביבה של הענן, עם ברירת מחדל לקישור החיצוני
const API_BASE_URL = import.meta.env.VITE_API_URL || "https://diniquickerserver.onrender.com";

export async function createReport(formData) {
    // החלפת localhost בכתובת הדינמית
    const response = await fetch(`${API_BASE_URL}/report/create`, {
        method: "POST",
        body: formData
    });

    if (!response.ok) {
        let errorMessage = "Failed to create report";
        try {
            const errorText = await response.text();
            if (errorText) {
                errorMessage = errorText;
            }
        } catch (e) {
            // אם לא הצלחנו לקרוא את הטקסט, נשתמש בהודעת ברירת מחדל
        }
        throw new Error(`${errorMessage} (Status: ${response.status})`);
    }

    const contentType = response.headers.get("content-type");
    if (!contentType || !contentType.includes("application/vnd.openxmlformats")) {
        console.warn("Unexpected content type:", contentType);
    }

    return response.blob(); 
}