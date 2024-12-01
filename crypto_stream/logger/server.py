from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, Optional
import logging
from datetime import datetime
import json

# Configure basic logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Logger Service",
    description="Centralized logging service for crypto stream platform",
    version="1.0.0",
    openapi_url="/api/v1/logger/openapi.json",
    docs_url="/api/v1/logger/docs",
    redoc_url="/api/v1/logger/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
)


class LogEntry(BaseModel):
    service: str
    level: str
    message: str
    timestamp: Optional[str] = None
    metadata: Optional[Dict] = None


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "logger"}


@app.post("/logs")
async def create_log(entry: LogEntry):
    """Create a new log entry"""
    entry.timestamp = entry.timestamp or datetime.now().isoformat()

    # Log to file based on service
    log_file = f"logs/{entry.service}/{datetime.now().strftime('%Y%m%d')}.log"

    # Ensure directory exists
    from pathlib import Path

    Path(f"logs/{entry.service}").mkdir(parents=True, exist_ok=True)

    # Write log entry
    with open(log_file, "a") as f:
        f.write(json.dumps(entry.dict()) + "\n")

    # Also log to console
    log_level = getattr(logging, entry.level.upper(), logging.INFO)
    logger.log(log_level, f"[{entry.service}] {entry.message}")

    return {"status": "logged", "entry": entry.dict()}


@app.get("/logs/{service}")
async def get_logs(service: str, date: Optional[str] = None):
    """Get logs for a specific service"""
    if date is None:
        date = datetime.now().strftime("%Y%m%d")

    log_file = f"logs/{service}/{date}.log"
    try:
        with open(log_file, "r") as f:
            logs = [json.loads(line) for line in f]
        return {"logs": logs}
    except FileNotFoundError:
        return {"logs": []}
