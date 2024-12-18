from typing import Dict, Optional
import json
import os
import logging
from pyflink.datastream import StreamExecutionEnvironment, RuntimeExecutionMode
from pyflink.common import JobClient
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
import tracemalloc
import uuid
import asyncio
from asyncio import Lock
from confluent_kafka.admin import AdminClient


tracemalloc.start()

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
        self._logger = logger
        self.lock = Lock()
        self.env = StreamExecutionEnvironment.get_execution_environment()
        self.env.set_runtime_mode(RuntimeExecutionMode.STREAMING)
        self.env.set_parallelism(1)
        self.env.enable_checkpointing(60000)

        self.env.get_config().set_restart_strategy(
            RestartStrategies.fixed_delay_restart(3, 10000)
        )

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
        self.job_futures: Dict[str, JobClient] = {}

        # Create the asyncio task
        asyncio.create_task(self._monitor_jobs())

    def check_kafka_connection(self):
        try:
            admin_client = AdminClient({"bootstrap.servers": KAFKA_BOOTSTRAP_SERVERS})
            metadata = admin_client.list_topics(timeout=5)
            if metadata.topics:
                logger.info("Kafka connection is healthy")
                return True
            else:
                logger.warning("Kafka connection established but no topics found")
                return True
        except Exception as e:
            logger.error(f"Kafka connection failed: {str(e)}")
            return False

    async def _monitor_jobs(self):
        """Monitor job status and handle failures"""
        while True:
            try:
                if not self.check_kafka_connection():
                    logger.error("Kafka connection lost. Retrying...")
            except Exception as e:
                logger.error(f"Error during Kafka health check: {str(e)}")

            async with self.lock:
                try:
                    self.cleanup_old_jobs()
                    for job_id, future in list(self.job_futures.items()):
                        if future.get_job_status().done():
                            try:
                                logger.info(f"Job {job_id} completed successfully")
                                self.active_jobs[job_id]["status"] = "completed"
                            except Exception as e:
                                logger.error(f"Job {job_id} failed: {str(e)}")
                                self.active_jobs[job_id]["status"] = "failed"
                                self.active_jobs[job_id]["error"] = str(e)

                                # Attempt to restart the job
                                logger.info(f"Attempting to restart job {job_id}")
                                await self._restart_job(job_id)
                except Exception as e:
                    logger.error(f"Error in job monitoring: {str(e)}")
            await asyncio.sleep(10)  # Use await sleep for async

    async def _restart_job(self, job_id):
        """Attempt to restart a failed job"""
        try:
            if job_id in self.active_jobs:
                job_config = self.active_jobs[job_id]["config"]
                logger.info(f"Restarting job {job_id}")
                # Restart the job asynchronously
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
        async with self.lock:
            try:
                logger.info(f"Starting Flink job: {job_config.name}")

                job_id = f"flink-{job_config.name}-{job_config.analysis_type}"

                # Create source and sink topics
                source_topic = job_config.kafka_topic
                # sink_topic = f"analysis-{job_config.analysis_type}-{source_topic}"
                sink_topic = f"analysis-{job_config.analysis_type}-{source_topic}-{uuid.uuid4().hex}"  # noqa: E501

                logger.info(
                    f"Using source topic: {source_topic}, sink topic: {sink_topic}"
                )

                if not self.check_kafka_connection():
                    raise RuntimeError(
                        "Unable to connect to Kafka. Please check the connection."
                    )

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
                    if job_status.done():
                        try:
                            # This will raise an exception if the job failed
                            future.get_job_execution_result()
                            # .result() # do this to get the result from the completable future  # noqa: E501
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
                    if not future.get_job_status().done():
                        success = future.cancel()
                        if success:
                            logger.info(f"Successfully cancelled job: {job_id}")
                        else:
                            logger.error(f"Failed to cancel job: {job_id}")
                    del self.job_futures[job_id]

                logger.info(f"Marked Flink job as stopped: {job_id}")
            except Exception as e:
                logger.error(f"Failed to stop job {job_id}: {str(e)}")
                raise

    async def start(self):
        """Initialize and start background monitoring tasks."""
        self.monitor_task = asyncio.create_task(self._monitor_jobs())

    async def shutdown(self):
        """Stop all jobs and monitoring tasks."""
        await self.stop_all_jobs()
        if hasattr(self, "monitor_task") and self.monitor_task:
            self.monitor_task.cancel()
            try:
                await self.monitor_task
            except asyncio.CancelledError:
                logger.info("Monitoring task cancelled successfully.")

    async def stop_all_jobs(self):
        for job_id in list(self.active_jobs.keys()):
            try:
                await self.stop_job(job_id)
            except Exception as e:
                logger.error(f"Failed to stop job {job_id} during shutdown: {str(e)}")

    def cleanup_old_jobs(self, retention_period: int = 600):
        now = datetime.now()
        to_remove = [
            job_id
            for job_id, job in self.active_jobs.items()
            if job["status"] in {"completed", "failed"}
            and (now - datetime.fromisoformat(job["start_time"])).total_seconds()
            > retention_period
        ]
        for job_id in to_remove:
            del self.active_jobs[job_id]
            logger.info(f"Cleaned up job {job_id} from active jobs.")
