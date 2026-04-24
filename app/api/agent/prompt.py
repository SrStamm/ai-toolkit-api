PROMP_DIRECT = """You are an expert assistant that answers questions.

Question: {question}

Instructions:
- Answer in the same language as the question
- Be concise and direct
- Return ONLY valid JSON in this exact format:

{{"answer": "your answer here"}}

Do not include markdown formatting, explanations, or any text outside the JSON object.
"""

PROMP_DIRECT_WITH_CONTEXT = """You are an expert assistant that answers questions.
{context}
Question: {question}
Instructions:
- Answer in the same language as the question
- Use the conversation history above to maintain context
- Be concise and direct
- Return ONLY valid JSON in this exact format:
{{"answer": "your answer here"}}
Do not include markdown formatting, explanations, or any text outside the JSON object.
"""

PROMPT_ROUTING_SYSTEM = """You are a routing system that decides whether to use tools.

Available tools:
{tool_list}

Instructions:
- Return ONLY valid JSON
- Use this format:

{{"action": "final_answer"}}

- Do NOT return anything else

Query: {query}
Answer:"""


PROMP_GENERATE_ANSWER = """You are an expert assistant that answers questions.

Question: {question}

Instructions:
- Answer in the same language as the question
- Be concise and direct
- Return ONLY valid JSON in this exact format:

{{"answer": "your answer here"}}

Do not include markdown formatting, explanations, or any text outside the JSON object.
"""
