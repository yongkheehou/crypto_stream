FROM flink:1.19.0

# Update packages and install Python 3.11 and required tools
RUN apt-get update && \
    apt-get install -y python3.11 python3.11-dev python3.11-distutils curl && \
    rm -rf /var/lib/apt/lists/*

# Install pip for Python 3.11 using get-pip.py
RUN curl https://bootstrap.pypa.io/get-pip.py -o get-pip.py && \
    python3.11 get-pip.py && \
    rm get-pip.py

# Ensure the `python` and `pip` commands point to Python 3.11
RUN ln -sf /usr/bin/python3.11 /usr/bin/python && \
    ln -sf /usr/local/bin/pip /usr/bin/pip && \
    python -m pip install --upgrade pip setuptools wheel

# Install Java & updates
RUN apt-get update && \
    apt-get install -y openjdk-21-jdk ant && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

ENV JAVA_HOME=/usr/lib/jvm/java-21-openjdk-arm64

WORKDIR /opt/flink

# Install necessary build tools and wget
RUN apt-get update && apt-get install -y gcc wget && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN pip install --no-cache-dir poetry

# Copy dependency files
COPY crypto_stream/flink/pyproject.toml crypto_stream/flink/poetry.lock ./

# Configure Poetry not to use a virtualenv
RUN poetry config virtualenvs.create false

# Install Python dependencies via Poetry
RUN poetry install

RUN python -c "import pyflink"

COPY crypto_stream/flink/download_libs.sh ./
RUN chmod +x ./download_libs.sh && ./download_libs.sh

ENV FLINK_PIPELINE_JARS=/opt/flink/lib/flink-connector-kafka-3.3.0-1.19.jar:/opt/flink/lib/kafka-clients-3.3.0.jar

# Copy application code
COPY crypto_stream/flink/ ./
COPY crypto_stream/shared/ ./shared/

EXPOSE 8001

CMD ["poetry", "run", "uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8001"]
