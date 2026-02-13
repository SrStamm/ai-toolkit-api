#!/bin/bash
docker compose --profile monitoring --profile ollama start || docker compose --profile monitoring --profile ollama up --detach

docker compose logs -f

docker compose --profile monitoring stop
