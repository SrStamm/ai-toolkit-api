# ai-toolkit

**Herramientas de IA para backend (FastAPI)**

`ai-toolkit` es una **API educativa y experimental** construida en **FastAPI** para explorar **patrones reales de integración de Large Language Models (LLMs) en sistemas backend**, priorizando:

* control estricto del output del modelo
* validación automática y manejo explícito de errores
* arquitectura clara, desacoplada y mantenible
* mínima dependencia de frameworks de orquestación "mágicos"

> 🎯 **Objetivo**: no es un producto final, sino un *laboratorio backend* para entender y demostrar cómo diseñar servicios con IA de forma segura, testeable y extensible.

---

## Estado actual (febrero 2026)

La aplicación **ya funciona como una API RAG completa para consumo de documentación**, permitiendo **ingerir fuentes externas y realizar preguntas actualizadas sobre ese contexto**, con foco en control, métricas y arquitectura backend.

### RAG (núcleo del proyecto)

* ✅ Ingesta de documentación vía URL
* ✅ Limpieza y normalización por tipo de fuente
* ✅ Chunking **específico por tipo de documento**:

  * HTML: separación por `<h2>` / `<h3>`
  * README / Markdown: secciones semánticas
  * PDF y texto plano: tamaño fijo
* ✅ Strategy Pattern para chunking
* ✅ Embeddings locales con `sentence-transformers`

  * creación por **batches**
  * manejo de errores (timeouts, respuestas vacías, retry simple)
* ✅ Vector store **abstraído** (implementación actual: Qdrant)
* ✅ Batch insert de chunks
* ✅ Metadata por chunk (`source`, `domain`, `topic`, `chunk_index`)
* ✅ Query con embedding de consulta
* ✅ Filtros dinámicos por dominio y temática
* ✅ **Re-ranking simple con Cross-Encoder**
* ✅ Construcción explícita del contexto enviado al LLM
* ✅ Respuestas con **citaciones por chunk**
* ✅ Streaming de respuesta

### Observabilidad y control

* ✅ Logs estructurados
* ✅ Medición de tiempo de respuesta del LLM (decorador)
* ✅ Tracking de tokens consumidos
* ✅ Estimación de costo por request

### Frontend (demo funcional)

* ✅ Ingesta de URLs
* ✅ Chat con streaming
* ✅ Citations visibles
* ✅ Estados de carga y errores
* ✅ Inputs opcionales de dominio y temática
* ✅ Panel simple de estado

---

## Filosofía de diseño

Este proyecto prioriza:

* **Transparencia del flujo** (cada paso del pipeline es explícito)
* **Control del riesgo** (validación, retries, errores manejados)
* **Separación de responsabilidades**
* **Intercambiabilidad de componentes** (LLMs, vector store, embeddings)

No se abstrae complejidad: se **expone** para poder aprenderla.

---

## Arquitectura general

```
HTTP (FastAPI)
   ↓
Routers (API layer)
   ↓
Services (lógica de negocio)
   ↓
Clients / Providers
   ├─ LLM providers
   ├─ Embedding providers
   └─ Vector store clients
```

### Capas principales

* **Routers**: definición de endpoints y validación de input
* **Service layer**: orquestación explícita del flujo (RAG, extracción)
* **Core**:

  * cliente de LLM
  * pricing / conteo de tokens
  * logging estructurado
  * settings
* **Providers / Clients**:

  * LLM (ej: Mistral)
  * Vector DB (Qdrant)
  * Embeddings locales

---

## Extracción estructurada

Extracción de información estructurada desde documentos semi-estructurados usando:

* Prompts determinísticos
* Schemas Pydantic como contrato de salida
* Validación automática
* Manejo explícito de errores y retries

### Ejemplo

Extracción desde un CSV típico del SII (Chile):

```json
{
  "invoices": [
    {
      "tipo_doc": "30",
      "folio": "8741",
      "rut_contraparte": "55555555-5",
      "razon_social": "Andres E.I.R.L.",
      "fecha_emision": "01-06-2010",
      "monto_neto": 148000.0,
      "monto_iva": 28120.0,
      "monto_total": 176120.0,
      "producto_o_descripcion": null
    }
  ]
}
```

---

## RAG – Ejemplo de uso

### Ingestar documentación

```http
POST /rag/ingest
```

```json
{
  "url": "https://fastapi.tiangolo.com/tutorial/",
  "domain": "backend",
  "topic": "fastapi"
}
```

### Consultar documentación

```http
POST /rag/ask
```

```json
{
  "text": "How does dependency injection work in FastAPI?",
  "domain": "backend",
  "topic": "fastapi"
}
```

Respuesta:

```json
{
  "answer": "...",
  "citations": [
    {
      "source": "https://fastapi.tiangolo.com/tutorial/",
      "chunk_index": 3
    }
  ]
}
```

---

## Roadmap técnico (aprendizaje – 2026)

Las siguientes etapas son **mejoras técnicas incrementales**, manteniendo el proyecto como una **API RAG de documentación**.

### Importancia alta

* Factory para selección de LLM provider
* Robustecer retry logic

  * circuit breaker simple
  * fallback a modelo local si el proveedor externo falla

### Importancia media

* Cost tracking acumulado

  * por sesión
  * por usuario
* Endpoint de métricas

  * requests
  * latencia
  * tokens
  * errores
* Re-ingesta incremental de documentos

### Importancia baja / experimental

* Endpoint `/rag/reset`
* Modelo local vía Ollama
* Evaluación automática con RAGAS

---

## Instalación local rápida

```bash
git clone https://github.com/SrStamm/ai-toolkit.git
cd ai-toolkit
docker-compose up --build
```

---

## Qué demuestra este proyecto

* Diseño de APIs backend orientadas a IA
* Integración controlada de LLMs en servidores
* Validación de outputs no determinísticos
* Implementación manual de RAG
* Arquitectura desacoplada y mantenible
* Seguridad y guardrails pensados desde el diseño

---

## Estructura del proyecto

```bash
ai-toolkit/
├─ app/
│  ├─ core/
│  │  ├─ custom_logging.py
│  │  ├─ llm_client.py
│  │  ├─ models.py
│  │  ├─ pricing.py
│  │  ├─ settings.py
│  │  └─ llm_providers/
│  │     └─ mistral_provider.py
│  ├─ feature/
│  │  ├─ extraction/
│  │  │  ├─ exceptions.py
│  │  │  ├─ factory.py
│  │  │  ├─ interface.py
│  │  │  ├─ prompts.py
│  │  │  ├─ router.py
│  │  │  ├─ schema.py
│  │  │  ├─ service.py
│  │  │  ├─ cleaners/
│  │  │  ├─ semantic/
│  │  │  ├─ source/
│  │  │  └─ tests/
│  │  └─ rag/
│  │     ├─ exceptions.py
│  │     ├─ interfaces.py
│  │     ├─ prompt.py
│  │     ├─ router.py
│  │     ├─ schemas.py
│  │     ├─ service.py
│  │     └─ providers/
│  │        ├─ local_ai.py
│  │        └─ qdrant_client.py
│  ├─ tests/
│  └─ main.py
└─ front-ai-toolkit/
```
