# ai-toolkit

> **Versión actual:** `v4.0`  
> **Estado:** estable (educacional / experimental, con agente determinístico)

**Herramientas de IA para backend (FastAPI)**

`ai-toolkit` es una API educativa y experimental construida en FastAPI para explorar cómo diseñar sistemas backend con LLMs de forma profesional, poniendo foco en:

- control explícito del comportamiento del modelo
- validación estricta del output
- manejo consciente de errores y retries
- arquitectura desacoplada y extensible
- observabilidad y métricas
- orquestación de herramientas con agente determinístico

> 🎯 Objetivo del proyecto
> No es un producto final, sino un laboratorio backend para demostrar criterio arquitectónico real en sistemas con IA: cómo se diseñan, cómo evolucionan y cómo se preparan para un entorno enterprise-like.

---

## Estado actual – v4.0 (Agente determinístico + Orquestación)

La versión v4.0 extiende el sistema RAG hacia un agente determinístico capaz de decidir qué herramienta usar según la naturaleza de la consulta. Se mantiene toda la infraestructura de v2.2 (Celery, Redis, Prometheus, Grafana) y se agrega una capa de orquestación sobre el pipeline existente.

### Objetivos alcanzados en v4.0

- Tool registry centralizado con decorador `@register_tool`
- Abstracción de herramientas mediante `ToolDefinition` y `ToolResponse`
- Router LLM que decide entre herramientas disponibles según la query
- Memoria de sesión con ventana deslizante (window size configurable)
- Inyección de dependencias por tool (cada tool declara qué deps necesita)
- Agente expuesto vía endpoint `/agent/ask-custom`
- Frontend actualizado para consumir el endpoint del agente

### Arquitectura v4.0

```ascii
Cliente / Frontend
↓
FastAPI – /agent/ask-custom
  - Validación de request
  - Gestión de session_id
↓
Agent
  - SessionMemory (historial por sesión)
  - Router LLM (decide qué tool usar)
  - Tool Executor (inyecta dependencias y ejecuta)
↓
Tools
  ├── direct  → LLM sin contexto documental
  └── rag     → LlamaIndex Orchestrator → Qdrant
↓
AgentResponse (output + session_id + metadata)
```

### Tools disponibles

| Tool     | Descripción                                                   | Dependencias       |
| -------- | ------------------------------------------------------------- | ------------------ |
| `direct` | Responde conocimiento general sin consultar documentos        | `llm_client`       |
| `rag`    | Busca en la base vectorial y construye respuesta con contexto | `rag_orchestrator` |

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
- orquestación determinística con routing LLM

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

### Agente

- Tool registry centralizado con decorador `@register_tool`
- Routing LLM hacia la tool adecuada
- Memoria de sesión con ventana deslizante
- Inyección de dependencias declarativa por tool
- Respuesta estructurada con `AgentResponse`

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
- Integración con endpoint del agente

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

### V3.0 – RAG avanzado y evaluación (completado)

- Hybrid search (sparse + dense vectors)
- Mejor estrategia de metadata
- Mejora de filtros semánticos

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

### V4.0 – Agente determinístico (completado)

- Tool registry con decorador `@register_tool`
- Abstracción de herramientas (`ToolDefinition`, `ToolResponse`)
- Agente con router LLM
- Memoria de sesión por ventana deslizante
- Tools: `direct` y `rag`
- Endpoint `/agent/ask-custom`

### V4.1 – Planner + mejoras del agente (próximo)

- Memoria de sesión con Redis
- Output estructurado del router (JSON + validación Pydantic)
- Planner básico (por definir)
- Router entre: RAG, Tool, Direct LLM

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
