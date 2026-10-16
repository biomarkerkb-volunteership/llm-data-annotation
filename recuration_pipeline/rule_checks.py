import re
import pandas as pd

from record_loader import load_records
from vocab_loader import load_vocabulary


# -------------------------------------------------
# File paths
# -------------------------------------------------

DATA_FILE = "recuration_pipeline/biomarkers_top_50.tsv"

ENTITY_VOCAB_FILE = "recuration_pipeline/controlled_vocab/entity_type.txt"
CHANGE_VOCAB_FILE = "recuration_pipeline/controlled_vocab/change_type.txt"
ASPECT_VOCAB_FILE = "recuration_pipeline/controlled_vocab/aspect_type.txt"

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
# Check 3: Whitespace / formatting
# -------------------------------------------------

def find_entity_type_formatting_issues(df):
    """
    Find entity types containing unnecessary
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
# Check 4: Controlled vocabulary casing
# -------------------------------------------------

def find_casing_issues(df, columns, vocabularies):
    """
    Find values that match an official CV term
    when case is ignored, but do not use the
    official casing.

    Examples:
        Protein -> protein
        dna -> DNA
        Increased -> increased
    """

    problems = []

    for column, allowed_values in zip(
        columns,
        vocabularies
    ):

        # Create mapping:
        # lowercase version -> official version
        official_case = {
            value.lower(): value
            for value in allowed_values
        }

        for _, row in df.iterrows():

            value = row.get(column)

            if pd.isna(value):
                continue

            value = str(value).strip()

            lower_value = value.lower()

            if (
                lower_value in official_case
                and value != official_case[lower_value]
            ):

                problems.append({
                    "biomarker_id": row["biomarker_id"],
                    "field": column,
                    "current_value": value,
                    "expected_value":
                        official_case[lower_value],
                    "issue": "incorrect casing"
                })

    return pd.DataFrame(problems)


# -------------------------------------------------
# Check 5: Identifier prefix / format
# -------------------------------------------------

def find_identifier_format_issues(df):
    """
    Check basic identifier prefixes and formats.
    """

    problems = []

    for _, row in df.iterrows():

        biomarker_id = row.get("biomarker_id")
        entity_id = row.get(
            "assessed_biomarker_entity_id"
        )
        condition_id = row.get("condition_id")
        specimen_id = row.get("specimen_id")

        # -----------------------------------------
        # BiomarkerKB ID
        # Example: AN6284-1
        # -----------------------------------------

        if pd.notna(biomarker_id):

            value = str(biomarker_id).strip()

            if not re.fullmatch(
                r"[A-Z]{2}\d{4}-\d+",
                value
            ):

                problems.append({
                    "biomarker_id": biomarker_id,
                    "field": "biomarker_id",
                    "current_value": value,
                    "issue":
                        "unexpected BiomarkerKB ID format"
                })

        # -----------------------------------------
        # Assessed biomarker entity ID
        #
        # Examples:
        # PRO:PR_000050342
        # HGNC:1234
        # CHEBI:12345
        #
        # Different entity types may use different
        # identifier namespaces, so we check the
        # general PREFIX:IDENTIFIER structure.
        # -----------------------------------------

        if pd.notna(entity_id):

            value = str(entity_id).strip()

            if not re.fullmatch(
                r"[A-Za-z][A-Za-z0-9_-]*:"
                r"[A-Za-z0-9_.-]+",
                value
            ):

                problems.append({
                    "biomarker_id": biomarker_id,
                    "field":
                        "assessed_biomarker_entity_id",
                    "current_value": value,
                    "issue":
                        "invalid identifier prefix/format"
                })

        # -----------------------------------------
        # Condition ID
        #
        # If the identifier uses the DOID namespace,
        # verify the DOID format.
        #
        # Example:
        # DOID:0080600
        # -----------------------------------------

        if pd.notna(condition_id):

            value = str(condition_id).strip()

            if value.startswith("DOID:"):

                if not re.fullmatch(
                    r"DOID:\d+",
                    value
                ):

                    problems.append({
                        "biomarker_id": biomarker_id,
                        "field": "condition_id",
                        "current_value": value,
                        "issue": "invalid DOID format"
                    })

        # -----------------------------------------
        # Specimen ID
        #
        # If the identifier uses UBERON,
        # verify its format.
        #
        # Example:
        # UBERON:0000178
        # -----------------------------------------

        if pd.notna(specimen_id):

            value = str(specimen_id).strip()

            if value.startswith("UBERON:"):

                if not re.fullmatch(
                    r"UBERON:\d+",
                    value
                ):

                    problems.append({
                        "biomarker_id": biomarker_id,
                        "field": "specimen_id",
                        "current_value": value,
                        "issue": "invalid UBERON format"
                    })

    return pd.DataFrame(problems)


# -------------------------------------------------
# Create QC report
# -------------------------------------------------

def create_qc_report(
    invalid_entities,
    invalid_changes,
    invalid_aspects,
    missing_required,
    formatting_issues,
    casing_issues,
    identifier_issues
):

    problems = []

    # ---------------------------------------------
    # Invalid entity types
    # ---------------------------------------------

    for _, row in invalid_entities.iterrows():

        problems.append({
            "biomarker_id": row["biomarker_id"],
            "field": "assessed_entity_type",
            "current_value":
                row["assessed_entity_type"],
            "issue":
                "invalid controlled vocabulary value"
        })

    # ---------------------------------------------
    # Invalid / unresolved change types
    # ---------------------------------------------

    for _, row in invalid_changes.iterrows():

        problems.append({
            "biomarker_id": row["biomarker_id"],
            "field": "change_type_vocab",
            "current_value":
                row["change_type_vocab"],
            "issue":
                "invalid or unresolved "
                "controlled vocabulary value"
        })

    # ---------------------------------------------
    # Invalid / unresolved aspect types
    # ---------------------------------------------

    for _, row in invalid_aspects.iterrows():

        problems.append({
            "biomarker_id": row["biomarker_id"],
            "field": "aspect_type_vocab",
            "current_value":
                row["aspect_type_vocab"],
            "issue":
                "invalid or unresolved "
                "controlled vocabulary value"
        })

    # ---------------------------------------------
    # Missing required fields
    # ---------------------------------------------

    problems.extend(missing_required)

    # ---------------------------------------------
    # Whitespace / formatting problems
    # ---------------------------------------------

    for _, row in formatting_issues.iterrows():

        problems.append({
            "biomarker_id": row["biomarker_id"],
            "field": "assessed_entity_type",
            "current_value":
                row["assessed_entity_type"],
            "issue":
                "formatting / whitespace problem"
        })

    # ---------------------------------------------
    # Casing problems
    # ---------------------------------------------

    if not casing_issues.empty:

        for _, row in casing_issues.iterrows():

            problems.append({
                "biomarker_id": row["biomarker_id"],
                "field": row["field"],
                "current_value":
                    row["current_value"],
                "issue":
                    "incorrect controlled vocabulary casing"
            })

    # ---------------------------------------------
    # Identifier problems
    # ---------------------------------------------

    if not identifier_issues.empty:

        for _, row in identifier_issues.iterrows():

            problems.append({
                "biomarker_id": row["biomarker_id"],
                "field": row["field"],
                "current_value":
                    row["current_value"],
                "issue": row["issue"]
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

    print(
        "\nBiomarkerKB records loaded successfully."
    )

    print(
        "Number of records:",
        len(records)
    )


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

    print(
        "Controlled vocabularies loaded successfully."
    )


    # -------------------------------------------------
    # Step 3: Entity type CV check
    # -------------------------------------------------

    invalid_entities = find_invalid_values(
        records,
        "assessed_entity_type",
        entity_types
    )


    # -------------------------------------------------
    # Step 4: Change type CV check
    # -------------------------------------------------

    invalid_changes = find_invalid_values(
        records,
        "change_type_vocab",
        change_types
    )


    # -------------------------------------------------
    # Step 5: Aspect type CV check
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
    # Step 7: Whitespace / formatting check
    # -------------------------------------------------

    formatting_issues = (
        find_entity_type_formatting_issues(
            records
        )
    )


    # -------------------------------------------------
    # Step 8: Casing check
    # -------------------------------------------------

    casing_issues = find_casing_issues(
        records,
        [
            "assessed_entity_type",
            "change_type_vocab",
            "aspect_type_vocab"
        ],
        [
            entity_types,
            change_types,
            aspect_types
        ]
    )


    # -------------------------------------------------
    # Step 9: Identifier prefix / format check
    # -------------------------------------------------

    identifier_issues = (
        find_identifier_format_issues(
            records
        )
    )


    # -------------------------------------------------
    # Display casing results
    # -------------------------------------------------

    print("\n------------------------------------")
    print("CASING ISSUES")
    print("------------------------------------")

    if casing_issues.empty:

        print("No casing issues found.")

    else:

        print(
            casing_issues.to_string(
                index=False
            )
        )

    print(
        "\nTotal casing issues:",
        len(casing_issues)
    )


    # -------------------------------------------------
    # Display identifier results
    # -------------------------------------------------

    print("\n------------------------------------")
    print("IDENTIFIER FORMAT ISSUES")
    print("------------------------------------")

    if identifier_issues.empty:

        print(
            "No identifier format issues found."
        )

    else:

        print(
            identifier_issues.to_string(
                index=False
            )
        )

    print(
        "\nTotal identifier format issues:",
        len(identifier_issues)
    )


    # -------------------------------------------------
    # Step 10: Print QC summary
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

    print(
        "Casing problems:",
        len(casing_issues)
    )

    print(
        "Identifier format problems:",
        len(identifier_issues)
    )


    # -------------------------------------------------
    # Step 11: Create QC report
    # -------------------------------------------------

    qc_report = create_qc_report(
        invalid_entities,
        invalid_changes,
        invalid_aspects,
        missing_required,
        formatting_issues,
        casing_issues,
        identifier_issues
    )


    # -------------------------------------------------
    # Step 12: Save QC report
    # -------------------------------------------------

    qc_report.to_csv(
        OUTPUT_FILE,
        index=False
    )

    print("\n====================================")
    print("QC REPORT")
    print("====================================")

    print(
        "Total problems:",
        len(qc_report)
    )

    print(
        f"QC report saved to: {OUTPUT_FILE}"
    )

    print("\nQC checks completed.")