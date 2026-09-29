# LLM-assisted recuration of BiomarkerKB records

## Project Overview

To create an LLM workflow that reads concurrent BiomarkerKB record at a time, cleans up the
fields so they match our data model and controlled vocabulary, then goes back to
the paper the record was curated from and checks whether the record is actually
supported by it.

1. Field-level QC: read the record, compare every field against the data
   model and the controlled vocabulary, and rewrite the ones that do not
   conform. This stage never looks at the literature. It only makes the record
   internally well formed.
2. Source retrieval: pull the PubMed record named in `evidence_source` and
   get the abstract, plus the full text when the paper is open access in PMC.
3. Validation against the source: ask whether the paper really says what the
   record claims. Is the assessed biomarker entity right? The entity type? The
   condition? Is `best_biomarker_role` supported, or was it inferred from the
   study design by a curator in a hurry? Where the record is wrong, propose a
   rewrite. Where it is right, pull out the exact sentence that supports it and
   write that into the `evidence` field.

Stage 3 will be the focus of the project.

Nothing here writes directly to the database. The output is a review file with the
original field, the proposed field, the reason, and the supporting sentence, for
a human curator to accept or reject.

## Problem Description

Given that a record says `differential expression of gene TNFRSF14 is prognostic in
iron deficiency anemia` and cites `PMID:34816550`, does that paper support the claim,
and which sentence says so? Record AN6196-1 cites its PubMed source and tags which
fields the citation is supposed to back, but carries no evidence text at all. That
gap is common, and manual curation for thousands of records is labor-intensive.

## Proposed Strategy

LangGraph, because the workflow is not a straight line. Validation has to be
able to fail and send a record back, or route it to human review, and the
evidence extraction step needs a verify-and-retry loop so that a paraphrase
never gets stored as a quotation.

Every node is written to be reusable across our other datasets. A node takes a
record and a config, not a hardcoded dataset name. The controlled vocabulary
loader, the PubMed client, the field validator and the evidence extractor should
all be liftable into the next project without edits. I would rather write four
modules that generalise than one script that only handles `PMC_biomarker_sets`.

**Caveats**

Deterministic checks come before the model. If a rule can catch it, a rule
catches it, and the model only sees what is left. It is cheaper and it does not
hallucinate.

Anything written into `evidence` has to appear character for character in the
source text. The check is a string comparison, not a second model call.

## Layout

```
langgraph_templates/    week 2 scratch work, four minimal scripts
```

The rest gets added as it is built. Planned: `biomarkerkb/` for the record and
vocabulary I/O, `pubmed/` for retrieval and caching, `graph/` for the nodes and
the assembled workflow, `eval/` for the gold set and scoring.

## Schedule

### Week 1, Sep 14 to 20. Briefing and first curation task

Done. Project briefing, then an introductory curation task to learn the data
model by using it. Deliverable: the completed curation sheet, plus my list of
questions about fields I found ambiguous.

### Week 2, Sep 21 to 27. Access, LangGraph, first scripts

This week. Get onto the GW HPC cluster and get a working Python environment
there. Work through the LangGraph video. Write template scripts that invoke an
LLM and confirm they run both locally and on the cluster.
Deliverable: `langgraph_templates/`, which is done, and a working account.

### Week 3, Sep 28 to Oct 4. Planning and workflow diagram

Screen the existing BiomarkerKB datasets and pick the first target set, chosen
for having both controlled vocabulary violations and missing annotations while
staying small enough to iterate on. Write down what is wrong with it, by
category and count. Design the recuration workflow and submit a diagram.
No implementation this week.
Deliverable: the problem inventory and the workflow diagram.

### Week 4, Oct 5 to 11. Record I/O, vocabulary loader, rule-based checks

Load records from the API, parse the three controlled vocabulary files, and
implement the checks that need no model: vocabulary membership, casing rules,
identifier prefix and format, required fields present. Assemble a gold set of
50 records corrected by hand, which is what everything later gets scored
against.
Deliverable: the loaders, the rule checks, and the gold set.

### Week 5, Oct 12 to 18. The QC and rewrite node

The first stage end to end. Rule checks run, then the model proposes rewrites
for what is left, constrained to the vocabulary by a schema rather than by
asking. Run it over the target set and score it against the gold 50.
Deliverable: a working stage 1 and its first numbers.

### Week 6, Oct 19 to 25. PubMed retrieval

An E-utilities client that turns `PubMed:34816550` into a title, abstract, and
full text where PMC has it open access. Cache to disk so a rerun costs nothing,
and stay inside the rate limit, which is three requests a second without an API
key and ten with one. Handle the records whose citation is missing, malformed,
or points at something that is not a paper.
Deliverable: a cached corpus for the target set, and a count of how many records
could not be resolved and why.

### Week 7, Oct 26 to Nov 1. Validation and evidence extraction

The core node. Given a record and its source text, decide per field whether the
paper supports it, and propose a rewrite where it does not. Pull the supporting
sentence and verify it verbatim against the source before it is allowed into
`evidence`. Record a confidence and a reason for every judgement.
Deliverable: a working stage 3 on single records.

### Week 8, Nov 2 to 8. Assembling the graph

Wire all three stages into one LangGraph workflow: state schema, conditional
routing, a human-review exit for anything the model is not confident about, and
checkpointing so a batch that dies at record 400 resumes at 400. Run it over a
few hundred records.
Deliverable: the assembled workflow and a first batch of review files.

### Week 9, Nov 9 to 15. Evaluation and error analysis

Score the full workflow against the gold 50. Precision and recall on flagged
errors, separately per field, since I expect entity type to be easy and
biomarker role to be hard. Read the failures and sort them into causes. Get a
curator to spot check a sample of the proposed rewrites so the numbers are
anchored to something other than my own gold set.
Deliverable: the evaluation write-up with per-field numbers and an error
taxonomy.

### Week 10, Nov 16 to 22. Generalising to the other datasets

Take out whatever is specific to the first dataset. Move dataset differences
into config. Run it against a second dataset with a different shape as a test of
whether the modules really are reusable. Write the docs that let somebody else
run this.
Deliverable: config-driven workflow, a second dataset processed, and setup docs.

### Week 11, Nov 23 to 29. Wrap up and handoff

Short week, Thanksgiving is the 26th. Final batch run, the write-up, and a
handoff walkthrough of the code.
Deliverable: final results, the report, and a repo somebody else can pick up.

Weeks 4 through 10 are my plan, not a commitment. PubMed retrieval in particular
tends to take longer than it looks because of the records that do not resolve
cleanly, so if something slips, it slips there and weeks 9 and 10 get shorter.

## Links

- Data: https://data.biomarkerkb.org/
- API: https://api.biomarkerkb.org/
- Data model and upload spec: https://wiki.biomarkerkb.org/Data_Submission/Data_Upload
- Controlled vocabulary: https://github.com/clinical-biomarkers/biomarker-controlled-vocabulary
- LangGraph intro video: https://youtu.be/jGg_1h0qzaM
