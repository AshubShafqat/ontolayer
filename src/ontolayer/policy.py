"""Default-deny authorization shared by every transport."""

from decimal import Decimal

from ontolayer.models import Actor, Entity, Ontology, Policy


class PolicyEngine:
    def __init__(self, ontology: Ontology, actor: Actor) -> None:
        self.ontology = ontology
        self.actor = actor
        self.rules = [
            p
            for p in ontology.policies
            if p.role in actor.roles and actor.namespace == ontology.namespace
        ]

    def type_allowed(self, type_name: str) -> bool:
        return any(type_name in rule.types for rule in self.rules)

    def metric_allowed(self, metric_id: str) -> bool:
        metric = self.ontology.metrics.get(metric_id)
        return bool(
            metric
            and any(metric_id in rule.metrics and metric.type in rule.types for rule in self.rules)
        )

    def _matches(self, rule: Policy, entity: Entity) -> bool:
        return entity.type in rule.types and all(
            attribute in self.actor.attributes
            and entity.properties.get(prop) == self.actor.attributes[attribute]
            for prop, attribute in rule.row_attributes.items()
        )

    def entity_allowed(self, entity: Entity) -> bool:
        return any(self._matches(rule, entity) for rule in self.rules)

    def fields(self, type_name: str, entity: Entity | None = None) -> set[str]:
        allowed: set[str] = set()
        for rule in self.rules:
            if type_name not in rule.types or (entity and not self._matches(rule, entity)):
                continue
            for name, prop in self.ontology.types[type_name].properties.items():
                if name in rule.properties.get(type_name, []) and (not prop.pii or rule.allow_pii):
                    allowed.add(name)
        return allowed

    def redact(self, entity: Entity) -> dict[str, object]:
        fields = self.fields(entity.type, entity)
        return {
            "id": entity.id,
            "type": entity.type,
            "properties": {
                k: str(v) if isinstance(v, Decimal) else v
                for k, v in entity.properties.items()
                if k in fields
            },
            "status": self.ontology.types[entity.type].status,
        }
