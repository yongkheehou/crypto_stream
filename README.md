# Crypto Stream

A microservices-based cryptocurrency streaming platform using Apache Kafka, Flink, and Streamlit.

## Services

1. **Logger Service**
   - Centralized logging service
   - Handles log aggregation from all services

2. **Kafka Service**
   - Manages Kafka topics
   - Handles message production/consumption

3. **Flink Service**
   - Manages Apache Flink jobs
   - Handles stream processing

4. **Streamlit Service**
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
> **Note**: Tunneling is required for the ingress to work because Minikube runs all services in a VM that is inaccessible from the host machine.

7. Access services through localhost:
- Logger Service: http://localhost/api/v1/logger
- Flink Service: http://localhost/api/v1/flink
- Kafka Service: http://localhost/api/v1/kafka
- Streamlit Service: http://localhost/api/v1/streamlit

## API Documentation

Each service (e.g. `logger`, `flink`, `kafka`, `streamlit`) provides its own OpenAPI documentation:

- Docs: http://localhost/api/v1/{service}/docs
- ReDoc: http://localhost/api/v1/{service}/redoc
- OpenAPI: http://localhost/api/v1/{service}/openapi.json

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

## Potential Future Improvements for Production

> **Note**: This is an experimental project designed for local development and testing. The deployment is configured to run on a local Kubernetes cluster using Minikube, making it suitable for development and experimentation purposes. For production AWS deployments, additional configurations and security measures would be required.

### AWS Infrastructure as Code
- [ ] Add Terraform configurations for AWS:
  - EKS cluster setup
  - VPC with public/private subnets
  - Security Groups and NACLs
  - IAM roles and policies
  - Route53 for DNS management
  - ACM for SSL certificates
- [ ] Implement different environments (dev, staging, prod)
  - Separate AWS accounts per environment
  - AWS Organizations setup
  - Cross-account access management
- [ ] Set up remote state management
  - S3 backend for Terraform state
  - DynamoDB for state locking
  - State file encryption

### Domain and SSL
- [ ] Configure AWS Route53
  - Register domain through Route53
  - Set up hosted zones
  - Configure DNS records
- [ ] Implement SSL/TLS with AWS Certificate Manager
  - Request public certificates
  - Automatic certificate validation
  - Integration with ALB/NLB
  - Certificate renewal automation

### AWS Security Enhancements
- [ ] Implement AWS authentication and authorization
  - AWS IAM for service roles
  - AWS Secrets Manager for secrets
  - AWS KMS for encryption
- [ ] Add security scanning
  - Amazon Inspector for vulnerability assessment
  - AWS GuardDuty for threat detection
  - AWS Security Hub for security standards
  - AWS Config for compliance rules

### AWS Monitoring and Observability
- [ ] Set up AWS monitoring stack
  - Amazon CloudWatch for metrics and logs instead of separate logging service (current setup)
  - CloudWatch Container Insights
  - CloudWatch Synthetics for endpoint monitoring
  - CloudWatch Alarms for notifications
- [ ] Implement distributed tracing
  - AWS X-Ray integration
  - AWS Distro for OpenTelemetry
  - Service mesh with AWS App Mesh

### CI/CD Pipeline
- [ ] Implement CI/CD
  - GitHub Actions for building containers and pushing to Amazon ECR
  - Amazon ECR for container registry
- [ ] Set up GitOps with AWS
  - GitHub integration
  - Automated deployments to EKS
  - Rollback procedures

### Cost Management
- [ ] Implement AWS cost controls
  - AWS Cost Explorer monitoring
  - AWS Budgets setup
- [ ] Optimize infrastructure costs
  - Auto-scaling policies
  - Spot instances for non-critical workloads
  - Reserved instances planning
  - Resource cleanup automation

## License

MIT
