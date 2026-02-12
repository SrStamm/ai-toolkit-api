#!/bin/bash
docker compose --profile monitoring start || docker compose --profile monitoring up --detach

docker compose logs -f

docker compose --profile monitoring stop
