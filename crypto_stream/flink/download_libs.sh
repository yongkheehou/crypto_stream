mkdir -p ./lib

curl -o ./lib/flink-connector-kafka-3.3.0-1.19.jar https://repo1.maven.org/maven2/org/apache/flink/flink-connector-kafka/3.3.0-1.19/flink-connector-kafka-3.3.0-1.19.jar
curl -o ./lib/kafka-clients-3.3.0.jar https://repo1.maven.org/maven2/org/apache/kafka/kafka-clients/3.3.0/kafka-clients-3.3.0.jar

echo "Libs downloaded successfully"
