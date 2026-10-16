from pathlib import Path
import pandas as pd


# -------------------------------------------------
# File paths
# -------------------------------------------------

BASE_DIR = Path(__file__).parent

DATA_FILE = BASE_DIR / "biomarkers_top_50.tsv"
QC_FILE = BASE_DIR / "qc_report.csv"
OUTPUT_FILE = BASE_DIR / "gold_set_50.csv"

GOLD_SIZE = 50


# -------------------------------------------------
# Select records for gold set
# -------------------------------------------------

def select_gold_records(records, qc_report):
    """
    Select exactly 50 rows for manual gold-set annotation.

    Priority:
    1. Already manually reviewed biomarker IDs
    2. Records flagged by QC
    3. Remaining records

    Exactly 50 dataset rows are returned.
    """

    selected_indices = []

    # ---------------------------------------------
    # 1. Already manually reviewed records
    # ---------------------------------------------

    manually_reviewed = [
        "AN6284-1",
        "AN6745-1",
        "BD0266-1"
    ]

    for biomarker_id in manually_reviewed:

        matches = records[
            records["biomarker_id"] == biomarker_id
        ]

        if not matches.empty:

            # Take one row for this biomarker
            index = matches.index[0]

            if index not in selected_indices:
                selected_indices.append(index)

        if len(selected_indices) >= GOLD_SIZE:
            break


    # ---------------------------------------------
    # 2. Add rows belonging to QC-flagged records
    # ---------------------------------------------

    qc_ids = set(
        qc_report["biomarker_id"]
        .dropna()
        .astype(str)
    )

    for index, row in records.iterrows():

        if len(selected_indices) >= GOLD_SIZE:
            break

        if (
            str(row["biomarker_id"]) in qc_ids
            and index not in selected_indices
        ):
            selected_indices.append(index)


    # ---------------------------------------------
    # 3. Fill remaining slots
    # ---------------------------------------------

    for index in records.index:

        if len(selected_indices) >= GOLD_SIZE:
            break

        if index not in selected_indices:
            selected_indices.append(index)


    # ---------------------------------------------
    # Safety
    # ---------------------------------------------

    selected_indices = selected_indices[:GOLD_SIZE]

    selected = records.loc[selected_indices].copy()

    selected = selected.reset_index(drop=True)

    if len(selected) != GOLD_SIZE:

        raise ValueError(
            f"Expected {GOLD_SIZE} rows, "
            f"but selected {len(selected)}."
        )

    return selected


# -------------------------------------------------
# Create manual annotation template
# -------------------------------------------------

def create_gold_template(selected):
    """
    Create the gold-set template.

    Original values are preserved.
    Gold values remain blank until manually reviewed.
    """

    gold = pd.DataFrame()

    # ---------------------------------------------
    # Record information
    # ---------------------------------------------

    gold["biomarker_id"] = (
        selected["biomarker_id"].values
    )

    gold["condition"] = (
        selected["condition"].values
    )

    gold["evidence_source"] = (
        selected["evidence_source"].values
    )

    gold["evidence"] = (
        selected["evidence"].values
    )


    # ---------------------------------------------
    # Original BiomarkerKB annotation
    # ---------------------------------------------

    gold["original_entity"] = (
        selected["assessed_biomarker_entity"].values
    )

    gold["original_entity_id"] = (
        selected["assessed_biomarker_entity_id"].values
    )

    gold["original_entity_type"] = (
        selected["assessed_entity_type"].values
    )

    gold["original_change_type"] = (
        selected["change_type_vocab"].values
    )

    gold["original_aspect_type"] = (
        selected["aspect_type_vocab"].values
    )


    # ---------------------------------------------
    # Human-corrected gold annotation
    # ---------------------------------------------

    gold["gold_entity"] = ""
    gold["gold_entity_id"] = ""
    gold["gold_entity_type"] = ""
    gold["gold_change_type"] = ""
    gold["gold_aspect_type"] = ""


    # ---------------------------------------------
    # Manual review information
    # ---------------------------------------------

    gold["review_status"] = "pending"
    gold["correction_reason"] = ""
    gold["review_notes"] = ""

    return gold


# =================================================
# Main
# =================================================

if __name__ == "__main__":

    print("\n====================================")
    print("BIOMARKERKB GOLD SET")
    print("====================================")


    # ---------------------------------------------
    # Load files
    # ---------------------------------------------

    records = pd.read_csv(
        DATA_FILE,
        sep="\t"
    )

    qc_report = pd.read_csv(
        QC_FILE
    )

    print(
        "\nRecords available:",
        len(records)
    )

    print(
        "QC flags available:",
        len(qc_report)
    )


    # ---------------------------------------------
    # Select exactly 50 records
    # ---------------------------------------------

    selected = select_gold_records(
        records,
        qc_report
    )

    print(
        "Unique records selected:",
        len(selected)
    )


    # ---------------------------------------------
    # Create gold template
    # ---------------------------------------------

    gold = create_gold_template(
        selected
    )


    # ---------------------------------------------
    # Save
    # ---------------------------------------------

    gold.to_csv(
        OUTPUT_FILE,
        index=False
    )


    # ---------------------------------------------
    # Output summary
    # ---------------------------------------------

    print("\nGold-set template created.")

    print(
        "File:",
        OUTPUT_FILE
    )

    print("\nReview status:")

    print(
        gold["review_status"]
        .value_counts()
        .to_string()
    )

    print("\nIMPORTANT:")

    print(
        "The gold_* fields are intentionally blank."
    )

    print(
        "Each record must be manually reviewed "
        "before it becomes part of the final gold set."
    )