from prometheus_client import CollectorRegistry, Counter, Histogram, Gauge, multiprocess

registry = CollectorRegistry()
multiprocess.MultiProcessCollector(registry)

llm_requests_total = Counter(
    'llm_requests_total',
    "Total LLM requests",
    labelnames=['provider', 'model', 'status'],
    registry=registry
)

llm_request_duration_seconds = Histogram(
    'llm_requests_duration_seconds',
    'LLM request latency',
    ['provider', 'model'],
    registry=registry
)

llm_fallback_total = Counter(
    'llm_fallback_total',
    'LLM fallback activations',
    ['from_provider', 'to_provider'],
    registry=registry
)

circuit_state_changes_total = Counter(
    "llm_circuit_state_changes_total",
    "Circuit breaker state transitions",
    ["new_state"],
    registry=registry
)

llm_circuit_state = Gauge(
    "llm_circuit_state",
    "Current circuit breaker state (0=CLOSED, 1=HALF-OPEN, 2=OPEN)",
    registry=registry
)

rag_vector_search_duration_seconds = Histogram(
    'rag_vector_search_duration_seconds',
    'Vector search duration in seconds',
    ['domain', 'topic'],
    registry=registry
)

rag_pipeline_duration_seconds = Histogram(
    'rag_pipeline_duration_seconds',
    'Pipeline duration',
    ['operation_type', 'domain', 'topic'],
    registry=registry
)

rag_chunks_retrieved = Histogram(
    "rag_chunks_retrieved",
    "Number of chunks retrieved per query",
    ['domain', 'topic'],
    registry=registry
)

celery_tasks_total = Counter(
    'celery_tasks_total',
    'Total tasks finally',
    ['task_name', 'status'],
    registry=registry
)

celery_task_duration_seconds = Histogram(
    'celery_task_duration_seconds',
    'Task duration',
    ['task_name'], 
    registry=registry
)


http_requests_total = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ["method", "endpoint", "status"], 
    registry=registry
)

# ================================
# Embedding Metrics
# ================================

embedding_duration_seconds = Histogram(
    'embedding_generation_duration_seconds',
    'Embedding generation time',
    ['model', 'batch_size'],
    registry=registry
)

embedding_requests_total = Counter(
    'embedding_requests_total',
    'Total embedding requests',
    ['model', 'status'],
    registry=registry
)

# ================================
# Document Ingestion Metrics
# ================================

documents_ingested_total = Counter(
    'documents_ingested_total',
    'Total documents ingested',
    ['source_type', 'status'],  # url/pdf, success/error
    registry=registry
)

documents_chunks_total = Counter(
    'documents_chunks_total',
    'Total chunks created from documents',
    ['source_type'],
    registry=registry
)

# ================================
# Cost & Token Metrics
# ================================

llm_total_cost_dollars = Counter(
    'llm_total_cost_dollars',
    'Total cost spent on LLM calls in dollars',
    ['provider', 'model'],
    registry=registry
)

llm_tokens_used_total = Counter(
    'llm_tokens_used_total',
    'Total tokens used',
    ['provider', 'model', 'token_type'],  # prompt/completion
    registry=registry
)

