"""Single-process, durable draft review and atomic certified snapshot publication.

Only a namespace administrator may read raw definitions or write proposals. Browser
requests never select arbitrary filesystem paths. Releases copy trusted source
bytes, validate the complete graph, and publish a pointer only after validation.
"""

import csv
import difflib
import hashlib
import io
import json
import re
from pathlib import Path
from typing import Any
from uuid import uuid4

import yaml

from ontolayer.models import Actor, Ontology
from ontolayer.service import Service
from ontolayer.spec import export_graph, lint


class Workbench:
    def __init__(self, service: Service, directory: Path):
        self.service = service
        self.root = directory.resolve() / service.ontology.namespace
        self.root.mkdir(parents=True, exist_ok=True)
        pointer = self.root / "active.json"
        if pointer.exists():
            release = self._identifier(json.loads(pointer.read_text())["release"])
            restored = Service.from_file(self.root / release / "ontology.yaml", service.audit)
            if restored.ontology.namespace != service.ontology.namespace:
                raise ValueError("Stored workspace namespace mismatch")
            self._activate(restored)

    @staticmethod
    def _identifier(value: str) -> str:
        if not re.fullmatch(r"[a-f0-9]{32}", value):
            raise ValueError("Invalid draft identifier")
        return value

    def _authorize(self, actor: Actor) -> None:
        if actor.namespace != self.service.ontology.namespace or "admin" not in actor.roles:
            from ontolayer.service import Denied

            raise Denied("Administrator role required")

    def revision(self) -> str:
        data = self.service.ontology.model_dump_json()
        snapshots = sorted((e.id, e.snapshot) for e in self.service.backend.entities())
        return hashlib.sha256((data + json.dumps(snapshots)).encode()).hexdigest()

    def document(self, actor: Actor) -> dict[str, Any]:
        self._authorize(actor)
        with self.service.lock:
            return {
                "document": self.service.ontology.model_dump(mode="json"),
                "revision": self.revision(),
            }

    def export(self, actor: Actor, format: str) -> str:
        self._authorize(actor)
        with self.service.lock:
            ontology = self.service.ontology
            if format == "json":
                return ontology.model_dump_json(indent=2)
            if format == "yaml":
                return yaml.safe_dump(ontology.model_dump(mode="json"), sort_keys=False)
            if format == "turtle":
                return str(export_graph(ontology).serialize(format="turtle"))
            raise ValueError("Choose yaml, json or turtle")

    def preview(
        self, actor: Actor, document: dict[str, Any], revision: str, uploads: dict[str, str]
    ) -> dict[str, Any]:
        self._authorize(actor)
        with self.service.lock:
            if revision != self.revision():
                raise ValueError("Workspace changed; reload before reviewing")
            candidate = Ontology.model_validate(document)
            active = self.service.ontology
            if candidate.namespace != active.namespace:
                raise ValueError("Namespace cannot change")
            if tuple(map(int, candidate.version.split("."))) <= tuple(
                map(int, active.version.split("."))
            ):
                raise ValueError("Increase the ontology version before creating a draft")
            if set(uploads) - candidate.mappings.keys():
                raise ValueError("Upload must name a candidate mapping")
            if sum(len(v.encode()) for v in uploads.values()) > 48000:
                raise ValueError("Uploads exceed the 48 KB workbench limit")
            for name, mapping in candidate.mappings.items():
                previous = active.mappings.get(name)
                if name not in uploads and (
                    previous is None
                    or mapping.path != previous.path
                    or mapping.kind != previous.kind
                    or mapping.table != previous.table
                ):
                    raise ValueError("New source paths require a CSV upload")
                if name in uploads:
                    if mapping.kind != "csv":
                        raise ValueError("Browser uploads support CSV mappings only")
                    reader = csv.DictReader(io.StringIO(uploads[name]))
                    headers = reader.fieldnames or []
                    if len(headers) != len(set(headers)) or not headers:
                        raise ValueError("CSV headers must be present and unique")
                    expected = {
                        mapping.id_column,
                        *mapping.columns.values(),
                        *mapping.links.values(),
                    }
                    if not expected <= set(headers):
                        raise ValueError("CSV headers do not match the mapping")
                    if len(list(reader)) > 1000:
                        raise ValueError("Upload is limited to 1000 rows")
            identifier = uuid4().hex
            directory = self.root / identifier
            directory.mkdir()
            # All filesystem destinations are generated by the server.
            for name, mapping in candidate.mappings.items():
                destination = f"{name}.{'csv' if mapping.kind == 'csv' else 'sqlite'}"
                if name in uploads:
                    content = uploads[name].encode("utf-8")
                else:
                    root = self.service.source_root
                    if root is None:
                        raise ValueError("No trusted source directory configured")
                    source = (root / active.mappings[name].path).resolve()
                    if not source.is_relative_to(root):
                        raise ValueError("Source escapes trusted directory")
                    content = source.read_bytes()
                (directory / destination).write_bytes(content)
                mapping.path = destination
            for obj in candidate.types.values():
                obj.status = "draft"
            for metric in candidate.metrics.values():
                metric.status = "draft"
            path = directory / "ontology.yaml"
            path.write_text(
                yaml.safe_dump(candidate.model_dump(mode="json"), sort_keys=False), encoding="utf-8"
            )
            validated = Service.from_file(path)
            before = yaml.safe_dump(active.model_dump(mode="json"), sort_keys=False)
            after = path.read_text(encoding="utf-8")
            receipt = {
                "id": identifier,
                "base_revision": revision,
                "creator": actor.id,
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            }
            (directory / "draft.json").write_text(json.dumps(receipt), encoding="utf-8")
            self.service.audit.record(actor, "preview_draft", "allowed", active.version)
            return {
                **receipt,
                "findings": lint(candidate),
                "diff": "".join(
                    difflib.unified_diff(
                        before.splitlines(True),
                        after.splitlines(True),
                        fromfile="active",
                        tofile="draft",
                    )
                ),
                "entities": len(validated.backend.entities()),
                "relationships": len(validated.backend.edges()),
                "mappings": {n: m.model_dump() for n, m in candidate.mappings.items()},
            }

    def certify(self, actor: Actor, identifier: str, revision: str) -> dict[str, Any]:
        self._authorize(actor)
        with self.service.lock:
            directory = self.root / self._identifier(identifier)
            receipt = json.loads((directory / "draft.json").read_text(encoding="utf-8"))
            if revision != self.revision() or receipt["base_revision"] != revision:
                raise ValueError("Stale draft; review against the current workspace")
            proposal = directory / "ontology.yaml"
            if hashlib.sha256(proposal.read_bytes()).hexdigest() != receipt["sha256"]:
                raise ValueError("Draft changed after review")
            candidate = Ontology.model_validate(
                yaml.safe_load(proposal.read_text(encoding="utf-8"))
            )
            for obj in candidate.types.values():
                obj.status = "certified"
            for metric in candidate.metrics.values():
                metric.status = "certified"
            certified = directory / "certified.yaml"
            certified.write_text(
                yaml.safe_dump(candidate.model_dump(mode="json"), sort_keys=False), encoding="utf-8"
            )
            validated = Service.from_file(certified, self.service.audit)
            self.service.audit.record(actor, "certify_draft", "allowed", candidate.version)
            # Rename only after the entire candidate graph passes validation.
            certified.replace(proposal)
            publication = {
                "release": identifier,
                "reviewer": actor.id,
                "version": candidate.version,
            }
            (directory / "review.json").write_text(json.dumps(publication), encoding="utf-8")
            temporary = self.root / f"pointer-{uuid4().hex}.json"
            temporary.write_text(json.dumps(publication), encoding="utf-8")
            temporary.replace(self.root / "active.json")
            self._activate(validated)
            return {**publication, "revision": self.revision()}

    def _activate(self, candidate: Service) -> None:
        self.service.ontology = candidate.ontology
        self.service.backend = candidate.backend
        self.service.source_root = candidate.source_root
