# Contributing

Use Python 3.12 or 3.13 and `uv sync --locked`. Create a branch, add a fixture or regression test
for behavior changes, then run:

```sh
uv run ruff check src tests scripts
uv run ruff format --check src tests scripts
uv run mypy src
uv run pytest --cov-fail-under=85
uv run ontolayer evaluate --ontology examples/retail/ontology.yaml --questions examples/retail/questions.yaml
```

The JSON Schema is generated from the public models. After changing those models, run
`uv run ontolayer schema` and include the schema diff. Explain compatibility changes in an ADR.
Use synthetic fixtures only. Never commit credentials, real customer data, or model API keys.

Propose ontology changes in separate files/branches. The maintainer reviews business meaning,
policy scope, source mappings, and evaluation results before certifying and merging them.
Use existing public interfaces to add backends, and provide backend conformance tests before
claiming support. Avoid backend-specific query strings in the semantic API.
