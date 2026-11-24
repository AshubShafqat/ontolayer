from pathlib import Path

import pytest

from ontolayer.auth import actor_from_file
from ontolayer.models import Actor
from ontolayer.service import Service

ROOT = Path(__file__).resolve().parents[1]
RETAIL = ROOT / "examples" / "retail"


@pytest.fixture
def service() -> Service:
    return Service.from_file(RETAIL / "ontology.yaml")


@pytest.fixture
def admin() -> Actor:
    return actor_from_file(RETAIL / "admin.yaml")


@pytest.fixture
def north() -> Actor:
    return actor_from_file(RETAIL / "north.yaml")
