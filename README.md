# ai-toolkit

> **Versión actual:** `v3.0`  
> **Estado:** estable (educacional / experimental, con RAG avanzado)

**Herramientas de IA para backend (FastAPI)**

`ai-toolkit` es una API educativa y experimental construida en FastAPI para explorar cómo diseñar sistemas backend con LLMs de forma profesional, poniendo foco en:

- control explícito del comportamiento del modelo
- validación estricta del output
- manejo consciente de errores y retries
- arquitectura desacoplada y extensible
- observabilidad y métricas
- calidad del pipeline RAG

> 🎯 Objetivo del proyecto
> No es un producto final, sino un laboratorio backend para demostrar criterio arquitectónico real en sistemas con IA: cómo se diseñan, cómo evolucionan y cómo se preparan para un entorno enterprise-like.

---

## Estado actual – v3.0 (RAG avanzado: Hybrid Search + Chunking semántico)

La versión v3.0 extiende la base sólida de v2.2 hacia la mejora de **calidad del pipeline RAG**, introduciendo búsqueda híbrida real y una estrategia de chunking y metadata significativamente más precisa.

### Qué cambió respecto a v2.2

**Hybrid Search (sparse + dense)**

La búsqueda vectorial ahora combina dos vectores por chunk:

- `dense`: embeddings semánticos vía Sentence Transformers
- `sparse`: vectores TF-IDF/BM25 para matching léxico exacto

La fusión se realiza con **RRF (Reciprocal Rank Fusion)** directamente en Qdrant, sin post-procesamiento manual. Esto mejora el recall en queries con términos técnicos específicos donde la búsqueda semántica sola falla.

**Chunking semántico por tipo de documento**

Cada tipo de documento tiene su propia estrategia de chunking, ahora con detección de estructura y metadata enriquecida:

- `PDFCleaner`: limpieza profunda de artefactos (guiones rotos, líneas de índice, TOC), detección de headings por título case y numeración, overlap consistente entre chunks
- `HTMLCleaner`: segmentación por `h2`/`h3`, sección como anchor semántico
- `MarkdownCleaner`: split por `#`/`##`/`###`, heading preservado en texto y metadata

**Metadata enriquecida por chunk**

Todos los chunks ahora incluyen el campo `section`, que refleja el heading o sección del documento al que pertenece el chunk. Esto permite al LLM contextualizar mejor la respuesta y al reranker priorizar chunks con mayor relevancia estructural.

```json
{
  "text": "...",
  "section": "Hybrid Search and Retrieval",
  "source": "AI Engineering.pdf",
  "domain": "libros",
  "topic": "ia",
  "chunk_index": 142,
  "ingested_at": 1771870686
}
```

### Arquitectura v3.0

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
  - Extracción (URL / PDF / HTML / Markdown)
  - Limpieza específica por tipo
  - Chunking semántico con detección de sección
  - Embeddings híbridos (dense + sparse)
  - Inserción en Vector Store con metadata enriquecida
  - Actualización de estado en Redis
↓
Qdrant (Hybrid Search con RRF)
↓
Reranker (Cross-Encoder)
↓
LLM con contexto estructurado
↓
Respuesta a Frontend vía streaming
```

---

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
- No se detectaron deadlocks, pérdida de tasks, corrupción de vector store ni memory leaks evidentes.

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
- mejora iterativa de calidad RAG sin romper infraestructura

---

## Funcionalidades del sistema

### Core RAG

- Ingesta de documentos vía URL o archivos (PDF, HTML, Markdown)
- Chunking semántico específico por tipo de documento
- Detección de sección/heading por documento
- Strategy Pattern para chunking
- Embeddings híbridos (dense + sparse) con batching
- Hybrid Search con RRF en Qdrant
- Re-ranking con Cross-Encoder
- Metadata enriquecida por chunk (source, section, domain, topic, chunk_index)
- Construcción de contexto explícito para el LLM
- Streaming de respuesta

### Observabilidad y métricas

- Logs estructurados
- Decoradores de latencia por LLM y RAG
- Métricas Prometheus: histogram de latencia por etapa, tokens consumidos, errores, fallbacks y circuit breaker
- Métricas específicas para Celery: duración de tasks, status (success/error)
- Panel básico de estado en Frontend

### Frontend

- Chat estilo RAG
- Inputs opcionales: dominio, topic
- Estado de carga y errores
- Citations por chunk
- Visualización parcial del progreso de tasks

---

## Roadmap de versiones

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

### V3.0 – RAG avanzado: calidad (completado)

- Hybrid Search (dense + sparse) con RRF
- Chunking semántico por tipo de documento
- Detección de sección/heading como metadata
- Limpieza profunda de PDFs (TOC, artefactos, headings)
- `ChunkWithMetadata` como contrato entre cleaner y vector store

### V3.1 – Evaluación RAG (próximo)

- Integrar RAGAS
- Medir faithfulness
- Medir answer relevancy
- Medir context precision

### V3.2 – LlamaIndex (exploratorio)

- Implementar versión equivalente con LlamaIndex
- Comparar latencia, recall, calidad y complejidad de código

### V4.0 – Agente (futuro)

- Tool registry
- Skill abstraction
- Agente determinístico (policy simple)
- Planner básico con router entre RAG, Tool y Direct LLM

---

## Filosofía de diseño

- Transparencia del flujo: cada paso del pipeline es trazable
- Separación de responsabilidades: API, lógica de negocio y proveedores desacoplados
- Control del riesgo: retries, errores y fallback explícitos
- Intercambiabilidad de componentes: LLM, embeddings y vector stores reemplazables sin afectar el core
- Mejora iterativa: cada versión mejora una dimensión distinta (infraestructura → observabilidad → calidad)

---

## Instalación local rápida

```bash
git clone https://github.com/SrStamm/ai-toolkit.git
cd ai-toolkit
docker-compose up --build
```
