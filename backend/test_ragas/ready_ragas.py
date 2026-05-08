import os
import json
import asyncio
import dotenv
import pandas as pd
dotenv.load_dotenv()

from ragas import aevaluate
from ragas.dataset_schema import EvaluationDataset, SingleTurnSample
from ragas.metrics import Faithfulness, ContextPrecision, ContextRecall
from ragas.llms import LangchainLLMWrapper
from langchain_openai import ChatOpenAI

ragas_llm = LangchainLLMWrapper(ChatOpenAI(
    api_key=os.environ.get("OPENAI_KEY"),
    model="gpt-4.1-mini-2025-04-14",
    temperature=0,
    max_tokens=4096
))

samples = []
raw_rows = []
with open(r"C:\project-agent\backend\ragas_logsgpt4o-mini_filled.jsonl", "r", encoding="utf-8") as f:
    for line in f:
        row = json.loads(line)
        if not row.get("retrieved_contexts") or not row.get("response"):
            continue
        raw_query = row["ai_query"]
        user_input_str = json.dumps(raw_query, ensure_ascii=False) if isinstance(raw_query, dict) else str(raw_query)
        
        samples.append(SingleTurnSample(
            user_input=user_input_str,
            retrieved_contexts=row["retrieved_contexts"],
            response=row["response"],
            reference=row["reference"]
        ))
        raw_rows.append({
            "timestamp":  row.get("timestamp", ""),
            "user_input": row.get("user_input", ""),
            "retrieved_contexts":   row["retrieved_contexts"],
            "response":   row["response"],
        })

print(f"✓ โหลด {len(samples)} samples")
dataset = EvaluationDataset(samples=samples)

metrics = [
    Faithfulness(llm=ragas_llm),
    ContextPrecision(llm=ragas_llm),
    ContextRecall(llm=ragas_llm),
]

def score_label(score: float) -> str:
    if score >= 0.8: return "ดี"
    if score >= 0.5: return "พอใช้"
    return "ต้องปรับปรุง"

async def main():
    results = await aevaluate(dataset=dataset, metrics=metrics)
    df = results.to_pandas()

    meta_df = pd.DataFrame(raw_rows)
    df = pd.concat([
        meta_df.reset_index(drop=True),
        df[["faithfulness", "context_precision", "context_recall"]].reset_index(drop=True)
    ], axis=1)

    df["faithfulness_label"] = df["faithfulness"].apply(score_label)
    df["context_precision_label"] = df["context_precision"].apply(score_label)
    df["context_recall_label"] = df["context_recall"].apply(score_label)
    df["overall_score"] = df[["faithfulness", "context_precision", "context_recall"]].mean(axis=1).round(3)
    df["overall_label"] = df["overall_score"].apply(score_label)

    df = df[[
        "timestamp",
        "user_input",
        "retrieved_contexts",
        "response",
        "faithfulness",
        "faithfulness_label",
        "context_precision",
        "context_precision_label",
        "context_recall",
        "context_recall_label",
        "overall_score",
        "overall_label",
    ]]

    df.columns = [
        "เวลา",
        "คำถามลูกค้า",
        "retrieved_contexts",
        "คำตอบ AI",
        "Faithfulness (0-1)",
        "Faithfulness",
        "Context Precision (0-1)",
        "Context Precision",
        "Context Recall (0-1)",
        "Context Recall",
        "คะแนนรวม (0-1)",
        "ภาพรวม",
    ]

    df_final = pd.concat([df], ignore_index=True)
    
    summary_stats = {
        "summary": {
            "total_samples": len(df),
            "Faithfulness": {
                "mean":  round(df["Faithfulness (0-1)"].mean(), 3),
                "label": score_label(df["Faithfulness (0-1)"].mean())
            },
            "Context Precision": {
                "mean":  round(df["Context Precision (0-1)"].mean(), 3),
                "label": score_label(df["Context Precision (0-1)"].mean())
            },
            "Context Recall": {
                "mean":  round(df["Context Recall (0-1)"].mean(), 3),
                "label": score_label(df["Context Recall (0-1)"].mean())
            },
            "Overall": {
                "mean":  round(df["คะแนนรวม (0-1)"].mean(), 3),
                "label": score_label(df["คะแนนรวม (0-1)"].mean())
            }
        }
    }

    records = df_final.to_dict(orient="records")
    output = {"results": records, **summary_stats}

    with open("ragas_results_gpt4o-mini_ref_3.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

asyncio.run(main())