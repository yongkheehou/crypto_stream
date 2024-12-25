FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    openjdk-17-jre-headless \
    wget \
    zip \
    procps \
    && rm -rf /var/lib/apt/lists/*

# Set up Spark environment
ENV SPARK_VERSION=3.5.3
ENV SPARK_HOME=/opt/spark
ENV SPARK_JARS_DIR=/opt/spark/jars
ENV PATH=$PATH:$SPARK_HOME/bin
ENV SPARK_CLASSPATH=$SPARK_JARS_DIR/*

# Create directories
RUN mkdir -p ${SPARK_HOME} && \
    mkdir -p ${SPARK_JARS_DIR}

# Download and install Spark with correct permissions
RUN wget https://downloads.apache.org/spark/spark-${SPARK_VERSION}/spark-${SPARK_VERSION}-bin-hadoop3.tgz \
    && tar -xzf spark-${SPARK_VERSION}-bin-hadoop3.tgz \
    && mv spark-${SPARK_VERSION}-bin-hadoop3/* ${SPARK_HOME}/ \
    && rm spark-${SPARK_VERSION}-bin-hadoop3.tgz \
    && rm -rf spark-${SPARK_VERSION}-bin-hadoop3 \
    && chmod -R 755 ${SPARK_HOME}

# Install Spark Kafka connector
RUN wget https://repo1.maven.org/maven2/org/apache/spark/spark-sql-kafka-0-10_2.12/${SPARK_VERSION}/spark-sql-kafka-0-10_2.12-${SPARK_VERSION}.jar -P $SPARK_JARS_DIR

WORKDIR /app

# Copy application code
COPY crypto_stream/spark/ ./
COPY crypto_stream/shared/ ./shared/

# Create spark_files directory and zip Python dependencies (only .py files)
RUN mkdir -p /app/spark_files && \
    find . -name "*.py" -print | zip /app/spark_files/spark_deps.zip -@

# Copy and install Python dependencies using Poetry
COPY crypto_stream/spark/pyproject.toml crypto_stream/spark/poetry.lock ./
RUN pip install poetry && \
    poetry config virtualenvs.create false && \
    poetry install --no-dev

# Ensure correct permissions
RUN chmod -R 755 /app

CMD ["poetry", "run", "uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8001"]
