from prometheus_client import Counter, Histogram

llm_requests_total = Counter(
    'llm_request_total',
    "Total LLM requests",
    labelnames=['provider', 'model', 'status']
)

llm_request_duration_seconds = Histogram(
    'llm_request_duration_seconds',
    'LLM request latency',
    ['provider', 'model']
)

llm_fallback_total = Counter(
    'llm_fallback_total',
    'LLM fallback activations',
    ['from_provider', 'to_provider']
)

circuit_state_changes_total = Counter(
    "llm_circuit_state_changes_total",
    "Circuit breaker state transitions",
    ["new_state"],
)

rag_vector_search_duration_seconds = Histogram(
    'rag_vector_search_duration_seconds',
    'Vector search duration in seconds'
)

rag_pipeline_duration_seconds = Histogram(
    'rag_pipeline_duration_seconds',
    'Pipeline duration'
)

rag_chunks_retrieved = Histogram(
    "rag_chunks_retrieved",
    "Number of chunks retrieved per query"
)

celery_tasks_total = Counter(
    'celery_tasks_total',
    'Total tasks finally',
    ['task_name', 'status']
)

celery_task_duration_seconds = Histogram(
    'celery_task_duration_seconds',
    'Task duration',
    ['task_name']
)

