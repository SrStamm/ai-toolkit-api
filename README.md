# ai-toolkit

> **Versión actual:** `v4.4`  
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

## Estado actual – v4.4 (Unified Task Architecture & Refactor)

La versión v4.4 unifica la arquitectura de tareas (ingesta y agente) y refactoriza el frontend para seguir el Principio de Responsabilidad Única (SRP).

### Objetivos alcanzados en v4.4

**Backend:**

- **Autonomous Ingestion:** El agente puede disparar tareas de ingesta (`reindex_document`) y gestión de documentos vía tools dedicadas.
- **Unified Task Backend:** Todas las tareas (Celery o JobService) devuelven el mismo formato: `{ status, step, progress }`.
- **Tool Registry Refactor:** Registro dinámico de tools con `@register_tool`.
- **Documents Management Tools:** `delete_document`, `reindex_document`, `get_document_metadata`.

**Frontend (Arquitectura Unificada):**

- **JobContext Global:** Estado centralizado para TODAS las tareas (ingesta UI y agente).
- **IngestionInterface refactorizado:** Dividido en 4 componentes siguiendo SRP:
  - `IngestionHeader`: Título y descripción.
  - `SourceTabs`: Lógica de URL/PDF (drag & drop, handlers).
  - `MetadataFields`: Formulario de dominio/tema.
  - `ActiveJobsPanel`: Visualización de tareas activas desde el contexto.
- **Formato Unificado:** Todas las tareas muestran `"step"` (ej. "Starting document reindexing") y barra de progreso, independientemente de quién las disparó.
- **Cleanup:** Eliminación de código muerto (`ToolStatus.tsx`, `oldImplementations.ts`).

### Arquitectura v4.4

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
  ├── reindex_document → Ingestion Job (JobService/Celery)
  └── ...other_tools
↓
AgentResponse (output + session_id + metadata + task_id)

Frontend
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

### Tools disponibles

| Tool                    | Descripción                                                                 | Dependencias       |
| ----------------------- | --------------------------------------------------------------------------- | ------------------ |
| `retrieve_context`      | Busca en la base vectorial, soporta `domain` opcional y devuelve citaciones | `rag_orchestrator` |
| `delete_document`       | Elimina un documento de la base vectorial por `source` o `document_id`      | `rag_orchestrator` |
| `reindex_document`      | Re-procesa un documento existente (dispara tarea de ingesta)                | `rag_orchestrator` |
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
- **JobContext Global:** Estado unificado para todas las tareas (ingesta y agente)
- **IngestionInterface Refactor:** Dividido en `SourceTabs`, `MetadataFields`, `ActiveJobsPanel` (SRP)
- Visualización de progreso unificada: Todas las tareas muestran `step` y barra de progreso
- Integración con endpoint del agente

---

## Roadmap

### V4.4 – Unified Task Architecture & Frontend Refactor (COMPLETADO)

- **Backend:**
  - Unificación de tareas: Todas devuelven `{ status, step, progress }`
  - Refactor del tool registry con `@register_tool`
  - Nuevas tools: `delete_document`, `reindex_document`, `get_document_metadata`
- **Frontend:**
  - `JobContext` global para unificar estado de tareas (ingesta/agente)
  - `IngestionInterface` refactorizado (SRP):
    - `IngestionHeader`
    - `SourceTabs` (URL/PDF logic)
    - `MetadataFields`
    - `ActiveJobsPanel` (all tasks displayed here)
  - Eliminación de código muerto (`ToolStatus.tsx`, `oldImplementations.ts`)

### V4.5 – Agent-triggered ingestion with user metadata (PRÓXIMO)

- **Simplified Human-in-the-loop**:
  - Agent detects new document and asks user for metadata via chat
  - User provides `domain` and `topic`
  - Agent triggers `reindex_document` → task appears in `IngestionInterface`
- **No complex queues needed**: Uses existing `JobContext` + UI unification from v4.4
- **Flow**:
  1. Agent: "Found new doc. Want me to ingest it? Need domain & topic."
  2. User: "Yes, domain='tech', topic='docs'"
  3. Agent triggers task → visible in `ActiveJobsPanel`

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
