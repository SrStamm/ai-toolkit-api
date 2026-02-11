#!/bin/bash
docker compose --profile monitoring start && docker compose logs -f

docker compose --profile monitoring stop
