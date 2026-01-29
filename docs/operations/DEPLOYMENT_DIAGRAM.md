# Deployment Diagram (Minimal)

## Overview
- Single Docker Compose stack on `layra-net`.
- Only three ports are exposed to the host.

## Topology (Mermaid)

```mermaid
flowchart LR
  user[Users / Browser] -- ":8090" --> nginx[nginx]
  nginx --> frontend[frontend]
  nginx --> backend[backend]

  subgraph Core Services
    backend --> kafka[kafka]
    backend --> mysql[mysql]
    backend --> mongodb[mongodb]
    backend --> redis[redis]
    backend --> minio[minio]
    backend --> milvus[milvus-standalone]
    backend --> modelserver[model-server]
    backend --> sandbox[python-sandbox]
    backend --> unoserver[unoserver]
  end

  subgraph Milvus Dependencies
    milvus --> milvus_etcd[milvus-etcd]
    milvus --> milvus_minio[milvus-minio]
  end

  subgraph Init Jobs
    kafka_init[kafka-init] -.-> kafka
    weights_init[model-weights-init] -.-> modelserver
  end

  subgraph Observability
    prometheus[Prometheus :9090] --> grafana[Grafana :3001]
  end
```

## Exposed Ports (Host)
- `8090` nginx (primary app entrypoint)
- `9090` Prometheus
- `3001` Grafana

## Notes
- All other services are internal to `layra-net`.
- `kafka-init` and `model-weights-init` are one-time init jobs.
