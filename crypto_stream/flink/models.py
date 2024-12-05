from pydantic import BaseModel, field_validator
from typing import Optional


class FlinkJob(BaseModel):
    name: str
    kafka_topic: str
    analysis_type: str = (
        "simple"  # "simple", "moving_average", "rsi", "macd", "bollinger"
    )
    window_size: int = 5  # minutes

    # Optional parameters for specific analysis types
    macd_fast_period: Optional[int] = 12
    macd_slow_period: Optional[int] = 26
    macd_signal_period: Optional[int] = 9
    bollinger_std: Optional[float] = 2.0

    @field_validator("analysis_type")
    @classmethod
    def validate_analysis_type(cls, v):
        valid_types = ["simple", "moving_average", "rsi", "macd", "bollinger"]
        if v not in valid_types:
            raise ValueError(f"Analysis type must be one of: {', '.join(valid_types)}")
        return v

    @field_validator("window_size")
    @classmethod
    def validate_window_size(cls, v):
        if not 1 <= v <= 60:
            raise ValueError("Window size must be between 1 and 60 minutes")
        return v

    @field_validator("macd_fast_period")
    @classmethod
    def validate_macd_fast_period(cls, v):
        if v is not None and not 2 <= v <= 100:
            raise ValueError("MACD fast period must be between 2 and 100")
        return v

    @field_validator("macd_slow_period")
    @classmethod
    def validate_macd_slow_period(cls, v):
        if v is not None and not 5 <= v <= 200:
            raise ValueError("MACD slow period must be between 5 and 200")
        return v

    @field_validator("bollinger_std")
    @classmethod
    def validate_bollinger_std(cls, v):
        if v is not None and not 0.1 <= v <= 5.0:
            raise ValueError("Bollinger standard deviation must be between 0.1 and 5.0")
        return v
