from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from shared.logging_client import LoggerClient

# Initialize logger
logger = LoggerClient("flink-service")

app = FastAPI(
    title="Flink Service",
    description="API for managing Apache Flink jobs",
    version="1.0.0",
    openapi_url="/api/v1/flink/openapi.json",
    docs_url="/api/v1/flink/docs",
    redoc_url="/api/v1/flink/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
)


class FlinkJob(BaseModel):
    name: str
    job_config: dict


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    await logger.info("Health check requested")
    return {"status": "healthy", "service": "flink"}


@app.get("/jobs")
async def list_jobs():
    """List all Flink jobs"""
    await logger.info("Listing all jobs")
    return {"jobs": []}


@app.post("/jobs")
async def create_job(job: FlinkJob):
    """Create a new Flink job"""
    await logger.info(
        f"Creating new job: {job.name}", metadata={"job_config": job.dict()}
    )
    return {"status": "created", "job": job.dict()}


@app.get("/jobs/{job_id}")
async def get_job(job_id: str):
    """Get job status"""
    await logger.info("Getting job status", metadata={"job_id": job_id})
    return {"job_id": job_id, "status": "running"}


@app.on_event("shutdown")
async def shutdown_event():
    """Clean up resources on shutdown"""
    await logger.close()
