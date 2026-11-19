
import json
from pathlib import Path

import pandas as pd

BASE = Path("recuration_pipeline")
INPUT = BASE / "week8_results"
OUTPUT = BASE / "week9_results"
OUTPUT.mkdir(exist_ok=True)

rows = []

for path in sorted(INPUT.glob("*.json")):
    with path.open(encoding="utf-8") as f:
        data = json.load(f)

    record = data.get("record") or {}
    biomarker_id = record.get("biomarker_id", path.stem)

    for item in data.get("validation_results") or []:
        if item.get("field") != "best_biomarker_role":
            continue

        original = record.get("best_biomarker_role", "")
        proposed = item.get("proposed_rewrite")
        judgment = item.get("judgment", "")

        rows.append({
            "biomarker_id": biomarker_id,
            "original_role": original,
            "validation_judgment": judgment,
            "proposed_role": proposed or "",
            "confidence": item.get("confidence"),
            "supporting_sentence": (
                item.get("supporting_sentence") or ""
            ),
            "validation_reason": item.get("reason", ""),
            "curator_correct_role": "",
            "curator_error_present": "",
            "curator_accept_proposal": "",
            "curator_notes": "",
        })

df = pd.DataFrame(rows)

if df.empty:
    raise ValueError("No biomarker-role validation results found.")

# Prefer difficult cases: unsupported or insufficient evidence.
priority = {
    "unsupported": 0,
    "insufficient_evidence": 1,
    "supported": 2,
}

df["priority"] = (
    df["validation_judgment"]
    .map(priority)
    .fillna(3)
)

# Select a mix of judgments, then fill remaining slots.
selected = []

for judgment in [
    "unsupported",
    "insufficient_evidence",
    "supported",
]:
    subset = df[
        df["validation_judgment"] == judgment
    ].sort_values(
        "confidence", ascending=True, na_position="last"
    )

    selected.append(subset.head(3))

sample = pd.concat(selected).drop_duplicates(
    "biomarker_id"
)

remaining = df[
    ~df["biomarker_id"].isin(sample["biomarker_id"])
].sort_values(
    ["priority", "confidence"],
    ascending=[True, True],
    na_position="last"
)

sample = pd.concat([
    sample,
    remaining.head(max(0, 10 - len(sample)))
]).head(10)

sample = sample.drop(columns=["priority"])

sample.to_csv(
    OUTPUT / "week9_biomarker_role_curator_sample.csv",
    index=False
)

print("\n=== BIOMARKER ROLE CURATOR SAMPLE ===")
print("Total role validation records:", len(df))
print("Selected for curator:", len(sample))

print("\nJudgment distribution:")
print(sample["validation_judgment"].value_counts())

print("\nSelected IDs:")
print(sample[[
    "biomarker_id",
    "original_role",
    "validation_judgment",
    "proposed_role",
]].to_string(index=False))

print("\nSaved successfully.")
