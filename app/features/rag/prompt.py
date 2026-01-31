PROMPT_TEMPLATE = """
You are a helpful assistant. Answer the user's question based ONLY on the provided context.

Context:
{context}

Question: {question}

Instructions:
- Answer in the same language as the question
- Be concise and direct
- If the context doesn't contain the answer, say "I don't have enough information to answer that"
- DO NOT use JSON format, just provide the answer as plain text

Answer:
"""

PROMPT_TEMPLATE_CHAT = """
You are an expert assistant.

Answer the user's question using the information provided in the context below.
You may rephrase, summarize, or explain the content in your own words,
but do not add information that is not supported by the context.

Return ONLY valid JSON, without markdown or explanation.
Format:
{{
  "answer": string
}}


If the context does not contain enough information to answer the question,
say clearly that you do not have enough information.

Be clear, concise, and accurate.


Context:
{context}

Question: {question}
"""
