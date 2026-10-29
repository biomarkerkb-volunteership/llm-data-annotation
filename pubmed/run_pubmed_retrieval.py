import csv
import time
from pathlib import Path

from pubmed_client import retrieve_paper

REQUEST_DELAY = 0.4
# File locations
BASE_DIR = Path(__file__).resolve().parent.parent

DATA_FILE = BASE_DIR / "recuration_pipeline" / "biomarkers_top_50.tsv"
REPORT_FILE = Path(__file__).parent / "pubmed_retrieval_report.csv"


def run_batch():
    results = []

    # Read BiomarkerKB target dataset
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter="\t")
        records = list(reader)

    print(f"Loaded {len(records)} BiomarkerKB records.")

    for i, record in enumerate(records, start=1):
        biomarker_id = record.get("biomarker_id", "")
        evidence_source = record.get("evidence_source", "")

        print(
            f"[{i}/{len(records)}] "
            f"{biomarker_id} | {evidence_source}"
        )

        result = retrieve_paper(evidence_source)

        results.append({
            "biomarker_id": biomarker_id,
            "evidence_source": evidence_source,
            "status": result.get("status"),
            "reason": result.get("reason", ""),
            "pmid": result.get("pmid", ""),
            "pmcid": result.get("pmcid", ""),
            "title": result.get("title", ""),
            "has_abstract": bool(result.get("abstract")),
            "has_full_text": bool(result.get("full_text")),
        })

    # Save retrieval report
    fieldnames = [
        "biomarker_id",
        "evidence_source",
        "status",
        "reason",
        "pmid",
        "pmcid",
        "title",
        "has_abstract",
        "has_full_text",
    ]

    with open(REPORT_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)

    resolved = sum(r["status"] == "resolved" for r in results)
    unresolved = len(results) - resolved

    print("\n------------------------------")
    print("PUBMED RETRIEVAL SUMMARY")
    print("------------------------------")
    print("Total records:", len(results))
    print("Resolved:", resolved)
    print("Unresolved:", unresolved)
    print("Report saved to:", REPORT_FILE)


if __name__ == "__main__":
    run_batch()