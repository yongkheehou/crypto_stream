from contextlib import asynccontextmanager
from fastapi import (
    FastAPI,
    HTTPException,
    WebSocket,
    WebSocketDisconnect,
    Depends,
)
from starlette.middleware.cors import CORSMiddleware
from fastapi.security import APIKeyHeader
import time
from typing import Dict, List
from shared.logging_client import LoggerClient
from models import Message, StreamConfig
from stream_manager import StreamManager
from websocket_manager import WebSocketManager
import json

# Initialize logger
logger = LoggerClient("kafka-service")

# Initialize managers
websocket_manager = WebSocketManager(logger)
stream_manager = StreamManager(logger, websocket_manager)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await stream_manager.initialize_kafka()

    yield

    # Shutdown
    await stream_manager.shutdown()
    await websocket_manager.close_all()
    await logger.close()


app = FastAPI(
    title="Kafka Service",
    description="API for managing Kafka topics and streaming Binance data",
    version="1.0.0",
    openapi_url="/api/v1/kafka/openapi.json",
    docs_url="/api/v1/kafka/docs",
    redoc_url="/api/v1/kafka/redoc",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
)

# Rate limiting configuration
RATE_LIMIT = 100  # requests per minute
RATE_LIMIT_WINDOW = 60  # seconds
REQUEST_HISTORY: Dict[str, List[float]] = {}

# API Key security
API_KEY_HEADER = APIKeyHeader(name="X-API-Key")


async def check_rate_limit(client_id: str = Depends(API_KEY_HEADER)):
    """Rate limiting middleware"""
    now = time.time()
    if client_id not in REQUEST_HISTORY:
        REQUEST_HISTORY[client_id] = []

    # Remove old requests outside the window
    REQUEST_HISTORY[client_id] = [
        ts for ts in REQUEST_HISTORY[client_id] if now - ts < RATE_LIMIT_WINDOW
    ]

    if len(REQUEST_HISTORY[client_id]) >= RATE_LIMIT:
        raise HTTPException(
            status_code=429, detail="Rate limit exceeded. Please try again later."
        )

    REQUEST_HISTORY[client_id].append(now)
    return client_id


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    await logger.info("Health check requested")
    return {"status": "healthy", "service": "kafka"}


@app.websocket("/ws/{stream_id}")
async def websocket_endpoint(websocket: WebSocket, stream_id: str):
    """WebSocket endpoint for real-time updates"""
    if not stream_manager.get_stream_status(stream_id):
        await websocket.close(code=4004, reason="Stream not found")
        return

    await websocket_manager.connect(websocket, stream_id)
    try:
        while True:
            await websocket.receive_text()  # Keep connection alive
    except WebSocketDisconnect:
        websocket_manager.disconnect(websocket, stream_id)


@app.post("/streams/start", dependencies=[Depends(check_rate_limit)])
async def start_stream(config: StreamConfig):
    """Start a new market data stream"""
    stream_id = f"binance-{config.symbol.lower()}-{config.interval}"

    if stream_manager.get_stream_status(stream_id):
        raise HTTPException(status_code=400, detail="Stream already exists")

    try:
        # Test the connection first
        await stream_manager.fetch_klines(config.symbol, config.interval, 1)

        # Start the stream
        stream_id = await stream_manager.start_stream(config)

        return {
            "status": "success",
            "message": "Stream started",
            "stream_id": stream_id,
            "websocket_url": f"/ws/{stream_id}",
        }

    except Exception as e:
        await logger.error(f"Error starting stream: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/streams/{stream_id}/stop", dependencies=[Depends(check_rate_limit)])
async def stop_stream(stream_id: str):
    """Stop a market data stream"""
    if not stream_manager.get_stream_status(stream_id):
        raise HTTPException(status_code=404, detail="Stream not found")

    await stream_manager.stop_stream(stream_id)
    return {"status": "success", "message": "Stream stopped"}


@app.post("/streams/{stream_id}/pause", dependencies=[Depends(check_rate_limit)])
async def pause_stream(stream_id: str):
    """Pause a market data stream"""
    stream = stream_manager.get_stream_status(stream_id)
    if not stream:
        raise HTTPException(status_code=404, detail="Stream not found")

    await stream_manager.pause_stream(stream_id)
    return {"status": "success", "message": "Stream paused"}


@app.post("/streams/{stream_id}/resume", dependencies=[Depends(check_rate_limit)])
async def resume_stream(stream_id: str):
    """Resume a paused market data stream"""
    stream = stream_manager.get_stream_status(stream_id)
    if not stream:
        raise HTTPException(status_code=404, detail="Stream not found")

    await stream_manager.resume_stream(stream_id)
    return {"status": "success", "message": "Stream resumed"}


@app.get("/streams", dependencies=[Depends(check_rate_limit)])
async def list_streams():
    """List all streams and their status"""
    return {"streams": stream_manager.list_streams()}


@app.post("/topics/{topic}/messages", dependencies=[Depends(check_rate_limit)])
async def produce_message(topic: str, message: Message):
    """Produce a message to a topic"""
    try:
        if stream_manager.kafka_producer is None:
            raise RuntimeError("Kafka producer not initialized")
        stream_manager.kafka_producer.send(topic, message.content)
        await logger.info(
            f"Message produced to topic: {topic}", metadata={"message": message.dict()}
        )
        return {"status": "produced", "topic": topic}
    except Exception as e:
        await logger.error(f"Error producing message: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.websocket("/topics/{topic}/consume")
async def consume_messages(websocket: WebSocket, topic: str):
    """WebSocket endpoint to consume messages from a topic"""
    await websocket.accept()

    try:
        # Create a consumer for this connection
        consumer = stream_manager.create_consumer(topic)

        while True:
            try:
                # Poll for messages
                messages = consumer.poll(timeout_ms=1000)
                for tp, records in messages.items():
                    for record in records:
                        # Send message to WebSocket client
                        await websocket.send_json(
                            {
                                "topic": topic,
                                "partition": tp.partition,
                                "offset": record.offset,
                                "value": json.loads(record.value.decode("utf-8")),
                            }
                        )
            except Exception as e:
                await logger.error(f"Error consuming messages: {str(e)}")
                break

    except WebSocketDisconnect:
        pass
    finally:
        if consumer:
            consumer.close()
