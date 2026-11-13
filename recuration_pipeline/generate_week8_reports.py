import csv
import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
RESULTS_DIR = BASE_DIR / "week8_results"

review_records = []
accepted_records = []

for file in sorted(RESULTS_DIR.glob("*.json")):

    with open(file, encoding="utf-8") as f:
        result = json.load(f)

    record = result.get("record", {})

    row = {
        "biomarker_id": record.get("biomarker_id", file.stem),
        "status": result.get("status", ""),
        "review_reasons": "; ".join(
            result.get("review_reasons", [])
        ),
        "qc_rewrites": json.dumps(
            result.get("qc_rewrites", [])
        ),
        "validation_results": json.dumps(
            result.get("validation_results", [])
        )
    }

    # Include proposed corrections in human review
    if result.get("qc_rewrites") or result.get("needs_human_review"):
        review_records.append(row)
    elif result.get("status") == "accepted":
        accepted_records.append(row)
    else:
        row["review_reasons"] += "; Unrecognized processing status"
        review_records.append(row)

fieldnames = [
    "biomarker_id",
    "status",
    "review_reasons",
    "qc_rewrites",
    "validation_results"
]

for filename, rows in [
    ("week8_human_review.csv", review_records),
    ("week8_accepted.csv", accepted_records)
]:
    output = RESULTS_DIR / filename

    with open(output, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

print("Human review:", len(review_records))
print("Accepted:", len(accepted_records))
print("Reports saved to:", RESULTS_DIR)