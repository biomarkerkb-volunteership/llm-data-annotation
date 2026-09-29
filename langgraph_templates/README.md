# LangGraph templates

Four scripts I wrote while working through the LangGraph intro.
You will need an [Openai AI key](https://platform.openai.com/login) to run them.

| Script                    | What it adds                                                          |
| ------------------------- | --------------------------------------------------------------------- |
| `01_hello_llm.py`         | simple LLM invocation with showing the model reasonings               |
| `02_two_nodes.py`         | a second node, and state being handed from one to the next            |
| `03_structured_output.py` | a pydantic schema, so the reply comes back parsed instead of as prose |
| `04_check_and_retry.py`   | a conditional edge that loops back when a check fails                 |

## Running them

```bash
cd langgraph_templates
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env    # then paste the API key in .env
# Alternatively, you may directly import OPENAI_API_KEY as an environmental variable
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
