# ai-toolkit

> **Versión actual:** `v4.1`  
> **Estado:** estable (educacional / experimental, with contextual agent)

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

## Estado actual – v4.1 (Agente contextual)

La versión v4.1 extiende el agente determinístico de v4.0 con memoria de conversación. El agente ahora recuerda lo que el usuario dijo y lo que el assistant respondió en sesiones previas, manteniendo contexto a través de múltiples turnos de diálogo.

### Objetivos alcanzados en v4.1

- memorias de sesión conversaciones en Redis (sliding window de 5 mensajes)
- TTL de 3 horas (renovable en cada interacción)
- Historial de conversación inyectado al LLM en cada request
- El agente responde correctamente cuando el usuario hace referencia a información previa

### Arquitectura v4.0

```
Cliente / Frontend
↓
FastAPI – /agent/agent-loop
  - Validación de request
  - Gestión de session_id
↓
Agent (orquestador)
  - SessionMemory (historial por sesión)
  - while True loop
      ↓
    Router.get_decision() → Decision(ActionType)
      ↓
    ToolRunner.run() → ToolResponse
      ↓
    Tool (pure function)
      ↓
  State actualizado
↓
Tools
  ├── retrieve_context  → RAG → Qdrant
  └── ...other_tools
↓
AgentResponse (output + session_id + metadata)
```

### Components

| Componente     | Responsabilidad                                                                          |
| -------------- | ---------------------------------------------------------------------------------------- |
| **Agent**      | Orchestrator: controla el flow, llama router, ejecuta tool_runner, decide siguiente paso |
| **Router**     | LLM decide acción, devuelve `Decision` tipada con `ActionType` enum                      |
| **ToolRunner** | Valida inputs, resuelve dependencias, mapea state → tool input, ejecuta la tool          |

### Tools disponibles

| Tool               | Descripción                                                   | Dependencias       |
| ------------------ | ------------------------------------------------------------- | ------------------ |
| `retrieve_context` | Busca en la base vectorial y construye respuesta con contexto | `rag_orchestrator` |

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

- **Arquitectura de 3 componentes**: Agent (orchestrator), Router (LLM decision), ToolRunner (execution)
- Tool registry centralizado con decorador `@register_tool`
- Routing LLM hacia la tool adecuada con `Decision` tipada
- `ActionType` enum: `RETRIEVE_CONTEXT`, `CALL_TOOL`, `FINAL_ANSWER`
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

### V3.1 (completado)

- Integrar RAGAS
- Medir faithfulness
- Medir answer relevancy
- Medir context precision

### V3.2 (completado)

- Implementar versión con LlamaIndex
- Comparar:
  - Latencia
  - Recall
  - Calidad
  - Complejidad de código

### V4.0 – Agente determinístico (completado)

- Tool registry con decorador `@register_tool`
- Abstracción de herramientas (`ToolDefinition`, `ToolResponse`)
- **Arquitectura de 3 componentes**: Agent, Router, ToolRunner
- Router LLM con `Decision` tipada (`ActionType` enum)
- Memoria de sesión por ventana deslizante
- Tool: `retrieve_context`
- Endpoint `/agent/agent-loop`

### V4.1 – Agente contextual (completado)

- Memoria de conversación en Redis con sliding window (5 mensajes)
- TTL de 3 horas, renovado en cada interacción
- Historial de conversación inyectado al LLM
- El agente responde correctamente cuando el usuario hace referencia a información previa

### V4.2 – Agent State & Multi-Provider

- Soporte para múltiples providers:
  - groq
  - Selección dinámica de modelo/provider por request
- Dynamic model selection:
  - Configuración de providers (.yaml/.py)
  - Selección via headers o request config
  - `LLMFactory` resuelve provider activo
- Evolución del estado del agente:
  - `last_tool`
  - `last_tool_result`
  - `tool_execution_count`
- Mejora en trazabilidad del reasoning del agente

### V4.3 – Retrieval Quality & Streaming

- Mejora de `retrieve_context`:
  - Filtros por dominio
  - Devolver citations
- Documents management tools:
  - `delete_document`
  - `reindex_document`
  - `get_document_metadata`
  - Uso de metadata (`document_name`) como identificador lógico
- Streaming de respuesta del agente
- Refactor del tool registry:
  - Registro dinámico de tools

### V4.4 – Autonomous Ingestion & Simplification

- Nuevas tools:
  - `ingest_url`
  - `ingest_file`
- Human-in-the-loop ingestion:
  - Las ingestas no se ejecutan automáticamente
  - Se encolan como `PENDING`
  - Nuevas tools:
    - `list_pending_ingestions`
    - `approve_ingestion`
- El agente solicita metadata al usuario:
  - `domain`
  - `topic`
- Mejora del Router:
  - Detección automática de input (URL vs archivo)
  - Eliminación de argumentos innecesarios en `_final_answer_`
- Simplificación del sistema:
  - Eliminación de endpoints redundantes
  - Eliminación de RAG manual (todo pasa por el agente)

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
