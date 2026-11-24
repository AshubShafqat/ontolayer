import asyncio
import os
import sys
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from typer.testing import CliRunner

from ontolayer.agent import ask, call_tool, model_plan, rule_plan
from ontolayer.api import create_app
from ontolayer.auth import authenticate
from ontolayer.cli import app
from ontolayer.service import Service
from tests.conftest import RETAIL


def test_rest_auth_and_injection(service: Service) -> None:
    client = TestClient(create_app(service, RETAIL / "credentials.yaml"))
    url = "/v1/tools/query_metric"
    assert client.get("/health").json() == {"status": "ok"}
    assert client.post(url, json={}).status_code == 401
    assert client.post(url, headers={"Authorization": "Bearer bad"}, json={}).status_code == 401
    headers = {"Authorization": "Bearer demo-north-token"}
    result = client.post(url, headers=headers, json={"arguments": {"metric_id": "revenue"}})
    assert result.json()["values"] == {"total": "330.0"}
    assert (
        client.post(
            url,
            headers=headers,
            json={"arguments": {"metric_id": "revenue", "actor": {"roles": ["admin"]}}},
        ).status_code
        == 400
    )
    assert (
        client.post(
            "/v1/tools/get_lineage",
            headers=headers,
            json={"arguments": {"entity_id": "Customer:C2"}},
        ).status_code
        == 403
    )
    assert client.get("/metrics", headers=headers).status_code == 403
    assert (
        client.get("/metrics", headers={"Authorization": "Bearer demo-admin-token"}).status_code
        == 200
    )


def test_real_mcp_client() -> None:
    async def scenario() -> None:
        params = StdioServerParameters(
            command=sys.executable,
            args=[
                "-m",
                "ontolayer",
                "mcp",
                "--ontology",
                str(RETAIL / "ontology.yaml"),
                "--actor",
                str(RETAIL / "north.yaml"),
            ],
            env={"PYTHONPATH": os.environ["PYTHONPATH"]} if "PYTHONPATH" in os.environ else None,
        )
        async with stdio_client(params) as (r, w), ClientSession(r, w) as session:
            await session.initialize()
            names = {tool.name for tool in (await session.list_tools()).tools}
            assert names == Service.OPERATIONS
            result = await call_tool(session, "query_metric", metric_id="revenue")
            assert result["values"] == {"total": "330.0"}
            assert not (
                await call_tool(session, "explain_policy_decision", entity_id="Customer:C2")
            )["allowed"]
            with pytest.raises(ValueError):
                await call_tool(session, "get_lineage", entity_id="Customer:C2")

    asyncio.run(scenario())


@pytest.mark.parametrize(
    "question, expected",
    [
        ("revenue from 2026-10-01 to 2026-11-01", "250.0"),
        ("revenue by region", "330.0"),
        ("profit next year", None),
        ("revenue last month", None),
    ],
)
def test_real_reference_agent(question: str, expected: str | None) -> None:
    result = asyncio.run(ask(RETAIL / "ontology.yaml", RETAIL / "north.yaml", question))
    if expected:
        assert expected in result["answer"]
        assert "lines.csv" in result["answer"]
        assert result["result"]["status"] == "certified"
    else:
        assert result["result"]["answerable"] is False


def test_rule_planner_is_conservative() -> None:
    definitions = [{"id": "revenue", "synonyms": ["sales"]}, {"id": "orders"}]
    assert rule_plan("revenue and orders", definitions).clarification
    assert rule_plan("revenue region=north", definitions).filters == {"region": "north"}
    assert rule_plan("revenue excluding refunds", definitions).clarification


@pytest.mark.parametrize("provider", ["ollama", "openai-compatible"])
def test_model_protocol_with_mock_server(monkeypatch: pytest.MonkeyPatch, provider: str) -> None:
    def response(request: httpx.Request) -> httpx.Response:
        content = '{"metric_id":"revenue"}'
        body = (
            {"message": {"content": content}}
            if provider == "ollama"
            else {"choices": [{"message": {"content": content}}]}
        )
        return httpx.Response(200, json=body)

    original = httpx.AsyncClient
    monkeypatch.setattr(
        httpx,
        "AsyncClient",
        lambda **kwargs: original(transport=httpx.MockTransport(response), **kwargs),
    )
    plan = asyncio.run(model_plan("revenue", [], provider, "test", "http://model.invalid"))
    assert plan.metric_id == "revenue"


def test_cli_commands(tmp_path: Path) -> None:
    runner = CliRunner()
    for command in ("validate", "lint", "build"):
        result = runner.invoke(app, [command, "--ontology", str(RETAIL / "ontology.yaml")])
        assert result.exit_code == 0, result.output
    assert runner.invoke(app, ["version"]).exit_code == 0
    output = tmp_path / "schema.json"
    assert runner.invoke(app, ["schema", "--output", str(output)]).exit_code == 0
    assert output.exists()
    for flag in ([], ["--data"]):
        result = runner.invoke(
            app,
            [
                "export",
                "--ontology",
                str(RETAIL / "ontology.yaml"),
                "--output",
                str(tmp_path / "out.ttl"),
                *flag,
            ],
        )
        assert result.exit_code == 0, result.output
    result = runner.invoke(
        app,
        [
            "query",
            "--ontology",
            str(RETAIL / "ontology.yaml"),
            "--actor",
            str(RETAIL / "north.yaml"),
            "--metric",
            "revenue",
        ],
    )
    assert result.exit_code == 0
    assert "330.0" in result.output
    output = tmp_path / "credentials.yaml"
    result = runner.invoke(
        app, ["issue-token", "--actor", str(RETAIL / "north.yaml"), "--output", str(output)]
    )
    assert result.exit_code == 0
    assert authenticate(result.output.strip(), output).id == "demo-north"
