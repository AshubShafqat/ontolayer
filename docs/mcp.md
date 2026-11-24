# Connecting an agent over MCP

OntoLayer uses the official MCP Python SDK and the stdio transport. Start one process per trusted
actor. There is no `actor` or `role` argument on the tools. The actor file belongs to the launcher,
not to the user prompt.

Run directly:

```sh
uv run ontolayer mcp --ontology examples/retail/ontology.yaml --actor examples/retail/north.yaml
```

MCP owns stdout. Logs go to stderr and the audit file. An idle process waiting for a client is normal.

For Claude Desktop or Cursor, merge this entry into that client's MCP server configuration.
Replace `/absolute/path/ontolayer` with the actual checkout path; on Windows escape backslashes
as `C:\\path\\ontolayer`, or use forward slashes. `uv` must be on the client's PATH.

```json
{
  "mcpServers": {
    "ontolayer-north": {
      "command": "uv",
      "args": [
        "--directory", "/absolute/path/ontolayer", "run", "ontolayer", "mcp",
        "--ontology", "examples/retail/ontology.yaml",
        "--actor", "examples/retail/north.yaml"
      ]
    }
  }
}
```

Clients differ in how configuration is installed; this is a server-entry example, not an automatic
client setup. The bundled agent and integration tests use a real `ClientSession` to initialize,
discover tools, and call them through a subprocess.

| Tool | Purpose |
| --- | --- |
| search_terms | Resolve permitted concept/metric names and synonyms |
| get_concept | Read definitions and allowed properties |
| list_entities | Paginate visible entities |
| get_relationships | Retrieve links with two visible endpoints |
| find_path | Find an undirected path through visible nodes, bounded to six hops |
| get_metric | Read a permitted metric definition |
| check_answerable | Check metric visibility and certification |
| query_metric | Execute a bounded, policy-scoped calculation |
| get_lineage | Retrieve provenance for a visible entity |
| explain_policy_decision | Safe visibility explanation |
| list_ontology_versions | Read this process's loaded version |

The MCP surface is read-only. Use the maintainer CLI and Git review for proposed changes.
Natural-language requests can fail after `check_answerable` if parameters are invalid; that tool
checks availability and certification, not universal answerability of arbitrary questions.
