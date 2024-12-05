from typing import Dict, List, Optional
from datetime import datetime
import asyncio
import httpx
import json
import os
from confluent_kafka import Producer
from shared.constants import KAFKA_BOOTSTRAP_SERVERS
from shared.logging_client import LoggerClient
from models import StreamStatus, StreamConfig
from websocket_manager import WebSocketManager
from dotenv import load_dotenv
import time

load_dotenv()


class StreamManager:
    def __init__(self, logger: LoggerClient, websocket_manager: WebSocketManager):
        self.logger = logger
        self.websocket_manager = websocket_manager
        self.active_streams: Dict[str, dict] = {}
        self.kafka_producer: Optional[Producer] = None
        self.binance_base_url = os.getenv(
            "BINANCE_BASE_URL", "https://api.binance.com/api/v3"
        )

    def delivery_callback(self, err, msg):
        """Synchronous callback for message delivery reports"""
        if err is not None:
            print(f"Message delivery failed: {err}")  # Use print for sync callback
        else:
            print(f"Message delivered to {msg.topic()} [{msg.partition()}]")

    async def initialize_kafka(self, bootstrap_servers: str = KAFKA_BOOTSTRAP_SERVERS):
        """Initialize Kafka producer"""
        try:
            conf = {
                "bootstrap.servers": bootstrap_servers,
                "client.id": "crypto-stream-producer",
                "retries": 5,
                "retry.backoff.ms": 1000,
                "delivery.timeout.ms": 30000,
                "request.timeout.ms": 10000,
                "message.timeout.ms": 30000,
            }
            self.kafka_producer = Producer(conf)
            await self.logger.info("Kafka producer initialized successfully")
        except Exception as e:
            await self.logger.error(f"Failed to initialize Kafka producer: {str(e)}")
            raise

    async def fetch_klines(
        self, symbol: str, interval: str = "1m", limit: int = 100
    ) -> List:
        """Fetch kline data from Binance API"""
        url = f"{self.binance_base_url}/klines"
        params = {"symbol": symbol, "interval": interval, "limit": limit}

        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            return response.json()

    def process_kline_data(self, kline: List) -> dict:
        """Process raw kline data into a structured format"""
        return {
            "open_time": datetime.fromtimestamp(kline[0] / 1000).isoformat(),
            "open": float(kline[1]),
            "high": float(kline[2]),
            "low": float(kline[3]),
            "close": float(kline[4]),
            "volume": float(kline[5]),
            "close_time": datetime.fromtimestamp(kline[6] / 1000).isoformat(),
            "quote_volume": float(kline[7]),
            "trades": int(kline[8]),
            "taker_buy_base": float(kline[9]),
            "taker_buy_quote": float(kline[10]),
        }

    async def stream_market_data(self, symbol: str, interval: str, stream_id: str):
        """
        Continuously streams market data from Binance to Kafka
        1. Fetch data from Binance
        2. Process the data
        3. Send to Kafka
        4. Use websocket_manager to broadcast updates to WebSocket clients
        """
        await self.logger.info(
            f"Starting stream for {symbol}", metadata={"stream_id": stream_id}
        )

        while self.active_streams[stream_id]["status"] != StreamStatus.STOPPED:
            if self.active_streams[stream_id]["status"] == StreamStatus.PAUSED:
                await asyncio.sleep(1)
                continue

            try:
                klines = await self.fetch_klines(symbol, interval, limit=100)

                for kline in klines:
                    if self.active_streams[stream_id]["status"] != StreamStatus.ACTIVE:
                        break

                    processed_data = self.process_kline_data(kline)

                    if self.kafka_producer is None:
                        raise RuntimeError("Kafka producer not initialized")

                    # Convert data to JSON string
                    message = json.dumps(processed_data).encode("utf-8")

                    # Produce message to Kafka
                    self.kafka_producer.produce(
                        topic=stream_id, value=message, callback=self.delivery_callback
                    )

                    # Trigger any events that are ready to be delivered
                    self.kafka_producer.poll(0)

                    await self.websocket_manager.broadcast_to_clients(
                        stream_id, processed_data
                    )

                sleep_time = 60  # default 1m
                if interval.endswith("m"):
                    sleep_time = int(interval[:-1]) * 60
                elif interval.endswith("h"):
                    sleep_time = int(interval[:-1]) * 3600

                await asyncio.sleep(sleep_time)

            except Exception as e:
                await self.logger.error(f"Error in stream {stream_id}: {str(e)}")
                await asyncio.sleep(5)

    def get_stream_status(self, stream_id: str) -> Optional[dict]:
        """Get status of a specific stream"""
        return self.active_streams.get(stream_id)

    def list_streams(self) -> Dict[str, dict]:
        """List all streams and their status"""
        return self.active_streams

    async def start_stream(self, config: StreamConfig) -> str:
        """
        Start a new market data stream
        1. Create stream ID
        2. Start background task to fetch data
        """
        stream_id = f"binance-{config.symbol.lower()}-{config.interval}"

        self.active_streams[stream_id] = {
            "status": StreamStatus.ACTIVE,
            "config": config.dict(),
            "started_at": datetime.now().isoformat(),
            "last_updated": datetime.now().isoformat(),
        }

        asyncio.create_task(
            self.stream_market_data(config.symbol, config.interval, stream_id)
        )
        return stream_id

    async def stop_stream(self, stream_id: str):
        """Stop a market data stream"""
        if stream_id in self.active_streams:
            self.active_streams[stream_id]["status"] = StreamStatus.STOPPED
            self.active_streams[stream_id]["last_updated"] = datetime.now().isoformat()

    async def pause_stream(self, stream_id: str):
        """Pause a market data stream"""
        if stream_id in self.active_streams:
            self.active_streams[stream_id]["status"] = StreamStatus.PAUSED
            self.active_streams[stream_id]["last_updated"] = datetime.now().isoformat()

    async def resume_stream(self, stream_id: str):
        """Resume a paused market data stream"""
        if stream_id in self.active_streams:
            self.active_streams[stream_id]["status"] = StreamStatus.ACTIVE
            self.active_streams[stream_id]["last_updated"] = datetime.now().isoformat()

    async def shutdown(self):
        """Clean up resources"""
        for stream_id in list(self.active_streams.keys()):
            await self.stop_stream(stream_id)

        if self.kafka_producer:
            # Make sure all messages are delivered before shutting down
            self.kafka_producer.flush()

    def create_consumer(self, topic: str):
        """Create a Kafka consumer for a topic"""
        from confluent_kafka import Consumer

        consumer = Consumer(
            {
                "bootstrap.servers": KAFKA_BOOTSTRAP_SERVERS,
                "group.id": f"consumer-{topic}-{int(time.time())}",
                "auto.offset.reset": "latest",
            }
        )
        consumer.subscribe([topic])
        return consumer
