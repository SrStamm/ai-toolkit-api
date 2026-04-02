"""
Cliente Redis con soporte para settings centralizados.
"""

from redis import Redis
from .settings import get_settings


def get_redis_client() -> Redis:
    """
    Get Redis client using centralized settings.

    Supports both REDIS_URL and individual REDIS_HOST/REDIS_PORT env vars
    for backwards compatibility.
    """
    settings = get_settings()

    if settings.redis_url:
        # Use full URL if provided
        return Redis.from_url(settings.redis_url)

    # Fallback to individual settings
    return Redis(
        host=settings.redis_host,
        port=settings.redis_port,
        db=settings.redis_db,
    )


# Singleton instance
_redis_client: Redis | None = None


def get_redis() -> Redis:
    """Get or create Redis client singleton."""
    global _redis_client
    if _redis_client is None:
        _redis_client = get_redis_client()
    return _redis_client


# Alias for backwards compatibility
redis_client = get_redis()
