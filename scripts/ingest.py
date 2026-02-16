import httpx

sources = [
    "https://docs.docker.com/reference/compose-file/profiles/",
    "https://docs.docker.com/compose/how-tos/multiple-compose-files/merge/",
    "https://docs.docker.com/compose/how-tos/multiple-compose-files/extends/",
    "https://fastapi.tiangolo.com/tutorial/middleware/",
    "https://fastapi.tiangolo.com/tutorial/cors/",
    "https://fastapi.tiangolo.com/tutorial/sql-databases/",
    "https://fastapi.tiangolo.com/tutorial/bigger-applications/",
    "https://fastapi.tiangolo.com/tutorial/background-tasks/",
    "https://docs.celeryq.dev/en/stable/userguide/application.html",
    "https://docs.celeryq.dev/en/stable/userguide/tasks.html",
    "https://docs.celeryq.dev/en/stable/userguide/calling.html",
    "https://docs.celeryq.dev/en/stable/userguide/workers.html",
    "https://docs.celeryq.dev/en/stable/userguide/daemonizing.html",
    "https://redis.io/docs/latest/develop/get-started/data-store/",
    "https://redis.io/docs/latest/develop/get-started/document-database/",
    "https://redis.io/docs/latest/develop/get-started/vector-database/",
    "https://redis.io/docs/latest/develop/get-started/rag/",
    "https://redis.io/docs/latest/develop/get-started/redis-in-ai/",
    "https://redis.io/docs/latest/develop/tools/cli/",
    "https://redis.io/docs/latest/develop/tools/insight/",
    "https://redis.io/docs/latest/develop/tools/redis-for-vscode/",
    "https://redis.io/docs/latest/develop/using-commands/keyspace/"
    "https://redis.io/docs/latest/develop/using-commands/pipelining/",
    "https://redis.io/docs/latest/develop/using-commands/transactions/",
    "https://redis.io/docs/latest/develop/using-commands/multi-key-operations/",
    "https://redis.io/docs/latest/develop/data-types/compare-data-types/",
    "https://redis.io/docs/latest/develop/data-types/strings/",
    "https://redis.io/docs/latest/develop/data-types/json/",
    "https://redis.io/docs/latest/develop/data-types/lists/",
    "https://redis.io/docs/latest/develop/data-types/sets/",
    "https://redis.io/docs/latest/develop/data-types/hashes/",
    "https://redis.io/docs/latest/develop/data-types/sorted-sets/",
    "https://redis.io/docs/latest/develop/data-types/vector-sets/",
    "https://www.python-httpx.org/quickstart/",
    "https://www.python-httpx.org/advanced/clients/",
    "https://www.python-httpx.org/advanced/authentication/",
    "https://www.python-httpx.org/advanced/ssl/",
]


with httpx.Client() as client:
    for source in sources:
        data = {"url": source}

        response = client.post(
            "http://localhost:8000/rag/ingest/job",
            json=data,
            timeout=60.0
        )

print("Benchmark terminado.")

