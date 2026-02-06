# ai-toolkit

> **Versión actual:** `v1.0`  
> **Estado:** estable (educacional / experimental)

**Herramientas de IA para backend (FastAPI)**

`ai-toolkit` es una **API educativa y experimental** construida en **FastAPI** para explorar **cómo diseñar sistemas backend con LLMs de forma profesional**, poniendo foco en:

- control explícito del comportamiento del modelo
- validación estricta del output
- manejo consciente de errores y retries
- arquitectura desacoplada y extensible
- observabilidad y medición de costos

> 🎯 **Objetivo del proyecto**  
> No es un producto final, sino un **laboratorio backend** para demostrar **criterio arquitectónico real** en sistemas con IA: cómo se diseñan, cómo evolucionan y cómo se preparan para un entorno empresarial.

Este README documenta **el alcance cerrado de la versión v1.0** y describe **la evolución planificada hacia v2 y v3**.

---

## Estado actual – v1.0 (RAG baseline)

La versión **v1.0** representa el **baseline funcional del proyecto**:
un sistema RAG completamente operativo, diseñado para priorizar **claridad, control y corrección** por sobre escalabilidad.

Cuenta con una **demo privada en la nube** para validación funcional.

---

## Funcionalidades incluidas en v1.0

### RAG (núcleo del sistema)

- Ingesta de documentación vía URL
- Limpieza y normalización por tipo de fuente
- Chunking **específico por tipo de documento**:
  - HTML: separación por `<h2>` / `<h3>`
  - README / Markdown: secciones semánticas
  - PDF y texto plano: tamaño fijo
- Strategy Pattern para chunking
- Embeddings locales con `sentence-transformers`
  - creación por batches
  - manejo de errores (timeouts, respuestas vacías, retry simple)
- Vector store abstraído (implementación actual: Qdrant)
- Batch insert de chunks
- Metadata por chunk (`source`, `domain`, `topic`, `chunk_index`)
- Query con embedding de consulta
- Filtros dinámicos por dominio y temática
- Re-ranking simple con Cross-Encoder
- Construcción explícita del contexto enviado al LLM
- Respuestas con citaciones por chunk
- Streaming de respuesta

---

### Observabilidad y control (v1.0)

- Logs estructurados
- Medición de tiempo de respuesta del LLM
- Tracking de tokens consumidos
- Estimación de costo por request

---

### Frontend (demo funcional)

- Ingesta de URLs y PDFs
- Chat con streaming
- Citations visibles
- Estados de carga y error
- Inputs opcionales de dominio y temática
- Panel simple de estado

---

## Filosofía de diseño

El proyecto prioriza deliberadamente:

- **Transparencia del flujo**  
  Cada paso del pipeline es explícito y trazable.
- **Separación de responsabilidades**  
  API, lógica de negocio y proveedores están claramente desacoplados.
- **Control del riesgo**  
  Validación, retries y errores se manejan de forma consciente.
- **Intercambiabilidad de componentes**  
  LLMs, embeddings y vector stores pueden reemplazarse sin afectar el core.

No se oculta complejidad: se **expone para poder aprenderla**.

---

## Arquitectura general (v1.0)

```ascii
HTTP (FastAPI)
↓
Routers (API layer)
↓
Services (orquestación explícita)
↓
Clients / Providers
├─ LLM providers
├─ Embedding providers
└─ Vector store clients
```

---

## Limitaciones conocidas de v1.0

Esta versión **no está orientada a producción**.  
Por diseño:

- la ingesta se realiza de forma síncrona
- el estado se mantiene en memoria
- no hay workers ni colas de procesamiento

Estas decisiones fueron intencionales para:

- simplificar el flujo
- priorizar comprensión y control
- establecer un baseline claro

---

## Versionado conceptual del proyecto

El proyecto evoluciona por **versiones conceptuales**, cada una con objetivos claros.

---

## v1.0 – RAG baseline (actual)

**Enfoque**

- RAG explícito y controlado
- Arquitectura limpia
- Observabilidad básica
- Correctness del output

**No incluye**

- Procesamiento asincrónico
- Workers o colas
- Métricas persistentes
- Modelos locales
- Agentes

---

## v2.0 – RAG asincrónico + observabilidad (en desarrollo)

La versión **v2.0** extiende v1 hacia un **escenario enterprise-like**, mostrando cómo escalar el sistema sin perder control.

### Objetivos de v2

- Separar API y procesamiento pesado
- Introducir procesamiento asincrónico
- Mejorar observabilidad técnica
- Mantener el mismo pipeline RAG, pero ejecutado por workers

### Cambios principales

- Procesamiento asincrónico con **Celery**
- Broker y backend de estado (Redis)
- Ingesta de documentos fuera del request HTTP
- Estado de tareas accesible por `job_id`
- Métricas del pipeline:
  - latencia
  - tokens
  - errores
- Factory de LLM providers
- Comparación entre LLM remoto y modelo local (Ollama)

### Arquitectura v2 (alto nivel)

```ascii
Cliente / Frontend
↓
FastAPI (API layer)

validación

creación de job_id

dispatch de tareas
↓
Broker (Redis)
↓
Celery Worker

extracción

limpieza

chunking

embeddings

inserción en vector store
```

---

## v3.0 – MCP + Agent orchestration (exploratorio)

La versión **v3.0** explora patrones avanzados de sistemas con IA.

### Objetivo

- Exponer capacidades del sistema como **skills reutilizables**
- Introducir un **agente mínimo**, no autónomo

El agente podrá decidir:

- responder directamente
- usar RAG
- ejecutar una skill específica

No se busca:

- autonomía total
- loops largos
- sistemas auto-reflexivos

Esta versión es **experimental y educativa**.

---

## Instalación local rápida

```bash
git clone https://github.com/SrStamm/ai-toolkit.git
cd ai-toolkit
docker-compose up --build
```
