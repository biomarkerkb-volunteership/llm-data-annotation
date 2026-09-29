"""Smallest thing that works: one node, one LLM call.

    python 01_hello_llm.py
"""

from typing_extensions import TypedDict

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI # from langchain_anthropic import ChatAnthropic; .env -> ANTHROPIC_API_KEY=...
from langgraph.graph import END, START, StateGraph

load_dotenv()

reasoning = {
    "effort": "medium",
    "summary": "detailed" # concise, detailed, auto
    }

llm = ChatOpenAI(model="gpt-6-luna", reasoning=reasoning, output_version="responses/v1")

# Define the state type for the graph
class State(TypedDict):
    question: str
    answer: str


def ask(state: State) -> dict:
    response = llm.invoke(state["question"])
    return {"answer": response}

# Build the graph by defining and connecting nodes
builder = StateGraph(State)
builder.add_node("ask", ask)
builder.add_edge(START, "ask")
builder.add_edge("ask", END)
graph = builder.compile()


if __name__ == "__main__":
    # Invoke the graph with a question
    graph_output = graph.invoke(
        {"question": "In one sentence, what's the difference between a monitoring biomarker and a prognostic biomarker?"}
    )
    
    # Response text:
    print(f"Output:\n{graph_output['answer'].text}")

    # Reasoning summaries:
    print("\nReasoning summaries:")
    for block in graph_output['answer'].content:
        if block["type"] == "reasoning":
            for summary in block["summary"]:
                print(summary["text"])
