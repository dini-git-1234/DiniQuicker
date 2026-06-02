// src/api/reportApi.js

export async function createReport(formData) {
    const response = await fetch("http://localhost:8000/report/create", {
        method: "POST",
        body: formData
    });

    if (!response.ok) {
        // נסה לקבל הודעת שגיאה מהשרת
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

    // בדיקה שהתגובה היא blob
    const contentType = response.headers.get("content-type");
    if (!contentType || !contentType.includes("application/vnd.openxmlformats")) {
        console.warn("Unexpected content type:", contentType);
    }

    return response.blob(); // מקבלים את הדוח כקובץ
}
