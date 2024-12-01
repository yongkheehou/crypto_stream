from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from shared.logging_client import LoggerClient

# Initialize logger
logger = LoggerClient("kafka-service")

app = FastAPI(
    title="Kafka Service",
    description="API for managing Apache Kafka topics and messages",
    version="1.0.0",
    openapi_url="/api/v1/kafka/openapi.json",
    docs_url="/api/v1/kafka/docs",
    redoc_url="/api/v1/kafka/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
)


class Message(BaseModel):
    content: dict


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    await logger.info("Health check requested")
    return {"status": "healthy", "service": "kafka"}


@app.get("/topics")
async def list_topics():
    """List all Kafka topics"""
    await logger.info("Listing all topics")
    return {"topics": []}


@app.post("/topics/{topic}")
async def create_topic(topic: str):
    """Create a new Kafka topic"""
    await logger.info(f"Creating new topic: {topic}")
    return {"status": "created", "topic": topic}


@app.post("/topics/{topic}/messages")
async def produce_message(topic: str, message: Message):
    """Produce a message to a topic"""
    await logger.info(
        f"Producing message to topic: {topic}", metadata={"message": message.dict()}
    )
    return {"status": "produced", "topic": topic, "message": message.dict()}


@app.on_event("shutdown")
async def shutdown_event():
    """Clean up resources on shutdown"""
    await logger.close()
