# v0.3 baseline audit

Audited v0.2 commit `bd401e9` on 25 November 2026. The user subsequently authorized completing all phases, superseding the original phase pauses. No public route or ontology format change is proposed.

## Reproduction and evidence

Start (Windows, from the repository):

```powershell
.\scripts\dev.ps1 -m ontolayer serve --ontology examples/retail/ontology.yaml --credentials examples/retail/credentials.yaml --demo --host 127.0.0.1 --port 8000
```

Baseline verification: `./scripts/dev.ps1 -m pytest -q --cov-fail-under=85`: 62 passed, 89.24% coverage. Ruff check and format passed; mypy passed on 18 modules. `npm run test:e2e` with `ONTOLAYER_EXTERNAL_SERVER=1`: six passed. Prettier passed. Docker is unavailable locally; [baseline CI](https://github.com/AshubShafqat/ontolayer/actions/runs/45532065931) passed both Python versions, browser, dependency and container jobs.

[Measurements](audit-v0.3/measurements.json) contain 30 viewport observations and six flow observations. [API evidence](audit-v0.3/api-results.json) contains 39 probes. Screenshots use filenames `SCREEN-WIDTH.png` in [screenshots](audit-v0.3/screenshots), for overview, explorer, studio, access and signin at each width below. These observations cover the synthetic fixture, not arbitrary customer ontologies.

| Width | Overview | Explorer | Studio | Access | Sign in |
|---|---|---|---|---|---|
| 320 | Document 348px; identity overflows | Document 638px; table expands grid | Document 348px; fields clipped | Document 348px; table not keyboard-scrollable | Fits |
| 375 | Fits | Document 638px | Fits; paired mobile fields | Table not keyboard-scrollable | Fits |
| 768 | Fits | Fits | Fits | Fits | Fits |
| 1024 | Graph needs horizontal scroll | Table scroll contained | Fits | Fits | Fits |
| 1440 | Fits | Fits | Fits | Fits | Fits |
| 1920 | Fits; excessive whitespace | Fits | Fits | Fits | Fits |

New axe checks found `scrollable-region-focusable` on Access at 320 and 375. Existing desktop checks missed these. Controls below the requested 44px target occur on every screen, including identity, navigation, examples and record lineage. Measured candidates include links and disabled controls; not all constitute WCAG failures.

## Screen walkthrough

- **Overview:** orient users and show governed totals. Counts, version and metric catalog work. Missing health checks, recent queries/denials, certification breakdown and validation summary. The static graph has no node interaction or zoom.
- **Explorer:** understand definitions and inspect records. Pagination, property filtering and lineage work. Missing concept search, relationship details and interactive map. Intrinsic grid width causes the mobile defect.
- **Studio:** run a calculation with evidence. Guided dates, grouping, filters, constrained language questions, history and JSON download work. October revenue is 250 USD for North. Relative dates prompt clarification. Missing advanced JSON, CSV, result sorting/filtering and explicit limits explanations. Financial display converts exact decimal strings to floating-point and rounds to two places.
- **Access:** understand identity and inspect visibility. C1 lineage is visible; C2 returns the same denial as a nonexistent identifier. Missing comparison workflow and readable lineage trail. The properties table cannot receive keyboard focus on narrow screens.
- **Sign in:** establish authenticated identity. Invalid credentials are rejected; demo roles work. Tokens remain in memory. No theme preference or keyboard help.
- **Restricted guest:** zero concepts/metrics and meaningful empty states. No private records exposed.
- **Offline:** navigating to Explorer displays “Failed to fetch”, leaves a spinner and still says Connected. Missing retry and timeout handling.

## API walkthrough

Public HTML, assets, health and config return 200. Developer docs/OpenAPI return 200; disabled ReDoc returns 404. Workspace requires a valid bearer token (401 otherwise). Metrics require operator (403 for North). Ask returns 250 for the valid question, clarification for ambiguity and 422 for invalid input.

All eleven tools were exercised: search_terms, get_concept, list_entities, get_relationships, find_path, get_metric, query_metric, check_answerable, get_lineage, explain_policy_decision and list_ontology_versions. Invalid tool/arguments and client actor injection return 400. Forbidden and absent lineage both return 403. Revenue scopes: admin 600, North 250, South 350; guest denied. Untrusted CORS preflight receives no allow-origin header. Responses have CSP, no-store and request IDs. Error formats differ between validation, transport and middleware.

## Prioritized usability work

| Rank | Problem | Impact | Effort | Remedy |
|---|---|---|---|---|
| 1 | Explorer horizontal page overflow | High | Small | Grid children min-width zero |
| 2 | Clipped mobile fields/header | High | Small | Single-column forms, wrapping identity |
| 3 | Offline spinner never clears | High | Small | Recoverable error + retry |
| 4 | Small targets | High | Small | Shared 44px control tokens |
| 5 | Table keyboard access | High | Small | Named focusable regions |
| 6 | No global discovery | High | Medium | Search permitted concepts and metrics |
| 7 | Static graph | Medium | Medium | Node focus, zoom and pan controls |
| 8 | JSON-heavy provenance | Medium | Small | Readable source trail |
| 9 | No theme preference | Medium | Small | Light/dark/system tokens |
| 10 | Sparse onboarding/help | Medium | Medium | Beginner README and keyboard help |

## Prioritized functionality work

| Rank | Gap | Impact | Effort |
|---|---|---|---|
| 1 | No authenticated draft/certification workflow | High | Large |
| 2 | No import preview/commit boundary | High | Large |
| 3 | Decimal display precision loss | High | Small |
| 4 | No request timeout/cancellation | High | Small |
| 5 | Inconsistent error contract | High | Medium |
| 6 | No advanced query/result exports | Medium | Medium |
| 7 | No validation view | Medium | Small |
| 8 | No MCP setup/test view | Medium | Medium |
| 9 | No audit view/comparison | Medium | Medium |
| 10 | Missing responsive/visual/performance CI gates | High | Medium |

## Implementation sequence

1. Preserve the application structure; add shared theme/responsive components and recovery states. Test narrow layouts and both themes.
2. Extend existing screens and add validation, MCP, audit and settings views. Keep every semantic query behind existing authorization.
3. Add global search, explicit authorized drafts and import previews, structured errors, cancellation and English-first locale scaffolding. Drafts never update active definitions implicitly. Avoid arbitrary file paths from browser inputs.
4. Extend browser/security coverage and CI; record actual limitations rather than claiming enterprise readiness from unit tests alone.
5. Document actual commands, architecture, policies, screenshots and supported operations.
6. Release only after checks pass; report any remaining limitations and preserve existing APIs/specification.
