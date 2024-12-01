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
	kubectl apply -f k8s/logger-deployment.yaml
	kubectl apply -f k8s/flink-deployment.yaml
	kubectl apply -f k8s/kafka-deployment.yaml
	kubectl apply -f k8s/streamlit-deployment.yaml

k8s-forward:
	@echo "Port forwarding for Logger service..."
	kubectl port-forward service/logger-service 8000:8000 &
	@echo "Port forwarding for Flink service..."
	kubectl port-forward service/flink-service 8001:8001 &
	@echo "Port forwarding for Kafka service..."
	kubectl port-forward service/kafka-service 8002:8002 &
	@echo "Port forwarding for Streamlit service..."
	kubectl port-forward service/streamlit-service 8003:8003 &
	@echo "Port forwarding setup complete."

k8s-stop-forward:
	@echo "Stopping port forwarding..."
	@pkill -f "kubectl port-forward service/logger-service"
	@pkill -f "kubectl port-forward service/flink-service"
	@pkill -f "kubectl port-forward service/kafka-service"
	@pkill -f "kubectl port-forward service/streamlit-service"
	@echo "Port forwarding stopped."

k8s-urls:
	@echo "Logger service: $$(minikube service logger-service --url)"
	@echo "Flink service: $$(minikube service flink-service --url)"
	@echo "Kafka service: $$(minikube service kafka-service --url)"
	@echo "Streamlit service: $$(minikube service streamlit-service --url)"

k8s-clean:
	kubectl delete -f k8s/logger-deployment.yaml
	kubectl delete -f k8s/flink-deployment.yaml
	kubectl delete -f k8s/kafka-deployment.yaml
	kubectl delete -f k8s/streamlit-deployment.yaml

# Cleanup
clean:
	docker-compose down
	minikube delete
