import json
import pandas as pd

files = [
    "ragas_results_gpt4o-mini_ref_1.json",
    "ragas_results_gpt4o-mini_ref_2.json",
    "ragas_results_gpt4o-mini_ref_3.json",
]

score_cols = [
    "Faithfulness (0-1)",
    "Context Precision (0-1)",
    "Context Recall (0-1)",
    "คะแนนรวม (0-1)",
]

def score_label(score: float) -> str:
    if score >= 0.8: return "ดี"
    if score >= 0.5: return "พอใช้"
    return "ต้องปรับปรุง"

all_dfs = []
for f in files:
    with open(f, "r", encoding="utf-8") as fp:
        data = json.load(fp)
    all_dfs.append(pd.DataFrame(data["results"]))

avg_df = all_dfs[0].copy()
for col in score_cols:
    stacked = pd.concat([df[col] for df in all_dfs], axis=1)
    avg_df[col] = stacked.mean(axis=1).round(3)

    label_col = col.replace(" (0-1)", "")
    if label_col == "คะแนนรวม":
        label_col = "ภาพรวม"
    avg_df[label_col] = avg_df[col].apply(score_label)

summary_stats = {
    "summary": {
        "total_samples": len(avg_df),
        "rounds_averaged": len(files),
    }
}
for col in score_cols:
    name = col.replace(" (0-1)", "")
    if name == "คะแนนรวม":
        name = "Overall"
    summary_stats["summary"][name] = {
        "mean": round(avg_df[col].mean(), 3),
        "label": score_label(avg_df[col].mean()),
    }


records = avg_df.to_dict(orient="records")
output = {"results": records, **summary_stats}

with open("ragas_results_averaged_gpt4o-mini.json", "w", encoding="utf-8") as fp:
    json.dump(output, fp, ensure_ascii=False, indent=2)