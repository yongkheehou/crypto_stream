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

```bash
pwd
```
