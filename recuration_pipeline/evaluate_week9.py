
import json
from pathlib import Path

import pandas as pd

BASE = Path("recuration_pipeline")
GOLD_FILE = BASE / "gold_set_50_complete_review.xlsx"
RESULTS_DIR = BASE / "week8_results"
OUTPUT_DIR = BASE / "week9_results"

# Gold-standard columns for the four evaluated fields
FIELDS = {
    "assessed_biomarker_entity": ("original_entity", "gold_entity"),
    "assessed_entity_type": ("original_entity_type", "gold_entity_type"),
    "change_type_vocab": ("original_change_type", "gold_change_type"),
    "aspect_type_vocab": ("original_aspect_type", "gold_aspect_type"),
}


def normalize(value):
    if pd.isna(value):
        return ""
    return str(value).strip().casefold()


def evaluate():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    gold = pd.read_excel(GOLD_FILE)

    reviewed = gold[
        gold["review_status"].astype(str).str.strip().str.lower()
        == "reviewed"
    ].copy()

    print("Gold records:", len(gold))
    print("Reviewed records:", len(reviewed))
    print("Pending excluded:", len(gold) - len(reviewed))

    rows = []

    for _, record in reviewed.iterrows():
        biomarker_id = str(record["biomarker_id"]).strip()
        json_path = RESULTS_DIR / f"{biomarker_id}.json"

        if not json_path.exists():
            raise FileNotFoundError(json_path)

        with json_path.open(encoding="utf-8") as f:
            result = json.load(f)

        qc_fields = {
            issue.get("field")
            for issue in result.get("qc_issues", [])
        }

        rewrite_fields = {
            item.get("field")
            for item in result.get("qc_rewrites", [])
        }

        validation = {
            item.get("field"): item
            for item in result.get("validation_results", [])
        }

        for field, (original_col, gold_col) in FIELDS.items():
            original = normalize(record[original_col])
            gold_value = normalize(record[gold_col])

            # Missing labels cannot be scored as correct.
            if not original or not gold_value:
                continue

            actual_error = original != gold_value

            # QC flags and proposed rewrites are our
            # primary predictions of annotation errors.
            predicted_error = (
                field in qc_fields or field in rewrite_fields
            )

            if actual_error and predicted_error:
                outcome = "TP"
            elif not actual_error and predicted_error:
                outcome = "FP"
            elif actual_error and not predicted_error:
                outcome = "FN"
            else:
                outcome = "TN"

            v = validation.get(field, {})

            rows.append({
                "biomarker_id": biomarker_id,
                "field": field,
                "original_value": record[original_col],
                "gold_value": record[gold_col],
                "actual_error": actual_error,
                "predicted_error": predicted_error,
                "outcome": outcome,
                "validation_judgment": v.get("judgment", ""),
                "validation_confidence": v.get("confidence", ""),
            })

    details = pd.DataFrame(rows)

    if details.empty:
        raise ValueError("No evaluable gold labels found.")

    details.to_csv(
        OUTPUT_DIR / "week9_detection_details.csv",
        index=False
    )

    summary = []

    for field in FIELDS:
        subset = details[details["field"] == field]

        counts = subset["outcome"].value_counts()
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
            and precision + recall > 0
            else None
        )

        summary.append({
            "field": field,
            "evaluated": len(subset),
            "TP": tp,
            "FP": fp,
            "FN": fn,
            "TN": tn,
            "precision": precision,
            "recall": recall,
            "f1": f1,
        })

    summary_df = pd.DataFrame(summary)

    summary_df.to_csv(
        OUTPUT_DIR / "week9_field_metrics.csv",
        index=False
    )

    print("\nWEEK 9: QC ERROR-DETECTION EVALUATION")
    print(summary_df.to_string(index=False))
    print("\nSaved detailed results and field metrics.")


if __name__ == "__main__":
    evaluate()
