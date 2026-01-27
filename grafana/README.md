# Grafana Dashboards for Layra

This directory contains pre-configured Grafana dashboards for monitoring the Layra application.

## Directory Structure

```
grafana/
├── dashboards/              # Dashboard JSON definitions
│   ├── system-overview.json
│   ├── api-performance.json
│   ├── database-metrics.json
│   ├── kafka-metrics.json
│   └── rag-pipeline.json
└── provisioning/           # Grafana provisioning configuration
    ├── datasources/
    │   └── datasources.yml
    └── dashboards/
        └── dashboards.yml
```

## Dashboards

### 1. System Overview
- **UID:** `layra-system-overview`
- **Tags:** layra, system, infrastructure
- **Refresh:** 30 seconds
- **Panels:**
  - CPU Usage %
  - Memory Usage %
  - Memory Usage by Container
  - Network I/O
  - Disk Usage %
  - Disk I/O
  - Service Status

### 2. API Performance
- **UID:** `layra-api-performance`
- **Tags:** layra, api, performance
- **Refresh:** 15 seconds
- **Panels:**
  - API Latency (percentiles)
  - Request Rate
  - Error Rate by Status Code
  - Request Count by Status
  - Database Connection Pool Usage
  - Circuit Breaker Status
  - Top Endpoints by Request Volume
- **Variables:**
  - Endpoint (multi-select)

### 3. Database Metrics
- **UID:** `layra-database-metrics`
- **Tags:** layra, database, storage
- **Refresh:** 30 seconds
- **Panels:**
  - MySQL: Connection Pool, Query Latency, Query Rate
  - MongoDB: Query Latency, Operation Rate
  - Redis: Command Latency, Operations Rate
  - Milvus: Operation Latency, Collection Stats

### 4. Kafka Metrics
- **UID:** `layra-kafka-metrics`
- **Tags:** layra, kafka, messaging
- **Refresh:** 15 seconds
- **Panels:**
  - Consumer Lag
  - Message Throughput
  - Network I/O
  - Request Latency
  - Request Errors
  - Consumer Rebalances
  - Broker Status
  - Messages Produced by Topic
- **Variables:**
  - Topic (multi-select)
  - Consumer Group (multi-select)

### 5. RAG Pipeline
- **UID:** `layra-rag-pipeline`
- **Tags:** layra, rag, ai, pipeline
- **Refresh:** 15 seconds
- **Panels:**
  - Embedding Generation Latency
  - Vector Database Query Latency
  - RAG Operation Rate
  - RAG Error Rate
  - Average Documents Retrieved
  - File Processing Rate
  - LLM Request Latency
  - LLM Error Rate
  - LLM Request Rate by Model
  - End-to-End RAG Latency
  - Queries by Collection
- **Variables:**
  - LLM Model (multi-select)
  - Collection (multi-select)

## Provisioning

Dashboards are automatically provisioned when Grafana starts using the configuration in `provisioning/`.

### Datasources (`provisioning/datasources/datasources.yml`)
- Prometheus datasource at `http://prometheus:9090`
- 15-second time interval
- 60-second query timeout

### Dashboard Provider (`provisioning/dashboards/dashboards.yml`)
- Provider name: "Layra Dashboards"
- Folder: "Layra"
- Update interval: 30 seconds
- UI updates allowed

## Usage

### Automatic Provisioning
Dashboards are automatically loaded when you start Grafana via Docker Compose:

```bash
docker-compose up -d grafana
```

Access Grafana at `http://localhost:3001` with credentials:
- Username: `admin`
- Password: `${GRAFANA_PASSWORD:-admin}`

### Manual Import
If you need to manually import a dashboard:

1. Navigate to Grafana UI
2. Go to Dashboards > Import
3. Upload the JSON file from `dashboards/`
4. Select Prometheus as datasource
5. Click Import

### Exporting Modified Dashboards
After customizing a dashboard in the UI:

1. Go to the dashboard
2. Click Share > Export
3. Select "Export for sharing externally"
4. Save to JSON file in `dashboards/` directory

## Customization

### Modifying Dashboards
Edit the JSON files in `dashboards/` to customize:
- Panel queries and visualizations
- Layout and grid positions
- Thresholds and alerts
- Variables and filters

### Adding New Dashboards
1. Create dashboard in Grafana UI
2. Export as JSON
3. Save to `dashboards/` directory
4. Dashboard will be automatically provisioned

### Custom Queries
All dashboards use Prometheus queries. Reference metrics:
- Backend: `http://localhost:8090/api/v1/health/metrics`
- Prometheus UI: `http://localhost:9090`

## Metrics Reference

### API Metrics
- `layra_api_requests_total` - Total API requests
- `layra_api_request_duration_seconds` - Request latency histogram
- `layra_db_connections_active` - Active DB connections
- `layra_db_connections_max` - Max DB connections

### Kafka Metrics
- `layra_kafka_consumer_lag` - Consumer lag
- `layra_kafka_producer_records_total` - Records produced
- `layra_kafka_consumer_records_total` - Records consumed

### RAG Metrics
- `layra_embedding_requests_total` - Embedding requests
- `layra_embedding_request_duration_seconds` - Embedding latency
- `layra_vectordb_queries_total` - Vector DB queries
- `layra_llm_requests_total` - LLM requests

## Troubleshooting

### Dashboards Not Loading
```bash
# Check Grafana logs
docker logs layra-grafana

# Verify provisioning files are mounted
docker exec layra-grafana ls -la /etc/grafana/provisioning
```

### No Data in Panels
```bash
# Check Prometheus targets
curl http://localhost:9090/api/v1/targets

# Verify backend metrics
curl http://localhost:8090/api/v1/health/metrics
```

### Variables Not Populating
```bash
# Test label values query
curl 'http://localhost:9090/api/v1/label/__name__/values'
```

## Best Practices

1. **Time Ranges**: Use appropriate time ranges for different metrics
   - Real-time: Last 5-15 minutes (API latency, errors)
   - Trends: Last 1-6 hours (throughput, resource usage)
   - Patterns: Last 24-7 days (capacity planning)

2. **Alert Thresholds**: Configure alert thresholds based on:
   - Baseline metrics from normal operation
   - SLA requirements
   - Resource limits

3. **Dashboard Maintenance**:
   - Review and update dashboards monthly
   - Remove unused panels
   - Add new metrics as features are added

4. **Performance**:
   - Use `rate()` for counters
   - Use `histogram_quantile()` for latency
   - Avoid complex subqueries when possible

## References

- [Grafana Documentation](https://grafana.com/docs/)
- [Prometheus Query Language](https://prometheus.io/docs/prometheus/latest/querying/basics/)
- [Layra Monitoring Guide](../../README.md#monitoring)
