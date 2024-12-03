FROM ghcr.io/lakehq/flink:1.19.0-python3.11

WORKDIR /app

# Install necessary build tools
RUN apt-get update && apt-get install -y gcc

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

# Expose port
EXPOSE 8001

# Run the application
CMD ["poetry", "run", "uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8001"]
