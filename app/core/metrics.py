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
