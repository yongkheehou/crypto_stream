from fastapi import FastAPI, HTTPException
from starlette.middleware.cors import CORSMiddleware
from shared.logging_client import LoggerClient
from spark_job_manager import SparkJobManager
from models import SparkJob
from contextlib import asynccontextmanager

# Initialize logger and Spark job manager
logger = LoggerClient("pyspark-service")
spark_manager = SparkJobManager()


@asynccontextmanager
async def lifespan(app: FastAPI):
    await logger.info("Starting PySpark Service")
    yield
    await logger.info("Stopping PySpark Service")
    for job_name in spark_manager.get_active_jobs():
        spark_manager.stop_job(job_name)


app = FastAPI(
    title="PySpark Service",
    description="API for managing PySpark jobs",
    version="1.0.0",
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
    return {"jobs": spark_manager.get_active_jobs()}


@app.post("/jobs")
async def create_job(job: SparkJob):
    """Create a new PySpark job"""
    try:
        job_name = spark_manager.start_job(job)
        await logger.info(f"Started job: {job_name}")
        return {"status": "created", "job_name": job_name}
    except Exception as e:
        await logger.error(f"Failed to create job: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/jobs/{job_name}")
async def get_job(job_name: str):
    """Get job status"""
    try:
        status = spark_manager.get_job_status(job_name)
        return status
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.delete("/jobs/{job_name}")
async def stop_job(job_name: str):
    """Stop a running job"""
    try:
        result = spark_manager.stop_job(job_name)
        await logger.info(f"Stopped job: {job_name}")
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        await logger.error(f"Failed to stop job: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
