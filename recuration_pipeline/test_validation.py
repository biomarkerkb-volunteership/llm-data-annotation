
import json
from pathlib import Path

import pandas as pd

from recuration_pipeline.validation_node import validate_record


def main():
    # Load BiomarkerKB records
    records = pd.read_csv(
        "recuration_pipeline/biomarkers_top_50.tsv",
        sep="\t"
    ).fillna("")

    # Select one record
    biomarker_id = "AN5170-3"

    matching = records[
        records["biomarker_id"] == biomarker_id
    ]

    if matching.empty:
        raise ValueError("Biomarker record not found.")

    record = matching.iloc[0].to_dict()

    # Load the cached scientific paper
    pmid = "21482694"
    cache_path = Path("pubmed/cache") / f"{pmid}.json"

    with open(cache_path, "r", encoding="utf-8") as f:
        paper = json.load(f)

    print("====================================")
    print("WEEK 7 VALIDATION TEST")
    print("====================================")
    print("Biomarker ID:", biomarker_id)
    print("Paper PMID:", pmid)
    print("Paper title:", paper["title"])
    print("Source length:", len(paper.get("full_text") or paper.get("abstract") or ""))

    # Run LLM validation
    result = validate_record(record, paper)

    # Display judgments
    for item in result.results:
        print("\n------------------------------------")
        print("Field:", item.field)
        print("Judgment:", item.judgment)
        print("Proposed rewrite:", item.proposed_rewrite)
        print("Confidence:", item.confidence)
        print("Reason:", item.reason)
        print("Verified evidence:", item.supporting_sentence)

    # Save structured output for inspection
    output_path = Path("recuration_pipeline/week7_single_record_result.json")

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(
            result.model_dump(),
            f,
            indent=2,
            ensure_ascii=False
        )

    print("\nSaved result to:", output_path)


if __name__ == "__main__":
    main()
