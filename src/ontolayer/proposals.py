"""Human-reviewed draft workflow. Agent proposals cannot replace active definitions."""

import hashlib
import json
from pathlib import Path
from uuid import uuid4

import yaml

from ontolayer.models import Ontology
from ontolayer.spec import lint, load


def propose(candidate: Path, directory: Path) -> Path:
    ontology = load(candidate)
    for obj in ontology.types.values():
        obj.status = "draft"
    for metric in ontology.metrics.values():
        metric.status = "draft"
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{uuid4().hex}.yaml"
    path.write_text(yaml.safe_dump(ontology.model_dump(), sort_keys=False), encoding="utf-8")
    return path


def certify(proposal: Path, output: Path, reviewer: str) -> None:
    """Trusted maintainer command. Exclusive creation never overwrites an active ontology."""
    if not reviewer.strip():
        raise ValueError("A reviewer is required")
    ontology = load(proposal)
    for obj in ontology.types.values():
        obj.status = "certified"
    for metric in ontology.metrics.values():
        metric.status = "certified"
    receipt = {
        "reviewer": reviewer,
        "proposal_sha256": hashlib.sha256(proposal.read_bytes()).hexdigest(),
        "version": ontology.version,
        "warnings": lint(ontology),
    }
    with output.open("x", encoding="utf-8") as handle:
        handle.write(yaml.safe_dump(ontology.model_dump(), sort_keys=False))
    output.with_suffix(".review.json").write_text(json.dumps(receipt, indent=2), encoding="utf-8")


def draft_csv(source: Path, namespace: str, concept: str, owner: str, output: Path) -> None:
    """Produce a conservative draft from headers; a human assigns semantics and policies."""
    import csv

    from ontolayer.models import ObjectType, Property, SourceMapping

    with source.open(encoding="utf-8-sig", newline="") as handle:
        headers = csv.DictReader(handle).fieldnames
    if not headers or "id" not in headers:
        raise ValueError("CSV needs a header and an id column")
    relative = source.resolve().relative_to(output.parent.resolve()).as_posix()
    ontology = Ontology(
        namespace=namespace,
        version="0.1.0",
        description="Unreviewed CSV-derived draft",
        types={
            concept: ObjectType(
                description=f"Review business meaning of {concept}",
                owner=owner,
                properties={
                    h: Property(description=f"Review meaning of {h}") for h in headers if h != "id"
                },
            )
        },
        mappings={
            "source": SourceMapping(
                type=concept,
                path=relative,
                id_column="id",
                columns={h: h for h in headers if h != "id"},
            )
        },
    )
    with output.open("x", encoding="utf-8") as handle:
        handle.write(yaml.safe_dump(ontology.model_dump(), sort_keys=False))
