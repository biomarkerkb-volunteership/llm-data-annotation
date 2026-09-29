"""Two nodes in sequence, so you can see state being handed along.

Node 1 pulls the biomarker phrase apart into change / entity / aspect.
Node 2 rebuilds it in BiomarkerKB house style.

    python 02_two_nodes.py
"""

from typing_extensions import TypedDict

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, StateGraph

load_dotenv()

llm = ChatOpenAI(model="gpt-6-luna", max_tokens=1024)


class State(TypedDict):
    raw: str
    parts: str
    rewritten: str


def split_parts(state: State) -> dict:
    prompt = (
        "A BiomarkerKB biomarker is a change in some aspect of an assessed entity, "
        "for example 'increased IL6 level' = increased / IL6 / level.\n"
        f"Split this one the same way: {state['raw']}\n"
        "Answer as change | entity | aspect and nothing else."
    )
    return {"parts": llm.invoke(prompt).content.strip()}


def rewrite(state: State) -> dict:
    prompt = (
        f"change | entity | aspect = {state['parts']}\n"
        "Write it back as a single biomarker string, lowercase except gene "
        "and protein symbols. No explanation."
    )
    return {"rewritten": llm.invoke(prompt).content.strip()}


builder = StateGraph(State)
builder.add_node("split_parts", split_parts)
builder.add_node("rewrite", rewrite)
builder.add_edge(START, "split_parts")
builder.add_edge("split_parts", "rewrite")
builder.add_edge("rewrite", END)
graph = builder.compile()


if __name__ == "__main__":
    out = graph.invoke({"raw": "Elevated Serum CRP Levels"})
    print("parts:    ", out["parts"])
    print("rewritten:", out["rewritten"])
