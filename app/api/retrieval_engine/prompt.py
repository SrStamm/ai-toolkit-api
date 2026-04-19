# Prompt unificado para respuestas NO-streaming (JSON)
PROMPT_RAG_JSON = """You are an expert assistant that answers questions based ONLY on the provided context.

Context:
{context}

Question: {question}

Instructions:
- Answer in the same language as the question
- Be concise and direct
- If the context doesn't contain enough information, say "I don't have enough information to answer that question."
- DO NOT add information that is not in the context
- Return ONLY valid JSON in this exact format:

{{"answer": "your answer here"}}

Do not include markdown formatting, explanations, or any text outside the JSON object.
"""

# Prompt para respuestas streaming (texto plano)
PROMPT_RAG_STREAM = """You are an expert assistant that answers questions based ONLY on the provided context.

Context:
{context}

Question: {question}

Instructions:
- Answer in the same language as the question
- Be concise and direct
- If the context doesn't contain enough information, say "I don't have enough information to answer that question."
- DO NOT add information that is not in the context
- Provide your answer as plain text, without any JSON formatting

Answer:"""


#  Backward compatibility (deprecated, use PROMPT_RAG_JSON instead)
PROMPT_TEMPLATE_CHAT = PROMPT_RAG_JSON
PROMPT_TEMPLATE = PROMPT_RAG_STREAM
