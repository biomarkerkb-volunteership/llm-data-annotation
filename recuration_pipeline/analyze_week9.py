
import json
from collections import Counter
from pathlib import Path

import pandas as pd

BASE = Path("recuration_pipeline")
INPUT = BASE / "week8_results"
OUTPUT = BASE / "week9_results"
OUTPUT.mkdir(exist_ok=True)

GOLD_FIELDS = {
    "assessed_biomarker_entity": "gold_entity",
    "assessed_entity_type": "gold_entity_type",
    "change_type_vocab": "gold_change_type",
    "aspect_type_vocab": "gold_aspect_type",
}


def normalize(value):
    if value is None or pd.isna(value):
        return ""
    return str(value).strip().casefold()


def analyze():
    gold = pd.read_excel(
        BASE / "gold_set_50_complete_review.xlsx"
    )
    reviewed = gold[
        gold["review_status"].astype(str)
        .str.strip().str.lower() == "reviewed"
    ].set_index("biomarker_id")

    detection = pd.read_csv(
        OUTPUT / "week9_detection_details.csv"
    )
    failures = detection[
        detection["outcome"].isin(["FP", "FN"])
    ].copy()
    failures.to_csv(
        OUTPUT / "week9_missed_errors.csv",
        index=False
    )

    taxonomy = []
    rewrites = []
    samples = []
    statuses = Counter()

    paths = sorted(INPUT.glob("*.json"))

    for path in paths:
        with path.open(encoding="utf-8") as f:
            data = json.load(f)

        record = data.get("record") or {}
        biomarker_id = str(
            record.get("biomarker_id", path.stem)
        )
        status = data.get("status", "unknown")
        statuses[status] += 1

        paper = data.get("paper") or {}
        qc_issues = data.get("qc_issues") or []
        qc_rewrites = data.get("qc_rewrites") or []
        validations = data.get("validation_results") or []

        for issue in qc_issues:
            taxonomy.append({
                "biomarker_id": biomarker_id,
                "category": "QC vocabulary or field issue",
                "field": issue.get("field", ""),
                "details": issue.get("issue", ""),
            })

        if paper.get("status") != "resolved":
            taxonomy.append({
                "biomarker_id": biomarker_id,
                "category": "Paper retrieval issue",
                "field": "evidence_source",
                "details": paper.get("status", "missing"),
            })

        if not validations:
            taxonomy.append({
                "biomarker_id": biomarker_id,
                "category": "Validation unavailable",
                "field": "",
                "details": "No field-level validation results",
            })

        for item in validations:
            judgment = item.get("judgment", "")
            field = item.get("field", "")
            confidence = item.get("confidence")

            if judgment in (
                "unsupported",
                "insufficient_evidence",
            ):
                taxonomy.append({
                    "biomarker_id": biomarker_id,
                    "category": judgment,
                    "field": field,
                    "details": item.get("reason", ""),
                })

            if confidence is not None and confidence < 0.8:
                taxonomy.append({
                    "biomarker_id": biomarker_id,
                    "category": "Low confidence",
                    "field": field,
                    "details": str(confidence),
                })

        proposals = list(qc_rewrites)

        for item in validations:
            if item.get("proposed_rewrite"):
                proposals.append({
                    "field": item.get("field"),
                    "proposed_value": item["proposed_rewrite"],
                    "reason": item.get("reason", ""),
                })

        for proposal in proposals:
            field = proposal.get("field")
            proposed = proposal.get("proposed_value")
            source = (
                "QC" if proposal in qc_rewrites
                else "Validation"
            )

            gold_value = None
            match = None

            if (
                biomarker_id in reviewed.index
                and field in GOLD_FIELDS
            ):
                gold_value = reviewed.loc[
                    biomarker_id, GOLD_FIELDS[field]
                ]

                if normalize(gold_value):
                    match = (
                        normalize(proposed)
                        == normalize(gold_value)
                    )

            rewrites.append({
                "biomarker_id": biomarker_id,
                "field": field,
                "source": source,
                "original_value": record.get(field, ""),
                "proposed_value": proposed,
                "gold_value": gold_value,
                "exact_gold_match": match,
                "reason": proposal.get("reason", ""),
            })

            samples.append({
                "biomarker_id": biomarker_id,
                "field": field,
                "source": source,
                "original_value": record.get(field, ""),
                "proposed_value": proposed,
                "evidence_source": record.get(
                    "evidence_source", ""
                ),
                "curator_decision": "",
                "curator_notes": "",
            })

    taxonomy_df = pd.DataFrame(taxonomy)
    rewrites_df = pd.DataFrame(rewrites)
    samples_df = pd.DataFrame(samples)

    taxonomy_df.to_csv(
        OUTPUT / "week9_error_taxonomy.csv",
        index=False
    )
    rewrites_df.to_csv(
        OUTPUT / "week9_rewrite_evaluation.csv",
        index=False
    )

    # Sample across fields and proposal sources.
    # This is a candidate set, not a completed curator review.
    sample = (
        samples_df.drop_duplicates(
            ["biomarker_id", "field", "source"]
        )
        .groupby(["field", "source"], group_keys=False)
        .head(3)
        .head(20)
    )
    sample.to_csv(
        OUTPUT / "week9_curator_spotcheck.csv",
        index=False
    )

    print("\n=== WEEK 9 FULL ANALYSIS ===")
    print("JSON outputs:", len(paths))
    print("Status counts:", dict(statuses))

    print("\nQC missed errors:")
    print(failures[[
        "biomarker_id", "field", "outcome"
    ]].to_string(index=False))

    print("\nError taxonomy counts:")
    print(taxonomy_df["category"].value_counts())

    print("\nProposed rewrites:", len(rewrites_df))
    evaluated = rewrites_df[
        rewrites_df["exact_gold_match"].notna()
    ]
    print("Gold-comparable rewrites:", len(evaluated))

    if not evaluated.empty:
        print(
            "Exact gold matches:",
            int(evaluated["exact_gold_match"].sum())
        )

    print("Curator spot-check candidates:", len(sample))
    print("\nResults saved to:", OUTPUT)


if __name__ == "__main__":
    analyze()
