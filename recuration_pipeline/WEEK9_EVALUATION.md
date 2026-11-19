# Week 9 — Evaluation and Error Analysis

## Overview

This week focused on evaluating the BiomarkerKB annotation recuration pipeline against the gold-standard dataset, measuring error-detection performance, analyzing failures, and preparing proposed corrections for curator review.

The gold dataset contained 50 records, of which 37 were fully reviewed and used for evaluation. All 96 outputs from the Week 8 pipeline were also analyzed.

## Evaluation Results

The initial QC evaluation achieved 80% recall for entity type, 100% for change type, and 97% for aspect type. QC missed the only entity error, resulting in 0% entity recall.

After combining QC with evidence validation, the workflow achieved **97.6% precision, 100% recall, and 98.8% F1-score** across the four evaluated fields.

Per-field combined workflow results:

- **Assessed biomarker entity:** 50% precision, 100% recall.
- **Assessed entity type:** 100% precision, 100% recall.
- **Change type:** 100% precision, 100% recall.
- **Aspect type:** 100% precision, 100% recall.

These metrics are based on the 37 reviewed records. Biomarker-role precision and recall could not be calculated because reviewed gold labels were unavailable.

## Error Analysis and Taxonomy

The QC stage missed three errors in `BD0266-1` involving the biomarker entity, entity type, and aspect type. Evidence validation successfully identified all three and proposed corrections matching the gold standard.

The combined workflow produced one false positive in `BA6984-5`, proposing `CLPTM1` instead of the gold-standard value `CLPTM1L`.

The main diagnostic categories across the 96 outputs were:

- **Insufficient evidence:** 254 occurrences.
- **Low confidence:** 182 occurrences.
- **QC vocabulary or field issues:** 64 occurrences.
- **Unsupported annotations:** 60 occurrences.
- **Validation unavailable:** 3 occurrences.
- **Paper retrieval issues:** 1 occurrence.

These are diagnostic occurrences rather than unique incorrect records. Additional failure types included gene nomenclature disagreements, change-type interpretation differences, and overly broad entity corrections.

## Proposed Rewrites and Curator Review

The pipeline generated 304 proposed rewrites. Of the 102 proposals comparable with reviewed gold values, 99 matched exactly, giving **97.1% exact agreement**.

Three nonmatching proposals were identified:

- `AN6485-1`: Change-type disagreement (`increased` vs. `presence of`).
- `BA6984-5`: Gene-name disagreement (`CLPTM1` vs. `CLPTM1L`).
- `BD0259-1`: Entity overgeneralization (`BRCA1/2` vs. `BRCA1`).

A sample of 20 proposed corrections was prepared for curator spot-checking. An additional 10 biomarker-role cases were selected for review.

**Curator feedback is pending.**