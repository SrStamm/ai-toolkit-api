#!/bin/bash
docker compose --profile monitoring up --detach && docker compose logs -f
