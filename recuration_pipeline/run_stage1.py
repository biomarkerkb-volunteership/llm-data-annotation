import pandas as pd

from qc_rewrite_node import rewrite_flagged_field


RECORDS_FILE = "recuration_pipeline/biomarkers_top_50.tsv"
QC_FILE = "recuration_pipeline/qc_report.csv"
OUTPUT_FILE = "recuration_pipeline/stage1_results.csv"


def run_stage1(limit=None):

    # Load original BiomarkerKB records
    records = pd.read_csv(
        RECORDS_FILE,
        sep="\t"
    )

    # Load deterministic QC problems from Week 4
    qc_report = pd.read_csv(QC_FILE)

    # For testing, optionally process only the first N problems
    if limit is not None:
        qc_report = qc_report.head(limit)

    results = []

    print("\n====================================")
    print("STAGE 1 BATCH QC REWRITE")
    print("====================================")
    print("QC problems to process:", len(qc_report))

    for index, problem in qc_report.iterrows():

        biomarker_id = problem["biomarker_id"]
        flagged_field = problem["field"]
        current_value = problem["current_value"]
        issue = problem["issue"]

        matching_records = records[
            records["biomarker_id"] == biomarker_id
        ]

        if matching_records.empty:
            print(
                f"[SKIP] {biomarker_id}: record not found"
            )
            continue

        record = matching_records.iloc[0].to_dict()

        print(
            f"\n[{len(results) + 1}/{len(qc_report)}] "
            f"{biomarker_id} | {flagged_field}"
        )

        try:

            rewrite = rewrite_flagged_field(
                record,
                flagged_field,
                issue
            )

            results.append({
                "biomarker_id": biomarker_id,
                "field": flagged_field,
                "original_value": current_value,
                "proposed_value": rewrite.proposed_value,
                "issue": issue,
                "reason": rewrite.reason,
                "status": "rewritten",
            })

            print(
                f"{current_value} -> "
                f"{rewrite.proposed_value}"
            )

        except ValueError as error:

            # Some deterministic QC checks may not need
            # an LLM rewrite schema yet.
            results.append({
                "biomarker_id": biomarker_id,
                "field": flagged_field,
                "original_value": current_value,
                "proposed_value": "",
                "issue": issue,
                "reason": str(error),
                "status": "skipped",
            })

            print("[SKIP]", error)

    results_df = pd.DataFrame(results)

    results_df.to_csv(
        OUTPUT_FILE,
        index=False
    )

    print("\n====================================")
    print("STAGE 1 COMPLETE")
    print("====================================")
    print("Results saved:", OUTPUT_FILE)
    print("Rows saved:", len(results_df))

    return results_df


if __name__ == "__main__":

    # Small test before processing the full QC report
    run_stage1()