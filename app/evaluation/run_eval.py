import json
from pathlib import Path
import httpx
from ragas import evaluate
from ragas.llms import llm_factory
from ragas.embeddings.base import embedding_factory
from ragas.metrics import Faithfulness, AnswerRelevancy, ContextPrecision
from datasets import Dataset

import os
from mistralai import Mistral
from openai import OpenAI
from dotenv import load_dotenv
from ragas.embeddings import LangchainEmbeddingsWrapper
from langchain_mistralai import MistralAIEmbeddings
from ragas.llms import LangchainLLMWrapper
from langchain_mistralai import ChatMistralAI
from ragas.embeddings import HuggingFaceEmbeddings


load_dotenv()

def client(question: str, domain: str):
    with httpx.Client() as client:
        response = client.post(
            "http://localhost:8000/rag/ask",
            json={"text": question, "domain": domain},
            timeout=90.0
        )
        return response.json()


DATASET_PATH = Path("app/evaluation/datasets/fastapi_docs.json")
with open(DATASET_PATH, "r") as f:
    dataset = json.load(f)

questions, answers, contexts, ground_truths = [], [], [], []

print("""
    ----------
    Iniciando tests
    ----------
""")

for item in dataset:
    try:
        response = client(item["question"], item["domain"])
    except Exception as e:
        print(f"Error on question {item['id']}: {e}")
        continue

    questions.append(item["question"])
    answers.append(response["answer"])
    contexts.append([c["text"] for c in response["citations"]])
    ground_truths.append(item["ground_truth"])

print("""
    ----------
    Terminando tests
    ----------
""")


eval_dataset = Dataset.from_dict({
    "question": questions,
    "answer": answers,
    "contexts": contexts,
    "ground_truth": ground_truths
})


mistral_client = Mistral(api_key=os.getenv("F_API_KEY"))


evaluator_llm = LangchainLLMWrapper(
    ChatMistralAI(
        api_key=os.getenv("F_API_KEY"),
        model="mistral-small-latest"
    )
)

evaluator_embeddings = HuggingFaceEmbeddings(
    model_name="sentence-transformers/all-MiniLM-L6-v2",
    model=""
)

result = evaluate(
    eval_dataset,
    metrics=[
        Faithfulness(),
        AnswerRelevancy(),
        ContextPrecision(),
    ],
    llm=evaluator_llm,
    embeddings=evaluator_embeddings,
)

print(f"Contexts: {contexts}")
print(f"ground_truths: {ground_truths}")

print(result)
