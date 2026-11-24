"""CLI entry points for maintainers, transports, and the reference agent."""

import asyncio
import hashlib
import json
import secrets
from pathlib import Path
from typing import Annotated, Literal

import typer
import uvicorn
import yaml

from ontolayer import __version__
from ontolayer.agent import ask as agent_ask
from ontolayer.api import create_app
from ontolayer.auth import actor_from_file
from ontolayer.evaluation import evaluate
from ontolayer.proposals import certify as certify_proposal
from ontolayer.proposals import draft_csv, propose
from ontolayer.server import create_mcp
from ontolayer.service import AuditLog, Service
from ontolayer.spec import export_graph, load, write_schema
from ontolayer.spec import lint as lint_spec

app = typer.Typer(help="OntoLayer: business ontology, knowledge graphs, and governed MCP.")
FileOption = Annotated[Path, typer.Option(exists=True, dir_okay=False)]


@app.command("evaluate")
def evaluate_command(ontology: FileOption, questions: FileOption) -> None:
    """Evaluate fixture questions through the reference agent and real MCP transport."""
    result = asyncio.run(evaluate(ontology, questions))
    emit(result)
    if result["passed"] != result["total"]:
        raise typer.Exit(1)


def emit(value: object) -> None:
    typer.echo(json.dumps(value, indent=2, ensure_ascii=False))


@app.command()
def version() -> None:
    """Show package version."""
    typer.echo(__version__)


@app.command()
def validate(ontology: FileOption) -> None:
    """Validate syntax, typed references, policies, mappings, and metric definitions."""
    document = load(ontology)
    emit({"valid": True, "namespace": document.namespace, "version": document.version})


@app.command()
def lint(ontology: FileOption) -> None:
    """Report advisory business modeling warnings."""
    emit(lint_spec(load(ontology)))


@app.command()
def schema(output: Path = Path("spec/ontology.schema.json")) -> None:
    """Write the JSON Schema for editor and CI integrations."""
    write_schema(output)


@app.command()
def export(ontology: FileOption, output: Path = Path("ontology.ttl"), data: bool = False) -> None:
    """Export schema/SHACL or data as Turtle. Trusted local maintainer command."""
    content = (
        Service.from_file(ontology).backend.export()
        if data
        else export_graph(load(ontology)).serialize(format="turtle")
    )
    output.write_text(content, encoding="utf-8")
    emit({"written": str(output)})


@app.command()
def build(ontology: FileOption) -> None:
    """Ingest and validate all sources atomically."""
    service = Service.from_file(ontology)
    emit(
        {
            "entities": len(service.backend.entities()),
            "edges": len(service.backend.edges()),
            "version": service.ontology.version,
        }
    )


@app.command()
def mcp(
    ontology: FileOption, actor: FileOption, audit: Path = Path(".ontolayer/audit.jsonl")
) -> None:
    """Run MCP over stdio with the launcher's trusted actor (no stdout logs)."""
    service = Service.from_file(ontology, AuditLog(audit))
    create_mcp(service, actor_from_file(actor)).run(transport="stdio")


@app.command()
def serve(
    ontology: FileOption,
    credentials: FileOption,
    host: str = "127.0.0.1",
    port: int = 8000,
    audit: Path = Path(".ontolayer/audit.jsonl"),
) -> None:
    """Run the token-authenticated REST service; /docs contains the interactive API."""
    service = Service.from_file(ontology, AuditLog(audit))
    uvicorn.run(create_app(service, credentials), host=host, port=port)


@app.command()
def ask(
    question: str,
    ontology: FileOption,
    actor: FileOption,
    provider: Literal["rules", "ollama", "openai-compatible"] = "rules",
    model: str = "qwen3:8b",
    base_url: str = "http://localhost:11434",
) -> None:
    """Run the LangGraph reference agent against a real MCP subprocess."""
    emit(asyncio.run(agent_ask(ontology, actor, question, provider, model, base_url)))


@app.command()
def query(
    ontology: FileOption,
    actor: FileOption,
    metric: Annotated[str, typer.Option()],
    group_by: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
) -> None:
    """Execute a metric directly, using exactly the same service as MCP."""
    service = Service.from_file(ontology)
    emit(
        service.call(
            actor_from_file(actor),
            "query_metric",
            metric_id=metric,
            group_by=group_by,
            start_date=start_date,
            end_date=end_date,
        )
    )


@app.command("propose")
def propose_command(candidate: FileOption, directory: Path = Path(".ontolayer/proposals")) -> None:
    """Validate a candidate and save a separate draft for review."""
    emit({"proposal": str(propose(candidate, directory))})


@app.command()
def certify(
    proposal: FileOption,
    output: Annotated[Path, typer.Option()],
    reviewer: Annotated[str, typer.Option()],
) -> None:
    """Human maintainer workflow: certify to a new file, never overwrite main."""
    certify_proposal(proposal, output, reviewer)
    emit({"certified": str(output)})


@app.command("draft-csv")
def draft_csv_command(
    source: FileOption,
    output: Annotated[Path, typer.Option()],
    namespace: Annotated[str, typer.Option()],
    concept: Annotated[str, typer.Option()],
    owner: Annotated[str, typer.Option()],
) -> None:
    """Propose an ontology from CSV headers. All concepts remain drafts, default deny."""
    draft_csv(source, namespace, concept, owner, output)
    emit({"draft": str(output)})


@app.command("issue-token")
def issue_token(actor: FileOption, output: Annotated[Path, typer.Option()]) -> None:
    """Create a credential file and print its random token once. Do not commit this file."""
    token = secrets.token_urlsafe(32)
    record = {
        "credentials": [
            {
                "token_sha256": hashlib.sha256(token.encode()).hexdigest(),
                "actor": actor_from_file(actor).model_dump(),
            }
        ]
    }
    with output.open("x", encoding="utf-8") as handle:
        handle.write(yaml.safe_dump(record))
    typer.echo(token)


if __name__ == "__main__":
    app()
