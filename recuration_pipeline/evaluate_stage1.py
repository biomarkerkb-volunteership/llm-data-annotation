import pandas as pd


RESULTS_FILE = "recuration_pipeline/stage1_results.csv"
GOLD_FILE = "recuration_pipeline/gold_set_50_complete_review.xlsx"
OUTPUT_FILE = "recuration_pipeline/stage1_evaluation.csv"


# Map QC field names to the corresponding gold-set columns
GOLD_FIELD_MAP = {
    "assessed_entity_type": "gold_entity_type",
    "change_type_vocab": "gold_change_type",
    "aspect_type_vocab": "gold_aspect_type",
}


def evaluate_stage1():

    results = pd.read_csv(RESULTS_FILE)
    gold = pd.read_excel(GOLD_FILE)

    print("\n====================================")
    print("STAGE 1 EVALUATION")
    print("====================================")

    print("Stage 1 predictions:", len(results))
    print("Gold-set records:", len(gold))

    evaluation_rows = []

    for _, prediction in results.iterrows():

        biomarker_id = prediction["biomarker_id"]
        field = prediction["field"]
        proposed_value = prediction["proposed_value"]

        # Only evaluate fields for which we have
        # a corresponding gold-set column.
        if field not in GOLD_FIELD_MAP:
            continue

        gold_column = GOLD_FIELD_MAP[field]

        matching_gold = gold[
            gold["biomarker_id"] == biomarker_id
        ]

        if matching_gold.empty:
            continue

        gold_record = matching_gold.iloc[0]

        # Do not treat unresolved/pending records
        # as trusted ground truth.
        review_status = str(
            gold_record.get("review_status", "")
        ).strip().lower()

        if review_status != "reviewed":
            continue

        gold_value = gold_record.get(gold_column)

        # Skip reviewed records where this particular
        # gold field is still blank.
        if pd.isna(gold_value):
            continue

        gold_value = str(gold_value).strip()
        proposed_value = str(proposed_value).strip()

        if gold_value == "":
            continue

        is_match = (
            proposed_value.lower()
            == gold_value.lower()
        )

        evaluation_rows.append({
            "biomarker_id": biomarker_id,
            "field": field,
            "original_value": prediction["original_value"],
            "proposed_value": proposed_value,
            "gold_value": gold_value,
            "match": is_match,
        })

    evaluation = pd.DataFrame(evaluation_rows)

    evaluation.to_csv(
        OUTPUT_FILE,
        index=False
    )

    total = len(evaluation)

    if total == 0:
        print("\nNo reviewed gold predictions available for evaluation.")
        return evaluation

    correct = int(evaluation["match"].sum())
    incorrect = total - correct
    accuracy = correct / total

    print("\n====================================")
    print("RESULTS")
    print("====================================")

    print("Evaluated predictions:", total)
    print("Exact matches:", correct)
    print("Mismatches:", incorrect)
    print(f"Accuracy: {accuracy:.2%}")

    print("\nResults by field:")

    field_summary = (
        evaluation
        .groupby("field")["match"]
        .agg(["count", "sum", "mean"])
    )

    field_summary = field_summary.rename(
        columns={
            "count": "evaluated",
            "sum": "correct",
            "mean": "accuracy",
        }
    )

    field_summary["accuracy"] = (
        field_summary["accuracy"] * 100
    ).round(2)

    print(field_summary)

    print("\n====================================")
    print("MISMATCHES")
    print("====================================")

    mismatches = evaluation[
        evaluation["match"] == False
    ]

    if mismatches.empty:
        print("No mismatches.")
    else:
        print(
            mismatches[
                [
                    "biomarker_id",
                    "field",
                    "proposed_value",
                    "gold_value",
                ]
            ].to_string(index=False)
        )

    print(
        "\nDetailed evaluation saved:",
        OUTPUT_FILE
    )

    return evaluation


if __name__ == "__main__":
    evaluate_stage1()