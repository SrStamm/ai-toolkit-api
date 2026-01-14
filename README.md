# ai-toolkit  
**Herramientas de IA para backend**

API educativa y experimental construida en **FastAPI** para practicar integración de **Large Language Models** en servidores backend.

## Objetivos del proyecto (roadmap 2026)
1. Extracción estructurada robusta (ya en buen estado)
  - Prompts determinísticos + schemas Pydantic
  - Validación automática + retry si el output no valida
  - Soporte para PDFs escaneados → AWS Textract (próximo)

2. RAG básico (sin LangChain ni LlamaIndex)

 - Chunking simple (por párrafo o tamaño fijo)
 - Embeddings locales (sentence-transformers) o Bedrock Titan
 - Vector store ligero: FAISS local o pgvector en PostgreSQL
 - Endpoint de consulta: /ask sobre documentos subidos previamente

3. Guardrails y rechazo seguro (prioridad alta)

 - Allowlist de intenciones permitidas
 - Clasificador de intención previo al LLM principal
 - Bloqueo de prompts peligrosos / jailbreak
 - Respuestas fallback seguras y amigables

4. Moderación / clasificación temprana

    - Pequeño LLM o regex + reglas → decide si:
    - procesar normalmente
    - pedir más contexto
    - rechazar directamente

Posibles extensiones (si el tiempo y la motivación acompañan)

- Agentes básicos (ReAct-style): agente que decide qué tool/feature llamar
- Multimodal básico: extracción de texto de imágenes (Textract + LLM)
- Autenticación simple + multiusuario
- Background tasks para archivos grandes (Celery o Lambda + SQS)
- Métricas: tokens consumidos, latencia, costo estimado

---

## Extracción estructurada

Ejemplo de output con el CSV típico del SII en Chile:

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
    },
    // ... resto de facturas
  ]
}
```

---

## Instalación local rápida

```bash
git clone https://github.com/SrStamm/ai-toolkit.git
cd ai-toolkit
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # configura LLM keys
uvicorn app.main:app --reload --port 8000
```
