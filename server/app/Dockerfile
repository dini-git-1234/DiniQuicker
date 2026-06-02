FROM python:3.11-slim

# עדכון חבילות והתקנת תעודות אבטחה
RUN apt-get update \
    && apt-get install -y ca-certificates \
    && update-ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .

RUN pip install --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# התקנת דפדפן כרומיום והדרישות שלו עבור פליירייט
RUN playwright install --with-deps chromium

COPY . .

EXPOSE 8000

# הגדרת משתנה סביבה חיוני להרצת דפדפנים בתוך דוקר בענן ללא קריסות
ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright
# ביטול ה-sandbox של כרום שגורם לקריסות בהרבה שרתי ענן
ENV QT_X11_NO_MITSHM=1
ENV OPENBOX_ARGS="--with-file"

# הורדת ה---reload ושינוי מספר ה-workers במידת הצורך (עדיף להשתמש בפורט דינמי מהסביבה אם הפלטפורמה דורשת)
CMD ["sh", "-c", "python -m uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"]