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

Available tools:
{tool_list}

Return JSON with tool name and parameters.

Example output:
{{"tool": "rag", "parameters": {{"query": "how does middleware work", "top_k": 3}}}}

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
