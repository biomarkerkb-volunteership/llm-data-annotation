import sqlite3
from pathlib import Path

from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.sqlite import SqliteSaver
from typing import TypedDict


class TestState(TypedDict):
    value: int


def first_step(state):
    return {"value": state["value"] + 1}


def second_step(state):
    return {"value": state["value"] + 10}


db_path = Path("recuration_pipeline/checkpoints/resume_test.sqlite")
db_path.parent.mkdir(parents=True, exist_ok=True)

# First run: stop after the first node
with SqliteSaver.from_conn_string(str(db_path)) as saver:
    builder = StateGraph(TestState)
    builder.add_node("first", first_step)
    builder.add_node("second", second_step)
    builder.add_edge(START, "first")
    builder.add_edge("first", "second")
    builder.add_edge("second", END)

    graph = builder.compile(checkpointer=saver)

    config = {"configurable": {"thread_id": "resume-test-1"}}

    graph.invoke(
        {"value": 0},
        config=config,
        interrupt_after=["first"]
    )

    snapshot = graph.get_state(config)
    print("Before resume:", snapshot.values)
    print("Pending:", snapshot.next)

# Second run: reopen the SQLite database and resume
with SqliteSaver.from_conn_string(str(db_path)) as saver:
    graph = builder.compile(checkpointer=saver)

    result = graph.invoke(None, config=config)

    print("After resume:", result)