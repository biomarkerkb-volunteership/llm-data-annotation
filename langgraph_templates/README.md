# LangGraph templates

Four scripts I wrote while working through the LangGraph intro. They are
deliberately tiny. Each one adds exactly one idea to the previous one, and
nothing here is meant to survive into the real pipeline.

| Script | What it adds |
|---|---|
| `01_hello_llm.py` | one node, one call, so you can see what a graph minimally is |
| `02_two_nodes.py` | a second node, and state being handed from one to the next |
| `03_structured_output.py` | a pydantic schema, so the reply comes back parsed instead of as prose |
| `04_check_and_retry.py` | a conditional edge that loops back when a check fails |

Script 4 is the one that matters. It extracts a supporting sentence from an
abstract, then checks with plain string matching that the sentence really is in
the abstract, and sends the graph back round if it isn't. That verify-then-loop
shape is how the evidence field gets filled without a paraphrase ever being
stored as a quotation.

## Running them

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env    # then paste the key in
python 01_hello_llm.py
```

Scripts 1, 2 and 4 cost a few cents each. Script 3 makes four calls.

## Notes to self

`with_structured_output()` passes the pydantic model to the API as a tool
schema, so the model has to fill the fields rather than being asked nicely to
produce JSON. Using a `Literal` for the controlled vocabulary means an
off-vocabulary answer fails validation instead of quietly getting written.

The check in script 4 is deliberately not another model call. A string
comparison is free, instant, and cannot invent a match.

The `attempts >= 3` guard in `route()` is load bearing. Without it a model that
never quotes verbatim loops forever.
