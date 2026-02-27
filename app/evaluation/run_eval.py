import json
from pathlib import Path
import httpx
from ragas import evaluate
from ragas.metrics import Faithfulness, AnswerCorrectness, ContextPrecision
from datasets import Dataset

import os
from mistralai import Mistral
from dotenv import load_dotenv
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

DATASET_PATH2 = Path("app/evaluation/datasets/ai_engineering_book.json")
with open(DATASET_PATH2, "r") as f:
    dataset2 = json.load(f)

questions, answers, contexts, ground_truths = [], [], [], []

print("""
    ----------
    Iniciando tests : FastAPI
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
    Terminando tests : FastAPI
    ----------
""")

print("""
    ----------
    Iniciando tests : AI Engineering
    ----------
""")

questions_2, answers_2, contexts_2, ground_truths_2 = [], [], [], []

for item in dataset2:
    try:
        response = client(item["question"], item["domain"])
    except Exception as e:
        print(f"Error on question {item['id']}: {e}")
        continue

    questions_2.append(item["question"])
    answers_2.append(response["answer"])
    contexts_2.append([c["text"] for c in response["citations"]])
    ground_truths_2.append(item["ground_truth"])

print("""
    ----------
    Terminando tests : AI Engineering
    ----------
""")


eval_dataset_fastapi = Dataset.from_dict({
    "question": questions,
    "answer": answers,
    "contexts": contexts,
    "ground_truth": ground_truths
})

eval_dataset_book = Dataset.from_dict({
    "question": questions_2,
    "answer": answers_2,
    "contexts": contexts_2,
    "ground_truth": ground_truths_2
})


mistral_client = Mistral(api_key=os.getenv("F_API_KEY"))


evaluator_llm = LangchainLLMWrapper(
    ChatMistralAI(
        api_key=os.getenv("F_API_KEY"),
    )
)

evaluator_embeddings = HuggingFaceEmbeddings(
    model="sentence-transformers/all-MiniLM-L6-v2"
)

result_fastapi = evaluate(
    eval_dataset_fastapi,
    metrics=[
        Faithfulness(),
        AnswerCorrectness(),
        ContextPrecision(),
    ],
    llm=evaluator_llm,
    embeddings=evaluator_embeddings,
)

result_book = evaluate(
    eval_dataset_book,
    metrics=[
        Faithfulness(),
        AnswerCorrectness(),
        ContextPrecision(),
    ],
    llm=evaluator_llm,
    embeddings=evaluator_embeddings,
)


print(f"Resultados FastAPI: {result_fastapi}")
print(f"Resultados AI Engineering: {result_book}")

results_to_save = {
    "fastapi" : result_fastapi.to_pandas().mean(numeric_only=True).to_dict(),
    "ai_engineering" : result_book.to_pandas().mean(numeric_only=True).to_dict()
}

import numpy as np

def clean_nans(obj):
    if isinstance(obj, dict):
        return {k: clean_nans(v) for k, v in obj.items()}
    elif isinstance(obj, float) and (np.isnan(obj)):
        return None
    return obj

save_path = Path("app/evaluation/results/results_v3_1_separate_dataset_2.json")

with open(save_path, "w", encoding="utf-8") as f:
    json.dump(clean_nans(results_to_save), f, indent=4, ensure_ascii=False)
