"""Application-facing views built only from the caller's permitted semantic data."""

from typing import Any

from ontolayer.agent import rule_plan
from ontolayer.models import Actor
from ontolayer.service import Denied, Service


def workspace(service: Service, actor: Actor) -> dict[str, Any]:
    terms: list[dict[str, Any]] = []
    offset: int | None = 0
    while offset is not None:
        page = service.call(actor, "search_terms", limit=100, offset=offset)
        terms.extend(page["items"])
        offset = page["next_offset"]
    concepts = []
    metrics = []
    for term in terms:
        if term["kind"] == "concept":
            concepts.append(service.call(actor, "get_concept", concept=term["id"]))
        else:
            try:
                metrics.append(service.call(actor, "get_metric", metric_id=term["id"]))
            except Denied:
                continue
    concept_ids = {c["id"] for c in concepts}
    # Schema relationships only; no unfiltered entity records or source paths are exposed.
    links = [
        {"id": key, **link.model_dump()}
        for key, link in service.ontology.links.items()
        if link.source in concept_ids and link.target in concept_ids
    ]
    return {
        "actor": actor.model_dump(),
        "namespace": service.ontology.namespace,
        "version": service.ontology.version,
        "concepts": concepts,
        "metrics": metrics,
        "links": links,
        "scope": "authorized records only",
    }


def answer(service: Service, actor: Actor, question: str) -> dict[str, Any]:
    definitions = workspace(service, actor)["metrics"]
    plan = rule_plan(question, definitions)
    if plan.clarification or not plan.metric_id:
        return {"answerable": False, "answer": plan.clarification or "Choose a metric."}
    ready = service.call(actor, "check_answerable", metric_id=plan.metric_id)
    if not ready["answerable"]:
        return {"answerable": False, "answer": "No available certified metric. Please clarify."}
    result = service.call(
        actor,
        "query_metric",
        **plan.model_dump(
            exclude={"clarification"},
            exclude_none=True,
        ),
    )
    return {
        "answerable": True,
        "result": result,
        "plan": plan.model_dump(),
        "answer": ", ".join(
            f"{key}: {value} {result['unit']}" for key, value in result["values"].items()
        ),
    }
