import httpx
import time
import csv

questions= [
  "Como uso profiles en docker",
  "Como funciona merge en docker",
  "Que hace extends en docker?",
  "Como funciona middleware en FastAPI? QUe pasa si uso varios middleware al mismo tiempo?",
  "Como se usa SQL en FastAPI",
  "Que son los workers en celery?"
]

results = []

with httpx.Client() as client:
    for i in range(5):
        for question in questions:
            data = {"text": question}
            start = time.perf_counter()

            response = client.post(
                "http://localhost:8000/rag/ask",
                json=data,
                timeout=60.0
            )

            end = time.perf_counter()

            latency = end - start

            response_json = response.json()
            metadata = response_json.get("metadata", {})
            provider = metadata.get("provider","unknown")

            results.append({
                "provider": provider,
                "latency": latency,
                "status": response.status_code
            })

with open("benchmark_results.csv", "w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=["provider", "latency", "status"])
    writer.writeheader()
    writer.writerows(results)

print("Benchmark terminado.")

