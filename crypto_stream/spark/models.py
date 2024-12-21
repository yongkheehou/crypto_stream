from pydantic import BaseModel, Field
from pyspark.sql.types import (
    StructType,
    StructField,
    FloatType,
    TimestampType,
    LongType,
)


class SparkJob(BaseModel):
    name: str
    kafka_topic: str
    analysis_type: str = Field(
        default="simple",
        description="Type of analysis: 'simple', 'moving_average', etc.",
    )
    window_size: int = Field(default=5, description="Window size for analysis")

    def get_schema(self):
        """
        Define the schema for incoming Kafka JSON messages based on kline data fields.
        """
        return StructType(
            [
                StructField("open_time", TimestampType(), True),
                StructField("open", FloatType(), True),
                StructField("high", FloatType(), True),
                StructField("low", FloatType(), True),
                StructField("close", FloatType(), True),
                StructField("volume", FloatType(), True),
                StructField("close_time", TimestampType(), True),
                StructField("quote_volume", FloatType(), True),
                StructField("trades", LongType(), True),
                StructField("taker_buy_base", FloatType(), True),
                StructField("taker_buy_quote", FloatType(), True),
            ]
        )
