FROM ghcr.io/lakehq/flink:1.19.0-python3.11

WORKDIR /app

# Install necessary build tools and wget
RUN apt-get update && apt-get install -y gcc wget && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Download Flink Kafka connector and its dependencies
RUN wget https://repo1.maven.org/maven2/org/apache/flink/flink-connector-kafka/3.3.0-1.19/flink-connector-kafka-3.3.0-1.19.jar -P /opt/flink/lib/ && \
    wget https://repo1.maven.org/maven2/org/apache/kafka/kafka-clients/3.3.2/kafka-clients-3.3.2.jar -P /opt/flink/lib/

# Install Poetry
RUN pip install poetry

RUN pip install --no-cache-dir apache-flink poetry

# Copy dependency files
COPY crypto_stream/flink/pyproject.toml crypto_stream/flink/poetry.lock ./

# Configure Poetry to not create virtual environments
RUN poetry config virtualenvs.create false

# Install Python dependencies
RUN poetry install --only main

# Copy application code
COPY crypto_stream/flink/ ./
COPY crypto_stream/shared/ ./shared/

# Create directory for Flink dependencies and copy JARs
RUN mkdir -p /opt/flink/plugins/kafka && \
    cp /opt/flink/lib/flink-connector-kafka-*.jar /opt/flink/plugins/kafka/ && \
    cp /opt/flink/lib/kafka-clients-*.jar /opt/flink/plugins/kafka/

# Set environment variable for Flink pipeline JARs with absolute paths
ENV FLINK_PIPELINE_JARS=/opt/flink/plugins/kafka/flink-connector-kafka-3.3.0-1.19.jar:/opt/flink/plugins/kafka/kafka-clients-3.6.1.jar
ENV FLINK_PYTHON_EXECUTABLE=/usr/bin/python3

# Expose application port
EXPOSE 8001

# Run the application
CMD ["poetry", "run", "uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8001"]
