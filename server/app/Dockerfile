FROM python:3.11

RUN apt-get update \
    && apt-get install -y ca-certificates \
    && update-ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .

RUN pip install --upgrade pip \
    && pip install -r requirements.txt

RUN playwright install --with-deps chromium
COPY . .

EXPOSE 8000



CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
