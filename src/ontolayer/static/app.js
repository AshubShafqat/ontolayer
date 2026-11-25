"use strict";

const $ = (selector) => document.querySelector(selector);
const esc = (value) =>
  String(value ?? "").replace(
    /[&<>"']/g,
    (c) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[
        c
      ],
  );
const paths = {
  overview:
    '<rect x="3" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="3" width="7" height="7" rx="1.5"/><rect x="3" y="14" width="7" height="7" rx="1.5"/><rect x="14" y="14" width="7" height="7" rx="1.5"/>',
  graph:
    '<circle cx="6" cy="6" r="3"/><circle cx="18" cy="7" r="3"/><circle cx="12" cy="19" r="3"/><path d="m9 6 6 1M7 9l4 7m6-6-4 6"/>',
  query: '<path d="m5 5 7 7-7 7m9 0h6"/>',
  shield:
    '<path d="M12 3 4 6v6c0 5 8 9 8 9s8-4 8-9V6z"/><path d="m8 12 3 3 5-6"/>',
  arrow: '<path d="M5 12h14m-5-5 5 5-5 5"/>',
  cube: '<path d="m12 2 9 5v10l-9 5-9-5V7zm-9 5 9 5 9-5m-9 5v10"/>',
  data: '<ellipse cx="12" cy="5" rx="8" ry="3"/><path d="M4 5v14c0 4 16 4 16 0V5M4 12c0 4 16 4 16 0"/>',
  check: '<path d="m5 12 4 4L19 6"/>',
  search: '<circle cx="10" cy="10" r="6"/><path d="m15 15 5 5"/>',
  refresh: '<path d="M20 8a8 8 0 1 0 0 8M20 3v5h-5"/>',
  logout: '<path d="M9 4H4v16h5m5-12 4 4-4 4m-6-4h12"/>',
  spark:
    '<path d="m12 3 2.5 6.5L21 12l-6.5 2.5L12 21l-2.5-6.5L3 12l6.5-2.5z"/>',
  download: '<path d="M12 3v12m-5-5 5 5 5-5M4 17v4h16v-4"/>',
  link: '<path d="m9 15 6-6m-5-3 2-2a5 5 0 0 1 7 7l-2 2m-3 5-2 2a5 5 0 0 1-7-7l2-2"/>',
  lock: '<rect x="5" y="10" width="14" height="11" rx="2"/><path d="M8 10V7a4 4 0 0 1 8 0v3m-4 4v3"/>',
};
const icon = (name) =>
  `<svg class="icon" viewBox="0 0 24 24" aria-hidden="true">${paths[name] || paths.cube}</svg>`;
const badge = (status) =>
  `<span class="tag ${status === "certified" ? "" : "amber"}">${icon(status === "certified" ? "check" : "cube")}${esc(status)}</span>`;
const pretty = (id) =>
  String(id)
    .replace(/_/g, " ")
    .replace(/([a-z])([A-Z])/g, "$1 $2")
    .replace(/^./, (c) => c.toUpperCase());
const number = (value) => {
  const [whole, fraction] = String(value).split(".");
  return /^-?\d+$/.test(whole)
    ? whole.replace(/\B(?=(\d{3})+(?!\d))/g, ",") +
        (fraction ? `.${fraction}` : "")
    : String(value);
};
const state = {
  config: null,
  token: "",
  role: "north",
  data: null,
  view: "overview",
  concept: null,
  offset: 0,
  result: null,
  history: [],
  controller: new AbortController(),
  epoch: 0,
};
const navigation = [
  ["overview", "Overview", "overview"],
  ["explorer", "Ontology explorer", "graph"],
  ["studio", "Query studio", "query"],
  ["access", "Access & lineage", "shield"],
];

async function api(path, body) {
  const headers = {};
  if (state.token) headers.Authorization = `Bearer ${state.token}`;
  if (body !== undefined) headers["Content-Type"] = "application/json";
  const response = await fetch(path, {
    method: body === undefined ? "GET" : "POST",
    headers,
    body: body === undefined ? undefined : JSON.stringify(body),
    signal: AbortSignal.any([
      state.controller.signal,
      AbortSignal.timeout(15000),
    ]),
    cache: "no-store",
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    if (response.status === 401 && state.data)
      logout("Your credential is no longer valid. Please sign in again.");
    const details =
      typeof data.detail === "string"
        ? data.detail
        : "Check the supplied fields and try again.";
    throw new Error(
      `${details}${response.headers.get("X-Request-ID") ? ` · Request ${response.headers.get("X-Request-ID").slice(0, 8)}` : ""}`,
    );
  }
  return data;
}
const tool = (operation, args = {}) =>
  api(`/v1/tools/${operation}`, { arguments: args });
function announce(message) {
  $("#announcer").textContent = message;
}
function showError(error) {
  if (error.name === "AbortError") return;
  const target = $("#error") || $("#login-error");
  if (target) {
    target.hidden = false;
    target.textContent =
      error.name === "TimeoutError"
        ? "The request timed out. Retry when the server is available."
        : error.message === "Failed to fetch"
          ? "You are offline or the server is unavailable. Check your connection and retry."
          : error.message;
    target.setAttribute("role", "alert");
    target.insertAdjacentHTML(
      "beforeend",
      ' <button class="btn" data-action="retry">Retry page</button>',
    );
  }
  document.querySelectorAll(".loading").forEach((el) => el.remove());
}
function loading() {
  return '<div class="loading" role="status"><span class="spinner"></span>Loading your permitted data…</div>';
}
function empty(title, description) {
  return `<div class="empty">${icon("graph")}<h3>${esc(title)}</h3><p>${esc(description)}</p></div>`;
}

function login(message = "") {
  $("#app").innerHTML =
    `<div class="login-wrap"><section class="login-story"><a href="/" class="brand"><img src="/static/mark.svg" alt="">OntoLayer</a><div class="eyebrow">THE BUSINESS KNOWLEDGE WORKSPACE</div><h1>Connect your data.<br>Give it meaning.</h1><p>Explore business concepts, ask governed questions, and follow every answer back to its source.</p><div class="status"><span class="dot"></span>Local workspace ready</div></section><main id="main" class="login-form-wrap"><form id="login-form" class="login-form"><div class="eyebrow">WELCOME TO ONTOLAYER</div><h2>Open your workspace</h2><p>Use a credential issued by your workspace administrator. It stays in memory for this session.</p><div id="login-error" class="error-banner" ${message ? "" : "hidden"}>${esc(message)}</div><label for="token">Access token</label><input id="token" name="token" type="password" autocomplete="off" required placeholder="Enter your access token"><button class="btn primary" type="submit">Connect to workspace ${icon("arrow")}</button>${state.config?.demo ? `<div class="divider">or explore synthetic data</div><button class="btn" type="button" data-action="demo-login">Open retail demo ${icon("arrow")}</button><p class="note">Demo roles let you see how access policies change the results.</p>` : ""}</form></main></div>`;
}
function resetIdentity() {
  state.controller.abort();
  state.controller = new AbortController();
  state.epoch++;
  state.data = null;
  state.result = null;
  state.history = [];
  state.concept = null;
  state.offset = 0;
}
function logout(message = "") {
  resetIdentity();
  state.token = "";
  login(message);
}
async function connect(token, role = "custom") {
  resetIdentity();
  state.token = token;
  state.role = role;
  const epoch = state.epoch;
  try {
    const data = await api("/v1/workspace");
    if (epoch !== state.epoch) return;
    state.data = data;
    shell();
    await renderView();
  } catch (error) {
    if (error.name !== "AbortError" && epoch === state.epoch) {
      state.token = "";
      login(error.message);
    }
  }
}
function shell() {
  const d = state.data;
  $("#app").innerHTML =
    `<div class="layout"><aside class="sidebar"><a class="brand" href="#overview"><img src="/static/mark.svg" alt="">OntoLayer</a><div class="workspace-label">WORKSPACE</div><nav class="nav" aria-label="Workspace navigation">${navigation.map(([id, label, symbol]) => `<a href="#${id}" data-nav="${id}">${icon(symbol)}${label}</a>`).join("")}</nav><div class="side-bottom"><div class="side-note">${icon("shield")}<strong>Meaning with boundaries</strong>Every query follows your workspace’s access policies.</div><div class="side-footer"><span>v${esc(state.config.version)}</span>${state.config.docs ? '<a href="/docs" target="_blank" rel="noopener">API docs ↗</a>' : "<span>Protected workspace</span>"}</div></div></aside><div class="main-wrap"><header class="topbar"><div class="breadcrumb">${icon("cube")}<strong>${esc(pretty(d.namespace))} workspace</strong><span class="separator">/</span><span class="location" id="location">Overview</span><span class="tag neutral">v${esc(d.version)}</span></div><div class="top-actions"><span class="status"><span class="dot"></span>Connected</span><div class="identity"><span class="avatar">${esc(d.actor.id.slice(0, 2).toUpperCase())}</span><div>${
      state.config.demo && state.role !== "custom"
        ? `<label class="sr-only" for="identity-role">Demo identity</label><select id="identity-role">${[
            ["north", "North region"],
            ["south", "South region"],
            ["analyst", "Global analyst"],
            ["admin", "Administrator"],
            ["guest", "Restricted guest"],
          ]
            .map(
              ([v, l]) =>
                `<option value="${v}" ${v === state.role ? "selected" : ""}>${l}</option>`,
            )
            .join("")}</select><small>Synthetic demo identity</small>`
        : `<span class="identity-name">${esc(d.actor.id)}</span><small>${esc(d.actor.roles.join(", ") || "No role grants")}</small>`
    }</div></div><button class="icon-btn" data-action="logout" title="Sign out" aria-label="Sign out">${icon("logout")}</button></div></header><main id="main" class="content" tabindex="-1"><div id="error" class="error-banner" hidden></div><div id="view"></div><footer class="footer"><span>${icon("shield")} Results are limited to your authorized records.</span><span>${esc(d.namespace)} · Ontology ${esc(d.version)} · ${state.config.demo ? "Synthetic demo data" : "Authenticated workspace"}</span></footer></main></div></div>`;
}
function heading(eyebrow, title, subtitle, action = "") {
  return `<div class="page-heading"><div><div class="eyebrow">${eyebrow}</div><h1>${title}</h1><p class="subtitle">${subtitle}</p></div>${action}</div>`;
}
function cardHead(title, description = "", right = "") {
  return `<div class="card-head"><div><h2>${title}</h2>${description ? `<p>${description}</p>` : ""}</div>${right}</div>`;
}
function graph() {
  const nodes = state.data.concepts;
  if (!nodes.length)
    return empty(
      "No visible concepts",
      "Your identity has no ontology grants.",
    );
  const width = 600,
    height = Math.max(250, Math.ceil(nodes.length / 3) * 115 + 20);
  const positions = new Map(
    nodes.map((c, i) => [
      c.id,
      { x: 25 + (i % 3) * 195, y: 25 + Math.floor(i / 3) * 115 },
    ]),
  );
  const edges = state.data.links
    .map((link) => {
      const a = positions.get(link.source),
        b = positions.get(link.target);
      const x1 = a.x + 80,
        y1 = a.y + 38,
        x2 = b.x + 80,
        y2 = b.y + 38;
      return `<path class="graph-line" d="M${x1},${y1} L${x2},${y2}"/><text class="link-text" text-anchor="middle" x="${(x1 + x2) / 2}" y="${(y1 + y2) / 2 - 7}">${esc(link.id)}</text>`;
    })
    .join("");
  return `<div class="graph" tabindex="0" role="region" aria-label="Scrollable concept map"><svg viewBox="0 0 ${width} ${height}" role="img" aria-label="Concept map: ${esc(state.data.links.map((l) => `${l.source} ${l.id} ${l.target}`).join("; "))}">${edges}${nodes
    .map((c) => {
      const p = positions.get(c.id);
      return `<g><rect x="${p.x}" y="${p.y}" width="160" height="70" rx="10"/><rect class="node-icon" x="${p.x + 12}" y="${p.y + 15}" width="27" height="27" rx="7"/><text x="${p.x + 20}" y="${p.y + 34}">◇</text><text x="${p.x + 48}" y="${p.y + 30}">${esc(c.id)}</text><text class="node-meta" x="${p.x + 48}" y="${p.y + 48}">${Object.keys(c.properties).length} visible properties</text></g>`;
    })
    .join("")}</svg></div>`;
}
async function renderView() {
  if (!state.data) return;
  state.controller.abort();
  state.controller = new AbortController();
  state.view = navigation.some((n) => n[0] === location.hash.slice(1))
    ? location.hash.slice(1)
    : "overview";
  const epoch = ++state.epoch,
    view = state.view;
  document.querySelectorAll("[data-nav]").forEach((a) => {
    const active = a.dataset.nav === view;
    a.classList.toggle("active", active);
    if (active) a.setAttribute("aria-current", "page");
    else a.removeAttribute("aria-current");
  });
  $("#location").textContent = navigation.find((n) => n[0] === view)[1];
  $("#error").hidden = true;
  try {
    if (view === "overview") await overview(epoch);
    if (view === "explorer") await explorer(epoch);
    if (view === "studio") studio();
    if (view === "access") access();
    announce(`${navigation.find((n) => n[0] === view)[1]} loaded`);
  } catch (error) {
    if (epoch === state.epoch) showError(error);
  }
}
async function overview(epoch) {
  const d = state.data;
  $("#view").innerHTML =
    heading(
      "YOUR SEMANTIC WORKSPACE",
      "Business knowledge, connected.",
      "A shared view of your concepts, relationships, and trusted metrics.",
      `<a class="btn primary" href="#studio">${icon("spark")} Ask your data</a>`,
    ) + loading();
  const results = await Promise.all(
    d.metrics.map(async (m) => {
      if (m.status !== "certified") return null;
      try {
        return await tool("query_metric", { metric_id: m.id });
      } catch (error) {
        if (error.name === "AbortError") throw error;
        return { metric: m.id, error: error.message };
      }
    }),
  );
  if (epoch !== state.epoch) return;
  const successful = results.filter((r) => r && !r.error);
  const first = successful[0];
  const stats = [
    [
      d.concepts.length,
      "Business concepts",
      "Definitions you can explore",
      "cube",
    ],
    [d.links.length, "Relationships", "Connections across concepts", "graph"],
    [
      d.metrics.filter((m) => m.status === "certified").length,
      "Certified metrics",
      "Reviewed business calculations",
      "shield",
    ],
    [d.version, "Ontology version", "Active workspace definition", "data"],
  ];
  $("#view").innerHTML =
    heading(
      "YOUR SEMANTIC WORKSPACE",
      "Business knowledge, connected.",
      "A shared view of your concepts, relationships, and trusted metrics.",
      `<a class="btn primary" href="#studio">${icon("spark")} Ask your data</a>`,
    ) +
    `<div class="stats">${stats.map(([value, label, note, symbol]) => `<article class="stat"><div class="stat-title">${label}${icon(symbol)}</div><div class="stat-value">${esc(value)}</div><div class="stat-note">${note}</div></article>`).join("")}</div><div class="split"><section class="card">${cardHead("Your business, mapped", "Concept relationships in the current ontology", '<span class="tag purple">Live schema</span>')}${graph()}<div class="card-foot"><div class="legend"><span><i></i>Concept</span><span><i class="line"></i>Relationship</span></div><a href="#explorer">Explore ontology →</a></div></section><section class="card">${cardHead("At a glance", "Calculated from your permitted records")}<div class="card-body">${
      first
        ? `<div class="insight"><div class="insight-title">${esc(pretty(first.metric))} · All available dates</div><div class="insight-number">${esc(number(first.values.total))}<small>${esc(first.unit)}</small></div></div>${successful
            .slice(1)
            .map(
              (r) =>
                `<div class="metric-row"><span>${esc(pretty(r.metric))}</span><strong>${esc(number(r.values.total))} ${esc(r.unit)}</strong></div>`,
            )
            .join(
              "",
            )}<p class="note">${icon("shield")} These figures reflect your identity’s access scope. Change identity to compare permissions.</p>`
        : empty(
            "No executable metrics",
            "An administrator must grant access to certified metric definitions.",
          )
    }</div><div class="card-foot"><span>Actual values · No generated estimates</span><a href="#studio">Run a query →</a></div></section></div><section class="card">${cardHead("Metric catalog", "One reviewed definition for every business question", `<span class="tag neutral">${d.metrics.length} available</span>`)}${d.metrics.length ? `<div class="table-wrap"><table><thead><tr><th>Metric</th><th>Business grain</th><th>Owner</th><th>Status</th><th></th></tr></thead><tbody>${d.metrics.map((m) => `<tr><td><div class="cell-title"><span class="mini-icon">${icon("data")}</span><div><strong>${esc(pretty(m.id))}</strong><small>${esc(m.unit)} · ${esc(m.aggregation.replaceAll("_", " "))}</small></div></div></td><td>${esc(m.grain)}</td><td>${esc(m.owner)}</td><td>${badge(m.status)}</td><td><button class="table-button" data-metric="${esc(m.id)}">Query ${icon("arrow")}</button></td></tr>`).join("")}</tbody></table></div>` : empty("No metrics available", "Your current identity has no metric grants.")}</section>`;
}
async function explorer(epoch) {
  const d = state.data;
  if (!d.concepts.length) {
    $("#view").innerHTML =
      heading(
        "ONTOLOGY EXPLORER",
        "Understand the business.",
        "Definitions and records available to your identity.",
      ) +
      `<section class="card">${empty("No concept access", "Switch to an authorized demo identity or request access from your administrator.")}</section>`;
    return;
  }
  if (!d.concepts.some((c) => c.id === state.concept)) {
    state.concept = d.concepts[0].id;
    state.offset = 0;
  }
  const c = d.concepts.find((c) => c.id === state.concept);
  $("#view").innerHTML =
    heading(
      "ONTOLOGY EXPLORER",
      "Understand the business.",
      "Explore the definitions behind your data, then inspect the connected records.",
    ) +
    `<div class="explorer"><aside class="card">${cardHead("Concepts", `${d.concepts.length} available to you`)}<div class="concept-menu">${d.concepts.map((c) => `<button class="concept-button ${c.id === state.concept ? "active" : ""}" data-concept="${esc(c.id)}">${icon("cube")}<span>${esc(c.id)}<small>${Object.keys(c.properties).length} properties</small></span></button>`).join("")}</div></aside><div><section class="card">${cardHead(esc(c.id), `Owner: ${esc(c.owner)}`, badge(c.status))}<div class="concept-description"><p>${esc(c.description)}</p><div class="property-chips">${Object.entries(
      c.properties,
    )
      .map(
        ([k, v]) =>
          `<span class="property-chip">${esc(k)}<span>${esc(v.type)}${v.pii ? " · PII" : ""}</span></span>`,
      )
      .join(
        "",
      )}</div></div><div id="entity-list">${loading()}</div></section><section id="entity-detail" class="card detail" hidden></section></div></div>`;
  const rows = await tool("list_entities", {
    concept: c.id,
    limit: 20,
    offset: state.offset,
  });
  if (epoch !== state.epoch) return;
  const fields = Object.keys(c.properties);
  $("#entity-list").innerHTML =
    `<div class="toolbar"><label class="sr-only" for="record-filter">Filter records on this page</label><input id="record-filter" placeholder="Filter this page…" type="search"><span class="tag neutral">${rows.items.length} visible records on this page</span></div>${rows.items.length ? `<div class="table-wrap"><table><thead><tr><th>Record</th>${fields.map((f) => `<th>${esc(pretty(f))}</th>`).join("")}<th>Inspect</th></tr></thead><tbody id="entity-rows">${rows.items.map((e) => `<tr><td><code>${esc(e.id)}</code></td>${fields.map((f) => `<td>${esc(e.properties[f] ?? "—")}</td>`).join("")}<td><button class="table-button" data-entity="${esc(e.id)}">Lineage →</button></td></tr>`).join("")}</tbody></table></div>` : empty("No records in your scope", "The concept exists, but no records are visible to your identity.")}<div class="card-foot"><span>Property and row policies applied</span><div class="pagination"><button class="icon-btn" data-page="${Math.max(0, state.offset - 20)}" ${state.offset === 0 ? "disabled" : ""} aria-label="Previous records">←</button><span>Page ${Math.floor(state.offset / 20) + 1}</span><button class="icon-btn" data-page="${rows.next_offset ?? 0}" ${rows.next_offset === null ? "disabled" : ""} aria-label="Next records">→</button></div></div>`;
}
async function inspect(entityId) {
  const epoch = state.epoch;
  const target = $("#entity-detail");
  target.hidden = false;
  target.innerHTML = loading();
  const [lineage, edges] = await Promise.all([
    tool("get_lineage", { entity_id: entityId }),
    tool("get_relationships", { entity_id: entityId, limit: 100 }),
  ]);
  if (epoch !== state.epoch) return;
  target.innerHTML =
    cardHead("Record lineage", esc(entityId), badge(lineage.status)) +
    `<div class="card-body"><dl><dt>Source</dt><dd>${esc(lineage.source)}</dd><dt>Mapping</dt><dd>${esc(lineage.mapping)}</dd><dt>Ontology</dt><dd>${esc(lineage.ontology_version)}</dd><dt>Snapshot SHA-256</dt><dd><code>${esc(lineage.snapshot_sha256)}</code></dd></dl><h3>Visible relationships</h3>${edges.items.length ? edges.items.map((e) => `<div class="source">${icon("link")}<span>${esc(e.source)} <small>${esc(e.relation)} → ${esc(e.target)}</small></span></div>`).join("") : '<p class="note">No visible relationships for this record.</p>'}${edges.next_offset !== null ? '<p class="note">Showing the first 100 relationships.</p>' : ""}</div>`;
  target.scrollIntoView({ block: "nearest" });
}
function studio(metricId) {
  const d = state.data,
    metrics = d.metrics;
  const metric = metrics.find((m) => m.id === metricId) || metrics[0];
  $("#view").innerHTML =
    heading(
      "QUERY STUDIO",
      "Ask with confidence.",
      "Choose a governed calculation. Every answer includes its definition and source.",
    ) +
    `<div class="question-box"><div class="question-icon">${icon("spark")}</div><form id="question-form" class="question-form"><label for="question">Ask your business data</label><div class="question-input"><input id="question" name="question" placeholder="revenue from 2026-10-01 to 2026-11-01" maxlength="2000" required><button class="btn primary" type="submit">Ask ${icon("arrow")}</button></div><div class="examples">${metrics
      .slice(0, 3)
      .map(
        (m) =>
          `<button class="example" type="button" data-question="${esc(m.id)}">${esc(pretty(m.id))}</button>`,
      )
      .join(
        "",
      )}<span class="form-note">Metric + optional dates, grouping, or dimension=value.</span></div></form></div><div class="query-layout"><section class="card">${cardHead("Build a query", "Explicit definitions. Reproducible results.")}<div class="card-body">${metric ? `<form id="query-form"><div class="form-grid"><label class="full">Business metric<select name="metric_id" id="metric-select">${metrics.map((m) => `<option value="${esc(m.id)}" ${m.id === metric.id ? "selected" : ""}>${esc(pretty(m.id))} (${esc(m.unit)})</option>`).join("")}</select></label><div class="full" id="metric-description"></div><label>Start date<input type="date" name="start_date" id="start-date"></label><label>End date (exclusive)<input type="date" name="end_date" id="end-date"></label><label class="full">Group results by<select name="group_by" id="group-by"></select></label><label>Filter dimension<select name="filter_field" id="filter-field"></select></label><label>Equals<input name="filter_value" placeholder="e.g. north" maxlength="200"></label></div><div class="form-actions"><button class="btn primary" type="submit">${icon("query")} Run query</button><button class="btn" type="reset">Reset</button></div><p class="note">Blank dates include all available records. Your access scope is always applied before calculation.</p></form>` : empty("No permitted metrics", "Request access to a certified definition before running a query.")}</div></section><section class="card" id="query-result">${state.result ? resultHTML(state.result) : cardHead("Query result", "The evidence behind your answer") + empty("Ready when you are", "Run a query to see calculated values, scope, and source lineage.")}</section></div><section class="card compact">${cardHead("Session history", "Recent queries for your current identity only")}<div id="history">${historyHTML()}</div></section>`;
  if (metric) updateMetric(metric.id);
}
function updateMetric(id) {
  const m = state.data.metrics.find((m) => m.id === id);
  if (!m) return;
  $("#metric-description").innerHTML =
    `<p class="form-note">${esc(m.description)}</p><div class="property-chips">${badge(m.status)}<span class="tag neutral">${esc(m.grain)}</span><span class="tag purple">${esc(m.aggregation.replaceAll("_", " "))}</span></div>`;
  for (const selector of ["#group-by", "#filter-field"])
    $(selector).innerHTML =
      `<option value="">${selector === "#group-by" ? "No grouping — total" : "No filter"}</option>${m.dimensions.map((d) => `<option value="${esc(d)}">${esc(pretty(d))}</option>`).join("")}`;
  $("#start-date").disabled = !m.date_field;
  $("#end-date").disabled = !m.date_field;
}
function resultHTML(r) {
  const values = Object.entries(r.values),
    max = Math.max(...values.map(([, v]) => Number(v)), 1);
  return (
    cardHead("Query result", esc(pretty(r.metric)), badge(r.status)) +
    `<div class="card-body">${values.length === 1 ? `<div class="result-number">${esc(number(values[0][1]))}<small>${esc(r.unit)}</small></div>${values[0][0] !== "total" ? `<p>${esc(values[0][0])}</p>` : ""}` : values.length ? `<div class="bars">${values.map(([k, v]) => `<div class="bar-row"><span>${esc(k)}</span><meter min="0" max="${max}" value="${esc(v)}" aria-label="${esc(k)}"></meter><strong>${esc(number(v))} ${esc(r.unit)}</strong></div>`).join("")}</div>` : empty("No matching groups", "Change the filters or date interval.")}<div class="result-scope">${icon("shield")} ${esc(r.scope)}</div><dl class="result-grid"><div><dt>Date range</dt><dd>${esc(r.start_date || "Beginning")} → ${esc(r.end_date_exclusive || "Latest")}<small> (end exclusive)</small></dd></div><div><dt>Ontology version</dt><dd>${esc(r.ontology_version)}</dd></div><div><dt>Grain</dt><dd>${esc(r.grain)}</dd></div><div><dt>Filters</dt><dd>${
      Object.entries(r.filters)
        .map(([k, v]) => `${esc(k)} = ${esc(v)}`)
        .join(", ") || "None"
    }</dd></div></dl><h3>Source evidence</h3>${r.lineage.map((l) => `<div class="source">${icon("data")}<span>${esc(l.source)}<small>Mapping: ${esc(l.mapping)} · Snapshot ${esc(l.snapshot_sha256.slice(0, 12))}…</small></span></div>`).join("") || '<p class="note">No matching source records. An empty total is zero.</p>'}<details class="compact"><summary>Full result & provenance</summary><pre>${esc(JSON.stringify(r, null, 2))}</pre></details><div class="form-actions"><button class="btn" data-action="download">${icon("download")} Download result</button></div></div>`
  );
}
function historyHTML() {
  return state.history.length
    ? `<div class="table-wrap"><table><thead><tr><th>Metric</th><th>Result</th><th>Time</th><th>Status</th></tr></thead><tbody>${state.history
        .map(
          (h) =>
            `<tr><td>${esc(pretty(h.metric))}</td><td>${Object.entries(h.values)
              .map(([k, v]) => `${esc(k)}: ${esc(number(v))} ${esc(h.unit)}`)
              .join(
                " · ",
              )}</td><td>${esc(h.time)}</td><td>${badge(h.status)}</td></tr>`,
        )
        .join("")}</tbody></table></div>`
    : empty(
        "No queries yet",
        "Your session history appears here after a successful calculation.",
      );
}
function saveResult(result) {
  state.result = result;
  state.history.unshift({
    ...result,
    time: new Date().toLocaleTimeString([], {
      hour: "2-digit",
      minute: "2-digit",
    }),
  });
  state.history = state.history.slice(0, 10);
  $("#query-result").innerHTML = resultHTML(result);
  $("#history").innerHTML = historyHTML();
  announce("Query complete. Result and source evidence are available.");
}
function access() {
  const d = state.data;
  $("#view").innerHTML =
    heading(
      "ACCESS & LINEAGE",
      "Trust is part of the query.",
      "Inspect your effective scope and trace visible records back to their source.",
    ) +
    `<div class="split"><section class="card">${cardHead("Current identity", "Resolved by the server", '<span class="tag">Authenticated</span>')}<div class="card-body detail"><dl><dt>Actor</dt><dd>${esc(d.actor.id)}</dd><dt>Namespace</dt><dd>${esc(d.actor.namespace)}</dd><dt>Roles</dt><dd>${esc(d.actor.roles.join(", ") || "No grants")}</dd><dt>Attributes</dt><dd>${esc(JSON.stringify(d.actor.attributes))}</dd><dt>Visible concepts</dt><dd>${d.concepts.length}</dd><dt>Available metrics</dt><dd>${d.metrics.length}</dd></dl><p class="note">These are the current identity’s grants. A hidden record and a nonexistent record return the same public denial.</p></div></section><section class="card">${cardHead("Policy enforcement", "Controls applied inside the semantic service")}<div class="card-body">${[
      [
        "Default deny",
        "Only explicitly granted concepts, properties, and metrics are available.",
      ],
      [
        "Filter before calculation",
        "Rows outside your scope never contribute to your metric results.",
      ],
      [
        "Traceable answers",
        "Results carry source snapshots, mapping identifiers, and definition versions.",
      ],
    ]
      .map(
        ([t, p]) =>
          `<div class="guard">${icon("shield")}<div><h3>${t}</h3><p>${p}</p></div></div>`,
      )
      .join(
        "",
      )}</div></section></div><section class="card">${cardHead("Inspect a record", "Check visibility and retrieve source evidence when permitted")}<div class="card-body"><form id="access-form"><label for="access-entity">Entity identifier</label><div class="question-input"><input name="entity_id" id="access-entity" placeholder="e.g. Customer:C1" required maxlength="200"><button class="btn primary" type="submit">Inspect record ${icon("arrow")}</button></div></form><div id="access-result"></div></div></section><section class="card compact">${cardHead("Visible property contracts", "PII fields are omitted unless your role explicitly permits them")}<div class="table-wrap"><table><thead><tr><th>Concept</th><th>Properties you can see</th><th>Status</th></tr></thead><tbody>${d.concepts
      .map(
        (c) =>
          `<tr><td><strong>${esc(c.id)}</strong></td><td>${Object.entries(
            c.properties,
          )
            .map(
              ([p, v]) =>
                `<span class="property-chip">${esc(p)}${v.pii ? " · PII" : ""}</span>`,
            )
            .join(" ")}</td><td>${badge(c.status)}</td></tr>`,
      )
      .join("")}</tbody></table></div></section>`;
}

document.addEventListener("click", async (event) => {
  const el = event.target.closest("button");
  if (!el) return;
  try {
    if (el.dataset.action === "logout") logout();
    if (el.dataset.action === "retry") await renderView();
    if (el.dataset.action === "demo-login")
      await connect("demo-north-token", "north");
    if (el.dataset.concept) {
      state.concept = el.dataset.concept;
      state.offset = 0;
      await renderView();
    }
    if (el.dataset.page !== undefined) {
      state.offset = Number(el.dataset.page);
      await renderView();
    }
    if (el.dataset.entity) await inspect(el.dataset.entity);
    if (el.dataset.metric) {
      if (location.hash !== "#studio") {
        location.hash = "studio";
        setTimeout(() => studio(el.dataset.metric), 0);
      } else studio(el.dataset.metric);
    }
    if (el.dataset.question) {
      $("#question").value = el.dataset.question;
      $("#question").focus();
    }
    if (el.dataset.action === "download" && state.result) {
      const url = URL.createObjectURL(
        new Blob([JSON.stringify(state.result, null, 2)], {
          type: "application/json",
        }),
      );
      const a = document.createElement("a");
      a.href = url;
      a.download = `ontolayer-${state.result.metric}.json`;
      a.click();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
    }
  } catch (error) {
    showError(error);
  }
});
document.addEventListener("change", async (event) => {
  try {
    if (event.target.id === "identity-role")
      await connect(`demo-${event.target.value}-token`, event.target.value);
    if (event.target.id === "metric-select") updateMetric(event.target.value);
  } catch (error) {
    showError(error);
  }
});
document.addEventListener("input", (event) => {
  if (event.target.id === "record-filter") {
    const value = event.target.value.toLowerCase();
    document
      .querySelectorAll("#entity-rows tr")
      .forEach(
        (row) => (row.hidden = !row.textContent.toLowerCase().includes(value)),
      );
  }
});
document.addEventListener("reset", (event) => {
  if (event.target.id === "query-form")
    setTimeout(() => updateMetric($("#metric-select").value), 0);
});
document.addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = event.target,
    data = new FormData(form),
    button = form.querySelector('button[type="submit"]');
  const epoch = state.epoch;
  if (button) button.disabled = true;
  if ($("#error")) $("#error").hidden = true;
  try {
    if (form.id === "login-form")
      await connect(String(data.get("token")).trim());
    if (form.id === "query-form") {
      const args = { metric_id: data.get("metric_id") };
      for (const k of ["group_by", "start_date", "end_date"])
        if (data.get(k)) args[k] = data.get(k);
      if (args.start_date && args.end_date && args.start_date >= args.end_date)
        throw new Error("End date must be after the start date.");
      if (data.get("filter_field")) {
        if (!data.get("filter_value"))
          throw new Error("Enter a value for the selected filter.");
        args.filters = { [data.get("filter_field")]: data.get("filter_value") };
      }
      const result = await tool("query_metric", args);
      if (epoch === state.epoch) saveResult(result);
    }
    if (form.id === "question-form") {
      const result = await api("/v1/ask", {
        question: String(data.get("question")),
      });
      if (epoch !== state.epoch) return;
      if (result.answerable) saveResult(result.result);
      else {
        $("#query-result").innerHTML =
          cardHead("A little more context", "No calculation was guessed") +
          empty("Please clarify your question", result.answer);
        announce(result.answer);
      }
    }
    if (form.id === "access-form") {
      const entity_id = String(data.get("entity_id"));
      const decision = await tool("explain_policy_decision", { entity_id });
      const lineage = decision.allowed
        ? await tool("get_lineage", { entity_id })
        : null;
      if (epoch !== state.epoch) return;
      $("#access-result").innerHTML =
        `<div class="status-panel ${decision.allowed ? "" : "denied"}">${icon(decision.allowed ? "check" : "lock")} ${esc(decision.reason)}</div>${lineage ? `<pre>${esc(JSON.stringify(lineage, null, 2))}</pre>` : ""}`;
      announce(decision.reason);
    }
  } catch (error) {
    if (epoch === state.epoch) showError(error);
  } finally {
    if (button) button.disabled = false;
  }
});
window.addEventListener("hashchange", () => renderView());
async function start() {
  try {
    state.config = await api("/v1/config");
    if (state.config.demo) await connect("demo-north-token", "north");
    else login();
  } catch (error) {
    login(
      "The workspace is unavailable. Check that the server is running, then reload.",
    );
  }
}
start();
