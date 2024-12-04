from pydantic import BaseModel, field_validator
from enum import Enum


class StreamStatus(str, Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    STOPPED = "stopped"


class Message(BaseModel):
    content: dict


class StreamConfig(BaseModel):
    symbol: str  # e.g., "BTCUSDT"
    interval: str = "1m"  # e.g., "1m", "5m", "1h"
    limit: int = 100  # Number of candles to fetch

    @field_validator("symbol")
    @classmethod
    def validate_symbol(cls, v):
        if not v.isalnum():
            raise ValueError("Symbol must be alphanumeric")
        return v.upper()

    @field_validator("interval")
    @classmethod
    def validate_interval(cls, v):
        valid_intervals = [
            "1m",
            "3m",
            "5m",
            "15m",
            "30m",
            "1h",
            "2h",
            "4h",
            "6h",
            "8h",
            "12h",
            "1d",
            "3d",
            "1w",
            "1M",
        ]
        if v not in valid_intervals:
            raise ValueError(
                f'Invalid interval. Must be one of: {", ".join(valid_intervals)}'
            )
        return v

    @field_validator("limit")
    @classmethod
    def validate_limit(cls, v):
        if not 1 <= v <= 1000:
            raise ValueError("Limit must be between 1 and 1000")
        return v
