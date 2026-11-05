
import json
from pathlib import Path

import pandas as pd

from recuration_pipeline.validation_node import validate_record

DATA_PATH = Path("recuration_pipeline/biomarkers_top_50.tsv")
CACHE_DIR = Path("pubmed/cache")
OUTPUT_PATH = Path("recuration_pipeline/week7_abstract_result.json")

records = pd.read_csv(DATA_PATH, sep="\t", dtype=str).fillna("")

selected = None

for _, row in records.iterrows():
    record = row.to_dict()

    # Find a PMID referenced by the record.
    evidence_source = str(record.get("evidence_source", "")).strip()

    if not evidence_source.startswith("PubMed:"):
      continue

    pmid = evidence_source.split(":", 1)[1].strip()

    if not pmid.isdigit():
      continue

    if not pmid:
        continue

    paper_path = CACHE_DIR / f"{pmid}.json"

    if not paper_path.exists():
        continue

    with open(paper_path, encoding="utf-8") as f:
        paper = json.load(f)

    # Choose an abstract-only paper.
    if paper.get("abstract") and not paper.get("full_text"):
        selected = (record, paper)
        break

if selected is None:
    raise RuntimeError(
        "No abstract-only record found. "
        "Check the dataset PMID column and cache."
    )

record, paper = selected

print("====================================")
print("WEEK 7 ABSTRACT-ONLY VALIDATION")
print("====================================")
print("PMID:", paper.get("pmid"))
print("Title:", paper.get("title"))
print("Source: Abstract only")

result = validate_record(record, paper)

for item in result.results:
    print(
        f"{item.field}: {item.judgment} "
        f"(confidence={item.confidence})"
    )

OUTPUT_PATH.write_text(
    result.model_dump_json(indent=2),
    encoding="utf-8",
)

print("Saved:", OUTPUT_PATH)
