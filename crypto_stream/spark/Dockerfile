FROM python:3.11-slim

RUN apt-get update && apt-get install -y openjdk-17-jre-headless

# Set the working directory
WORKDIR /app

# Install poetry
RUN pip install poetry

# Copy only the dependencies file
COPY crypto_stream/spark/pyproject.toml crypto_stream/spark/poetry.lock ./

# Configure poetry to not create a virtual environment
RUN poetry config virtualenvs.create false

# Install dependencies
RUN poetry install --no-dev

# Copy service code and shared utilities
COPY crypto_stream/spark/ .
COPY crypto_stream/shared/ ./shared/

WORKDIR /app

# Start the Uvicorn server
CMD ["poetry", "run", "uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8001"]
