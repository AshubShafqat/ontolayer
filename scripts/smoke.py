"""Live production smoke test. Never print credentials or record contents."""

import json
import os
import sys
import urllib.error
import urllib.request
from decimal import Decimal
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


def main() -> None:
    base = sys.argv[1].rstrip("/")
    parsed = urlparse(base)
    if parsed.scheme != "https" and not (
        parsed.scheme == "http" and parsed.hostname in {"127.0.0.1", "localhost"}
    ):
        raise SystemExit("Use HTTPS for public hosts")
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise SystemExit("Use an origin URL without credentials or query parameters")

    def request(
        path: str, token: str | None = None, arguments: dict[str, Any] | None = None
    ) -> tuple[int, Any]:
        headers = {"Content-Type": "application/json"}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        data = json.dumps({"arguments": arguments}).encode() if arguments is not None else None
        req = urllib.request.Request(base + path, data=data, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=120) as response:
                raw = response.read()
                return response.status, json.loads(
                    raw
                ) if "application/json" in response.headers.get("Content-Type", "") else raw
        except urllib.error.HTTPError as error:
            return error.code, json.loads(error.read())

    assert request("/health") == (200, {"status": "ok"})
    print("PASS /health")
    for path in ["/", "/static/app.js"]:
        status, body = request(path)
        assert status == 200 and body
        print(f"PASS {path}")
    status, config = request("/v1/config")
    assert status == 200 and config["demo"] is False and config["docs"] is False
    print("PASS production profile")
    manifest = os.environ.get("ONTOLAYER_SMOKE_TOKENS_FILE")
    tokens = (
        json.loads(Path(manifest).read_text(encoding="utf-8"))
        if manifest
        else config["public_demo_tokens"]
    )
    for role, expected in [("north", "250.0"), ("south", "350.0"), ("analyst", "600.0")]:
        status, result = request(
            "/v1/tools/query_metric",
            tokens[role],
            {
                "metric_id": "revenue",
                "start_date": "2026-10-01",
                "end_date": "2026-11-01",
            },
        )
        assert status == 200 and Decimal(result["values"]["total"]) == Decimal(expected)
        print(f"PASS {role} October revenue = {expected}")
    status, listing = request("/v1/tools/list_entities", tokens["south"], {"concept": "Customer"})
    assert status == 200 and listing["items"]
    hidden = listing["items"][0]["id"]
    denied = []
    for entity in [hidden, "Customer:nonexistent-smoke-record"]:
        status, result = request("/v1/tools/get_lineage", tokens["north"], {"entity_id": entity})
        assert status == 403
        # Request IDs intentionally differ; business error bodies must match.
        result.pop("request_id", None)
        denied.append(result)
    assert denied[0] == denied[1]
    status, north = request("/v1/tools/list_entities", tokens["north"], {"concept": "Customer"})
    assert status == 200 and hidden not in {item["id"] for item in north["items"]}
    print("PASS north cannot see south record; hidden and missing are indistinguishable")
    print("PASS all live smoke checks")


if __name__ == "__main__":
    main()
