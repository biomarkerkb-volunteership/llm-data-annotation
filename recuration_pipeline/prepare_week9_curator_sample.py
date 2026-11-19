
from pathlib import Path
import pandas as pd

BASE = Path("recuration_pipeline/week9_results")

df = pd.read_csv(BASE / "week9_rewrite_evaluation.csv")

def norm(value):
    if pd.isna(value):
        return ""
    return str(value).strip().casefold()

# Remove missing proposals and unchanged-value proposals.
df = df[
    df["proposed_value"].notna()
].copy()

df = df[
    df.apply(
        lambda r: norm(r["original_value"])
        != norm(r["proposed_value"]),
        axis=1
    )
]

df = df.drop_duplicates(
    subset=[
        "biomarker_id",
        "field",
        "proposed_value"
    ]
)

# Include important cases identified during evaluation.
priority_ids = [
    "BD0266-1",
    "AN6485-1",
    "BA6984-5",
    "BD0259-1",
]

priority_fields = {
    "BD0266-1": [
        "assessed_biomarker_entity",
        "assessed_entity_type",
        "aspect_type_vocab",
    ],
    "AN6485-1": ["change_type_vocab"],
    "BA6984-5": ["assessed_biomarker_entity"],
    "BD0259-1": ["assessed_biomarker_entity"],
}

priority = df[
    df.apply(
        lambda r: (
            r["biomarker_id"] in priority_ids
            and r["field"] in priority_fields[
                r["biomarker_id"]
            ]
        ),
        axis=1
    )
]

# Add examples across different fields.
remaining = df.drop(priority.index)

diverse = (
    remaining.sort_values(
        ["field", "source", "biomarker_id"]
    )
    .groupby(["field", "source"], group_keys=False)
    .head(3)
)

sample = pd.concat(
    [priority, diverse],
    ignore_index=True
)

sample = sample.drop_duplicates(
    ["biomarker_id", "field", "proposed_value"]
).head(20)

sample["curator_decision"] = ""
sample["curator_corrected_value"] = ""
sample["curator_notes"] = ""

sample.to_csv(
    BASE / "week9_curator_spotcheck_final.csv",
    index=False
)

print("Final curator candidates:", len(sample))
print("\nBy field:")
print(sample["field"].value_counts())

print("\nPriority records included:")
for record_id in priority_ids:
    count = (sample["biomarker_id"] == record_id).sum()
    print(record_id, count)

print("\nSaved curator sample successfully.")
