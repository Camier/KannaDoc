from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
from fastapi import Response
import time

# --- Metrics Definitions ---

# Counters
files_ingested = Counter(
    'layra_ingestion_files_total',
    'Total files ingested',
    ['status']
)

api_requests_total = Counter(
    'layra_api_requests_total',
    'Total API requests',
    ['method', 'endpoint', 'http_status']
)

# Histograms
api_request_duration = Histogram(
    'layra_api_request_duration_seconds',
    'API request duration in seconds',
    ['method', 'endpoint']
)

# Gauges (Optional: would need periodic updates)
gpu_memory_usage = Gauge(
    'layra_gpu_memory_usage_bytes',
    'GPU memory usage in bytes',
    ['device_id']
)

active_tasks = Gauge(
    'layra_active_tasks',
    'Number of currently processing tasks'
)

# --- Utility Functions ---

def get_metrics():
    """Generates the latest metrics for the /metrics endpoint"""
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)

class PrometheusMiddleware:
    """Simple middleware to instrument FastAPI requests"""
    async def __call__(self, request, call_next):
        method = request.method
        endpoint = request.url.path
        
        start_time = time.time()
        
        response = await call_next(request)
        
        duration = time.time() - start_time
        http_status = response.status_code
        
        # Update metrics
        api_requests_total.labels(method=method, endpoint=endpoint, http_status=http_status).inc()
        api_request_duration.labels(method=method, endpoint=endpoint).observe(duration)
        
        return response
