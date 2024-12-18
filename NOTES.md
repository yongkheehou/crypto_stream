# Useful Debugging Commands

```bash
kubectl logs -l app=crypto-stream-flink
```

```bash
kubectl logs -f $(kubectl get pods -l app=flink-service -o jsonpath='{.items[0].metadata.name}')
```

- check if the flink service container contains the latest Dockerfile and jar files

```bash
kubectl logs -f $(kubectl get pods -l app=logger-service -o jsonpath='{.items[0].metadata.name}')
```

kubectl logs -f $(kubectl get pods -l app=flink-service -o jsonpath='{.items[0].metadata.name}')

```bash
pwd
```

```bash
kubectl exec -it $(kubectl get pods -l app=kafka-broker -o jsonpath='{.items[0].metadata.name}') -- /usr/bin/kafka-topics --list --bootstrap-server localhost:9092
```

- archive
 && \
    wget https://repo1.maven.org/maven2/org/apache/kafka/kafka-clients/3.3.0/kafka-clients-3.3.0.jar -P /opt/flink/lib/
&& \
    cp /opt/flink/lib/kafka-clients-*.jar /opt/flink/plugins/kafka/

- checking input topics

```bash
kubectl exec -it $(kubectl get pods -l app=kafka-broker -o jsonpath='{.items[0].metadata.name}') -- /usr/bin/kafka-console-consumer --bootstrap-server localhost:9092 --topic binance-btcusdt-1m --from-beginning --max-messages 3
```

```bash
kubectl exec -it $(kubectl get pods -l app=kafka-broker -o jsonpath='{.items[0].metadata.name}') -- /usr/bin/kafka-topics --describe --topic binance-btcusdt-1m --bootstrap-server localhost:9092
```

- checking output topics

```bash
kubectl exec -it $(kubectl get pods -l app=kafka-broker -o jsonpath='{.items[0].metadata.name}') -- /usr/bin/kafka-console-consumer --bootstrap-server localhost:9092 --topic analysis-rsi-binance-btcusdt-1m --from-beginning --max-messages 3
```

```bash
kubectl exec -it $(kubectl get pods -l app=kafka-broker -o jsonpath='{.items[0].metadata.name}') -- /usr/bin/kafka-topics --describe --topic analysis-rsi-binance-btcusdt-1m --bootstrap-server localhost:9092
```
