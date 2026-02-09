import os
from urllib.parse import urlparse
from redis import Redis

redis_host = os.getenv("REDIS_HOST", "localhost")
redis_port = int(os.getenv("REDIS_PORT", "6379"))
redis_db = int(os.getenv("REDIS_DB", "0"))

redis_url = os.getenv("REDIS_URL")

if redis_url:
    parsed = urlparse(redis_url)

    redis_host = parsed.hostname
    redis_port = parsed.port
    # redis_password = parsed.password
    redis_db = int(parsed.path.replace("/", "") or 0)

    redis_client = Redis(
        host=redis_host,
        port=redis_port,
        db=redis_db,
    )
else:
    # fallback local para desarrollo
    redis_client = Redis(
        host=os.getenv("REDIS_HOST", "localhost"),
        port=int(os.getenv("REDIS_PORT", 6379)),
        db=int(os.getenv("REDIS_DB", 0)),
    )
