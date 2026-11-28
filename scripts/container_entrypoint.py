"""Preserve ordinary Docker CLI usage; hosted mode always uses production safeguards."""

import base64
import os
import sys
from pathlib import Path


def command(environment: dict[str, str], arguments: list[str]) -> list[str]:
    if environment.get("ONTOLAYER_HOSTED") != "1":
        return ["ontolayer", *arguments]
    hostname = environment.get("RENDER_EXTERNAL_HOSTNAME", "")
    if not hostname or any(c in hostname for c in "/*: "):
        raise ValueError("RENDER_EXTERNAL_HOSTNAME must be an exact hostname")
    state = environment.get("ONTOLAYER_STATE_DIRECTORY", "/state")
    credentials = "/etc/secrets/credentials.yaml"
    public_tokens = "/etc/secrets/public-demo.json"
    encoded_credentials = environment.get("ONTOLAYER_CREDENTIALS_B64")
    encoded_public = environment.get("ONTOLAYER_PUBLIC_DEMO_B64")
    if encoded_credentials is not None or encoded_public is not None:
        if not encoded_credentials or not encoded_public:
            raise ValueError("Both encoded deployment files must be configured")
        try:
            private_bytes = base64.b64decode(encoded_credentials, validate=True)
            public_bytes = base64.b64decode(encoded_public, validate=True)
        except ValueError:
            raise ValueError("Invalid encoded deployment files") from None
        os.umask(0o077)
        directory = Path(state)
        directory.mkdir(parents=True, exist_ok=True)
        for filename, content in [
            ("credentials.yaml", private_bytes),
            ("public-demo.json", public_bytes),
        ]:
            destination = directory / filename
            destination.write_bytes(content)
            destination.chmod(0o600)
        credentials = str(directory / "credentials.yaml")
        public_tokens = str(directory / "public-demo.json")
    return [
        "ontolayer",
        "serve",
        "--production",
        "--host",
        "0.0.0.0",
        "--port",
        environment.get("PORT", "8000"),
        "--allowed-host",
        hostname,
        "--allowed-host",
        "127.0.0.1",
        "--ontology",
        "examples/retail/ontology.yaml",
        "--credentials",
        credentials,
        "--public-demo-tokens",
        public_tokens,
        "--audit",
        f"{state}/audit.jsonl",
        "--workspace-directory",
        f"{state}/workspace",
    ]


if __name__ == "__main__":
    args = command(dict(os.environ), sys.argv[1:])
    os.execvp(args[0], args)
