from pubmed.pubmed_client import retrieve_paper
from typing import TypedDict, Any
from recuration_pipeline.qc_rewrite_node import rewrite_flagged_field
from recuration_pipeline.validation_node import validate_record
from langgraph.graph import StateGraph, START, END

class BiomarkerState(TypedDict):

    # Original input
    record: dict[str, Any]

    # Stage 1: QC and rewrite
    qc_issues: list[dict[str, Any]]
    qc_rewrites: list[dict[str, Any]]

    # Stage 2: PubMed retrieval
    paper: dict[str, Any]

    # Stage 3: Literature validation
    validation_results: list[dict[str, Any]]

    # Conditional routing
    needs_human_review: bool
    review_reasons: list[str]

    # Final processing status
    status: str


# -----------------------------------------
# Stage 1: QC and Rewrite Node
# -----------------------------------------

def qc_rewrite_node(state: BiomarkerState) -> dict:

    record = state["record"]
    issues = state.get("qc_issues", [])
    rewrites = []
    review_reasons = []

    for issue in issues:
        field = issue["field"]

        try:
            result = rewrite_flagged_field(
                record,
                field,
                issue["issue"]
            )

            rewrites.append({
                "field": field,
                "original_value": record.get(field),
                "proposed_value": result.proposed_value,
                "reason": result.reason
            })

        except Exception as error:
            review_reasons.append(
                f"QC rewrite failed for {field}: {error}"
            )

    return {
        "qc_rewrites": rewrites,
        "review_reasons": review_reasons,
        "needs_human_review": bool(review_reasons),
        "status": "qc_completed"
    }
    

def pubmed_retrieval_node(state: BiomarkerState) -> dict:

    record = state["record"]
    evidence_source = record.get("evidence_source", "")

    result = retrieve_paper(evidence_source)

    review_reasons = list(state.get("review_reasons", []))

    if result.get("status") != "resolved":
        review_reasons.append(
            f"PubMed retrieval failed: {result.get('reason')}"
        )

    elif not result.get("full_text") and not result.get("abstract"):
        review_reasons.append(
            "No full text or abstract available for validation"
        )

    return {
        "paper": result,
        "review_reasons": review_reasons,
        "needs_human_review": bool(review_reasons),
        "status": "pubmed_completed"
    }
    

def evidence_validation_node(state: BiomarkerState) -> dict:

    record = state["record"]
    paper = state.get("paper", {})
    review_reasons = list(state.get("review_reasons", []))

    if paper.get("status") != "resolved":
        return {
            "validation_results": [],
            "review_reasons": review_reasons,
            "needs_human_review": True,
            "status": "validation_skipped"
        }

    if not paper.get("full_text") and not paper.get("abstract"):
        return {
            "validation_results": [],
            "review_reasons": review_reasons,
            "needs_human_review": True,
            "status": "validation_skipped"
        }

    try:
        result = validate_record(record, paper)

        validation_results = [
            item.model_dump()
            for item in result.results
        ]

        for item in validation_results:

            if item["judgment"] != "supported":
                review_reasons.append(
                    f"{item['field']}: {item['judgment']}"
                )

            if item["confidence"] < 0.8:
                review_reasons.append(
                    f"{item['field']}: low confidence "
                    f"({item['confidence']:.2f})"
                )

        return {
            "validation_results": validation_results,
            "review_reasons": review_reasons,
            "needs_human_review": bool(review_reasons),
            "status": "validation_completed"
        }

    except Exception as error:
        review_reasons.append(
            f"Evidence validation failed: {error}"
        )

        return {
            "validation_results": [],
            "review_reasons": review_reasons,
            "needs_human_review": True,
            "status": "validation_failed"
        }
        
# -----------------------------------------
# Assemble the LangGraph Workflow
# -----------------------------------------

def build_graph(checkpointer=None):

    builder = StateGraph(BiomarkerState)

    # Register the three stages
    builder.add_node("qc_rewrite", qc_rewrite_node)
    builder.add_node("pubmed_retrieval", pubmed_retrieval_node)
    builder.add_node("evidence_validation", evidence_validation_node)

    # Connect stages
    builder.add_edge(START, "qc_rewrite")
    builder.add_edge("qc_rewrite", "pubmed_retrieval")
    builder.add_edge("pubmed_retrieval", "evidence_validation")
    builder.add_edge("evidence_validation", END)

    return builder.compile(checkpointer=checkpointer)