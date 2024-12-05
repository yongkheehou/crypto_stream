from typing import Dict, Optional
import json
import os
import logging
from pyflink.datastream import StreamExecutionEnvironment, RuntimeExecutionMode
from pyflink.common.restart_strategy import RestartStrategies
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
from shared.constants import KAFKA_BOOTSTRAP_SERVERS
from analysis import (
    SimpleAnalysis,
    MovingAverageAnalysis,
    RSIAnalysis,
    MACDAnalysis,
    BollingerBandsAnalysis,
)
from datetime import datetime
import threading
import time

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(
        logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    )
    logger.addHandler(handler)


class FlinkJobManager:
    def __init__(self, logger_client):
        self._logger = None  # Don't store the logger instance

        # Initialize Flink environment with proper configuration
        self.env = StreamExecutionEnvironment.get_execution_environment()
        self.env.set_runtime_mode(RuntimeExecutionMode.STREAMING)
        self.env.set_parallelism(1)  # Set parallelism to 1 for easier debugging
        self.env.enable_checkpointing(60000)  # Enable checkpointing every 60 seconds

        # Set restart strategy
        self.env.get_config().set_restart_strategy(
            RestartStrategies.fixed_delay_restart(3, 10000)
        )  # 3 retries with 10 second delay

        # Configure Flink with JAR files
        jar_dir = "/opt/flink/lib"
        if os.path.exists(jar_dir):
            jar_files = [
                os.path.join(jar_dir, f)
                for f in os.listdir(jar_dir)
                if f.endswith(".jar")
            ]
            if jar_files:
                self.env.add_jars(*[f"file://{jar}" for jar in jar_files])

        self.active_jobs: Dict[str, dict] = {}
        self.job_futures = {}

        # Start job monitoring thread
        self.monitor_thread = threading.Thread(target=self._monitor_jobs, daemon=True)
        self.monitor_thread.start()

    async def _monitor_jobs(self):
        """Monitor job status and handle failures"""
        while True:
            try:
                for job_id, future in list(self.job_futures.items()):
                    if future.done():
                        try:
                            # Get the result to check for exceptions
                            future.result()
                            logger.info(f"Job {job_id} completed successfully")
                        except Exception as e:
                            logger.error(f"Job {job_id} failed: {str(e)}")
                            self.active_jobs[job_id]["status"] = "failed"
                            self.active_jobs[job_id]["error"] = str(e)

                            # Attempt to restart the job
                            logger.info(f"Attempting to restart job {job_id}")
                            await self._restart_job(job_id)
            except Exception as e:
                logger.error(f"Error in job monitoring: {str(e)}")
            time.sleep(10)  # Check every 10 seconds

    async def _restart_job(self, job_id):
        """Attempt to restart a failed job"""
        try:
            if job_id in self.active_jobs:
                job_config = self.active_jobs[job_id]["config"]
                logger.info(f"Restarting job {job_id}")
                # Create new job with same configuration
                await self.start_job(FlinkJob(**job_config))
        except Exception as e:
            logger.error(f"Failed to restart job {job_id}: {str(e)}")

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
            logger.info(f"Starting Flink job: {job_config.name}")

            job_id = f"flink-{job_config.name}-{job_config.analysis_type}"

            # Create source and sink topics
            source_topic = job_config.kafka_topic
            sink_topic = f"analysis-{job_config.analysis_type}-{source_topic}"

            logger.info(f"Using source topic: {source_topic}, sink topic: {sink_topic}")

            # Create Kafka source and sink
            source = self.create_kafka_source(source_topic)
            sink = self.create_kafka_sink(sink_topic)

            # Create data stream
            stream = self.env.from_source(
                source=source,
                watermark_strategy=WatermarkStrategy.for_monotonous_timestamps(),
                source_name=f"kafka-source-{job_id}",
            )

            # Add debug logging for raw input
            def log_input(x: str) -> str:
                try:
                    logger.debug(f"Raw input from Kafka: {x}")
                    return x
                except Exception as e:
                    logger.error(f"Error processing input: {str(e)}")
                    return x

            stream = stream.map(
                log_input,
                output_type=Types.STRING(),
            )

            # Parse JSON and extract price data
            def extract_price(data: str) -> float:
                try:
                    json_data = json.loads(data)
                    price = float(json_data["close"])
                    logger.debug(f"Extracted price: {price}")
                    return price
                except Exception as e:
                    logger.error(f"Error extracting price: {str(e)}, data: {data}")
                    return 0.0

            price_stream = stream.map(
                extract_price,
                output_type=Types.FLOAT(),
            )

            # Get and apply analysis operator
            analysis = self.get_analysis_operator(
                job_config.analysis_type,
                job_config.window_size,
                **job_config.model_dump(
                    exclude={"name", "kafka_topic", "analysis_type", "window_size"}
                ),
            )

            logger.info(f"Created analysis operator: {job_config.analysis_type}")
            result_stream = analysis.process(price_stream)

            # Add debug logging for analysis results
            def log_result(x: float) -> float:
                try:
                    logger.debug(f"Analysis result: {x}")
                    return x
                except Exception as e:
                    logger.error(f"Error logging result: {str(e)}")
                    return x

            result_stream = result_stream.map(
                log_result,
                output_type=Types.FLOAT(),
            )

            # Convert results to JSON strings and send to Kafka sink
            def format_result(x: float) -> str:
                try:
                    return json.dumps(
                        {"timestamp": datetime.now().isoformat(), "value": x}
                    )
                except Exception as e:
                    logger.error(f"Error formatting result: {str(e)}")
                    return json.dumps(
                        {
                            "timestamp": datetime.now().isoformat(),
                            "value": 0.0,
                            "error": str(e),
                        }
                    )

            result_stream.map(
                format_result,
                output_type=Types.STRING(),
            ).sink_to(sink)

            # Execute the job
            logger.info("Executing Flink job...")
            future = self.env.execute_async(job_id)
            self.job_futures[job_id] = future
            logger.info("Flink job execution started")

            # Store job info
            self.active_jobs[job_id] = {
                "config": job_config.model_dump(),  # Convert Pydantic model to dict
                "status": "running",
                "sink_topic": sink_topic,
                "start_time": datetime.now().isoformat(),
            }

            logger.info(f"Started Flink job: {job_id}")
            return job_id

        except Exception as e:
            logger.error(f"Failed to start Flink job: {str(e)}")
            raise

    def get_job_status(self, job_id: str) -> Optional[dict]:
        """Get the status of a specific job"""
        status = self.active_jobs.get(job_id)
        if status:
            # Check if the job is actually running
            future = self.job_futures.get(job_id)
            if future:
                try:
                    job_status = future.get_job_status()
                    if job_status.is_finished():
                        try:
                            # This will raise an exception if the job failed
                            future.result()
                        except Exception as e:
                            status["status"] = "failed"
                            status["error"] = str(e)
                except Exception as e:
                    status["status"] = "failed"
                    status["error"] = str(e)
        return status

    def list_jobs(self) -> Dict[str, dict]:
        """List all jobs and their status"""
        # Update status of all jobs before returning
        for job_id in list(self.active_jobs.keys()):
            self.get_job_status(job_id)
        return self.active_jobs

    async def stop_job(self, job_id: str):
        """Stop a running job"""
        if job_id in self.active_jobs:
            try:
                # Mark job as stopped
                self.active_jobs[job_id]["status"] = "stopped"
                self.active_jobs[job_id]["stop_time"] = datetime.now().isoformat()

                # Cancel the job future if it exists
                if job_id in self.job_futures:
                    future = self.job_futures[job_id]
                    if not future.done():
                        future.cancel()
                    del self.job_futures[job_id]

                logger.info(f"Marked Flink job as stopped: {job_id}")
            except Exception as e:
                logger.error(f"Failed to stop job {job_id}: {str(e)}")
                raise
