import asyncio
import json
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from typer.testing import CliRunner

from ontolayer.agent import call_tool
from ontolayer.api import create_app
from ontolayer.auth import actor_from_file
from ontolayer.cli import app
from ontolayer.server import create_mcp
from ontolayer.service import Denied, Service
from tests.conftest import RETAIL


def mcp_parameters(role: str, audit: Path) -> StdioServerParameters:
    return StdioServerParameters(
        command=sys.executable,
        args=[
            "-m",
            "ontolayer",
            "mcp",
            "--ontology",
            str(RETAIL / "ontology.yaml"),
            "--actor",
            str(RETAIL / f"{role}.yaml"),
            "--audit",
            str(audit),
        ],
    )


def test_october_revenue_all_transports(service: Service, tmp_path: Path) -> None:
    """One matrix verifies the same dated metric on all three actual transports."""
    args = {"metric_id": "revenue", "start_date": "2026-10-01", "end_date": "2026-11-01"}
    client = TestClient(create_app(service, RETAIL / "credentials.yaml"))

    async def scenario() -> None:
        for role, expected in [("north", "250.0"), ("south", "350.0"), ("analyst", "600.0")]:
            cli = CliRunner().invoke(
                app,
                [
                    "query",
                    "--ontology",
                    str(RETAIL / "ontology.yaml"),
                    "--actor",
                    str(RETAIL / f"{role}.yaml"),
                    "--metric",
                    "revenue",
                    "--start-date",
                    args["start_date"],
                    "--end-date",
                    args["end_date"],
                ],
            )
            assert cli.exit_code == 0, cli.output
            assert json.loads(cli.stdout)["values"] == {"total": expected}
            response = client.post(
                "/v1/tools/query_metric",
                json={"arguments": args},
                headers={"Authorization": f"Bearer demo-{role}-token"},
            )
            assert response.status_code == 200
            assert response.json()["values"] == {"total": expected}
            async with stdio_client(mcp_parameters(role, tmp_path / f"{role}.jsonl")) as (r, w):
                async with ClientSession(r, w) as session:
                    await session.initialize()
                    result = await call_tool(session, "query_metric", **args)
                    assert result["values"] == {"total": expected}

    asyncio.run(scenario())


def test_mcp_hidden_and_missing_are_identical(tmp_path: Path) -> None:
    async def scenario() -> None:
        async with stdio_client(mcp_parameters("admin", tmp_path / "admin.jsonl")) as (r, w):
            async with ClientSession(r, w) as session:
                await session.initialize()
                records = await call_tool(session, "list_entities", concept="Customer")
                hidden = next(
                    row["id"] for row in records["items"] if row["properties"]["region"] == "south"
                )
                visible = next(
                    row["id"] for row in records["items"] if row["properties"]["region"] == "north"
                )
        async with stdio_client(mcp_parameters("north", tmp_path / "north.jsonl")) as (r, w):
            async with ClientSession(r, w) as session:
                await session.initialize()
                for operation in [
                    "get_lineage",
                    "get_relationships",
                    "find_path",
                    "explain_policy_decision",
                ]:
                    replies = []
                    for entity in [hidden, "Customer:missing"]:
                        arguments = (
                            {"source": visible, "target": entity}
                            if operation == "find_path"
                            else {"entity_id": entity}
                        )
                        response = await session.call_tool(operation, arguments)
                        replies.append(response.model_dump(exclude_none=True))
                    assert replies[0] == replies[1], operation
                    serialized = json.dumps(replies[0])
                    assert hidden not in serialized
                    assert "snapshot_sha256" not in serialized
                    assert "next_offset" not in serialized

    asyncio.run(scenario())


def test_guest_all_mcp_tools_return_no_business_data(tmp_path: Path) -> None:
    arguments = {
        "search_terms": {},
        "get_concept": {"concept": "Customer"},
        "list_entities": {"concept": "Customer"},
        "get_relationships": {"entity_id": "Customer:C1"},
        "find_path": {"source": "Customer:C1", "target": "Order:O1"},
        "get_metric": {"metric_id": "revenue"},
        "query_metric": {"metric_id": "revenue"},
        "check_answerable": {"metric_id": "revenue"},
        "get_lineage": {"entity_id": "Customer:C1"},
        "explain_policy_decision": {"entity_id": "Customer:C1"},
        "list_ontology_versions": {},
    }
    assert set(arguments) == Service.OPERATIONS

    async def scenario() -> None:
        async with stdio_client(mcp_parameters("guest", tmp_path / "guest.jsonl")) as (r, w):
            async with ClientSession(r, w) as session:
                await session.initialize()
                for operation, args in arguments.items():
                    response = await session.call_tool(operation, args)
                    if operation == "search_terms":
                        assert response.structuredContent == {"items": [], "next_offset": None}
                    elif operation == "check_answerable":
                        assert response.structuredContent == {
                            "answerable": False,
                            "reason": "No available certified metric for this request",
                        }
                    elif operation == "explain_policy_decision":
                        assert response.structuredContent == {
                            "allowed": False,
                            "reason": "Not available to this caller",
                        }
                    else:
                        assert response.isError
                        assert "Not available to this caller" in str(response.content)
                        assert "Customer:C1" not in str(response.content)

    asyncio.run(scenario())


def test_cli_denial_and_all_dates() -> None:
    args = ["query", "--ontology", str(RETAIL / "ontology.yaml"), "--metric", "revenue", "--actor"]
    denied = CliRunner().invoke(app, [*args, str(RETAIL / "guest.yaml")])
    assert denied.exit_code == 1
    assert denied.stderr == "Error: Not available to this caller\n"
    assert "Traceback" not in denied.output
    assert denied.stdout == ""
    allowed = CliRunner().invoke(app, [*args, str(RETAIL / "north.yaml")])
    assert allowed.exit_code == 0
    assert "All dates" in allowed.stderr
    result = json.loads(allowed.stdout)
    assert result["start_date"] is None and result["end_date_exclusive"] is None
    assert result["values"]["total"] == "330.0"


@pytest.mark.parametrize("command", ["build", "export", "mcp", "serve", "query"])
def test_cli_service_commands_catch_denial(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, command: str
) -> None:
    def denied(*args: object, **kwargs: object) -> Service:
        raise Denied("sensitive internal detail")

    monkeypatch.setattr(Service, "from_file", denied)
    args = [command, "--ontology", str(RETAIL / "ontology.yaml")]
    if command in ["mcp", "query"]:
        args += ["--actor", str(RETAIL / "north.yaml")]
    if command == "query":
        args += ["--metric", "revenue"]
    if command == "export":
        args += ["--data", "--output", str(tmp_path / "data.ttl")]
    if command == "serve":
        args += ["--credentials", str(RETAIL / "credentials.yaml")]
    result = CliRunner().invoke(app, args)
    assert result.exit_code == 1
    assert result.stderr == "Error: Not available to this caller\n"
    assert result.stdout == ""


def test_mcp_descriptions_document_actual_arguments(service: Service) -> None:
    async def scenario() -> None:
        server = create_mcp(service, actor_from_file(RETAIL / "north.yaml"))
        tools = await server.list_tools()
        assert len(tools) == 11
        for tool in tools:
            description = tool.description or ""
            assert (
                "Arguments:" in description
                and "Example:" in description
                and "Returns:" in description
            )
            for name in tool.inputSchema.get("properties", {}):
                assert name in description

    asyncio.run(scenario())


def test_public_demo_manifest_cannot_publish_admin(service: Service, tmp_path: Path) -> None:
    import hashlib
    import secrets

    import yaml

    from ontolayer.service import AuditLog

    tokens = {role: secrets.token_urlsafe(32) for role in ["north", "south", "analyst", "admin"]}
    credentials = tmp_path / "credentials.yaml"
    credentials.write_text(
        yaml.safe_dump(
            {
                "credentials": [
                    {
                        "token_sha256": hashlib.sha256(token.encode()).hexdigest(),
                        "actor": actor_from_file(RETAIL / f"{role}.yaml").model_dump(),
                    }
                    for role, token in tokens.items()
                ]
            }
        ),
        encoding="utf-8",
    )
    public = tmp_path / "public.json"
    public.write_text(json.dumps({k: v for k, v in tokens.items() if k != "admin"}))
    service.audit = AuditLog(tmp_path / "audit.jsonl")
    client = TestClient(
        create_app(
            service,
            credentials,
            production=True,
            allowed_hosts=["testserver"],
            public_demo_tokens=public,
        )
    )
    config = client.get("/v1/config").json()
    assert config["demo"] is False and config["docs"] is False
    assert set(config["public_demo_tokens"]) == {"north", "south", "analyst"}
    assert tokens["admin"] not in json.dumps(config)
    assert client.get("/docs").status_code == 404
    headers = {"Authorization": f"Bearer {tokens['north']}"}
    assert (
        client.post(
            "/v1/drafts/validate", headers=headers, json={"document": {}, "revision": "a" * 64}
        ).status_code
        == 403
    )
    public.write_text(
        json.dumps(
            {"north": tokens["admin"], "south": tokens["south"], "analyst": tokens["analyst"]}
        )
    )
    with pytest.raises(ValueError, match="read-only"):
        create_app(service, credentials, public_demo_tokens=public)
    public.write_text(json.dumps(tokens))
    with pytest.raises(ValueError, match="exactly three"):
        create_app(service, credentials, public_demo_tokens=public)


def test_hosted_container_command() -> None:
    import runpy

    command = runpy.run_path("scripts/container_entrypoint.py")["command"]
    assert command({}, ["version"]) == ["ontolayer", "version"]
    args = command(
        {"ONTOLAYER_HOSTED": "1", "RENDER_EXTERNAL_HOSTNAME": "example.onrender.com"}, []
    )
    assert "--production" in args and "--demo" not in args
    assert args[args.index("--allowed-host") + 1] == "example.onrender.com"
    assert args[args.index("--audit") + 1] == "/state/audit.jsonl"
    assert args[args.index("--workspace-directory") + 1] == "/state/workspace"
    for host in ["", "*", "https://example.com", "example.com/"]:
        with pytest.raises(ValueError, match="hostname"):
            command({"ONTOLAYER_HOSTED": "1", "RENDER_EXTERNAL_HOSTNAME": host}, [])
