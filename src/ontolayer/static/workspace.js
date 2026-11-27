"use strict";

// Shared behaviors apply to dynamic views without replacing their existing flows.
const preferences = {
  get(key, fallback) {
    try {
      return localStorage.getItem(key) || fallback;
    } catch {
      return fallback;
    }
  },
  set(key, value) {
    try {
      localStorage.setItem(key, value);
    } catch {
      /* private browsing */
    }
  },
};
let messages = {};
async function configureLocale(language = "en") {
  const response = await fetch("/static/locales.json");
  const catalog = await response.json();
  const selected = catalog[language];
  if (!selected || selected.available === false)
    throw new Error("Translation is not available yet.");
  messages = selected;
  document.documentElement.lang = language;
  document.documentElement.dir = selected.direction;
}
function translate(key, fallback) {
  return messages[key] || fallback;
}
configureLocale().catch(() => {
  document.documentElement.lang = "en";
  document.documentElement.dir = "ltr";
});
function setTheme(value) {
  preferences.set(`ontolayer-theme-${state.data?.actor.id || "signin"}`, value);
  document.documentElement.dataset.theme =
    value === "system"
      ? matchMedia("(prefers-color-scheme: dark)").matches
        ? "dark"
        : "light"
      : value;
}
const mapObserver = new IntersectionObserver((entries) => {
  entries.forEach((entry) => {
    if (entry.isIntersecting) {
      mapObserver.unobserve(entry.target);
      if (!state.data || !entry.target.isConnected) return;
      entry.target.outerHTML = graphMarkup();
    }
  });
});
function enhance() {
  if (!state.data) return;
  document
    .querySelectorAll(".graph-placeholder:not([data-observed])")
    .forEach((el) => {
      el.dataset.observed = "true";
      mapObserver.observe(el);
    });
  document.querySelectorAll("th").forEach((el) => {
    if (!el.textContent.trim()) el.textContent = "Actions";
  });
  if ($(".top-actions") && !$("#global-search-button"))
    $(".top-actions").insertAdjacentHTML(
      "afterbegin",
      '<button id="global-search-button" class="btn" data-action="search">Search</button>',
    );
  if ($("#query-result .form-actions") && !$("#export-csv")) {
    $("#query-result .form-actions").insertAdjacentHTML(
      "beforeend",
      '<button id="export-csv" class="btn" data-action="csv">Export CSV</button><button class="btn" data-action="copy-result">Copy JSON</button>',
    );
    $("#query-result .card-body").insertAdjacentHTML(
      "beforeend",
      "<details><summary>Why was this answer limited?</summary><p>Only records granted to your current identity contribute. Hidden records, properties and source details are excluded before aggregation. Change dates or filters to change your query; request a different credential to change access.</p></details>",
    );
    $("#query-result .card-body").insertAdjacentHTML(
      "beforeend",
      '<details><summary>Result table · sort and filter</summary><label for="result-filter">Filter result groups</label><input id="result-filter" type="search"><button class="btn" data-action="sort-result">Reverse group order</button><div id="result-table"></div></details>',
    );
    renderResultTable();
  }
  document
    .querySelectorAll(".graph:not([data-interactive])")
    .forEach((region) => {
      region.dataset.interactive = "true";
      region.querySelector("svg").setAttribute("role", "group");
      region.insertAdjacentHTML(
        "beforebegin",
        '<div class="graph-controls"><button class="btn" data-zoom="in">Zoom in</button><button class="btn" data-zoom="out">Zoom out</button><button class="btn" data-zoom="reset">Reset map</button><span class="note">Drag to pan · tap a concept</span></div>',
      );
      region.previousElementSibling.insertAdjacentHTML(
        "beforeend",
        `<label>Focus concept<select class="graph-focus"><option value="">All concepts</option>${state.data.concepts.map((c) => `<option>${esc(c.id)}</option>`).join("")}</select></label><label>Map status<select class="graph-status"><option value="">All statuses</option><option>certified</option><option>draft</option></select></label><label class="check-label"><input class="graph-neighbors" type="checkbox" checked> Expand neighbors</label>`,
      );
      region.querySelectorAll("svg > g").forEach((node, i) => {
        node.classList.add(`node-family-${i % 4}`);
        const c = state.data.concepts[i];
        if (!c) return;
        node.setAttribute("role", "button");
        node.setAttribute("tabindex", "0");
        node.setAttribute(
          "aria-label",
          `${node.textContent} · Inspect concept`,
        );
        const select = () => {
          state.concept = c.id;
          state.offset = 0;
          if (location.hash === "#explorer") renderView();
          else location.hash = "explorer";
        };
        node.addEventListener("click", select);
        node.addEventListener("keydown", (e) => {
          if (["Enter", " "].includes(e.key)) {
            e.preventDefault();
            select();
          }
        });
      });
      let drag = null;
      region.addEventListener("pointerdown", (e) => {
        if (e.target.closest("g")) return;
        drag = {
          x: e.clientX,
          y: e.clientY,
          left: region.scrollLeft,
          top: region.scrollTop,
        };
        region.setPointerCapture(e.pointerId);
      });
      region.addEventListener("pointermove", (e) => {
        if (drag) {
          region.scrollLeft = drag.left + drag.x - e.clientX;
          region.scrollTop = drag.top + drag.y - e.clientY;
        }
      });
      region.addEventListener("pointerup", () => {
        drag = null;
      });
      region.addEventListener("pointercancel", () => {
        drag = null;
      });
    });
  document.querySelectorAll(".table-wrap").forEach((el) => {
    el.tabIndex = 0;
    el.setAttribute("role", "region");
    el.setAttribute("aria-label", "Scrollable data table");
  });
  const sidebar = $(".sidebar");
  if (sidebar && !$("#workspace-preferences")) {
    sidebar.insertAdjacentHTML(
      "beforeend",
      `<div id="workspace-preferences"><label for="theme">Appearance</label><select id="theme"><option value="system">System</option><option value="light">Light</option><option value="dark">Dark</option></select><button class="btn" data-action="help">Keyboard help</button></div>`,
    );
    $("#theme").value = preferences.get(
      `ontolayer-theme-${state.data.actor.id}`,
      "system",
    );
    setTheme($("#theme").value);
    sidebar.insertAdjacentHTML(
      "afterbegin",
      '<button id="menu-toggle" class="btn" aria-expanded="false" aria-controls="workspace-nav">Menu</button>',
    );
    $(".nav").id = "workspace-nav";
  }
  const status = $(".top-actions > .status");
  if (status) {
    const text = navigator.onLine ? "Connected" : "Offline";
    if (status.textContent.trim() !== text) status.textContent = text;
  }
}
function modal(title, content) {
  $("#dialog")?.remove();
  const dialog = document.createElement("dialog");
  dialog.id = "dialog";
  dialog.setAttribute("aria-labelledby", "dialog-title");
  dialog.innerHTML = `<h2 id="dialog-title">${esc(title)}</h2>${content}<form method="dialog"><button class="btn">Close</button></form>`;
  document.body.append(dialog);
  dialog.showModal();
}
document.addEventListener("change", (event) => {
  if (event.target.id === "theme") setTheme(event.target.value);
});
document.addEventListener("click", (event) => {
  const el = event.target.closest("button, a");
  if (!el) return;
  if (el.id === "menu-toggle") {
    const open = el.getAttribute("aria-expanded") !== "true";
    el.setAttribute("aria-expanded", String(open));
    $(".sidebar").classList.toggle("menu-open", open);
  }
  if (el.dataset.nav) {
    $(".sidebar")?.classList.remove("menu-open");
    $("#menu-toggle")?.setAttribute("aria-expanded", "false");
  }
  if (el.dataset.action === "help")
    modal(
      "Keyboard shortcuts",
      "<dl><dt>Alt + K</dt><dd>Search the workspace</dd><dt>Ctrl / Command + Enter</dt><dd>Run the guided query</dd><dt>Alt + T</dt><dd>Toggle theme</dd><dt>Escape</dt><dd>Close a dialog</dd></dl>",
    );
});
document.addEventListener("keydown", (event) => {
  if (event.altKey && event.key.toLowerCase() === "t") {
    event.preventDefault();
    setTheme(
      document.documentElement.dataset.theme === "dark" ? "light" : "dark",
    );
    if ($("#theme")) $("#theme").value = document.documentElement.dataset.theme;
  }
  if ((event.ctrlKey || event.metaKey) && event.key === "Enter") {
    event.preventDefault();
    $("#query-form")?.requestSubmit();
  }
});
matchMedia("(prefers-color-scheme: dark)").addEventListener("change", () => {
  if ($("#theme")?.value === "system") setTheme("system");
});
window.addEventListener("online", enhance);
window.addEventListener("offline", enhance);
let enhancing = false;
new MutationObserver(() => {
  if (enhancing) return;
  enhancing = true;
  requestAnimationFrame(() => {
    enhance();
    enhancing = false;
  });
}).observe($("#app"), { childList: true, subtree: true });
setTheme(preferences.get("ontolayer-theme-signin", "system"));

const toolExamples = {
  search_terms: { query: "revenue" },
  get_concept: { concept: "Customer" },
  list_entities: { concept: "Customer", limit: 20 },
  get_relationships: { entity_id: "Customer:C1" },
  find_path: { source: "Customer:C1", target: "Order:O1" },
  get_metric: { metric_id: "revenue" },
  query_metric: { metric_id: "revenue" },
  check_answerable: { metric_id: "revenue" },
  get_lineage: { entity_id: "Customer:C1" },
  explain_policy_decision: { entity_id: "Customer:C1" },
  list_ontology_versions: {},
};
function renderResultTable() {
  if (!$("#result-table") || !state.result) return;
  const query = $("#result-filter").value.toLowerCase();
  let rows = Object.entries(state.result.values)
    .filter(([k]) => k.toLowerCase().includes(query))
    .sort(([a], [b]) => a.localeCompare(b));
  if (state.resultReverse) rows.reverse();
  $("#result-table").innerHTML =
    `<div class="table-wrap"><table><thead><tr><th>Group</th><th>Exact value</th><th>Unit</th></tr></thead><tbody>${rows.map(([k, v]) => `<tr><td>${esc(k)}</td><td>${esc(number(v))}</td><td>${esc(state.result.unit)}</td></tr>`).join("")}</tbody></table></div>${rows.length ? "" : "<p>No matching groups.</p>"}`;
}
function filterGraph(controls) {
  const region = controls.nextElementSibling,
    focus = controls.querySelector(".graph-focus").value,
    status = controls.querySelector(".graph-status").value;
  const visible = new Set(
    focus ? [focus] : state.data.concepts.map((c) => c.id),
  );
  if (focus && controls.querySelector(".graph-neighbors").checked)
    state.data.links
      .filter((l) => l.source === focus || l.target === focus)
      .forEach((l) => {
        visible.add(l.source);
        visible.add(l.target);
      });
  state.data.concepts.forEach((c) => {
    if (status && c.status !== status) visible.delete(c.id);
  });
  region.querySelectorAll("svg > g").forEach((node, i) => {
    node.style.display = visible.has(state.data.concepts[i].id) ? "" : "none";
  });
  for (const selector of [".graph-line", ".link-text"])
    region.querySelectorAll(selector).forEach((node, i) => {
      const l = state.data.links[i];
      node.style.display =
        visible.has(l.source) && visible.has(l.target) ? "" : "none";
    });
}
const toolDescriptions = {
  search_terms: "Find permitted concepts, metrics and synonyms.",
  get_concept: "Read a concept and its visible properties.",
  list_entities: "Page through authorized records.",
  get_relationships: "Find relationships with visible endpoints.",
  find_path: "Find a bounded path through visible records.",
  get_metric: "Inspect a governed calculation.",
  query_metric: "Calculate a certified metric with scope and lineage.",
  check_answerable: "Check metric availability before calculating.",
  get_lineage: "Trace a visible record to its source.",
  explain_policy_decision: "Check visibility without exposing hidden records.",
  list_ontology_versions: "Read active ontology version metadata.",
};
function downloadText(name, content, type = "text/plain") {
  const url = URL.createObjectURL(new Blob([content], { type }));
  const a = document.createElement("a");
  a.href = url;
  a.download = name;
  a.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
function codeBlock(value) {
  return `<div class="code-block"><button class="btn" data-copy>Copy</button><pre tabindex="0">${esc(typeof value === "string" ? value : JSON.stringify(value, null, 2))}</pre></div>`;
}
function csvCell(value) {
  let text = String(value ?? "");
  if (/^[=+@\-\t\r]/.test(text)) text = "'" + text;
  return '"' + text.replaceAll('"', '""') + '"';
}
function globalSearch() {
  modal(
    "Search business knowledge",
    '<label for="global-search">Concept, synonym or metric</label><input id="global-search" type="search" autofocus><div id="search-results" aria-live="polite"></div>',
  );
  $("#global-search").focus();
}
function searchLocal(query) {
  const d = state.data;
  return [
    ...d.concepts.map((c) => ({ ...c, kind: "concept" })),
    ...d.metrics.map((m) => ({ ...m, kind: "metric" })),
  ].filter((c) =>
    [c.id, c.description, ...(c.synonyms || [])]
      .join(" ")
      .toLowerCase()
      .includes(query.toLowerCase()),
  );
}
function advancedForm(id = "advanced") {
  return `<form id="${id}-form"><label for="${id}-operation">Semantic tool</label><select id="${id}-operation" name="operation">${Object.keys(
    toolExamples,
  )
    .map((n) => `<option>${n}</option>`)
    .join(
      "",
    )}</select><p id="${id}-description" class="note">${toolDescriptions.search_terms}</p><label for="${id}-arguments">Arguments JSON</label><textarea id="${id}-arguments" name="arguments">${esc(JSON.stringify(toolExamples.search_terms, null, 2))}</textarea><button type="submit" class="btn primary">Test this tool</button></form><div id="${id}-result" aria-live="polite"></div>`;
}
async function renderExtras(view, epoch) {
  if (epoch !== state.epoch || !state.data) return;
  if (view === "overview") {
    $("#view .page-heading").classList.add("dashboard-heading");
    if (typeof dashboardVisuals === "function") await dashboardVisuals(epoch);
  }
  if (view === "explorer" && state.data.concepts.length) {
    $(".concept-menu").insertAdjacentHTML(
      "beforebegin",
      '<div class="card-body"><label for="concept-search">Find a concept</label><input id="concept-search" type="search"><label for="concept-status">Certification</label><select id="concept-status"><option value="">All statuses</option><option>certified</option><option>draft</option></select></div>',
    );
    const c = state.data.concepts.find((c) => c.id === state.concept);
    $(".concept-description").insertAdjacentHTML(
      "beforeend",
      `<p class="note">Synonyms: ${esc(c.synonyms.join(", ") || "None")}</p><h3>Relationships</h3>${
        state.data.links
          .filter((l) => l.source === c.id || l.target === c.id)
          .map(
            (l) => `<p>${esc(l.source)} → ${esc(l.id)} → ${esc(l.target)}</p>`,
          )
          .join("") || "<p>No visible relationships.</p>"
      }<h3>Metrics</h3>${
        state.data.metrics
          .filter((m) => m.type === c.id)
          .map(
            (m) =>
              `<button class="btn" data-metric="${esc(m.id)}">${esc(m.id)}</button>`,
          )
          .join("") || "<p>No visible metrics.</p>"
      }`,
    );
    $("#view").insertAdjacentHTML(
      "beforeend",
      `<section class="card">${cardHead("Explore relationships", "Tap a concept to inspect its records")}${graph()}</section>`,
    );
  }
  if (view === "access" && state.config.demo)
    $("#view").insertAdjacentHTML(
      "beforeend",
      `<section class="card">${cardHead("Compare demo identities", "Each side authenticates separately; no impersonation parameter is accepted")}<div class="card-body"><form id="compare-form"><div class="form-grid">${["left", "right"].map((s, i) => `<label>${pretty(s)} demo identity<select name="${s}">${["north", "south", "admin", "guest"].map((r) => `<option ${r === (i ? "south" : "north") ? "selected" : ""}>${r}</option>`).join("")}</select></label>`).join("")}<label class="full">Metric<select name="metric">${state.data.metrics.map((m) => `<option>${esc(m.id)}</option>`).join("")}</select></label></div><button class="btn primary" type="submit">Compare results</button></form><div id="comparison" class="split"></div></div></section>`,
    );
  if (!["validation", "audit", "mcp", "settings", "editor"].includes(view))
    return;
  $("#view").innerHTML =
    heading(
      "WORKSPACE",
      navigation.find((n) => n[0] === view)[1],
      {
        validation: "Review definition quality before certification.",
        audit: "Inspect requests and decisions available to your identity.",
        mcp: "Connect an agent to governed semantic tools.",
        settings: "Understand this deployment and your preferences.",
        editor: "Review changes as a draft before explicitly certifying them.",
      }[view],
    ) + loading();
  if (view === "validation") {
    const r = await api("/v1/validation");
    if (epoch !== state.epoch) return;
    $("#view").innerHTML =
      heading(
        "ONTOLOGY QUALITY",
        "Validation",
        `${r.score}/100 design score · ${r.scope}`,
        '<button class="btn" data-action="retry">Run linter</button>',
      ) +
      `<section class="card"><div class="card-body">${r.findings.map((f) => `<article class="finding"><span class="tag amber">${esc(f.severity)}</span><h3>${esc(f.rule)} · ${esc(f.path)}</h3><p>${esc(f.why)}</p><p>${esc(f.fix)}</p></article>`).join("") || empty("No design warnings", "The visible definitions pass the design linter. This is not a data quality or security certification.")}</div></section>`;
  }
  if (view === "audit") {
    const r = await api("/v1/audit");
    if (epoch !== state.epoch) return;
    state.auditItems = r.items;
    $("#view").innerHTML =
      heading("REQUEST HISTORY", "Audit log", r.scope) +
      `<section class="card"><div class="card-body"><label for="audit-filter">Filter user, tool, decision or timestamp</label><input id="audit-filter" type="search"><button class="btn" data-action="export-audit">Export filtered events</button></div><div id="audit-rows"></div></section>`;
    renderAudit("");
  }
  if (view === "mcp") {
    const r = await api("/v1/catalog");
    if (epoch !== state.epoch) return;
    const config = {
      mcpServers: {
        ontolayer: {
          command: "uv",
          args: [
            "run",
            "--directory",
            "/absolute/path/to/ontolayer",
            "ontolayer",
            "mcp",
            "--ontology",
            "examples/retail/ontology.yaml",
            "--actor",
            "examples/retail/north.yaml",
          ],
        },
      },
    };
    $("#view").innerHTML =
      heading(
        "AGENT CONNECTION",
        "MCP connect",
        "MCP uses a local stdio process; there is no HTTP MCP server URL.",
      ) +
      `<section class="card"><div class="card-body"><p>REST endpoint: <code>${esc(location.origin)}/v1/tools/{operation}</code>. The live tester below uses REST with your current identity and the same semantic service. It does not verify an external MCP client.</p><h3>Claude Desktop / Cursor / generic stdio client</h3><p>Set the absolute repository path and trusted actor file in this configuration. Restart your client after saving.</p>${codeBlock(config)}<h3>Available tools</h3>${r.tools.map((t) => `<details><summary>${esc(t.name)} — ${esc(toolDescriptions[t.name])}</summary>${codeBlock(t.inputSchema)}</details>`).join("")}${advancedForm("mcp")}</div></section>`;
  }
  if (view === "settings")
    $("#view").innerHTML =
      heading(
        "DEPLOYMENT",
        "Workspace settings",
        "Application details and preferences",
      ) +
      `<section class="card"><div class="card-body"><dl><dt>Application</dt><dd>${esc(state.config.version)}</dd><dt>Ontology</dt><dd>${esc(state.data.namespace)} ${esc(state.data.version)}</dd><dt>Environment</dt><dd>${state.config.demo ? "Synthetic demo" : "Authenticated deployment"}</dd><dt>Identity</dt><dd>${esc(state.data.actor.id)} · ${esc(state.data.actor.roles.join(", "))}</dd></dl><p>Theme preferences are stored per identity in this browser. Credentials and query results remain in memory.</p><p>The About page is available in English and Urdu.</p><a class="btn" href="https://github.com/AshubShafqat/ontolayer#readme" target="_blank" rel="noopener">Project documentation</a><button class="btn" data-action="help">Keyboard help</button></div></section>`;
  if (view === "editor") await renderEditor(epoch);
}
function renderAudit(query) {
  const rows = (state.auditItems || []).filter((e) =>
    Object.values(e).join(" ").toLowerCase().includes(query.toLowerCase()),
  );
  state.auditFiltered = rows;
  $("#audit-rows").innerHTML = rows.length
    ? `<div class="table-wrap"><table><thead><tr><th>Time</th><th>User</th><th>Tool</th><th>Decision</th></tr></thead><tbody>${rows.map((e) => `<tr><td>${esc(e.timestamp)}</td><td>${esc(e.actor)}</td><td>${esc(e.operation)}</td><td>${esc(e.outcome)}</td></tr>`).join("")}</tbody></table></div>`
    : empty("No matching events", "Try another filter or run a query first.");
}
document.addEventListener("input", (event) => {
  if (event.target.id === "result-filter") renderResultTable();
  if (event.target.id === "global-search")
    $("#search-results").innerHTML =
      searchLocal(event.target.value)
        .slice(0, 100)
        .map(
          (c) =>
            `<button class="btn" data-search-kind="${c.kind}" data-search-id="${esc(c.id)}">${esc(c.id)} · ${c.kind}</button>`,
        )
        .join("") || "<p>No permitted definitions match.</p>";
  if (event.target.id === "audit-filter") renderAudit(event.target.value);
  if (event.target.id === "concept-search") filterConcepts();
});
function filterConcepts() {
  const q = $("#concept-search").value.toLowerCase(),
    status = $("#concept-status").value;
  document.querySelectorAll("[data-concept]").forEach((el) => {
    const c = state.data.concepts.find((c) => c.id === el.dataset.concept);
    el.hidden =
      !c ||
      !(
        [c.id, c.description, ...c.synonyms]
          .join(" ")
          .toLowerCase()
          .includes(q) &&
        (!status || c.status === status)
      );
  });
}
document.addEventListener("change", (event) => {
  if (event.target.matches(".graph-focus,.graph-status,.graph-neighbors"))
    filterGraph(event.target.closest(".graph-controls"));
  if (event.target.id === "concept-status") filterConcepts();
  for (const id of ["advanced", "mcp"])
    if (event.target.id === `${id}-operation`) {
      $(`#${id}-arguments`).value = JSON.stringify(
        toolExamples[event.target.value],
        null,
        2,
      );
      $(`#${id}-description`).textContent =
        toolDescriptions[event.target.value];
    }
});
document.addEventListener("keydown", (event) => {
  if (event.altKey && event.key.toLowerCase() === "k") {
    event.preventDefault();
    if (state.data) globalSearch();
  }
});
document.addEventListener("click", async (event) => {
  const el = event.target.closest("button");
  if (!el) return;
  try {
    if (el.dataset.action === "load-graph")
      el.closest(".graph-placeholder").outerHTML = graphMarkup();
    if (el.dataset.action === "sort-result") {
      state.resultReverse = !state.resultReverse;
      renderResultTable();
    }
    if (el.dataset.action === "search") globalSearch();
    if (el.dataset.zoom) {
      const region = el.closest(".graph-controls").nextElementSibling;
      const svg = region.querySelector("svg");
      const zoom = Math.max(
        1,
        Math.min(
          4,
          el.dataset.zoom === "reset"
            ? 1
            : Number(region.dataset.zoom || 1) +
                (el.dataset.zoom === "in" ? 0.5 : -0.5),
        ),
      );
      region.dataset.zoom = zoom;
      svg.setAttribute("width", `${zoom * 100}%`);
      svg.classList.toggle("zoomed", zoom > 1);
      svg.style.width = `${zoom * 100}%`;
    }
    if (el.dataset.searchId) {
      $("#dialog").close();
      if (el.dataset.searchKind === "concept") {
        state.concept = el.dataset.searchId;
        state.offset = 0;
        location.hash = "explorer";
        await renderView();
      } else {
        location.hash = "studio";
        setTimeout(() => studio(el.dataset.searchId), 0);
      }
    }
    if (el.hasAttribute("data-copy")) {
      await navigator.clipboard.writeText(
        el.parentElement.querySelector("pre").textContent,
      );
      announce("Copied to clipboard");
      el.textContent = "Copied";
    }
    if (el.dataset.action === "export-audit")
      downloadText(
        "audit.json",
        JSON.stringify(state.auditFiltered, null, 2),
        "application/json",
      );
    if (el.dataset.action === "csv" && state.result)
      downloadText(
        `${state.result.metric}.csv`,
        [
          ["group", "value", "unit"],
          ...Object.entries(state.result.values).map(([k, v]) => [
            k,
            v,
            state.result.unit,
          ]),
        ]
          .map((r) => r.map(csvCell).join(","))
          .join("\r\n"),
        "text/csv",
      );
    if (el.dataset.action === "copy-result" && state.result) {
      await navigator.clipboard.writeText(
        JSON.stringify(state.result, null, 2),
      );
      announce("Result copied");
    }
  } catch (error) {
    showError(error);
  }
});
document.addEventListener("submit", async (event) => {
  const form = event.target,
    data = new FormData(form),
    epoch = state.epoch;
  if (!["advanced-form", "mcp-form", "compare-form"].includes(form.id)) return;
  const button = form.querySelector('[type="submit"]');
  button.disabled = true;
  try {
    if (form.id === "compare-form") {
      const results = await Promise.all(
        ["left", "right"].map(async (side) => {
          const role = data.get(side);
          const response = await fetch("/v1/tools/query_metric", {
            method: "POST",
            headers: {
              Authorization: `Bearer demo-${role}-token`,
              "Content-Type": "application/json",
            },
            body: JSON.stringify({
              arguments: { metric_id: data.get("metric") },
            }),
            signal: AbortSignal.any([
              state.controller.signal,
              AbortSignal.timeout(15000),
            ]),
          });
          const body = await response.json();
          return { role, body, ok: response.ok };
        }),
      );
      if (epoch !== state.epoch) return;
      $("#comparison").innerHTML = results
        .map(
          (r) =>
            `<div class="card-body"><h3>${esc(r.role)}</h3>${
              r.ok
                ? `<p>${Object.entries(r.body.values)
                    .map(
                      ([k, v]) =>
                        `${esc(k)}: ${esc(number(v))} ${esc(r.body.unit)}`,
                    )
                    .join("<br>")}</p><p>${esc(r.body.scope)}</p>`
                : `<p>${esc(r.body.detail || "Not available")}</p>`
            }</div>`,
        )
        .join("");
    } else {
      const result = await tool(
        String(data.get("operation")),
        JSON.parse(data.get("arguments")),
      );
      if (epoch !== state.epoch) return;
      $(`#${form.id.replace("-form", "")}-result`).innerHTML =
        codeBlock(result);
      if (data.get("operation") === "query_metric" && $("#query-result"))
        saveResult(result);
    }
  } catch (error) {
    if (epoch === state.epoch) showError(error);
  } finally {
    button.disabled = false;
  }
});

let draftReview = null;
let validationTimer = null;
let validationSequence = 0;
let draftRevision = null;
let draftUploads = {};
async function renderEditor(epoch) {
  draftReview = null;
  draftUploads = {};
  draftRevision = null;
  if (!state.data.actor.roles.includes("admin")) {
    $("#view").innerHTML =
      heading(
        "GOVERNANCE",
        "Draft & import",
        "Changes require an administrator credential.",
      ) +
      empty(
        "Read-only identity",
        "Use your own administrator credential, or choose Administrator in the synthetic demo.",
      );
    return;
  }
  if (!state.config.editing) {
    $("#view").innerHTML = empty(
      "Workbench unavailable",
      "Configure a persistent workspace directory on the server.",
    );
    return;
  }
  const r = await api("/v1/ontology");
  if (epoch !== state.epoch) return;
  draftRevision = r.revision;
  const parts = r.document.version.split(".").map(Number);
  parts[2]++;
  r.document.version = parts.join(".");
  $("#view").innerHTML =
    heading(
      "CHANGE REVIEW",
      "Draft & import",
      "Edit, validate and review the diff. Only explicit certification changes the active workspace.",
    ) +
    `<section class="card"><div class="card-body"><p>The next patch version is prefilled. Add or edit concepts in <code>types</code>, relationships in <code>links</code>, and calculations in <code>metrics</code>. Source paths cannot read arbitrary files; new sources require a CSV upload.</p><form id="draft-form"><label for="ontology-upload">Import ontology JSON or YAML</label><input id="ontology-upload" type="file" accept=".json,.yaml,.yml"><label for="draft-document">Draft ontology document</label><textarea id="draft-document" name="document" spellcheck="false" rows="24">${esc(JSON.stringify(r.document, null, 2))}</textarea><p id="draft-validation" role="status">Edit the definition, then preview the complete graph.</p><label for="upload-mapping">Mapping name for CSV replacement / new source</label><input id="upload-mapping" placeholder="e.g. customers"><label for="csv-upload">CSV source (48 KB / 1000 rows maximum)</label><input id="csv-upload" type="file" accept=".csv"><p id="upload-status" role="status">No uploaded sources.</p><button class="btn primary" type="submit">Validate & preview draft</button></form><div class="form-actions">${["yaml", "json", "turtle"].map((f) => `<button class="btn" data-export-ontology="${f}">Export ${f.toUpperCase()}</button>`).join("")}</div><div id="draft-preview"></div></div></section>`;
}
document.addEventListener("input", (event) => {
  if (event.target.id === "draft-document") {
    draftReview = null;
    clearTimeout(validationTimer);
    const sequence = ++validationSequence,
      epoch = state.epoch,
      documentText = event.target.value;
    validationTimer = setTimeout(async () => {
      try {
        const result = await api("/v1/drafts/validate", {
          document: documentText,
          revision: draftRevision,
        });
        if (
          epoch === state.epoch &&
          sequence === validationSequence &&
          $("#draft-validation")
        )
          $("#draft-validation").textContent = result.message;
      } catch (error) {
        if (
          epoch === state.epoch &&
          sequence === validationSequence &&
          $("#draft-validation")
        )
          $("#draft-validation").textContent =
            "Live validation unavailable. Retry preview when connected.";
      }
    }, 500);
    $("#draft-preview").innerHTML = "";
    try {
      JSON.parse(event.target.value);
      $("#draft-validation").textContent =
        "Valid JSON syntax. Server validation and graph preview are still required.";
    } catch {
      $("#draft-validation").textContent =
        "JSON syntax is incomplete, or this is YAML. Preview will validate the full document on the server.";
    }
  }
});
document.addEventListener("change", async (event) => {
  if (!["ontology-upload", "csv-upload"].includes(event.target.id)) return;
  const file = event.target.files[0];
  if (!file) return;
  try {
    if (file.size > 48000)
      throw new Error("This workbench accepts files up to 48 KB.");
    const content = await file.text();
    draftReview = null;
    $("#draft-preview").innerHTML = "";
    if (event.target.id === "ontology-upload") {
      $("#draft-document").value = content;
      $("#draft-validation").textContent =
        "Imported document. Preview before certification.";
    } else {
      const mapping = $("#upload-mapping").value.trim();
      if (!/^[A-Za-z][A-Za-z0-9_]*$/.test(mapping))
        throw new Error("Enter the mapping name before selecting a CSV.");
      draftUploads[mapping] = content;
      $("#upload-status").textContent =
        `Uploaded mappings: ${Object.keys(draftUploads).join(", ")}. These are staged only.`;
    }
  } catch (error) {
    showError(error);
  }
});
document.addEventListener("submit", async (event) => {
  if (event.target.id !== "draft-form") return;
  const button = event.target.querySelector('[type="submit"]'),
    epoch = state.epoch;
  button.disabled = true;
  draftReview = null;
  try {
    const result = await api("/v1/drafts/preview", {
      document: $("#draft-document").value,
      revision: draftRevision,
      uploads: draftUploads,
    });
    if (epoch !== state.epoch) return;
    draftReview = result;
    $("#draft-preview").innerHTML =
      `<h2>Review draft</h2><p>${result.entities} validated records · ${result.relationships} relationships · ${result.findings.length} design warnings</p><h3>Mapping preview</h3>${codeBlock(result.mappings)}<h3>Changes from active ontology</h3>${codeBlock(result.diff)}<button class="btn primary" data-action="certify-dialog">Review certification</button>`;
  } catch (error) {
    if (epoch === state.epoch) showError(error);
  } finally {
    button.disabled = false;
  }
});
document.addEventListener("click", async (event) => {
  const el = event.target.closest("button");
  if (!el) return;
  try {
    if (el.dataset.exportOntology) {
      const response = await fetch(
        `/v1/ontology/export?format=${el.dataset.exportOntology}`,
        {
          headers: { Authorization: `Bearer ${state.token}` },
          signal: state.controller.signal,
        },
      );
      if (!response.ok)
        throw new Error("Ontology export requires administrator access.");
      downloadText(
        `ontology.${el.dataset.exportOntology === "turtle" ? "ttl" : el.dataset.exportOntology}`,
        await response.text(),
      );
    }
    if (el.dataset.action === "certify-dialog" && draftReview)
      modal(
        "Certify and activate this draft?",
        '<p>This explicitly certifies all definitions in the reviewed draft and replaces the active graph. Existing credentials will be evaluated against the reviewed policies. The complete release is saved for restart recovery.</p><button class="btn primary" data-action="certify-confirm">Certify & activate reviewed draft</button>',
      );
    if (el.dataset.action === "certify-confirm" && draftReview) {
      el.disabled = true;
      const epoch = state.epoch;
      const result = await api(`/v1/drafts/${draftReview.id}/certify`, {
        revision: draftRevision,
      });
      if (epoch !== state.epoch) return;
      $("#dialog").close();
      await connect(state.token, state.role);
      announce(`Activated ontology ${result.version}`);
    }
  } catch (error) {
    $("#dialog")?.close();
    showError(error);
  }
});

async function renderAbout(language = "en") {
  const epoch = state.epoch;
  const catalog = await fetch("/static/locales.json").then((r) => r.json());
  if (state.view !== "about" || epoch !== state.epoch) return;
  const locale = catalog[language] || catalog.en;
  const copy = locale.about;
  const repo = "https://github.com/AshubShafqat/ontolayer";
  const urls = [
    window.location.origin,
    `${window.location.origin}/health`,
    repo,
    `${repo}/blob/main/docs/mcp.md`,
    `${repo}/blob/main/docs/spec.md`,
    `${repo}/blob/main/docs/architecture.md`,
    `${repo}/blob/main/SECURITY.md`,
    `${repo}/blob/main/LICENSE`,
    "https://github.com/AshubShafqat",
    "https://ashub-portfolio.vercel.app",
  ];
  $("#view").innerHTML =
    `<section class="about-page" lang="${esc(language)}" dir="${esc(locale.direction)}">
    ${heading(esc(copy.eyebrow), esc(copy.title), esc(copy.description))}
    <label for="about-language">${esc(copy.language)}</label>
    <select id="about-language">${Object.keys(catalog)
      .map(
        (key) =>
          `<option value="${esc(key)}" ${key === language ? "selected" : ""}>${key === "ur" ? "اردو" : "English"}</option>`,
      )
      .join("")}</select>
    <section class="card about-demo"><div class="card-body"><h2>${esc(copy.demo)}</h2><p>${esc(copy.example)}</p><ol class="about-flow">${copy.flow.map((step) => `<li>${esc(step)}</li>`).join("")}</ol></div></section>
    <div class="about-columns"><section class="card"><div class="card-body"><h2>${esc(copy.resources)}</h2><ul class="about-links">${urls.map((url, i) => `<li><a href="${esc(url)}" target="_blank" rel="noopener noreferrer">${esc(copy.links[i])}${icon("arrow")}</a></li>`).join("")}</ul></div></section>
    <section class="card"><div class="card-body"><h2>${esc(copy.limitsTitle)}</h2><ul class="about-limits">${copy.limits.map((limit) => `<li>${esc(limit)}</li>`).join("")}</ul></div></section></div></section>`;
  $("#about-language").addEventListener("change", (event) =>
    renderAbout(event.target.value).catch(showError),
  );
}
