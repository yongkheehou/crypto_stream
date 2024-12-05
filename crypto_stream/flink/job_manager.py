from typing import Dict, Optional
import json
import os
from pyflink.datastream import StreamExecutionEnvironment, RuntimeExecutionMode
from pyflink.datastream.connectors.kafka import (
    KafkaSource,
    KafkaOffsetsInitializer,
    KafkaSink,
    KafkaRecordSerializationSchema,
    DeliveryGuarantee,
)
from pyflink.common.serialization import SimpleStringSchema
from pyflink.common.watermark_strategy import WatermarkStrategy
from pyflink.common.typeinfo import Types
from models import FlinkJob
from shared.logging_client import LoggerClient
from shared.constants import KAFKA_BOOTSTRAP_SERVERS
from analysis import (
    SimpleAnalysis,
    MovingAverageAnalysis,
    RSIAnalysis,
    MACDAnalysis,
    BollingerBandsAnalysis,
)
from datetime import datetime


class FlinkJobManager:
    def __init__(self, logger: LoggerClient):
        self.logger = logger
        self.env = StreamExecutionEnvironment.get_execution_environment()
        self.env.set_runtime_mode(RuntimeExecutionMode.STREAMING)

        # Configure Flink with JAR files
        pipeline_jars = os.getenv("FLINK_PIPELINE_JARS", "").split(":")
        if pipeline_jars:
            # Add each JAR file with file:// prefix
            jar_urls = [f"file://{jar}" for jar in pipeline_jars if os.path.exists(jar)]
            if jar_urls:
                self.env.add_jars(*jar_urls)

        self.active_jobs: Dict[str, dict] = {}

    def create_kafka_source(self, topic: str) -> KafkaSource:
        """Create a Kafka source for consuming data"""
        return (
            KafkaSource.builder()
            .set_bootstrap_servers(KAFKA_BOOTSTRAP_SERVERS)
            .set_topics(topic)
            .set_group_id("flink-analysis-group")
            .set_starting_offsets(KafkaOffsetsInitializer.latest())
            .set_value_only_deserializer(SimpleStringSchema())
            .build()
        )

    def create_kafka_sink(self, topic: str) -> KafkaSink:
        """Create a Kafka sink for analysis results"""
        return (
            KafkaSink.builder()
            .set_bootstrap_servers(KAFKA_BOOTSTRAP_SERVERS)
            .set_record_serializer(
                KafkaRecordSerializationSchema.builder()
                .set_topic(topic)
                .set_value_serialization_schema(SimpleStringSchema())
                .build()
            )
            .set_delivery_guarantee(DeliveryGuarantee.AT_LEAST_ONCE)
            .build()
        )

    def get_analysis_operator(self, analysis_type: str, window_size: int, **kwargs):
        """Get the appropriate analysis operator based on type"""
        if analysis_type == "simple":
            return SimpleAnalysis(window_size)
        elif analysis_type == "moving_average":
            return MovingAverageAnalysis(window_size)
        elif analysis_type == "rsi":
            return RSIAnalysis(window_size)
        elif analysis_type == "macd":
            return MACDAnalysis(
                kwargs.get("macd_fast_period", 12),
                kwargs.get("macd_slow_period", 26),
                kwargs.get("macd_signal_period", 9),
            )
        elif analysis_type == "bollinger":
            return BollingerBandsAnalysis(window_size, kwargs.get("bollinger_std", 2.0))
        else:
            raise ValueError(f"Unknown analysis type: {analysis_type}")

    async def start_job(self, job_config: FlinkJob) -> str:
        try:
            await self.logger.info(f"Starting Flink job: {job_config.name}")

            job_id = f"flink-{job_config.name}-{job_config.analysis_type}"

            # Create source and sink topics
            source_topic = job_config.kafka_topic
            sink_topic = f"analysis-{job_config.analysis_type}-{source_topic}"

            # Create Kafka source and sink
            source = self.create_kafka_source(source_topic)
            sink = self.create_kafka_sink(sink_topic)

            # Create data stream
            stream = self.env.from_source(
                source=source,
                watermark_strategy=WatermarkStrategy.for_monotonous_timestamps(),
                source_name=f"kafka-source-{job_id}",
            )

            # Parse JSON and extract price data
            price_stream = stream.map(
                lambda x: float(json.loads(x)["close"]), output_type=Types.FLOAT()
            )

            # Get and apply analysis operator
            analysis = self.get_analysis_operator(
                job_config.analysis_type,
                job_config.window_size,
                **job_config.model_dump(
                    exclude={"name", "kafka_topic", "analysis_type", "window_size"}
                ),
            )
            result_stream = analysis.process(price_stream)

            # Convert results to JSON strings and send to Kafka sink
            result_stream.map(
                lambda x: json.dumps(
                    {"timestamp": datetime.now().isoformat(), "value": x}
                ),
                output_type=Types.STRING(),
            ).sink_to(sink)

            # Execute the job
            self.env.execute_async(job_id)

            # Store job info
            self.active_jobs[job_id] = {
                "config": job_config,
                "status": "running",
                "sink_topic": sink_topic,
            }

            await self.logger.info(f"Started Flink job: {job_id}")
            return job_id

        except Exception as e:
            await self.logger.error(f"Failed to start Flink job: {str(e)}")
            raise

    def get_job_status(self, job_id: str) -> Optional[dict]:
        """Get the status of a specific job"""
        return self.active_jobs.get(job_id)

    def list_jobs(self) -> Dict[str, dict]:
        """List all jobs and their status"""
        return self.active_jobs

    async def stop_job(self, job_id: str):
        """Stop a running job"""
        if job_id in self.active_jobs:
            try:
                # Mark job as stopped (actual stopping happens when env is shut down)
                self.active_jobs[job_id]["status"] = "stopped"
                await self.logger.info(f"Marked Flink job as stopped: {job_id}")
            except Exception as e:
                await self.logger.error(f"Failed to stop job {job_id}: {str(e)}")
                raise
