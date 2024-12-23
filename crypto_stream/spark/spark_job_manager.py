from pyspark.sql import SparkSession
from pyspark.sql.functions import from_json, col
from models import SparkJob
from shared.logging_client import LoggerClient
from shared.constants import KAFKA_BOOTSTRAP_SERVERS
from analysis import AnalysisFactory

logger = LoggerClient("pyspark-service")


class SparkJobManager:
    def __init__(self):
        spark_version = "3.5.3"
        spark_jars = f"/opt/spark/jars/spark-sql-kafka-0-10_2.12-{spark_version}.jar"

        self.spark = (
            SparkSession.builder.appName("PySparkService")
            .config("spark.jars", spark_jars)
            .config("spark.submit.pyFiles", "/app/spark_files/spark_deps.zip")
            .config("spark.sql.streaming.checkpointLocation", "/tmp/checkpoints")
            .getOrCreate()
        )

        self.spark.sparkContext.setLogLevel("ERROR")
        self.active_queries = {}

    def get_active_jobs(self):
        return list(self.active_queries.keys())

    async def start_job(self, job: SparkJob):
        query_name = f"{job.name}-{job.analysis_type}"
        await logger.info(f"spark job manager: Starting Spark job: {query_name}")

        # Read from Kafka
        kafka_stream = (
            self.spark.readStream.format("kafka")
            .option("kafka.bootstrap.servers", KAFKA_BOOTSTRAP_SERVERS)
            .option("subscribe", job.kafka_topic)
            .load()
        )

        await logger.info(
            f"spark job manager: Reading from Kafka topic: {job.kafka_topic}"
        )

        value_df = kafka_stream.selectExpr("CAST(value AS STRING)")

        # Parse JSON and perform analysis
        schema = job.get_schema()
        parsed_df = value_df.select(
            from_json(col("value"), schema).alias("data")
        ).select("data.*")

        await logger.info(f"spark job manager: Applying analysis: {job.analysis_type}")

        # Use the AnalysisFactory to get the appropriate analysis operator
        analysis_operator = AnalysisFactory.get_operator(job)
        result_df = analysis_operator.process(parsed_df)

        await logger.info("spark job manager: Analysis complete")

        # Print results to the console
        query = (
            result_df.writeStream.outputMode("append")
            .format("console")  # Print to console instead of Kafka
            .start()
        )

        self.active_queries[query_name] = query
        return query_name

    def stop_job(self, job_name: str):
        if job_name in self.active_queries:
            query = self.active_queries.pop(job_name)
            query.stop()
            return {"status": "stopped", "job_name": job_name}
        else:
            raise ValueError(f"Job '{job_name}' not found")

    def get_job_status(self, job_name: str):
        query = self.active_queries.get(job_name)
        if not query:
            raise ValueError(f"Job '{job_name}' not found")
        return {"status": "running", "job_name": job_name}
