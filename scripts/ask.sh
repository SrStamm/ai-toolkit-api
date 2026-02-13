#!/bin/bash
questions=(
  "Como uso profiles en docker"
  "Como funciona merge en docker"
  "Que hace extends en docker?"
  "Como funciona middleware en FastAPI? QUe pasa si uso varios middleware al mismo tiempo?"
  "Como se usa SQL en FastAPI"
  "Que son los workers en celery?"
)

for question in "${questions[@]}"; do
  curl -X POST \
    -H "Content-Type: application/json" \
    -d "{\"text\": \"$question\"}" \
    http://localhost:8000/rag/ask
done
