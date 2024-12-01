from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from shared.logging_client import LoggerClient

# Initialize logger
logger = LoggerClient("streamlit-service")

app = FastAPI(
    title="Streamlit Service",
    description="API for managing Streamlit dashboards",
    version="1.0.0",
    openapi_url="/api/v1/streamlit/openapi.json",
    docs_url="/api/v1/streamlit/docs",
    redoc_url="/api/v1/streamlit/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
)


class Dashboard(BaseModel):
    name: str
    config: dict


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    await logger.info("Health check requested")
    return {"status": "healthy", "service": "streamlit"}


@app.get("/dashboards")
async def list_dashboards():
    """List all dashboards"""
    await logger.info("Listing all dashboards")
    return {"dashboards": []}


@app.post("/dashboards")
async def create_dashboard(dashboard: Dashboard):
    """Create a new dashboard"""
    await logger.info(
        f"Creating new dashboard: {dashboard.name}",
        metadata={"config": dashboard.dict()},
    )
    return {"status": "created", "dashboard": dashboard.dict()}


@app.get("/dashboards/{dashboard_id}")
async def get_dashboard(dashboard_id: str):
    """Get dashboard status"""
    await logger.info(
        "Getting dashboard status", metadata={"dashboard_id": dashboard_id}
    )
    return {"dashboard_id": dashboard_id, "status": "active"}
