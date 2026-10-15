# ai-toolkit

> **Versión actual:** `v4.5`  
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

## Estado actual – v4.5 (Autonomous Ingestion & Simplification)

La versión v4.5 simplifica el flujo de ingestión y refina el router del agente para una experiencia más autónoma.

### Objetivos alcanzados en v4.5

**Human-in-the-loop ingestion:**

- El agente detecta cuándo un nuevo documento (URL o PDF adjunto) no tiene metadata suficiente y pregunta al usuario directamente en el chat.
- El usuario responde con dominio y tema, y el agente dispara `ingest_document` automáticamente.
- Nuevo `ActionType.ASK_USER` separado de `FINAL_ANSWER` para eliminar ambigüedad en el routing.

**Mejora del Router:**

- Detección automática de input: el router distingue entre URLs, archivos PDF adjuntos y preguntas normales.
- Eliminación de `args.message` en `final_answer` — ahora `FINAL_ANSWER` solo significa "respuesta final".
- El router usa `ask_user` exclusivamente para preguntar al usuario, simplificando la lógica del agente.

**Simplificación del sistema:**

- Eliminación de endpoints redundantes (non-stream endpoints).
- Refactor del tool registry: `reindex_document` → `ingest_document`, nueva tool `ingest_pdf_file`.
- Flujo de ingestión unificado vía herramientas del agente en vez de endpoints separados.

**Frontend:**

- **Tool Steps display:** El chat muestra en tiempo real qué herramientas ejecuta el agente (`retrieve_context`, `ingest_document`, etc.) con chips colapsables.
- **Markdown tables:** Renderizado completo de tablas GFM con `remark-gfm`.
- **Simplificación:** Eliminación de código muerto y componentes obsoletos.

### Arquitectura v4.5

```
Cliente / Frontend
↓
FastAPI – /agent/agent-loop/stream
  - Validación de request
  - Gestión de session_id
↓
Agent (orquestador)
  - SessionMemory (historial por sesión)
  - while loop (max 5 steps)
      ↓
    Router.get_decision() → Decision(ActionType)
      ├── RETRIEVE_CONTEXT → ToolRunner → RAG → Qdrant
      ├── CALL_TOOL       → ToolRunner → ingest/delete/metadata
      ├── ASK_USER        → yield pregunta al usuario + return
      └── FINAL_ANSWER    → break → LLM generation o tool short-circuit
      ↓
  State actualizado
↓
SSE Events: agent_decision | tool_start | tool_done | llm_token | done

Frontend
↓
useChatStream (SSE consumer)
  ├── tool_start / tool_done → ToolSteps collapsible
  ├── llm_token              → streaming content
  └── done                   → final content + citations
↓
JobContext (Global State)
  └── Polling unificado (status, step, progress)
↓
IngestionInterface (Dashboard)
  ├── SourceTabs (URL/PDF)
  ├── MetadataFields
  └── ActiveJobsPanel (All tasks visualized here)
```

### Components

| Componente             | Responsabilidad                                                                          |
| ---------------------- | ---------------------------------------------------------------------------------------- |
| **Agent**              | Orchestrator: controla el flow, llama router, ejecuta tool_runner, decide siguiente paso |
| **Router**             | LLM decide acción, devuelve `Decision` tipada con `ActionType` enum                      |
| **ToolRunner**         | Valida inputs, resuelve dependencias, mapea state → tool input, ejecuta la tool          |
| **JobContext**         | Global state para TODAS las tareas (ingesta/agente). Polling unificado.                  |
| **IngestionInterface** | Dashboard orquestador que muestra tareas activas y controles de fuentes.                 |
| **ToolSteps**          | Componente colapsable que muestra herramientas ejecutadas por el agente paso a paso.     |

### Tools disponibles

| Tool                    | Descripción                                                                 | Dependencias       |
| ----------------------- | --------------------------------------------------------------------------- | ------------------ |
| `retrieve_context`      | Busca en la base vectorial, soporta `domain` opcional y devuelve citaciones | `rag_orchestrator` |
| `ingest_document`       | Ingiere un documento desde una URL (dispara tarea de ingesta)               | `rag_orchestrator` |
| `ingest_pdf_file`       | Ingiere un archivo PDF subido por el usuario                                | `rag_orchestrator` |
| `delete_document`       | Elimina un documento de la base vectorial por `source` o `document_id`      | `rag_orchestrator` |
| `get_document_metadata` | Obtiene metadatos de un documento (chunks, dominio, tema)                   | `rag_orchestrator` |

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

- **Arquitectura de 3 componentes**:
  - Agent (orchestrator)
  - Router (LLM decision)
  - ToolRunner (execution)
- Tool registry centralizado con decorador `@register_tool`
- Routing LLM hacia la tool adecuada con `Decision` tipada
- `ActionType` enum: `RETRIEVE_CONTEXT`, `CALL_TOOL`, `ASK_USER`, `FINAL_ANSWER`
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
- **JobContext Global:** Estado unificado para todas las tareas (ingesta y agente)
- **IngestionInterface Refactor:** Dividido en `SourceTabs`, `MetadataFields`, `ActiveJobsPanel` (SRP)
- Visualización de progreso unificada: Todas las tareas muestran `step` y barra de progreso
- Integración con endpoint del agente

---

## Roadmap

### V4.5 – Autonomous Ingestion & Simplification (ACTUAL)

- **Human-in-the-loop ingestion:**
  - Agente detecta nuevo documento y pregunta por metadata en chat
  - Agent triggerea `ingest_document` automáticamente
  - Nuevo `ActionType.ASK_USER` para flujos de pregunta/respuesta
- **Mejora del Router:**
  - Detección automática de input (URL vs archivo vs pregunta)
  - Eliminación de `args.message` en `final_answer`
- **Simplificación del sistema:**
  - Eliminación de endpoints redundantes (non-stream)
  - `reindex_document` → `ingest_document`, nueva tool `ingest_pdf_file`
- **Frontend:**
  - Tool Steps display en chat con componente colapsable
  - Renderizado de tablas markdown con `remark-gfm`

### V4.6 – Foundational (PRÓXIMO)

- Separar Runtime Loop de Agent
- Clase `ToolExecutionResult` para contrato de resultados
- Enum de todos los estados del agente
- Tool Contract para cada tool

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
