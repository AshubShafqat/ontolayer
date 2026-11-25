from decimal import Decimal

import pytest

from ontolayer.models import Actor
from ontolayer.policy import PolicyEngine
from ontolayer.service import Service
from ontolayer.sources import convert


def test_numeric_source_preserves_decimal_precision() -> None:
    result = convert("9007199254740993.01", "number")
    assert result == Decimal("9007199254740993.01")
    assert isinstance(result, Decimal)
    with pytest.raises(ValueError, match="28 significant"):
        convert("12345678901234567890123456789.01", "number")
    assert convert("1234567890123456789012345678", "number") == Decimal(
        "1234567890123456789012345678"
    )
    with pytest.raises(ValueError, match="exponents"):
        convert("1e99999999", "number")


def test_decimal_entity_values_are_serialized_without_float_conversion(
    service: Service,
    north: Actor,
) -> None:
    entity = next(e for e in service.backend.entities() if e.id == "OrderLine:L1")
    entity.properties["unit_price"] = Decimal("9007199254740993.01")
    redacted = PolicyEngine(service.ontology, north).redact(entity)
    assert redacted["properties"]["unit_price"] == "9007199254740993.01"
