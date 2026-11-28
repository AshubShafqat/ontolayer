# Deploy OntoLayer as one Render container

This configuration is ready to deploy but does not establish a live URL. Do not
claim a public deployment until the smoke test below passes against Render's URL.

## Accounts and credentials

GitHub CLI access is needed to push the branch and open the PR. Render needs an
account with permission to create a Docker web service and connect this GitHub
repository. Sign in to the Render dashboard locally; never paste a password or
Render API key into chat, a commit, or logs. A Render API key is only necessary
for API-based deployment, not the dashboard steps below.

## Generate credentials locally

From the repository root with `uv sync --locked` completed:

```sh
uv run python scripts/prepare_deploy.py
```

This invokes `ontolayer issue-token` separately for north, south, analyst and
admin, capturing its output without logging tokens. It refuses to overwrite an
existing `.ontolayer/deploy` directory. Store that directory privately. On Windows,
restrict its ACL to your user account; on Unix the script uses umask 077.

In Render, add two **Secret Files** under Environment:

- `credentials.yaml`: contents of `.ontolayer/deploy/credentials.yaml` (digests
  and actor mappings; keep private).
- `public-demo.json`: contents of `.ontolayer/deploy/public-demo.json` (only
  fresh north/south/analyst tokens, intentionally published by the sign-in screen).

Keep `.ontolayer/deploy/admin-token.txt` in your private password manager or a
private Render secret file. Never publish it, and never include an admin token
in `public-demo.json`. The server rejects a public manifest whose authenticated
actors have any roles other than the exact expected regional role and region attribute, or the analyst role.

Only use this public-token configuration with the repository's **synthetic**
retail data. Do not load real business data into this public demo. Public readers
can see everything their three sample roles allow.

## Create the service

1. Open <https://dashboard.render.com>, choose **New → Blueprint**, connect
   `AshubShafqat/ontolayer`, and select the reviewed PR branch (or main after merge).
2. Use the repository-root `render.yaml`. Review the plan: it deliberately uses
   **Free**, one instance, Dockerfile `./Dockerfile`, and health check `/health`.
   No paid resources are requested by the blueprint.
3. Add the two secret files above. If the first deploy starts before they exist,
   it will fail closed; add the files and trigger **Manual Deploy**.
4. Keep `ONTOLAYER_HOSTED=1`, `PORT=8000`, and
   `ONTOLAYER_STATE_DIRECTORY=/state`. Render supplies `RENDER_EXTERNAL_HOSTNAME`.
   Do not set a Docker command override. The container entrypoint builds an
   `ontolayer serve --production` command using that exact public allowed host,
   localhost for container health checks, audit `/state/audit.jsonl`, and
   workspace `/state/workspace`. Uvicorn runs one worker.
5. Wait for Render to report **Live** and copy the actual HTTPS URL. Render
   terminates TLS. Frontend and API remain same-origin; the CSP is unchanged.
6. Run the smoke test below. Only then record the actual URL and the three public
   tokens in README's Live demo section. Never substitute a guessed hostname.

## Persistence and operations

The Free tier may sleep and has an ephemeral filesystem. Audit events and draft /
certified workspace changes are lost after a restart or redeploy. The source
fixture is rebuilt into an in-memory graph. This is suitable only for the public
synthetic read-only demonstration, not durable enterprise data.

For durable state, deliberately select a paid service plan and attach one disk
mounted at `/state` (at least 1 GB). Add the corresponding `disk` block to
`render.yaml` when you choose that paid option. Keep one instance/one writer;
configure backups and audit retention externally. Do not add horizontal scaling
or a second worker. See [production requirements](production.md).

## Verify the live URL

Prerequisites: Python 3.12+ and Bash (Git Bash is suitable on Windows).

```sh
bash scripts/smoke.sh https://ACTUAL-RENDER-HOSTNAME
```

The script retrieves the intentionally public read-only tokens from `/v1/config`.
For a private manifest use `ONTOLAYER_SMOKE_TOKENS_FILE` pointing at a local JSON
file instead. It never prints tokens or record contents. It verifies health,
HTML, JavaScript, production mode, October totals 250.0 / 350.0 / 600.0, and north's
inability to see a south record. Hidden and nonexistent records must produce
identical business errors (excluding unique request IDs).

Expected output (an example, not evidence of a deployed service):

```text
PASS /health
PASS /
PASS /static/app.js
PASS production profile
PASS north October revenue = 250.0
PASS south October revenue = 350.0
PASS analyst October revenue = 600.0
PASS north cannot see south record; hidden and missing are indistinguishable
PASS all live smoke checks
```

Open `<actual-origin>/#about` after sign-in. `/docs` and `/openapi.json` must be
unavailable in production. The sign-in screen publishes only the explicit
read-only manifest, not a demo role switcher. MCP remains stdio and is not exposed
as an HTTP endpoint by this deployment.

References: [Render Docker](https://render.com/docs/docker),
[Blueprint schema](https://render.com/docs/blueprint-spec),
[persistent disks](https://render.com/docs/disks).

## Import credentials without copying their contents

As an alternative to Render Secret Files, `scripts/prepare_deploy.py` also creates
`.ontolayer/deploy/render.env`. In Render choose **Add from .env → Choose a file**
and select that file, then **Add variables**. This imports the hosted-mode flags,
encoded credential files and a private administrator token into Render's environment
secret store. The container writes the two decoded files under `/state` with
private permissions before starting the same production server. Never commit or
publish `render.env`; base64 is encoding, not encryption. The administrator token
is for the operator and is never included in the public `/v1/config` response.
The existing `/etc/secrets` file configuration remains supported when the encoded
variables are absent. Do not enable both configurations with different credentials.
