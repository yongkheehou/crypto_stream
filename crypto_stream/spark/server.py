from fastapi import FastAPI, HTTPException
from starlette.middleware.cors import CORSMiddleware
from shared.logging_client import LoggerClient
from pyspark.sql import SparkSession
from pyspark.sql.functions import from_json, col, expr
from models import SparkJob
from contextlib import asynccontextmanager

# Initialize logger
logger = LoggerClient("pyspark-service")

# Spark session
spark = (
    SparkSession.builder.appName("PySparkService")
    .config("spark.sql.streaming.checkpointLocation", "/tmp/checkpoints")
    .getOrCreate()
)

active_queries = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    await logger.info("Starting PySpark Service")
    yield
    await logger.info("Stopping PySpark Service")
    for query in active_queries.values():
        query.stop()


app = FastAPI(
    title="PySpark Service",
    description="API for managing PySpark jobs",
    version="1.0.0",
    openapi_url="/api/v1/pyspark/openapi.json",
    docs_url="/api/v1/pyspark/docs",
    redoc_url="/api/v1/pyspark/redoc",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
)


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    await logger.info("Health check requested")
    return {"status": "healthy", "service": "pyspark"}


@app.get("/jobs")
async def list_jobs():
    """List all PySpark jobs"""
    await logger.info("Listing all jobs")
    return {"jobs": list(active_queries.keys())}


@app.post("/jobs")
async def create_job(job: SparkJob):
    """Create a new PySpark job"""
    try:
        query_name = f"{job.name}-{job.analysis_type}"
        await logger.info(f"Starting job: {query_name}")

        # Read from Kafka
        kafka_stream = (
            spark.readStream.format("kafka")
            .option("kafka.bootstrap.servers", job.kafka_servers)
            .option("subscribe", job.kafka_topic)
            .load()
        )

        value_df = kafka_stream.selectExpr("CAST(value AS STRING)")

        # Parse JSON and perform analysis
        schema = job.get_schema()
        parsed_df = value_df.select(
            from_json(col("value"), schema).alias("data")
        ).select("data.*")

        if job.analysis_type == "simple":
            result_df = parsed_df.groupBy(expr("window(timestamp, '5 minutes')")).avg(
                "close"
            )
        elif job.analysis_type == "moving_average":
            result_df = parsed_df.withColumn(
                "moving_avg",
                expr("avg(close) OVER (ROWS BETWEEN 5 PRECEDING AND CURRENT ROW)"),
            )
        else:
            raise ValueError(f"Unsupported analysis type: {job.analysis_type}")

        # Write to Kafka sink
        query = (
            result_df.writeStream.outputMode("append")
            .format("kafka")
            .option("kafka.bootstrap.servers", job.kafka_servers)
            .option("topic", job.result_topic)
            .start()
        )

        active_queries[query_name] = query
        return {"status": "created", "job_name": query_name}

    except Exception as e:
        await logger.error(f"Failed to create job: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/jobs/{job_name}")
async def get_job(job_name: str):
    """Get job status"""
    if job_name not in active_queries:
        raise HTTPException(status_code=404, detail="Job not found")
    query = active_queries[job_name]
    return {"status": query.status, "isActive": query.isActive()}


@app.delete("/jobs/{job_name}")
async def stop_job(job_name: str):
    """Stop a running job"""
    try:
        if job_name in active_queries:
            query = active_queries.pop(job_name)
            query.stop()
            return {"status": "stopped", "job_name": job_name}
        else:
            raise HTTPException(status_code=404, detail="Job not found")
    except Exception as e:
        await logger.error(f"Failed to stop job: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
