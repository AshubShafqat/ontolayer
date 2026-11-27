"""Preserve ordinary Docker CLI usage; hosted mode always uses production safeguards."""

import os
import sys


def command(environment: dict[str, str], arguments: list[str]) -> list[str]:
    if environment.get("ONTOLAYER_HOSTED") != "1":
        return ["ontolayer", *arguments]
    hostname = environment.get("RENDER_EXTERNAL_HOSTNAME", "")
    if not hostname or any(c in hostname for c in "/*: "):
        raise ValueError("RENDER_EXTERNAL_HOSTNAME must be an exact hostname")
    state = environment.get("ONTOLAYER_STATE_DIRECTORY", "/state")
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
        "/etc/secrets/credentials.yaml",
        "--public-demo-tokens",
        "/etc/secrets/public-demo.json",
        "--audit",
        f"{state}/audit.jsonl",
        "--workspace-directory",
        f"{state}/workspace",
    ]


if __name__ == "__main__":
    args = command(dict(os.environ), sys.argv[1:])
    os.execvp(args[0], args)
