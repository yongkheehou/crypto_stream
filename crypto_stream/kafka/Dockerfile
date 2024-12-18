FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    gcc \
    libc6-dev \
    librdkafka-dev \
    netcat-traditional \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN pip install poetry

# Copy only the dependencies file
COPY crypto_stream/kafka/pyproject.toml crypto_stream/kafka/poetry.lock ./

# Configure poetry to not create a virtual environment
RUN poetry config virtualenvs.create false

# Install dependencies
RUN poetry install --no-dev

# Copy service code and shared utilities
COPY crypto_stream/kafka/ .
COPY crypto_stream/shared/ ./shared/

# Create directory for Kafka logs
RUN mkdir -p /tmp/kafka-logs && chmod 777 /tmp/kafka-logs

# Environment variables for Kafka client
ENV KAFKA_BOOTSTRAP_SERVERS=kafka-broker:9092

# Expose ports
EXPOSE 8002

# Run the application
CMD ["poetry", "run", "uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8002"]
