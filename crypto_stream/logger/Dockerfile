# Use a slim Python image
FROM python:3.12-slim

# Set the working directory
WORKDIR /app

# Install Poetry
RUN pip install poetry

# Copy only the dependencies file
COPY crypto_stream/logger/pyproject.toml pyproject.toml

# Configure poetry to not create a virtual environment
RUN poetry config virtualenvs.create false

# Install dependencies
RUN poetry install --no-dev

# Create logs directory
RUN mkdir -p /app/logs

# Copy service code
COPY crypto_stream/logger/ ./

# Expose port
EXPOSE 8000

# Run the application
CMD ["poetry", "run", "uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8000"]
