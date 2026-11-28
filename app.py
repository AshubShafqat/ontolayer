"""Vercel ASGI entrypoint; ordinary local and Docker entrypoints stay unchanged."""

import os
from pathlib import Path

from ontolayer.serverless import create_serverless_app

app = create_serverless_app(dict(os.environ), Path(__file__).resolve().parent)
