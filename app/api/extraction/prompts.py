EXTRACTION_PROMPT = """
Analiza el siguiente texto y extrae la información de la persona mencionada.
Si falta algún dato como el país, intenta inferirlo por el contexto o devuelve "Unknown".
No infieras edad si no aparece explícitamente.

Texto a procesar:
"{text}"
"""

EXTRACTION_FILE_PROMPT = """
Eres un experto en facturas electrónicas chilenas según normas del SII.
El siguiente texto es la representación en string de un CSV de libro de compras/ventas.

Extrae TODAS las facturas del CSV como una lista de objetos.
Para cada fila (excepto la de encabezados), crea un objeto InvoiceSchema.
Si un dato falta → usa "Unknown" o 0.0.
No inventes datos. No agregues campos extras.

Texto del CSV:
{text}

Devuelve SOLO un array JSON de objetos InvoiceSchema.
Sin texto adicional.
"""

EXTRACTION_FILE_PDF_PROMPT = """
Eres un experto en facturas electrónicas chilenas según normas del SII.
El siguiente texto es la representación en string de un PDF de libro de compras/ventas (separado por ;).

Analiza SOLO UNA factura/row a la vez si hay varias, pero prioriza extraer la más relevante o la primera completa.
Extrae SOLO los campos solicitados en el schema. Si un dato falta o no se puede inferir claramente → usa "Unknown" o 0.0 según corresponda.
No inventes datos, no agregues campos extras como nombres personales o emails a menos que aparezcan explícitamente.

Texto del PDF (separados por \n):
{text}

Devuelve SOLO el JSON estructurado según el schema InvoiceSchema, sin texto adicional.
"""
