# Crypto Stream

A microservices-based cryptocurrency streaming platform using Apache Flink, Kafka, and Streamlit.

## Services

1. **Flink Service** (Port 8001)
   - Manages Apache Flink jobs
   - Handles stream processing

2. **Kafka Service** (Port 8002)
   - Manages Kafka topics
   - Handles message production/consumption

3. **Streamlit Service** (Port 8003)
   - Manages dashboards
   - Provides visualization interface

## Prerequisites

- Python 3.12+
- Poetry
- Docker
- Minikube
- kubectl

## Setup

1. Install dependencies:
```bash
make install
```

2. Build Docker images:
```bash
make build
```

## Running Locally (Docker Compose)

Start all services using Docker Compose:
```bash
make run-local
```

Services will be available at:
- Flink: http://localhost:8001
- Kafka: http://localhost:8002
- Streamlit: http://localhost:8003

## Running on Kubernetes (Minikube)

1. Start Minikube and setup ingress:
```bash
make k8s-setup
```

2. Deploy services:
```bash
make k8s-deploy
```

3. Get service URLs:
```bash
make k8s-urls
```

## API Documentation

Each service provides its own OpenAPI documentation:

### Flink Service
- Swagger UI: http://localhost:8001/api/v1/flink/docs
- ReDoc: http://localhost:8001/api/v1/flink/redoc
- OpenAPI JSON: http://localhost:8001/api/v1/flink/openapi.json

### Kafka Service
- Swagger UI: http://localhost:8002/api/v1/kafka/docs
- ReDoc: http://localhost:8002/api/v1/kafka/redoc
- OpenAPI JSON: http://localhost:8002/api/v1/kafka/openapi.json

### Streamlit Service
- Swagger UI: http://localhost:8003/api/v1/streamlit/docs
- ReDoc: http://localhost:8003/api/v1/streamlit/redoc
- OpenAPI JSON: http://localhost:8003/api/v1/streamlit/openapi.json

When running on Kubernetes, replace localhost with the appropriate Minikube IP (get it using `minikube ip`).

## Cleanup

1. Stop local services:
```bash
make clean
```

2. Clean Kubernetes deployments:
```bash
make k8s-clean
```

## Development

The project uses Poetry for dependency management and Docker for containerization. Each service is structured as a separate microservice with its own FastAPI server.

### Project Structure
```
crypto_stream/
├── flink/
│   ├── server.py
│   └── Dockerfile
├── kafka/
│   ├── server.py
│   └── Dockerfile
├── streamlit/
│   ├── server.py
│   └── Dockerfile
├── utils/
│   └── logger.py
└── k8s/
    ├── flink-deployment.yaml
    ├── kafka-deployment.yaml
    └── streamlit-deployment.yaml
```

## License

MIT
