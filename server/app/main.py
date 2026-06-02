import os
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from fastapi import HTTPException
import logging
import uuid
from api import report
import asyncio
import sys

load_dotenv()


if sys.platform.startswith("win"):
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

app = FastAPI()

logger = logging.getLogger("quickerai")


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    request_id = request.headers.get("x-request-id") or str(uuid.uuid4())
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "ok": False,
            "error": {
                "type": "http_error",
                "message": exc.detail,
            },
            "request_id": request_id,
        },
        headers={"x-request-id": request_id},
    )


@app.exception_handler(RequestValidationError)
async def request_validation_exception_handler(request: Request, exc: RequestValidationError):
    request_id = request.headers.get("x-request-id") or str(uuid.uuid4())
    return JSONResponse(
        status_code=422,
        content={
            "ok": False,
            "error": {
                "type": "validation_error",
                "message": "Invalid request",
                "details": exc.errors(),
            },
            "request_id": request_id,
        },
        headers={"x-request-id": request_id},
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    request_id = request.headers.get("x-request-id") or str(uuid.uuid4())
    logger.exception("Unhandled server error (request_id=%s, path=%s)", request_id, request.url.path)
    return JSONResponse(
        status_code=500,
        content={
            "ok": False,
            "error": {
                "type": "internal_error",
                "message": "Internal server error",
            },
            "request_id": request_id,
        },
        headers={"x-request-id": request_id},
    )


app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition"],
)

app.include_router(report.router, prefix="/report")
