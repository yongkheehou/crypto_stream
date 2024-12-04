.PHONY: install build run-local run-k8s clean

lock:
	cd crypto_stream/logger && poetry lock
	cd crypto_stream/flink && poetry lock
	cd crypto_stream/kafka && poetry lock
	cd crypto_stream/streamlit && poetry lock

# Development
install:
	cd crypto_stream/logger && poetry install
	cd crypto_stream/flink && poetry install
	cd crypto_stream/kafka && poetry install
	cd crypto_stream/streamlit && poetry install

# Docker commands
build:
	docker build -t crypto-stream-logger:latest -f crypto_stream/logger/Dockerfile .
	docker build -t crypto-stream-flink:latest -f crypto_stream/flink/Dockerfile .
	docker build -t crypto-stream-kafka:latest -f crypto_stream/kafka/Dockerfile .
	docker build -t crypto-stream-streamlit:latest -f crypto_stream/streamlit/Dockerfile .

run-local:
	docker-compose up --build

# Kubernetes commands
k8s-setup:
	minikube start
	minikube addons enable ingress

k8s-deploy: build
	minikube image load crypto-stream-logger:latest
	minikube image load crypto-stream-flink:latest
	minikube image load crypto-stream-kafka:latest
	minikube image load crypto-stream-streamlit:latest
	@echo "Deploying Kafka broker and Zookeeper..."
	kubectl apply -f crypto_stream/k8s/kafka-broker.yaml
	@echo "Deploying Logger service..."
	kubectl apply -f crypto_stream/k8s/logger-deployment.yaml
	@echo "Deploying Flink service..."
	kubectl apply -f crypto_stream/k8s/flink-deployment.yaml
	@echo "Deploying Kafka service..."
	kubectl apply -f crypto_stream/k8s/kafka-deployment.yaml
	@echo "Deploying Streamlit service..."
	kubectl apply -f crypto_stream/k8s/streamlit-deployment.yaml
	@echo "Deploying Ingress..."
	kubectl apply -f crypto_stream/k8s/ingress.yaml

k8s-tunnel:
	minikube tunnel

k8s-pods:
	kubectl get pods

k8s-urls:
	@echo "Ingress IP: $$(minikube ip)"
	@echo ""
	@echo "Available endpoints:"
	@echo "- Health check:   http://$$(minikube ip)/health"
	@echo "- Logger API:     http://$$(minikube ip)/api/v1/logger"
	@echo "- Flink API:      http://$$(minikube ip)/api/v1/flink"
	@echo "- Kafka API:      http://$$(minikube ip)/api/v1/kafka"
	@echo "- Streamlit API:  http://$$(minikube ip)/api/v1/streamlit"

k8s-clean:
	kubectl delete -f crypto_stream/k8s/ingress.yaml
	kubectl delete -f crypto_stream/k8s/logger-deployment.yaml
	kubectl delete -f crypto_stream/k8s/flink-deployment.yaml
	kubectl delete -f crypto_stream/k8s/kafka-deployment.yaml
	kubectl delete -f crypto_stream/k8s/streamlit-deployment.yaml
	kubectl delete -f crypto_stream/k8s/kafka-broker.yaml

# Cleanup
clean:
	docker-compose down
	minikube delete
