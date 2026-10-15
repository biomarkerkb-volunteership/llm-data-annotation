import pandas as pd

from record_loader import load_records
from vocab_loader import load_vocabulary


# -------------------------------------------------
# File paths
# -------------------------------------------------

DATA_FILE = "biomarkers_top_50.tsv"

ENTITY_VOCAB_FILE = "controlled_vocab/entity_type.txt"
CHANGE_VOCAB_FILE = "controlled_vocab/change_type.txt"
ASPECT_VOCAB_FILE = "controlled_vocab/aspect_type.txt"

OUTPUT_FILE = "qc_report.csv"


# -------------------------------------------------
# Check 1: Controlled vocabulary validation
# -------------------------------------------------

def find_invalid_values(df, column, allowed_values):
    """
    Find records where a value is not present
    in the official controlled vocabulary.
    """

    invalid = df[
        df[column].notna()
        & ~df[column].isin(allowed_values)
    ]

    return invalid


# -------------------------------------------------
# Check 2: Required fields
# -------------------------------------------------

def find_missing_required_fields(df, required_fields):
    """
    Find records that are missing values
    in required BiomarkerKB fields.
    """

    problems = []

    for field in required_fields:

        if field not in df.columns:
            print(f"Warning: column '{field}' not found.")
            continue

        missing = df[
            df[field].isna()
            | (df[field].astype(str).str.strip() == "")
        ]

        for _, row in missing.iterrows():

            problems.append({
                "biomarker_id": row["biomarker_id"],
                "field": field,
                "current_value": "",
                "issue": "missing required value"
            })

    return problems


# -------------------------------------------------
# Check 3: Formatting
# -------------------------------------------------

def find_entity_type_formatting_issues(df):
    """
    Find entity types with unnecessary
    leading or trailing whitespace.
    """

    problems = df[
        df["assessed_entity_type"].notna()
        & (
            df["assessed_entity_type"]
            != df["assessed_entity_type"].str.strip()
        )
    ]

    return problems


# -------------------------------------------------
# Create QC report
# -------------------------------------------------

def create_qc_report(
    invalid_entities,
    invalid_changes,
    invalid_aspects,
    missing_required,
    formatting_issues
):

    problems = []

    # Invalid entity types
    for _, row in invalid_entities.iterrows():

        problems.append({
            "biomarker_id": row["biomarker_id"],
            "field": "assessed_entity_type",
            "current_value": row["assessed_entity_type"],
            "issue": "invalid controlled vocabulary value"
        })

    # Invalid / unresolved change types
    for _, row in invalid_changes.iterrows():

        problems.append({
            "biomarker_id": row["biomarker_id"],
            "field": "change_type_vocab",
            "current_value": row["change_type_vocab"],
            "issue": "invalid or unresolved controlled vocabulary value"
        })

    # Invalid / unresolved aspect types
    for _, row in invalid_aspects.iterrows():

        problems.append({
            "biomarker_id": row["biomarker_id"],
            "field": "aspect_type_vocab",
            "current_value": row["aspect_type_vocab"],
            "issue": "invalid or unresolved controlled vocabulary value"
        })

    # Missing required fields
    problems.extend(missing_required)

    # Formatting problems
    for _, row in formatting_issues.iterrows():

        problems.append({
            "biomarker_id": row["biomarker_id"],
            "field": "assessed_entity_type",
            "current_value": row["assessed_entity_type"],
            "issue": "formatting / whitespace problem"
        })

    return pd.DataFrame(problems)


# =================================================
# Run QC pipeline
# =================================================

if __name__ == "__main__":

    print("\n====================================")
    print("BIOMARKERKB QC")
    print("====================================")

    # -------------------------------------------------
    # Step 1: Load records
    # -------------------------------------------------

    records = load_records(DATA_FILE)

    print("\nBiomarkerKB records loaded successfully.")
    print("Number of records:", len(records))


    # -------------------------------------------------
    # Step 2: Load controlled vocabularies
    # -------------------------------------------------

    entity_types = load_vocabulary(
        ENTITY_VOCAB_FILE
    )

    change_types = load_vocabulary(
        CHANGE_VOCAB_FILE
    )

    aspect_types = load_vocabulary(
        ASPECT_VOCAB_FILE
    )

    print("Controlled vocabularies loaded successfully.")


    # -------------------------------------------------
    # Step 3: Entity type check
    # -------------------------------------------------

    invalid_entities = find_invalid_values(
        records,
        "assessed_entity_type",
        entity_types
    )


    # -------------------------------------------------
    # Step 4: Change type check
    # -------------------------------------------------

    invalid_changes = find_invalid_values(
        records,
        "change_type_vocab",
        change_types
    )


    # -------------------------------------------------
    # Step 5: Aspect type check
    # -------------------------------------------------

    invalid_aspects = find_invalid_values(
        records,
        "aspect_type_vocab",
        aspect_types
    )


    # -------------------------------------------------
    # Step 6: Required field check
    # -------------------------------------------------

    required_fields = [
        "biomarker_index",
        "component_index",
        "entity_index",
        "assessed_biomarker_entity_id",
        "assessed_biomarker_entity",
        "assessed_entity_type",
        "biomarker_controlled_vocab"
    ]

    missing_required = find_missing_required_fields(
        records,
        required_fields
    )


    # -------------------------------------------------
    # Step 7: Formatting check
    # -------------------------------------------------

    formatting_issues = find_entity_type_formatting_issues(
        records
    )


    # -------------------------------------------------
    # Step 8: Print summary
    # -------------------------------------------------

    print("\n====================================")
    print("QC SUMMARY")
    print("====================================")

    print(
        "Invalid entity types:",
        len(invalid_entities)
    )

    print(
        "Invalid/unresolved change types:",
        len(invalid_changes)
    )

    print(
        "Invalid/unresolved aspect types:",
        len(invalid_aspects)
    )

    print(
        "Missing required-field problems:",
        len(missing_required)
    )

    print(
        "Entity formatting problems:",
        len(formatting_issues)
    )


    # -------------------------------------------------
    # Step 9: Create QC report
    # -------------------------------------------------

    qc_report = create_qc_report(
        invalid_entities,
        invalid_changes,
        invalid_aspects,
        missing_required,
        formatting_issues
    )


    # -------------------------------------------------
    # Step 10: Save QC report
    # -------------------------------------------------

    qc_report.to_csv(
        OUTPUT_FILE,
        index=False
    )

    print("\n====================================")
    print("QC REPORT")
    print("====================================")

    print("Total problems:", len(qc_report))
    print(f"QC report saved to: {OUTPUT_FILE}")

    print("\nQC checks completed.")