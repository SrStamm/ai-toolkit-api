from pydantic import ValidationError
from ..rag.schemas import LLMAnswer
from ..llamaindex.orchrestator import (
    LLMClient,
    LlamaIndexOrchestrator,
    get_orchestrator,
    get_llm_client,
)
import structlog


logger = structlog.get_logger()


PROMPT = """
    You are an expert assistant that answers questions.

    Question: {question}

    Instructions:
    - Answer in the same language as the question
    - Be concise and direct
    - Return ONLY valid JSON in this exact format:

    {{"answer": "your answer here"}}

    Do not include markdown formatting, explanations, or any text outside the JSON object.
"""

class Agent:
    def __init__(
            self,
            llm: LLMClient,
            rag: LlamaIndexOrchestrator
    ):
        self.llm = llm
        self.rag = rag

    def router(self, query: str) -> str:
        prompt = f"""
        You are a routing system.

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

        decision = self.llm.generate_content(prompt).content

        logger.info("Router raw output", output=decision)

        if "rag" in decision:
            return "rag"

        return "direct"

    def execute(self, decision: str, query: str):
        if decision == "rag":
            return self.rag.custom_query(query=query)

        prompt = PROMPT.format(question=query)

        response = self.llm.generate_content(prompt)

        try:
            parsed = LLMAnswer.model_validate_json(response.content)
            answer = parsed.answer
        except ValidationError:
            answer = response.content

        return answer

    def agent(self, query: str):
        decision = self.router(query)
        logger.info("Agent decision", query=query, decision=decision)

        return self.execute(decision, query)


def create_agent() -> Agent:
    return Agent(
        llm=get_llm_client(),
        rag=get_orchestrator()
    )

def get_agent() -> Agent:
    return create_agent()

