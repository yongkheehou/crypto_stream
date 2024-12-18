from fastapi import FastAPI, HTTPException
from starlette.middleware.cors import CORSMiddleware
from shared.logging_client import LoggerClient
from job_manager import FlinkJobManager
from contextlib import asynccontextmanager
from models import FlinkJob

# Initialize logger and job manager
logger = LoggerClient("flink-service")
job_manager = FlinkJobManager(logger)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await job_manager.start()

    yield

    await job_manager.shutdown()
    await logger.close()


app = FastAPI(
    title="Flink Service",
    description="API for managing Apache Flink jobs",
    version="1.0.0",
    openapi_url="/api/v1/flink/openapi.json",
    docs_url="/api/v1/flink/docs",
    redoc_url="/api/v1/flink/redoc",
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
    return {"status": "healthy", "service": "flink"}


@app.get("/jobs")
async def list_jobs():
    """List all Flink jobs"""
    await logger.info("Listing all jobs")
    return {"jobs": job_manager.list_jobs()}


@app.post("/jobs")
async def create_job(job: FlinkJob):
    """Create a new Flink job"""
    try:
        job_id = await job_manager.start_job(job)
        await logger.info(f"Created new job: {job.name}", metadata={"job_id": job_id})
        return {"status": "created", "job_id": job_id}
    except Exception as e:
        await logger.error(f"Failed to create job: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/jobs/{job_id}")
async def get_job(job_id: str):
    """Get job status"""
    job_status = job_manager.get_job_status(job_id)
    if not job_status:
        raise HTTPException(status_code=404, detail="Job not found")
    return job_status


@app.delete("/jobs/{job_id}")
async def stop_job(job_id: str):
    """Stop a running job"""
    try:
        await job_manager.stop_job(job_id)
        return {"status": "stopped", "job_id": job_id}
    except Exception as e:
        await logger.error(f"Failed to stop job: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
