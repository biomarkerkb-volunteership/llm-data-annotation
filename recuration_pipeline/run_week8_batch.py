from collections import Counter
import csv
import json
from pathlib import Path

from recuration_pipeline.graph_workflow import build_persistent_graph


BASE_DIR = Path(__file__).resolve().parent
DATA_FILE = BASE_DIR / "biomarkers_top_50.tsv"
QC_FILE = BASE_DIR / "qc_report.csv"
OUTPUT_DIR = BASE_DIR / "week8_results"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def load_records():
    with open(DATA_FILE, encoding="utf-8") as f:
        return list(csv.DictReader(f, delimiter="\t"))


def load_qc_issues():
    issues_by_id = {}

    with open(QC_FILE, encoding="utf-8") as f:
        for issue in csv.DictReader(f):
            biomarker_id = issue["biomarker_id"]
            issues_by_id.setdefault(biomarker_id, []).append(issue)

    return issues_by_id


def main():
    records = load_records()
    issues_by_id = load_qc_issues()

    graph, connection = build_persistent_graph()

    try:
        # Track repeated biomarker IDs
        seen_ids = Counter()

        for index, record in enumerate(records, start=1):
            biomarker_id = record["biomarker_id"]
            seen_ids[biomarker_id] += 1

            # Preserve existing filenames for first occurrences.
            # Give later occurrences unique filenames.
            if seen_ids[biomarker_id] == 1:
                output_file = OUTPUT_DIR / f"{biomarker_id}.json"
            else:
                output_file = OUTPUT_DIR / f"{biomarker_id}_row_{index}.json"

            # Skip records already saved
            if output_file.exists():
                print(f"Skipping completed record: {biomarker_id}")
                continue

            print(f"Processing {index}: {biomarker_id}")

            state = {
                "record": record,
                "qc_issues": issues_by_id.get(biomarker_id, []),
                "qc_rewrites": [],
                "paper": {},
                "validation_results": [],
                "needs_human_review": False,
                "review_reasons": [],
                "status": "pending"
            }

            # Use a consistent thread ID for checkpoint recovery
            config = {
                "configurable": {
                    "thread_id": f"week8-{index}-{biomarker_id}"
                }
            }

            snapshot = graph.get_state(config)

            # Resume a record interrupted between graph nodes
            if snapshot.next:
                print(f"Resuming interrupted record: {biomarker_id}")
                result = graph.invoke(None, config=config)

            # Recover a completed result from SQLite
            elif snapshot.values and snapshot.values.get("status") in (
                "accepted", "human_review"
            ):
                print(f"Recovering saved result: {biomarker_id}")
                result = snapshot.values

            # Process a new record
            else:
                result = graph.invoke(state, config=config)

            # Any proposed QC correction requires review
            if result.get("qc_rewrites"):
                result["needs_human_review"] = True
                result["status"] = "human_review"

                if "QC corrections proposed" not in result.get(
                    "review_reasons", []
                ):
                    result.setdefault("review_reasons", []).append(
                        "QC corrections proposed"
                    )

            # Save complete result
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(result, f, indent=2, ensure_ascii=False)

            print(
                f"Completed: {biomarker_id} ({result['status']})"
            )

    finally:
        connection.close()


if __name__ == "__main__":
    main()
