"""Getting JSON back instead of prose, which is what the QC node will need.

with_structured_output() hands the schema to the model as a tool, so the reply
comes back already parsed and validated by pydantic.

    python 03_structured_output.py
"""

from typing import Literal

from typing_extensions import TypedDict

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, Field

load_dotenv()

# entity_type.txt, release 2026_02_17
ENTITY_TYPES = Literal[
    "protein", "glycan", "DNA", "RNA", "cell",
    "lipid", "image", "metabolite", "element", "gene",
]


class EntityTypeCall(BaseModel):
    """One assessed_entity_type, mapped onto the controlled vocabulary."""

    assessed_entity_type: ENTITY_TYPES = Field(description="the CV term to use")
    changed: bool = Field(description="true if this differs from the submitted value")
    why: str = Field(description="one short sentence")


llm = ChatOpenAI(model="gpt-6-luna", max_tokens=1024)
typer = llm.with_structured_output(EntityTypeCall)


class State(TypedDict):
    submitted: str
    call: EntityTypeCall


def normalise(state: State) -> dict:
    prompt = (
        "A BiomarkerKB curator submitted this assessed_entity_type: "
        f"'{state['submitted']}'. Map it onto the controlled vocabulary."
    )
    return {"call": typer.invoke(prompt)}


builder = StateGraph(State)
builder.add_node("normalise", normalise)
builder.add_edge(START, "normalise")
builder.add_edge("normalise", END)
graph = builder.compile()


if __name__ == "__main__":
    # All four of these are live in the database right now and none are in the CV.
    for bad in ["mRNA", "chemical element", "protein complex", "amino acid"]:
        call = graph.invoke({"submitted": bad})["call"]
        print(f"{bad:18} -> {call.assessed_entity_type:10} ({call.why})")
