# Crypto Stream

A microservices-based cryptocurrency streaming platform using Apache Flink, Kafka, and Streamlit.

## Services

1. **Logger Service** (Port 8000)
   - Centralized logging service
   - Handles log aggregation from all services

2. **Flink Service** (Port 8001)
   - Manages Apache Flink jobs
   - Handles stream processing

3. **Kafka Service** (Port 8002)
   - Manages Kafka topics
   - Handles message production/consumption

4. **Streamlit Service** (Port 8003)
   - Manages dashboards
   - Provides visualization interface

## Prerequisites

- Python 3.12+
- Poetry
- Docker Desktop
- Minikube
- kubectl

## Local Development Setup

1. Lock dependencies for all services:
```bash
make lock
```

2. Install dependencies:
```bash
make install
```

3. Build Docker images:
```bash
make build
```

4. Set up Minikube and enable required addons:
```bash
make k8s-setup
```

5. Deploy services to Kubernetes:
```bash
make k8s-deploy
```

6. Start Minikube tunnel (keep this running in a separate terminal):
```bash
make k8s-tunnel
```

7. Access services through localhost:
- Logger Service: http://localhost/api/v1/logger
- Flink Service: http://localhost/api/v1/flink
- Kafka Service: http://localhost/api/v1/kafka
- Streamlit Service: http://localhost/api/v1/streamlit

## API Documentation

Each service provides its own OpenAPI documentation:

- Logger Service:
  - Docs: http://localhost/api/v1/logger/docs
  - ReDoc: http://localhost/api/v1/logger/redoc
  - OpenAPI: http://localhost/api/v1/logger/openapi.json

- Flink Service:
  - Docs: http://localhost/api/v1/flink/docs
  - ReDoc: http://localhost/api/v1/flink/redoc
  - OpenAPI: http://localhost/api/v1/flink/openapi.json

- Kafka Service:
  - Docs: http://localhost/api/v1/kafka/docs
  - ReDoc: http://localhost/api/v1/kafka/redoc
  - OpenAPI: http://localhost/api/v1/kafka/openapi.json

- Streamlit Service:
  - Docs: http://localhost/api/v1/streamlit/docs
  - ReDoc: http://localhost/api/v1/streamlit/redoc
  - OpenAPI: http://localhost/api/v1/streamlit/openapi.json

## Cleanup

1. Delete Kubernetes deployments:
```bash
make k8s-clean
```

2. Clean up Docker containers and Minikube:
```bash
make clean
```

## Project Structure
```
crypto_stream/
├── shared/                 # Shared utilities
│   └── logging_client.py   # Centralized logging client
├── logger/                 # Logger Service
│   ├── Dockerfile
│   ├── pyproject.toml
│   └── server.py
├── flink/                  # Flink Service
│   ├── Dockerfile
│   ├── pyproject.toml
│   └── server.py
├── kafka/                  # Kafka Service
│   ├── Dockerfile
│   ├── pyproject.toml
│   └── server.py
├── streamlit/             # Streamlit Service
│   ├── Dockerfile
│   ├── pyproject.toml
│   └── server.py
├── k8s/                   # Kubernetes Configurations
│   ├── ingress.yaml
│   ├── logger-deployment.yaml
│   ├── flink-deployment.yaml
│   ├── kafka-deployment.yaml
│   └── streamlit-deployment.yaml
└── Makefile              # Build and deployment commands
```

## License

MIT
