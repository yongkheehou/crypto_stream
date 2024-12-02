import httpx
from typing import Dict, Optional
import logging
from datetime import datetime
from .constants import LOGGER_URL


class LoggerClient:
    def __init__(self, service_name: str, logger_url: str = LOGGER_URL):
        self.service_name = service_name
        self.logger_url = logger_url
        self.client = httpx.AsyncClient()

        # Also set up local logging as fallback
        self.local_logger = logging.getLogger(service_name)
        self.local_logger.setLevel(logging.INFO)

    async def log(self, level: str, message: str, metadata: Optional[Dict] = None):
        """Send log to centralized logging service"""
        try:
            log_entry = {
                "service": self.service_name,
                "level": level,
                "message": message,
                "timestamp": datetime.now().isoformat(),
                "metadata": metadata or {},
            }

            # Try to send to logging service
            response = await self.client.post(f"{self.logger_url}/logs", json=log_entry)
            response.raise_for_status()

        except Exception as e:
            # Fallback to local logging if centralized logging fails
            self.local_logger.error(f"Failed to send log to logging service: {str(e)}")
            self.local_logger.log(
                getattr(logging, level.upper(), logging.INFO), message, extra=metadata
            )

    async def info(self, message: str, metadata: Optional[Dict] = None):
        await self.log("INFO", message, metadata)

    async def error(self, message: str, metadata: Optional[Dict] = None):
        await self.log("ERROR", message, metadata)

    async def warning(self, message: str, metadata: Optional[Dict] = None):
        await self.log("WARNING", message, metadata)

    async def debug(self, message: str, metadata: Optional[Dict] = None):
        await self.log("DEBUG", message, metadata)

    async def close(self):
        """Close the HTTP client"""
        await self.client.aclose()
