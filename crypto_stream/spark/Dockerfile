FROM python:3.11-slim

RUN apt-get update
RUN apt-get install -y openjdk-11-jdk-headless

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

CMD ["poetry", "run", "uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8001"]
