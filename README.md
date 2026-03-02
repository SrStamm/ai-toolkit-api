# ai-toolkit

> **Versión actual:** `v3.1`  
> **Estado:** estable (educacional / experimental, con evaluación RAG real)

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

## Estado actual – v3.1 (Evaluación RAG con RAGAS)

La versión v3.1 incorpora evaluación formal del pipeline RAG usando **RAGAS**, con datasets curados para dos dominios distintos: documentación técnica (FastAPI) y texto de libro técnico (AI Engineering, O'Reilly).

### Qué se midió

Se evaluaron tres métricas sobre cada dataset:

- **Faithfulness**: si la respuesta está soportada por el contexto recuperado
- **Answer Correctness**: si la respuesta coincide con el ground truth
- **Context Precision**: si los chunks recuperados son relevantes para la pregunta

### Resultados

| Métrica            | FastAPI Docs | AI Engineering |
| ------------------ | ------------ | -------------- |
| Faithfulness       | 0.93         | 0.58           |
| Answer Correctness | 0.61         | 0.27           |
| Context Precision  | 0.67         | 0.25           |

### Análisis

**FastAPI** obtiene resultados sólidos. La documentación técnica es directa y los chunks recuperados son precisos. El faithfulness alto (0.93) confirma que el LLM responde basándose en el contexto, no alucina.

**AI Engineering** muestra métricas más bajas, lo cual es esperable por varias razones:

- El libro es denso conceptualmente: las respuestas requieren síntesis de múltiples secciones, no hay una cita directa.
- El contexto se recupera correctamente en varios casos, pero el reranker no siempre prioriza los chunks más relevantes para preguntas abstractas.
- El `context_precision` de 0.25 indica que hay margen de mejora en la estrategia de retrieval para texto no estructurado.

Dicho esto, en pruebas manuales el sistema responde correctamente la mayoría de las preguntas sobre el libro. Las métricas reflejan una dificultad inherente de evaluación automática sobre contenido abstracto, no necesariamente un fallo del pipeline.

---

## Estado anterior – v3.0 (RAG avanzado: Hybrid Search + Chunking semántico)

### Qué cambió respecto a v2.2

**Hybrid Search (sparse + dense)**

La búsqueda vectorial combina dos vectores por chunk:

- `dense`: embeddings semánticos vía Sentence Transformers
- `sparse`: vectores TF-IDF/BM25 para matching léxico exacto

La fusión se realiza con RRF (Reciprocal Rank Fusion) directamente en Qdrant, sin post-procesamiento manual.
En la búsqueda densa se aplica MMR (Maximal Marginal Relevance) para diversificar los candidatos y reducir chunks redundantes antes de la fusión.

**Chunking semántico por tipo de documento**

- `PDFCleaner`: limpieza profunda de artefactos (guiones rotos, líneas de índice, TOC), detección de headings por título case y numeración, overlap consistente entre chunks
- `HTMLCleaner`: segmentación por `h2`/`h3`, sección como anchor semántico
- `MarkdownCleaner`: split por `#`/`##`/`###`, heading preservado en texto y metadata

**Metadata enriquecida por chunk**

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

### Arquitectura v3.1

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
- evaluación formal del pipeline RAG con RAGAS

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
- MMR en búsqueda densa para diversidad de resultados
- Re-ranking con Cross-Encoder
- Metadata enriquecida por chunk (source, section, domain, topic, chunk_index)
- Construcción de contexto explícito para el LLM
- Streaming de respuesta

### Evaluación RAG

- Script de evaluación con RAGAS
- Métricas: faithfulness, answer correctness, context precision
- Datasets curados por dominio (FastAPI docs, AI Engineering book)
- Resultados exportados a JSON por versión

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

### V3.1 – Evaluación RAG (completado)

- Integración de RAGAS
- Métricas: faithfulness, answer correctness, context precision
- Datasets curados por dominio con ground truths extraídos del texto real
- Evaluación sobre dos dominios: documentación técnica y libro técnico
- Resultados versionados en JSON

### V3.2 – LlamaIndex (próximo)

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
- Mejora iterativa: cada versión mejora una dimensión distinta (infraestructura → observabilidad → calidad → evaluación)

---

## Instalación local rápida

```bash
git clone https://github.com/SrStamm/ai-toolkit.git
cd ai-toolkit
docker-compose up --build
```
