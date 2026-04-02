"""
Excepciones específicas para el dominio de LLM.

Permite distinguir entre errores transitorios (que pueden hacer retry)
y errores permanentes (que no tienen sentido reintentar).
"""


class LLMError(Exception):
    """Base exception for all LLM-related errors."""

    pass


class RetryableError(LLMError):
    """Errores transitorios que pueden reintentar (timeouts, network issues)."""

    pass


class PermanentError(LLMError):
    """Errores permanentes que no tienen sentido reintentar."""

    pass


# Retryable errors
class NetworkTimeoutError(RetryableError):
    """Network timeout occurred."""

    pass


class ConnectionError(RetryableError):
    """Failed to connect to LLM provider."""

    pass


# Alias for backwards compatibility
LLMConnectionError = ConnectionError


class RateLimitError(RetryableError):
    """Rate limit exceeded."""

    pass


class ServiceUnavailableError(RetryableError):
    """LLM service is temporarily unavailable."""

    pass


# Permanent errors
class InvalidAPIKeyError(PermanentError):
    """Invalid or missing API key."""

    pass


class ModelNotFoundError(PermanentError):
    """Requested model does not exist."""

    pass


class InvalidRequestError(PermanentError):
    """Malformed request to LLM provider."""

    pass


class ContextLengthExceededError(PermanentError):
    """Prompt exceeds model's context length."""

    pass


class ContentFilteredError(PermanentError):
    """Content was filtered by the provider."""

    pass


class StructuredOutputError(LLMError):
    """Raised when structured output parsing fails after max retries."""

    pass


# Vector store errors
class VectorStoreError(LLMError):
    """Base exception for vector store operations."""

    pass


class CollectionNotFoundError(VectorStoreError):
    """Requested collection does not exist."""

    pass


class EmbeddingError(VectorStoreError):
    """Error generating embeddings."""

    pass


class QueryError(VectorStoreError):
    """Error during vector query."""

    pass


# RAG errors
class ChunkingError(VectorStoreError):
    """Error during document chunking."""

    pass


class EmptySourceContentError(VectorStoreError):
    """Source content is empty after extraction."""

    pass


class SourceException(VectorStoreError):
    """Error extracting content from source."""

    pass


# Session errors
class SessionError(LLMError):
    """Base exception for session-related errors."""

    pass


class SessionNotFoundError(SessionError):
    """Requested session does not exist."""

    pass


class SessionExpiredError(SessionError):
    """Session has expired."""

    pass


# Tool errors
class ToolError(LLMError):
    """Base exception for tool-related errors."""

    pass


class ToolNotFoundError(ToolError):
    """Requested tool does not exist."""

    pass


class ToolExecutionError(ToolError):
    """Error executing a tool."""

    pass


class ToolValidationError(ToolError):
    """Invalid tool parameters."""

    pass
