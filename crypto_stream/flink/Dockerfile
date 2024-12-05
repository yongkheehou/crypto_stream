FROM ghcr.io/lakehq/flink:1.19.0-python3.11

WORKDIR /app

# Install necessary build tools and wget
RUN apt-get update && apt-get install -y gcc wget

# Download Flink Kafka connector and its dependencies
RUN wget https://repo1.maven.org/maven2/org/apache/flink/flink-connector-kafka/3.3.0-1.19/flink-connector-kafka-3.3.0-1.19.jar -P /opt/flink/lib/ && \
    wget https://repo1.maven.org/maven2/org/apache/kafka/kafka-clients/3.6.1/kafka-clients-3.6.1.jar -P /opt/flink/lib/

# Install Poetry
RUN pip install poetry

# Copy only the dependencies file
COPY crypto_stream/flink/pyproject.toml pyproject.toml

# Configure poetry to not create a virtual environment
RUN poetry config virtualenvs.create false

# Install dependencies with Poetry
RUN poetry install --only main

# Copy service code and shared utilities
COPY crypto_stream/flink/ ./
COPY crypto_stream/shared/ ./shared/

# Create directory for Flink dependencies and copy JARs
RUN mkdir -p /opt/flink/plugins/kafka && \
    cp /opt/flink/lib/flink-connector-kafka-*.jar /opt/flink/plugins/kafka/ && \
    cp /opt/flink/lib/kafka-clients-*.jar /opt/flink/plugins/kafka/

# Set environment variable for Flink pipeline JARs with absolute paths
ENV FLINK_PIPELINE_JARS=/opt/flink/plugins/kafka/flink-connector-kafka-3.3.0-1.19.jar:/opt/flink/plugins/kafka/kafka-clients-3.6.1.jar

# Expose port
EXPOSE 8001

# Run the application
CMD ["poetry", "run", "uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8001"]
