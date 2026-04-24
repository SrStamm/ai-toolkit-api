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

Have context: {context}

Instructions:
- Return ONLY valid JSON
- Use one of these formats:

{{"action": "retrieve_context"}}
{{"action": "final_answer"}}

Rules:
- If the user asks about documentation or knowledge base AND you DO NOT have context → use "retrieve_context"
- If you ALREADY have context → use "final_answer"
- Do NOT call retrieve_context more than once
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
