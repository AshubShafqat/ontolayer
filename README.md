# OntoLayer

**Business meaning your agents can query.**

Ontologies as code · Knowledge graphs · Governed metrics · MCP

[![CI](https://github.com/AshubShafqat/ontolayer/actions/workflows/ci.yml/badge.svg)](https://github.com/AshubShafqat/ontolayer/actions/workflows/ci.yml)
[![License: Apache-2.0](https://img.shields.io/badge/License-Apache--2.0-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.12%2B-blue.svg)](pyproject.toml)

OntoLayer is an open-source reference implementation of a business semantic layer. Define concepts,
relationships, mappings, metrics, and policies in YAML; ingest data into a validated knowledge graph;
and let agents retrieve definitions and execute approved calculations over MCP.

The core runs locally without Docker, a database server, an API key, or a model download.
The included LangGraph agent uses a real MCP client. Optional Ollama and OpenAI-compatible
planners add natural-language flexibility while calculations remain deterministic.

## Five-minute quickstart

Requires Git and [uv](https://docs.astral.sh/uv/getting-started/installation/).
Initial dependency/interpreter downloads need internet access; the demo itself runs offline.

```sh
git clone https://github.com/AshubShafqat/ontolayer.git
cd ontolayer
uv sync --locked --python 3.12
uv run ontolayer validate --ontology examples/retail/ontology.yaml
uv run ontolayer build --ontology examples/retail/ontology.yaml
uv run ontolayer ask "revenue from 2026-10-01 to 2026-11-01" --ontology examples/retail/ontology.yaml --actor examples/retail/north.yaml
```

Expected answer: **250 USD**, scoped to authorized north-region records, certified under ontology
version `1.0.0`, with lineage to `lines.csv`. The JSON contains snapshot and definition hashes.
Run the same question with `admin.yaml` for **600 USD** or `south.yaml` for **350 USD**.
The canceled order and November sales are excluded by the definition and date interval.

On Windows machines where the virtual-environment launcher is unavailable but installed Python
works, `./scripts/dev.ps1 -m ontolayer ...` uses that interpreter with the same dependencies.
It does not modify security settings. Run it from this directory after `uv sync`.

## What works

| Capability | Included |
| --- | --- |
| Ontology as code | Typed YAML, generated JSON Schema, references, owners, versions, certification |
| Modeling | Objects, links, interface contracts and advisory design linter |
| Ingestion | CSV and read-only SQLite adapters, stable identity and source snapshot hashes |
| Graph | RDFLib backend, atomic validation, OWL/Turtle export and SHACL constraints |
| Semantics | Search, entities, relationships, paths, definitions and bounded metric execution |
| Governance | Default deny, role/attribute grants, PII/property filtering before model access |
| Agent access | 11 read-only MCP tools and authenticated REST |
| Reference agent | LangGraph over MCP; rules, Ollama or OpenAI-compatible planner |
| Review workflow | CSV draft scaffolding, isolated proposals, explicit human certification |
| Examples | Retail and agriculture data, identities, policies and evaluation questions |
| Delivery | Tests, strict typing, CI, dependency SBOM/audit, wheel build, optional Docker |

This v0.1 is a complete local reference project, not an enterprise-readiness certification.
Remote graph backends, OIDC, HTTP MCP, document extraction, and production orchestration are not
implemented. See [architecture and limits](docs/architecture.md).

## Try the semantic layer

```sh
uv run ontolayer lint --ontology examples/retail/ontology.yaml
uv run ontolayer export --ontology examples/retail/ontology.yaml --output ontology.ttl
uv run ontolayer query --ontology examples/retail/ontology.yaml --actor examples/retail/admin.yaml --metric revenue --group-by region
uv run ontolayer evaluate --ontology examples/retail/ontology.yaml --questions examples/retail/questions.yaml
uv run ontolayer ask "harvest by crop" --ontology examples/agriculture/ontology.yaml --actor examples/agriculture/north.yaml
```

The no-key planner accepts a metric name/synonym, optional `by dimension`, `dimension=value`, and
`from YYYY-MM-DD to YYYY-MM-DD`. End dates are exclusive. Unsupported qualifiers such as
“last month” trigger clarification rather than guessed dates.

## Connect an agent through MCP

```sh
uv run ontolayer mcp --ontology examples/retail/ontology.yaml --actor examples/retail/north.yaml
```

Use `search_terms → get_metric → check_answerable → query_metric`. Discovery, entity listing,
graph traversal, lineage, and safe policy explanations are also available. The trusted launcher
chooses the actor; tools cannot change it. See the [MCP guide and client config](docs/mcp.md).

For optional local model planning, start Ollama, download a suitable model, then run:

```sh
uv run ontolayer ask "Show October 2026 revenue grouped by region" --ontology examples/retail/ontology.yaml --actor examples/retail/north.yaml --provider ollama --model qwen3:8b
```

For a compatible hosted or local API, use `--provider openai-compatible`,
`--base-url http://localhost:8001/v1` and `--model YOUR_MODEL`. Hosted providers may require
`ONTOLAYER_LLM_API_KEY` in the environment. Only permitted definitions and the question go to the
planner; results are rendered from governed tool output. Provider adapters have protocol-mock tests;
the core suite does not require a live model.

## REST API

```sh
uv run ontolayer serve --ontology examples/retail/ontology.yaml --credentials examples/retail/credentials.yaml
```

Open [interactive API docs](http://127.0.0.1:8000/docs), authorize with `demo-north-token`, and call
`POST /v1/tools/query_metric`:

```json
{"arguments": {"metric_id": "revenue", "start_date": "2026-10-01", "end_date": "2026-11-01"}}
```

The header is `Authorization: Bearer demo-north-token`. Demo tokens are public fixtures for synthetic
data. For real data, create private actors and random credentials with `issue-token`; serve behind TLS
and follow [the policy guide](docs/policy.md) and [security notes](SECURITY.md).
`/health` is public; `/metrics` requires an authenticated operator role.

## Define your own domain

Copy an example directory and change its ontology, sources, mappings, policies and questions.
Keep source files below the ontology's directory. The retail graph is:

```text
Customer ← placedBy — Order ← partOf — OrderLine — forProduct → Product
```

Metrics specify units, grain, filters and dates. Revenue uses actual line prices, not current product
prices. Source adapters map business properties to columns; backend adapters implement graph storage.

```sh
uv run ontolayer draft-csv --source examples/retail/customers.csv --output examples/retail/draft.yaml --namespace retail --concept Customer --owner retail-team
uv run ontolayer propose --candidate examples/retail/draft.yaml
```

Review the proposal, then use `certify --proposal PATH --output NEW_FILE --reviewer NAME` to create
a new certified file. Existing active files are never overwritten. Review source paths relative to
the final ontology location; the CLI does not copy source data. Commit reviewed changes through Git.
Certification records review state; it does not prove source-data accuracy.

## Development

```sh
uv run ruff check src tests scripts
uv run ruff format --check src tests scripts
uv run mypy src
uv run pytest --cov-fail-under=85
uv build
```

CI tests Python 3.12 and 3.13, runs real MCP evaluation, builds distributions, and creates a dependency
audit/SBOM. Docker is optional: `docker compose up --build` exposes the synthetic REST demo on
localhost port 8000. Docker and live model inference need their respective runtimes.

```text
src/ontolayer/   models, validation, adapters, graph, policies, MCP, API, agent, CLI
spec/           generated JSON Schema
examples/       retail and agriculture fixtures, actors, policies, questions
tests/          semantic, security, source, transport and agent checks
docs/           architecture, specification, policies, MCP and decisions
scripts/        fixture generation and Windows development runner
```

## References and license

Inspired by [NVIDIA Auto Ontology](https://github.com/NVIDIA/auto-ontology),
[ModernRelay Omnigraph](https://github.com/ModernRelay/omnigraph),
[TrustGraph](https://github.com/trustgraph-ai/trustgraph), and
[Palantir modeling guidance](https://www.palantir.com/docs/foundry/ontology/ontology-best-practices).
These are architecture references, not bundled backend integrations. See [NOTICE](NOTICE).

Apache-2.0. [Contributing](CONTRIBUTING.md) · [Governance](GOVERNANCE.md) ·
[Code of conduct](CODE_OF_CONDUCT.md) · [Security](SECURITY.md)
