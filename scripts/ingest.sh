#!/bin/bash
urls=(
  "https://docs.docker.com/reference/compose-file/profiles/"
  "https://docs.docker.com/compose/how-tos/multiple-compose-files/merge/"
  "https://docs.docker.com/compose/how-tos/multiple-compose-files/extends/"
  "https://fastapi.tiangolo.com/tutorial/middleware/"
  "https://fastapi.tiangolo.com/tutorial/cors/"
  "https://fastapi.tiangolo.com/tutorial/sql-databases/"
  "https://fastapi.tiangolo.com/tutorial/bigger-applications/"
  "https://fastapi.tiangolo.com/tutorial/background-tasks/"
  "https://docs.celeryq.dev/en/stable/userguide/application.html"
  "https://docs.celeryq.dev/en/stable/userguide/tasks.html"
  "https://docs.celeryq.dev/en/stable/userguide/calling.html"
  "https://docs.celeryq.dev/en/stable/userguide/workers.html"
  "https://docs.celeryq.dev/en/stable/userguide/daemonizing.html"
)

for url in "${urls[@]}"; do
  curl -X POST \
    -H "Content-Type: application/json" \
    -d "{\"url\": \"$url\", \"domain\": \"docker_fastapi\", \"topic\": \"learning\"}" \
    http://localhost:8000/rag/ingest/job
done
