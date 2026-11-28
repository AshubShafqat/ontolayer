# OntoLayer Testing & Validation Guide

## 1. Introduction

This guide describes how to test and validate the main features of OntoLayer.

OntoLayer is a business ontology and semantic layer that maps source data into business concepts, validates relationships, applies access policies, and provides governed query results with source evidence.

The purpose of this guide is to help contributors verify that the application behaves as expected before submitting changes.

## 2. Testing Environment

The project requires:

- Python 3.12 or later
- Git
- uv package manager
- Node.js for frontend development and browser tests

The application uses synthetic retail and agriculture datasets for demonstration and testing.

## 3. Run the Application

Clone the repository and install its dependencies:

```powershell
git clone https://github.com/AshubShafqat/ontolayer.git
cd ontolayer
uv sync --locked --python 3.12
```

Start the retail demo:

```powershell
.\scripts\dev.ps1 -m ontolayer serve --ontology examples/retail/ontology.yaml --credentials examples/retail/credentials.yaml --demo
```

Open the application:

http://127.0.0.1:8000/

The demo provides synthetic data and read-only access.

## 4. Manual Testing Checklist

### 4.1 Ontology Validation

- Verify that ontology definitions contain valid types and properties.
- Check that relationships reference existing source and target types.
- Confirm that metric definitions contain valid fields and dimensions.
- Verify that invalid ontology definitions produce validation errors.

### 4.2 Knowledge Graph

- Open the Explorer page.
- Search for a business concept.
- Inspect its properties and relationships.
- Verify that records and relationships are displayed according to the current user's permissions.
- Inspect source evidence and lineage where available.

### 4.3 Semantic Queries

- Open Query Studio.
- Select the Revenue metric.
- Set the start date to 2026-10-01.
- Set the end date to 2026-11-01.
- Run the query.

Expected results:

| Identity | Revenue |
|---|---:|
| North | 250 USD |
| South | 350 USD |
| Administrator | 600 USD |

Verify that the result includes the expected unit, scope, and source evidence.

### 4.4 Access Control

- Sign in using the North demo identity.
- Verify that North can access permitted records and metrics.
- Verify that restricted South records are not exposed.
- Repeat the test using the South identity.
- Confirm that unauthorized records remain inaccessible.

### 4.5 MCP Tools

- Open the MCP Connect page.
- Inspect the available tool schemas.
- Review the example inputs and outputs.
- Test supported semantic operations.
- Verify that requests follow the documented access policies.

## 5. Automated Testing

Run the backend test suite:

```powershell
uv run pytest --cov-fail-under=85
```

Run code quality checks:

```powershell
uv run ruff check src tests scripts
uv run ruff format --check src tests scripts
uv run mypy src
```

Run browser tests:

```powershell
npm ci
npx playwright install chromium
npm run test:e2e
```

Run performance tests:

```powershell
npm run test:performance
```

On Windows, if the Python launcher has problems, use the project development wrapper as described in the README.

## 6. Reporting Issues

When a test fails, contributors should record:

- The feature being tested
- The steps used to reproduce the issue
- The expected result
- The actual result
- Relevant error messages

Never include private credentials, personal records, or other sensitive information in test reports.

## 7. Contribution Guidelines

Before submitting a pull request:

1. Run the relevant tests.
2. Review the changes made to the project.
3. Ensure that documentation matches the current implementation.
4. Do not include private credentials or real customer data.
5. Explain the purpose of the contribution in the pull request.

For additional contribution requirements, refer to the repository's CONTRIBUTING.md file.

## 8. Conclusion

Testing and validation help maintain the reliability, consistency, and security of OntoLayer.

This guide provides a common starting point for contributors who want to understand the testing workflow and verify changes before submitting them.
