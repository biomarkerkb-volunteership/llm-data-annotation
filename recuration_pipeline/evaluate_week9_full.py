
import json
from pathlib import Path

import pandas as pd

BASE = Path("recuration_pipeline")
OUTPUT = BASE / "week9_results"
GOLD = BASE / "gold_set_50_complete_review.xlsx"

FIELDS = {
    "assessed_biomarker_entity": (
        "original_entity", "gold_entity"
    ),
    "assessed_entity_type": (
        "original_entity_type", "gold_entity_type"
    ),
    "change_type_vocab": (
        "original_change_type", "gold_change_type"
    ),
    "aspect_type_vocab": (
        "original_aspect_type", "gold_aspect_type"
    ),
}


def norm(value):
    if value is None or pd.isna(value):
        return ""
    return str(value).strip().casefold()


gold = pd.read_excel(GOLD)
reviewed = gold[
    gold["review_status"].astype(str)
    .str.strip().str.lower().eq("reviewed")
]

results = []

for _, row in reviewed.iterrows():
    biomarker_id = str(row["biomarker_id"])

    path = BASE / "week8_results" / f"{biomarker_id}.json"

    with path.open(encoding="utf-8") as f:
        data = json.load(f)

    qc_fields = {
        issue.get("field")
        for issue in data.get("qc_issues", [])
    }

    qc_fields.update(
        rewrite.get("field")
        for rewrite in data.get("qc_rewrites", [])
    )

    validation_fields = set()

    for item in data.get("validation_results", []):
        field = item.get("field")
        proposed = item.get("proposed_rewrite")

        if (
            proposed is not None
            and norm(proposed)
            and norm(proposed) != norm(
                data.get("record", {}).get(field)
            )
        ):
            validation_fields.add(field)

    predicted = qc_fields | validation_fields

    for field, (original_col, gold_col) in FIELDS.items():
        actual_error = (
            norm(row[original_col]) != norm(row[gold_col])
        )
        predicted_error = field in predicted

        outcome = (
            "TP" if actual_error and predicted_error
            else "FP" if predicted_error
            else "FN" if actual_error
            else "TN"
        )

        results.append({
            "biomarker_id": biomarker_id,
            "field": field,
            "actual_error": actual_error,
            "predicted_error": predicted_error,
            "outcome": outcome,
        })

details = pd.DataFrame(results)

metrics = []

for field, group in details.groupby("field"):
    counts = group["outcome"].value_counts()

    tp = int(counts.get("TP", 0))
    fp = int(counts.get("FP", 0))
    fn = int(counts.get("FN", 0))
    tn = int(counts.get("TN", 0))

    precision = tp / (tp + fp) if tp + fp else None
    recall = tp / (tp + fn) if tp + fn else None

    f1 = (
        2 * precision * recall / (precision + recall)
        if precision is not None
        and recall is not None
        and precision + recall
        else None
    )

    metrics.append({
        "field": field,
        "evaluated": len(group),
        "TP": tp,
        "FP": fp,
        "FN": fn,
        "TN": tn,
        "precision": precision,
        "recall": recall,
        "f1": f1,
    })

metrics_df = pd.DataFrame(metrics)

OUTPUT.mkdir(exist_ok=True)

details.to_csv(
    OUTPUT / "week9_full_detection_details.csv",
    index=False
)

metrics_df.to_csv(
    OUTPUT / "week9_full_field_metrics.csv",
    index=False
)

print("\n=== WEEK 9 FULL WORKFLOW EVALUATION ===")
print(metrics_df.to_string(index=False))

print("\nSaved both evaluation files.")
