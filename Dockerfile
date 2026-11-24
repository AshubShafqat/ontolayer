FROM python:3.12-slim
WORKDIR /app
COPY pyproject.toml README.md LICENSE ./
COPY src ./src
RUN pip install --no-cache-dir . && useradd --create-home ontolayer
COPY examples ./examples
RUN mkdir /app/.ontolayer && chown ontolayer:ontolayer /app/.ontolayer
USER ontolayer
EXPOSE 8000
ENTRYPOINT ["ontolayer"]
CMD ["serve", "--ontology", "examples/retail/ontology.yaml", "--credentials", "examples/retail/credentials.yaml", "--host", "0.0.0.0"]
