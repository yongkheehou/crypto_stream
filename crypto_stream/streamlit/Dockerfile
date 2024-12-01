FROM python:3.12-slim

WORKDIR /app

# Install Poetry
RUN pip install poetry

# Copy only the dependencies file
COPY crypto_stream/streamlit/pyproject.toml pyproject.toml

# Configure poetry to not create a virtual environment
RUN poetry config virtualenvs.create false

# Install dependencies
RUN poetry install --no-dev

# Copy service code and shared utilities
COPY crypto_stream/streamlit/ ./
COPY crypto_stream/shared/ ./shared/

# Expose port
EXPOSE 8003

# Run the application
CMD ["poetry", "run", "uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8003"]
