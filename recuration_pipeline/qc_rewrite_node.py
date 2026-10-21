import os
import pandas as pd
from typing import Literal

from dotenv import load_dotenv
from openai import OpenAI
from pydantic import BaseModel, Field


# -------------------------------------------------
# Load OpenAI API key
# -------------------------------------------------

load_dotenv()

client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY")
)


# -------------------------------------------------
# Structured output schemas
# -------------------------------------------------

class EntityTypeRewrite(BaseModel):

    proposed_value: Literal[
        "protein",
        "glycan",
        "DNA",
        "RNA",
        "cell",
        "lipid",
        "image",
        "metabolite",
        "element",
        "gene",
    ]

    reason: str = Field(
        description="Short reason for the proposed rewrite."
    )


class ChangeTypeRewrite(BaseModel):

    proposed_value: Literal[
        "increased",
        "decreased",
        "presence of",
        "absence of",
        "differential",
    ]

    reason: str = Field(
        description="Short reason for the proposed rewrite."
    )


class AspectTypeRewrite(BaseModel):

    proposed_value: Literal[
        "level",
        "expression",
        "sequence variation",
        "modification",
    ]

    reason: str = Field(
        description="Short reason for the proposed rewrite."
    )


# -------------------------------------------------
# Rewrite ONE flagged field
# -------------------------------------------------

def rewrite_flagged_field(record, flagged_field, issue):

    schema_map = {
        "assessed_entity_type": EntityTypeRewrite,
        "change_type_vocab": ChangeTypeRewrite,
        "aspect_type_vocab": AspectTypeRewrite,
    }

    if flagged_field not in schema_map:
        raise ValueError(
            f"No rewrite schema for field: {flagged_field}"
        )

    output_schema = schema_map[flagged_field]

    # Do not give Stage 1 the paper evidence text.
    record_for_qc = {
        key: value
        for key, value in record.items()
        if key != "evidence"
    }

    prompt = f"""
You are performing field-level quality control
for a BiomarkerKB record.

The deterministic QC rules already identified
ONE field that needs attention.

Flagged field:
{flagged_field}

QC issue:
{issue}

Record:
{record_for_qc}

Propose a corrected value ONLY for the flagged field.

Use only information already contained in the record.
Do not use or claim support from scientific literature.
Do not rewrite fields that were not flagged.

Give a short reason for the proposed value.
"""

    response = client.responses.parse(
        model="gpt-5-mini",
        input=[
            {
                "role": "system",
                "content": (
                    "You perform BiomarkerKB field-level QC. "
                    "Only correct the field identified by the "
                    "deterministic QC rules. Use only the supplied "
                    "record. Do not use scientific literature."
                ),
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
        text_format=output_schema,
    )

    return response.output_parsed


# -------------------------------------------------
# Test first 5 real QC problems
# -------------------------------------------------

if __name__ == "__main__":

    records = pd.read_csv(
        "recuration_pipeline/biomarkers_top_50.tsv",
        sep="\t"
    )

    qc_report = pd.read_csv(
        "recuration_pipeline/qc_report.csv"
    )

    print("\n====================================")
    print("WEEK 5 FIELD-SPECIFIC QC REWRITE")
    print("====================================")

    print("Records loaded:", len(records))
    print("QC problems loaded:", len(qc_report))

    test_problems = qc_report.head(5)

    for _, problem in test_problems.iterrows():

        biomarker_id = problem["biomarker_id"]
        flagged_field = problem["field"]
        current_value = problem["current_value"]
        issue = problem["issue"]

        matching_records = records[
            records["biomarker_id"] == biomarker_id
        ]

        if matching_records.empty:
            print(
                f"\nSkipping {biomarker_id}: "
                "record not found."
            )
            continue

        record = matching_records.iloc[0].to_dict()

        print("\n------------------------------------")
        print("Biomarker ID:", biomarker_id)
        print("Flagged field:", flagged_field)
        print("Current value:", current_value)

        try:
            result = rewrite_flagged_field(
                record,
                flagged_field,
                issue
            )

            print(
                "Proposed value:",
                result.proposed_value
            )

            print(
                "Reason:",
                result.reason
            )

        except ValueError as error:

            print(
                "Skipped:",
                error
            )