"""Question-based evaluation against real MCP agent executions."""

from pathlib import Path
from typing import Any

import yaml

from ontolayer.agent import ask


async def evaluate(ontology: Path, questions: Path) -> dict[str, Any]:
    cases = yaml.safe_load(questions.read_text(encoding="utf-8"))
    results = []
    for case in cases:
        result = await ask(ontology, questions.parent / case["actor"], case["question"])
        actual = result["result"]
        passed = (
            actual.get("answerable") is False
            if case.get("refuse")
            else actual.get("values") == case["expected"]
        )
        results.append({"question": case["question"], "passed": passed, "answer": result["answer"]})
    return {"passed": sum(r["passed"] for r in results), "total": len(results), "results": results}
