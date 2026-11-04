
import os
from typing import Literal

from dotenv import load_dotenv
from openai import OpenAI
from pydantic import BaseModel, Field

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

CONTROLLED_VOCAB = {
    "assessed_entity_type": {
        "protein", "glycan", "DNA", "RNA", "cell",
        "lipid", "image", "metabolite", "element", "gene"
    },
    "change_type_vocab": {
        "increased", "decreased", "presence of",
        "absence of", "differential"
    },
    "aspect_type_vocab": {
        "level", "expression",
        "sequence variation", "modification"
    }
}


class FieldValidation(BaseModel):
    field: str
    judgment: Literal[
        "supported",
        "unsupported",
        "insufficient_evidence"
    ]
    proposed_rewrite: str | None = None
    supporting_sentence: str | None = None
    confidence: float = Field(ge=0, le=1)
    reason: str


class ValidationResult(BaseModel):
    results: list[FieldValidation]


def validate_record(record, paper):
    fields_to_check = {
        "assessed_biomarker_entity":
            record.get("assessed_biomarker_entity"),
        "assessed_entity_type":
            record.get("assessed_entity_type"),
        "condition": record.get("condition"),
        "best_biomarker_role":
            record.get("best_biomarker_role"),
        "biomarker": record.get("biomarker"),
        "change_type_vocab":
            record.get("change_type_vocab"),
        "aspect_type_vocab":
            record.get("aspect_type_vocab"),
        "evidence": record.get("evidence"),
    }

    source_text = paper.get("full_text") or paper.get("abstract") or ""

    if not source_text.strip():
        raise ValueError("No source text available for validation.")

    prompt = f"""
You are validating a BiomarkerKB record against its
cited scientific paper.

Record fields:
{fields_to_check}

Paper title:
{paper.get("title", "")}

Paper source text:
{source_text}


IMPORTANT VALIDATION RULES:

1. Evaluate each field independently.

2. A field is "supported" only when the supplied
   source text supports its complete meaning.

3. For the "evidence" field, check every factual
   claim, including numerical values, experimental
   conditions, and comparisons.

4. If some claims are supported but others cannot
   be verified, return "insufficient_evidence".
   Explain which claims could not be verified.

5. Do not treat information mentioned in a cited
   reference as a finding established by the
   current paper.

6. Do not assume that a prognostic association
   automatically establishes a "risk" biomarker role.

7. For controlled-vocabulary fields, proposed
   rewrites must use only these values:

   assessed_entity_type:
   protein, glycan, DNA, RNA, cell, lipid,
   image, metabolite, element, gene

   change_type_vocab:
   increased, decreased, presence of,
   absence of, differential

   aspect_type_vocab:
   level, expression, sequence variation,
   modification

8. If the paper suggests a concept outside the
   allowed vocabulary, do not invent a new value.
   Return insufficient_evidence and explain why.

9. Every supporting sentence must be copied
   exactly from the supplied source text.

10. If the source text is missing necessary table
    values or experimental details, explicitly
    state that they could not be verified.

"""

    response = client.responses.parse(
        model="gpt-5-mini",
        input=[
            {
                "role": "system",
                "content": (
                    "You validate scientific biomarker claims "
                    "against supplied source text only."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        text_format=ValidationResult,
    )

    result = response.output_parsed
    
    # Reject proposed corrections outside controlled vocabulary
    for item in result.results:
        if (
            item.field in CONTROLLED_VOCAB
            and item.proposed_rewrite is not None
            and item.proposed_rewrite not in CONTROLLED_VOCAB[item.field]
        ):
            item.reason += (
                " Proposed rewrite rejected: "
                "value is outside the controlled vocabulary."
            )
            item.proposed_rewrite = None
            item.judgment = "insufficient_evidence"
            item.confidence = min(item.confidence, 0.5)

    # Verify quoted evidence is present verbatim.
    
    # Verify every evidence quotation against the source
    for item in result.results:
        if item.supporting_sentence:
            if item.supporting_sentence not in source_text:
                item.supporting_sentence = None
                item.reason += (
                    " Evidence quote failed verbatim verification."
                )

                if item.judgment == "supported":
                    item.judgment = "insufficient_evidence"
                    item.confidence = min(item.confidence, 0.5)

        # A supported judgment must have verified evidence
        if (
            item.judgment == "supported"
            and item.supporting_sentence is None
        ):
            item.judgment = "insufficient_evidence"
            item.confidence = min(item.confidence, 0.5)
            item.reason += (
                " No verified supporting sentence available."
            )

    return result
