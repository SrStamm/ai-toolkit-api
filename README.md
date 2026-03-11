# ai-toolkit

> **Versión actual:** `v3.2`  
> **Estado:** estable (educacional / experimental, con evaluación RAGAS y comparación LlamaIndex)

**Herramientas de IA para backend (FastAPI)**

`ai-toolkit` es una API educativa y experimental construida en FastAPI para explorar cómo diseñar sistemas backend con LLMs de forma profesional, poniendo foco en:

- control explícito del comportamiento del modelo
- validación estricta del output
- manejo consciente de errores y retries
- arquitectura desacoplada y extensible
- observabilidad y métricas

> 🎯 Objetivo del proyecto  
> No es un producto final, sino un laboratorio backend para demostrar criterio arquitectónico real en sistemas con IA: cómo se diseñan, cómo evolucionan y cómo se preparan para un entorno enterprise-like.

---

## Estado actual – v3.2 (LlamaIndex + Evaluación RAGAS)

La versión v3.2 introduce una implementación paralela del pipeline RAG usando LlamaIndex, evaluada empíricamente contra el pipeline manual con RAGAS. El objetivo no fue reemplazar el pipeline existente, sino comparar ambos enfoques con métricas reales y extraer conclusiones concretas.

### Qué se implementó

- Pipeline RAG completo con LlamaIndex (ingesta, indexing, retrieval, reranking)
- Hybrid search con SPLADE (sparse + dense vectors) sobre Qdrant
- Reranking con `cross-encoder/mmarco-mMiniLMv2-L12-H384-v1`
- Integración con el `LLMClient` existente (mantiene circuit breaker y cost tracking)
- Traducción automática de queries al inglés antes del retrieval para documentos en inglés
- Evaluación con RAGAS sobre dos datasets: FastAPI docs y un libro técnico en inglés

### Arquitectura v3.2 (LlamaIndex)

```ascii
Cliente / Frontend
↓
FastAPI — /llama/ask-custom
↓
LlamaIndexOrchestrator
  - Traducción de query (español → inglés)
  - Retrieval hybrid (SPLADE + dense, top_k=10)
  - Reranking (cross-encoder, top_n=5)
  - Construcción de contexto
  - LLMClient.generate_content()
↓
QueryResponse (answer + citations + metadata)
```

### Resultados RAGAS — Pipeline manual vs LlamaIndex

| Métrica            | FastAPI (manual) | FastAPI (LlamaIndex) | AI Eng (manual) | AI Eng (LlamaIndex) |
| ------------------ | ---------------- | -------------------- | --------------- | ------------------- |
| Faithfulness       | 0.933            | **1.000**            | 0.575           | **1.000**           |
| Answer Correctness | 0.612            | **0.627**            | 0.273           | **0.489**           |
| Context Precision  | **0.666**        | 0.500                | 0.249           | 0.250               |

### Conclusiones de la comparación

**LlamaIndex supera al pipeline manual en faithfulness y answer correctness** en ambos datasets. La mejora es especialmente notable en el libro técnico en inglés, donde answer correctness casi se duplicó (0.27 → 0.49).

**Context precision se mantiene similar**, con ligera ventaja del pipeline manual en FastAPI. Esto se debe a que las preguntas del dataset del libro son conceptuales y transversales — la información relevante está distribuida en múltiples chunks, lo que limita estructuralmente esta métrica independientemente del sistema de retrieval.

**El problema de cross-lingual retrieval fue determinante.** El libro está en inglés y las queries en español. Agregar una etapa de traducción automática antes del retrieval fue el cambio con mayor impacto: answer correctness del libro pasó de 0.26 a 0.49. Sin esto, el embedding model (`all-MiniLM-L6-v2`) no matcheaba correctamente queries en español con chunks en inglés.

### Limitaciones del dataset de evaluación

El dataset de evaluación del libro tiene preguntas conceptuales amplias ("lista los desafíos de despliegue") cuyas respuestas están distribuidas a lo largo de 500+ páginas. Ningún sistema RAG con top_k razonable puede cubrir exhaustivamente este tipo de preguntas. Para una evaluación más justa se recomienda usar preguntas localizadas, con respuesta contenida en uno o dos chunks.

---

## Estado anterior – v2.2 (RAG asincrónico + Observabilidad + Profiling)

La versión v2.2 consolida el sistema como un backend RAG asincrónico instrumentado profesionalmente, con:

- procesamiento desacoplado vía Celery
- métricas Prometheus completas
- dashboard Grafana operativo
- fallback entre LLM remoto y local
- circuit breaker funcional
- benchmarks comparativos reales
- profiling de throughput y latencia

### Arquitectura v2.2

```ascii
Cliente / Frontend
↓
FastAPI (API layer)
  - Validación
  - Creación de job_id
  - Dispatch de tareas a Celery
↓
Broker / Backend (Redis)
↓
Celery Worker
  - Extracción
  - Limpieza
  - Chunking
  - Embeddings
  - Inserción en Vector Store
  - Actualización de estado en Redis
↓
Respuesta a Frontend vía job_id
```

### Benchmarks reales (V2.2)

**LLM remoto (Mistral):** latencia promedio ~2–3s, sin errores, sin activación de circuit breaker.

**LLM local (Ollama):** latencia promedio 20–40s, CPU-bound, validación de fallback automático.

**Ingestión masiva (Celery):** 40+ URLs técnicas, 4096 puntos vectoriales generados, duración promedio de tasks ~37–44s, 0 errores, sistema estable bajo carga.

---

## Funcionalidades del sistema

### Core RAG (pipeline manual)

- Ingesta de documentos vía URL o archivos
- Chunking específico por tipo de documento con Strategy Pattern
- Embeddings locales y remotos con batching
- Hybrid search (sparse + dense)
- Re-ranking con cross-encoder
- Construcción de contexto explícito para el LLM
- Streaming de respuesta
- Metadata por chunk (source, domain, topic, chunk_index)

### Pipeline LlamaIndex (v3.2)

- Ingesta de PDFs y HTML vía LlamaIndex
- Hybrid search con SPLADE sobre Qdrant
- Reranking con SentenceTransformerRerank
- Traducción automática de queries para documentos en inglés
- Integración con LLMClient existente (mantiene circuit breaker y cost tracking)
- Evaluación con RAGAS (faithfulness, answer correctness, context precision)

### Observabilidad y métricas

- Logs estructurados
- Decoradores de latencia por LLM y RAG
- Métricas Prometheus: histogram de latencia por etapa, tokens consumidos, errores, fallbacks y circuit breaker
- Métricas Celery: duración de tasks, status
- Dashboard Grafana con percentiles P50, P95, P99

### Frontend

- Chat estilo RAG
- Inputs opcionales: dominio, topic
- Estado de carga y errores
- Citations por chunk
- Visualización parcial del progreso de tasks

---

## Roadmap

### Completado

- v2.1 — Observabilidad avanzada (histograms, Grafana, percentiles)
- v2.2 — Performance profiling (benchmark LLM remoto vs local, throughput Celery)
- v3.0 — RAG avanzado (hybrid search BM25 + vector, metadata strategy)
- v3.1 — Evaluación con RAGAS (faithfulness, answer correctness, context precision)
- v3.2 — Implementación con LlamaIndex y comparación empírica contra pipeline manual

### Próximo

### V4.0 — Agentes y orquestación

> Objetivo: introducir razonamiento y uso de herramientas

- Tool registry
- Skill abstraction
- Agente determinístico con policy simple
- Router entre RAG, Tool y Direct LLM

### V4.1 — Planner

- Planner básico
- Orquestación multi-step

---

## Filosofía de diseño

- Transparencia del flujo: cada paso del pipeline es trazable
- Separación de responsabilidades: API, lógica de negocio y proveedores desacoplados
- Control del riesgo: retries, errores y fallback explícitos
- Intercambiabilidad de componentes: LLM, embeddings y vector stores reemplazables sin afectar el core

---

## Instalación local rápida

```bash
git clone https://github.com/SrStamm/ai-toolkit.git
cd ai-toolkit
docker-compose up --build
```
