# ai-toolkit

> **Versión actual:** `v2.2`  
> **Estado:** estable (educacional / experimental, con profiling real)

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

## Estado actual – v2.2 (RAG asincrónico + Observabilidad + Profiling real)

La versión v2.2 consolida el sistema como un backend RAG asincrónico instrumentado profesionalmente, con:

- procesamiento desacoplado vía Celery
- métricas Prometheus completas
- dashboard Grafana operativo
- fallback entre LLM remoto y local
- circuit breaker funcional
- benchmarks comparativos reales
- profiling de throughput y latencia

### Objetivos alcanzados en v2.1 y v2.2

- Instrumentación completa del pipeline RAG
- Métricas específicas por etapa (vector search, LLM, Celery)
- Dashboard en Grafana con:
  - errores por etapa
  - fallbacks LLM
  - latencia promedio y percentiles
  - duración de tasks Celery (P50, P95, P99)
- Comparación empírica:
  - LLM remoto (Mistral)
  - LLM local (Ollama)
- Validación real de circuit breaker
- Test de carga sobre ingestión (40+ documentos técnicos)
- Inserción masiva en Qdrant (4096+ vectores generados vía Sentence Transformers)
- Throughput controlado sin errores ni pérdida de tasks

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

## Benchmarks reales (V2.2)

Se realizaron pruebas controladas para medir:

### LLM remoto (Mistral)
- Latencia promedio: ~2–3s
- Sin errores
- Sin activación de circuit breaker

### LLM local (Ollama)
- Latencia promedio: 20–40s
- CPU-bound
- Validación de fallback automático

### Ingestión masiva (Celery)
- 40+ URLs técnicas
- 4096 puntos vectoriales generados
- Duración promedio de tasks: ~37–44s
- 0 errores
- Sistema estable bajo carga

### Observaciones técnicas

- El sistema se comporta como CPU-bound durante generación de embeddings (Sentence Transformers).
- El aumento de latencia bajo carga es consistente con saturación controlada de CPU.
- No se detectaron:
  - deadlocks
  - pérdida de tasks
  - corrupción de vector store
  - memory leaks evidentes

---

## Validación arquitectónica

La arquitectura fue validada empíricamente mediante:

- tests de carga concurrentes
- profiling de latencia real
- comparación de proveedores LLM
- observabilidad completa con Prometheus + Grafana
- separación real entre API y procesamiento pesado

Este proyecto demuestra:

- diseño desacoplado
- tolerancia a fallos (fallback + circuit breaker)
- instrumentación profesional
- capacidad de escalar horizontalmente (Celery workers)


---

## Funcionalidades del sistema

### Core RAG

- Ingesta de documentos vía URL o archivos
- Chunking específico por tipo de documento
- Strategy Pattern para chunking
- Embeddings locales y remotos con batching
- Re-ranking simple
- Construcción de contexto explícito para el LLM
- Streaming de respuesta
- Metadata por chunk (source, domain, topic, chunk_index)

### Observabilidad y métricas

- Logs estructurados
- Decoradores de latencia por LLM y RAG
- Métricas Prometheus:
- Histogram de latencia por etapa
- Tokens consumidos
- Errores por etapa
- Fallbacks y circuit breaker
- Métricas específicas para Celery:
- Duración de tasks
- Status (success/error)
- Panel básico de estado en Frontend

### Frontend

- Chat estilo RAG
- Inputs opcionales: dominio, topic
- Estado de carga y errores
- Citations por chunk
- Visualización parcial del progreso de tasks

---

## Roadmap de versiones siguientes

### V2.1 – Observabilidad avanzada (completado)

- Histogram por etapa del RAG
- Métricas específicas para Celery
- Dashboard Grafana operativo
- Percentiles P50, P95, P99

### V2.2 – Performance profiling (completado)

- Benchmark LLM remoto vs local
- Validación empírica de circuit breaker
- Medición de throughput Celery
- Inserción masiva en Qdrant
- Análisis CPU-bound vs I/O-bound

### V3.0 – RAG avanzado y evaluación (exploratorio)

> Objetivo: mejorar calidad

- Mejorar filtros semánticos
- Mejor estrategia de metadata
- Hybrid search (BM25 + vector)

### V3.1

- Integrar RAGAS
- Medir faithfulness
- Medir answer relevancy
- Medir context precision

### V3.2

- Implementar versión con LlamaIndex
- Comparar:
  - Latencia
  - Recall
  - Calidad
  - Complejidad de código

### V4.0

> Objetivo: Orquestación

- Tool registry
- Skill abstraction
- Agente determinístico (policy simple)

### V4.1

- Planner básico
- Router entre:
  - RAG
  - Tool
  - Direct LLM


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

