# ai-toolkit

> **Versión actual:** `v2.0`  
> **Estado:** estable (educacional / experimental)

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

## Estado actual – v2.0 (RAG asincrónico + observabilidad)

La versión v2.0 representa un salto hacia un sistema escalable, donde la ingesta y el procesamiento de datos se ejecutan fuera del request HTTP mediante Celery, manteniendo el pipeline RAG y añadiendo observabilidad avanzada.

### Objetivos de v2.0

- Separar API y procesamiento pesado
- Introducir procesamiento asincrónico con workers
- Mejorar observabilidad técnica
- Mantener el pipeline RAG, pero ejecutado por Celery
- Medir latencia, tokens, errores y uso de recursos
- Comparar LLM remoto vs LLM local (Ollama)

### Cambios principales

- FastAPI + Celery:
  - API solo recibe requests y crea job_id para tasks asincrónicas
  - Workers realizan:
    - Extracción y limpieza de documentos
    - Chunking (HTML, Markdown, PDF)
    - Creación de embeddings
    - Inserción en vector store (Qdrant)
    - Eliminación de chunks antiguos o duplicados
- Métricas Prometheus:
  - Histogram de latencia por etapa: vector search, RAG pipeline, LLM
  - Tokens por request
  - Errores por etapa
  - Uso de fallback y circuit breaker
- Observabilidad:
  - Logs estructurados con structlog
  - Tracking de tokens consumidos y costo estimado
- LLM Factory:
  - Se puede cambiar entre modelo remoto (Mistral) o local (Ollama)
  - Dashboard en Grafana (pendiente en V2.1 para métricas completas)

### Arquitectura v2.0

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

---

## Funcionalidades incluidas en v2.0

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

### V2.1 – Observabilidad avanzada

- Histogram por etapa del RAG
- Métrica de tamaño promedio de chunks por request y size_tokens
- Métrica de recall (top_k hit ratio, requiere dataset de prueba)
- Dashboard serio en Grafana

### V2.2 – Performance profiling

- Benchmarks LLM local vs remoto
- Latencia de embedding vs tamaño batch
- Throughput de Celery
- Optimización de batch insert y creación de embeddings

### V3.0 – MCP + Agent orchestration (exploratorio)

- Exponer capacidades como skills reutilizables
- Introducir un agente mínimo que decida:
- Responder directamente
- Usar RAG
- Ejecutar una skill específica
- Experimental: no loops largos ni autonomía total

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
