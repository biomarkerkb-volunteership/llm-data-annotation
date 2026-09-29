"""A conditional edge, which is the only reason to reach for LangGraph at all.

The model pulls a sentence out of an abstract. A plain string check confirms the
sentence is actually in the abstract, character for character. If it isn't, the
graph loops back and tries again, up to twice.

This verify-then-loop shape is what the evidence field needs, so that nothing
paraphrased ever gets written as a quotation.

    python 04_check_and_retry.py
"""

from typing_extensions import TypedDict

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, StateGraph

load_dotenv()

llm = ChatOpenAI(model="gpt-6-luna", max_tokens=1024)

ABSTRACT = (
    "Serum interleukin-6 was measured in 214 patients with sepsis. "
    "Median IL6 at admission was 68 pg/mL in survivors and 310 pg/mL in "
    "non-survivors. Elevated IL6 at admission was associated with 28-day "
    "mortality (hazard ratio 2.4, 95% CI 1.6-3.7). "
    "C-reactive protein did not differ between the two groups."
)


class State(TypedDict):
    claim: str
    abstract: str
    evidence: str
    verified: bool
    attempts: int


def extract(state: State) -> dict:
    prompt = (
        f"Abstract:\n{state['abstract']}\n\n"
        f"Claim: {state['claim']}\n\n"
        "Quote the one sentence from the abstract that supports the claim. "
        "Copy it exactly, word for word. Return the sentence only."
    )
    return {
        "evidence": llm.invoke(prompt).content.strip(),
        "attempts": state.get("attempts", 0) + 1,
    }


def verify(state: State) -> dict:
    # Deterministic, not another model call. Cheap and it cannot hallucinate.
    return {"verified": state["evidence"].rstrip(".") in state["abstract"]}


def route(state: State) -> str:
    if state["verified"] or state["attempts"] >= 3:
        return END
    return "extract"


builder = StateGraph(State)
builder.add_node("extract", extract)
builder.add_node("verify", verify)
builder.add_edge(START, "extract")
builder.add_edge("extract", "verify")
builder.add_conditional_edges("verify", route, {"extract": "extract", END: END})
graph = builder.compile()


if __name__ == "__main__":
    out = graph.invoke(
        {
            "claim": "increased IL6 level is prognostic for mortality in sepsis",
            "abstract": ABSTRACT,
            "attempts": 0,
        }
    )
    print("verified:", out["verified"], f"(after {out['attempts']} attempt(s))")
    print("evidence:", out["evidence"])
