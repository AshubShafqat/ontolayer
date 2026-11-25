FROM python:3.12-slim AS builder
WORKDIR /app
COPY pyproject.toml uv.lock README.md LICENSE ./
COPY src ./src
RUN pip install --no-cache-dir uv==0.13.1 && uv sync --frozen --no-dev --no-editable

FROM python:3.12-slim
WORKDIR /app
COPY --from=builder /app/.venv /app/.venv
ENV PATH="/app/.venv/bin:$PATH" PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
RUN useradd --uid 1000 --create-home ontolayer
COPY examples ./examples
RUN mkdir /app/.ontolayer /state && chown ontolayer:ontolayer /app/.ontolayer /state
USER ontolayer
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=3)"
ENTRYPOINT ["ontolayer"]
CMD ["serve", "--ontology", "examples/retail/ontology.yaml", "--credentials", "examples/retail/credentials.yaml", "--demo", "--host", "0.0.0.0"]
