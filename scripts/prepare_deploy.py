"""Generate deployment credentials through issue-token without printing any secrets."""

import base64
import json
import os
import subprocess
import sys
from pathlib import Path

import yaml


def main() -> None:
    os.umask(0o077)
    destination = Path(".ontolayer/deploy")
    destination.mkdir(parents=True, exist_ok=False)
    records = []
    public = {}
    for role in ("north", "south", "analyst", "admin"):
        output = destination / f"{role}-credential.yaml"
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "ontolayer",
                "issue-token",
                "--actor",
                f"examples/retail/{role}.yaml",
                "--output",
                str(output),
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        token = result.stdout.strip()
        records.extend(yaml.safe_load(output.read_text(encoding="utf-8"))["credentials"])
        if role == "admin":
            (destination / "admin-token.txt").write_text(token + "\n", encoding="utf-8")
        else:
            public[role] = token
    (destination / "credentials.yaml").write_text(
        yaml.safe_dump({"credentials": records}), encoding="utf-8"
    )
    (destination / "public-demo.json").write_text(
        json.dumps(public, indent=2) + "\n", encoding="utf-8"
    )
    environment = {
        "ONTOLAYER_HOSTED": "1",
        "PORT": "8000",
        "ONTOLAYER_STATE_DIRECTORY": "/state",
        "ONTOLAYER_CREDENTIALS_B64": base64.b64encode(
            (destination / "credentials.yaml").read_bytes()
        ).decode(),
        "ONTOLAYER_PUBLIC_DEMO_B64": base64.b64encode(
            (destination / "public-demo.json").read_bytes()
        ).decode(),
        "ONTOLAYER_ADMIN_TOKEN": (destination / "admin-token.txt").read_text().strip(),
    }
    (destination / "render.env").write_text(
        "".join(f"{key}={value}\n" for key, value in environment.items()), encoding="utf-8"
    )
    print(
        "Created .ontolayer/deploy (gitignored). "
        "Upload credentials.yaml and public-demo.json as host secret files."
    )
    print("Keep admin-token.txt private in your secret manager; never publish its contents.")


if __name__ == "__main__":
    main()
