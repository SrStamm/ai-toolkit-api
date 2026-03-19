PROMP_DIRECT = """You are an expert assistant that answers questions.

Question: {question}

Instructions:
- Answer in the same language as the question
- Be concise and direct
- Return ONLY valid JSON in this exact format:

{{"answer": "your answer here"}}

Do not include markdown formatting, explanations, or any text outside the JSON object.
"""

PROMPT_ROUTING_SYSTEM = """You are a routing system.
Decide how the query should be answered.

Use RAG if the question refers to documentation or books.
Use DIRECT if it is general knowledge.

Examples:

Query: What is Python?
Answer: direct

Query: According to the documentation, how does middleware work in FastAPI?
Answer: rag

Query: What does the book AI Engineering say about evaluation?
Answer: rag

Query: What is HTTP?
Answer: direct

Query:
{query}

Answer with:
rag
or
direct
"""
