# ai-toolkit

## **Herramientas de IA para backend**

`ai-toolkit` es una API educativa y experimental construida en **FastAPI** para explorar **cómo integrar Large Language Models (LLMs) en sistemas backend reales**, con foco en:

- control estricto del output del modelo
- validación automática y manejo de errores
- arquitectura clara y mantenible
- mínima dependencia de frameworks "mágicos"

El objetivo del proyecto **no es crear un producto final**, sino comprender y demostrar **patrones backend aplicables a sistemas que integran IA**.

---

## Estado actual (enero 2026)

El proyecto ya cuenta con funcionalidades implementadas y utilizables:

- ✅ Extracción estructurada con LLMs usando **schemas Pydantic**
- ✅ Validación automática del output del modelo
- ✅ RAG básico implementado manualmente (sin LangChain ni LlamaIndex):
  - Chunking explícito de documentos
  - Embeddings locales con `sentence-transformers`
  - Vector store con **Qdrant**
  - Metadata por chunk (`source`, `domain`, `topic`)
  - Filtros semánticos por dominio y temática
  - Respuestas con **citaciones por chunk**

---

## Arquitectura general

El proyecto está organizado siguiendo principios backend clásicos:

- **FastAPI** como capa HTTP
- **Routers** → definición de endpoints
- **Service layer** → lógica de negocio (RAG, extracción, validación)
- **Clients** desacoplados para dependencias externas:
  - LLM provider
  - Vector database

- **Embeddings locales**, sin dependencia de APIs externas
- **Vector store intercambiable** (actualmente Qdrant)

El diseño prioriza **transparencia del flujo y control explícito** por sobre abstracciones automáticas.

---

## Extracción estructurada

Extracción de información estructurada a partir de documentos semi-estructurados (CSV, PDFs, texto plano), utilizando:

- Prompts determinísticos
- Schemas Pydantic como contrato
- Validación automática del output
- Manejo de errores y retry si el output no valida

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

## RAG (Retrieval-Augmented Generation)

Implementación manual de un RAG básico para comprender el flujo completo de extremo a extremo:

- Ingesta de documentos (HTML, README, texto plano)
- Chunking por secciones (`<h2>`, `<h3>`) o tamaño fijo
- Generación de embeddings local
- Almacenamiento vectorial con metadata
- Búsqueda semántica con filtros
- Construcción explícita del contexto enviado al LLM

No se utilizan frameworks externos de orquestación para mantener **control total del pipeline**.

---

## Ejemplo de uso

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

### Consultar documentos

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

## Roadmap (aprendizaje progresivo – 2026)

Las siguientes etapas están pensadas como **experimentos técnicos independientes**, no como features de producto.

### 1. Extracción estructurada avanzada

- Soporte para PDFs escaneados (OCR)
- Retry automático con prompts alternativos
- Mejor manejo de errores semánticos

### 2. RAG básico (extensiones)

- Chunking específico por tipo de documento
- Re-ranking simple de resultados
- Vector store alternativo (FAISS / pgvector)

### 3. Guardrails y rechazo seguro

- Allowlist de intenciones permitidas
- Clasificador de intención previo al LLM
- Bloqueo de prompts peligrosos / jailbreak
- Respuestas fallback seguras

### 4. Moderación temprana

- Clasificador liviano (regex + reglas o LLM pequeño)
- Decisión temprana: procesar / pedir contexto / rechazar

### Posibles extensiones

- Agentes básicos (ReAct-style)
- Extracción de texto desde imágenes (Textract + LLM)
- Autenticación simple y multiusuario
- Background tasks para archivos grandes (Celery o Lambda + SQS)
- Métricas: latencia, tokens consumidos, costo estimado

---

## Instalación local rápida

```bash
git clone https://github.com/SrStamm/ai-toolkit.git
cd ai-toolkit
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # configurar API keys del LLM
uvicorn app.main:app --reload --port 8000
```

---

## Qué demuestra este proyecto

- Diseño de APIs backend orientadas a IA
- Integración controlada de LLMs en servidores
- Validación de outputs no determinísticos
- Implementación manual de RAG sin frameworks externos
- Separación clara de responsabilidades
- Consideración de seguridad y guardrails desde el diseño

---

## Estrcuctura del proyecto

```bash
ai-toolkit/
|-- app/
  |- core/
    |- custom_logging.py
    |- llm_client.py
    |- models.py
    |- pricing.py
    |- settting.py
    |- llm_providers/
      |- mistral_provider.py
  |- feature/
    |- extraction/
      |- exceptions.py
      |- factory.py
      |- interface.py
      |- prompts.py
      |- router.py
      |- schema.py
      |- service.py
      |- cleaners/
        |- html_cleaner.py
        |- markdown_cleaner.py
      |- semantic/
        |- invoice_extractor.py
        |- person_extractor.py
      |- source/
        |- csv_source.py
        |- html_source.py
        |- pdf_source.py
        |- readme_source.py
      |- tests/
    |- rag/
      |- exceptions.py
      |- interfaces.py
      |- prompt.py
      |- router.py
      |- schemas.py
      |- service.py
      |- providers/
        |- local_ai.py # Embedding
        |- qdrant_client.py # Qdrant client
  |- tests/
  |- mian.py
|-- front-ai-toolkit/
```
