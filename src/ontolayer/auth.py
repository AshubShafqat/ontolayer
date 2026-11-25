"""Server-owned identities. Tokens are stored as SHA-256 digests, never plaintext."""

import hashlib
import secrets
from pathlib import Path
from typing import Self

import yaml
from pydantic import Field, model_validator

from ontolayer.models import Actor, Model


class Credential(Model):
    token_sha256: str = Field(pattern="^[0-9a-f]{64}$")
    actor: Actor


class Credentials(Model):
    credentials: list[Credential] = Field(min_length=1)

    @model_validator(mode="after")
    def unique_tokens(self) -> Self:
        digests = [entry.token_sha256 for entry in self.credentials]
        if len(digests) != len(set(digests)):
            raise ValueError("Credential digests must be unique")
        return self


def load_credentials(path: Path) -> Credentials:
    return Credentials.model_validate(yaml.safe_load(path.read_text(encoding="utf-8")))


def authenticate(token: str, path: Path) -> Actor:
    credentials = load_credentials(path)
    digest = hashlib.sha256(token.encode()).hexdigest()
    for entry in credentials.credentials:
        if secrets.compare_digest(entry.token_sha256, digest):
            return entry.actor
    raise ValueError("Invalid credential")


def actor_from_file(path: Path) -> Actor:
    return Actor.model_validate(yaml.safe_load(path.read_text(encoding="utf-8")))
