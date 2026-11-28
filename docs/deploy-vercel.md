# Student demo on Vercel Hobby

This option serves the real FastAPI application and its UI together on Vercel's
free Hobby plan for a personal, non-commercial student demonstration. Do not
choose Pro or add paid integrations. Account verification requirements can change;
stop if the account asks for payment details.

1. Sign in at https://vercel.com and choose the personal Hobby account.
2. Import `AshubShafqat/ontolayer`, using the branch containing `app.py` and
   `vercel.json` (`codex/finish-deployment` until merged). Select FastAPI.
3. Generate fresh credentials with `python scripts/prepare_deploy.py` if they
   have not already been prepared. Keep the generated directory private.
4. Set only `ONTOLAYER_CREDENTIALS_B64` and `ONTOLAYER_PUBLIC_DEMO_B64` from the
   private `.ontolayer/deploy/render.env` file as Vercel environment variables.
   These names are shared with the Docker deployment. Do not import the Render
   port, state-directory or admin-token variables. Never commit the environment file.
5. Vercel supplies `VERCEL_URL` and `VERCEL_PROJECT_PRODUCTION_URL`. If using a
   custom domain, set its exact hostname in `ONTOLAYER_PUBLIC_HOST` too.
6. Deploy, then run `python scripts/smoke.py https://<actual-deployed-host>`.
   Publish the actual URL only after the checks pass.

The app retains authentication, regional access policies, bounded operations,
security headers and production validation. North, South and Analyst buttons
use only the three read-only synthetic retail credentials. The private admin
token is never published.

## Limits of this deployment

The public serverless demo deliberately disables the ontology editing workbench.
Graph and query data load from the versioned repository on each cold start.
Audit history, rate counters and temporary files are per instance and ephemeral;
they are not a durable compliance log or a globally coordinated rate limiter.
Use the local app or a persistent container for editing and certification.
Durable multi-instance production operation requires external state and audit
storage. This is a functional student demo, not a durable enterprise deployment.

MCP still runs through the documented local stdio command; this deployment does
not introduce a remote MCP endpoint. Hobby usage quotas and cold starts apply.

References: [Hobby plan](https://vercel.com/docs/plans/hobby),
[FastAPI deployment](https://vercel.com/docs/frameworks/backend/fastapi),
[Python runtime](https://vercel.com/docs/functions/runtimes/python).
