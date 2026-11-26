"use strict";

function meaningFlow() {
  const steps = [
    [
      "data",
      "01 · Connect",
      "CSV and SQLite become real business records.",
      "explorer",
    ],
    [
      "graph",
      "02 · Define",
      "Concepts and links give each record meaning.",
      "explorer",
    ],
    [
      "shield",
      "03 · Govern",
      "Policies limit what each identity can see.",
      "access",
    ],
    [
      "spark",
      "04 · Ask",
      "Reviewed metrics return answers with evidence.",
      "studio",
    ],
  ];
  return `<section class="understanding"><div class="section-intro"><div><h2>From raw data to a trusted answer.</h2><p>Your shared business dictionary, brought to life.</p></div><button class="btn" data-action="explain-project">How it works ${icon("arrow")}</button></div><div class="meaning-flow">${steps.map(([symbol, title, description, route]) => `<a class="meaning-step" href="#${route}"><span class="step-icon">${icon(symbol)}</span><strong>${title}</strong><small>${description}</small></a>`).join("")}</div></section>`;
}
function certificationVisual() {
  const definitions = [...state.data.concepts, ...state.data.metrics];
  const certified = definitions.filter((d) => d.status === "certified").length;
  const total = definitions.length,
    percent = total ? Math.round((certified / total) * 100) : 0;
  return `<section class="card">${cardHead("Definition readiness", "Concepts and metrics visible to you")}<div class="certification-visual"><svg class="ring-chart" viewBox="0 0 160 160" role="img" aria-label="${certified} of ${total} visible definitions are certified"><circle class="ring-base" cx="80" cy="80" r="62"/><circle class="ring-value" cx="80" cy="80" r="62" pathLength="100" stroke-dasharray="${percent} 100"/><text class="ring-number" x="80" y="80">${percent}%</text><text class="ring-caption" x="80" y="100">CERTIFIED</text></svg><div class="legend-list"><span><b>${certified}</b> certified definitions</span><span><b>${total - certified}</b> drafts awaiting review</span><span><b>${state.data.links.length}</b> relationship types</span></div></div><div class="visual-explanation">Certification means an explicit reviewer approved a definition. It is not a guarantee of source-data quality.</div></section>`;
}
async function dashboardVisuals(epoch) {
  if (epoch !== state.epoch || !state.data) return;
  if (!$(".understanding"))
    $("#view .stats").insertAdjacentHTML("afterend", meaningFlow());
  const metric = state.data.metrics.find(
    (m) => m.status === "certified" && m.dimensions.length,
  );
  let result = null;
  if (metric)
    result = await tool("query_metric", {
      metric_id: metric.id,
      group_by: metric.dimensions[0],
    });
  if (epoch !== state.epoch || !state.data) return;
  const rows = result ? Object.entries(result.values) : [];
  const max = Math.max(1, ...rows.map(([, value]) => Number(value)));
  const chart = `<section class="card">${cardHead(result ? `${esc(pretty(result.metric))} by ${esc(pretty(metric.dimensions[0]))}` : "Your authorized data", "Live calculation · all available dates")}<div class="card-body">${rows.length ? rows.map(([group, value]) => `<div class="chart-row"><span>${esc(pretty(group))}</span><div class="chart-track"><svg width="100%" height="12" aria-hidden="true"><rect class="chart-fill" x="0" y="0" width="${(Math.max(0, Number(value)) / max) * 100}%" height="12" rx="6" fill="#7463d7"/></svg></div><strong>${esc(number(value))} ${esc(result.unit)}</strong></div>`).join("") : empty("No visible groups", "Your current identity has no grouped metric results.")}</div><div class="visual-explanation">Only permitted records contribute. Switch identity to see how the same definition produces a different authorized view.</div></section>`;
  $("#view .understanding").insertAdjacentHTML(
    "afterend",
    `<div class="visual-grid">${chart}${certificationVisual()}</div>`,
  );
}
document.addEventListener("click", (event) => {
  if (event.target.closest('[data-action="explain-project"]'))
    modal(
      "Meet your business semantic layer",
      `<p>OntoLayer is a dictionary, a map and a set of access rules for your business data.</p><div class="learning-note"><strong>Example: “What is revenue?”</strong><br>The ontology defines the calculation. Source mappings connect it to order lines. Policies select only records you may see. The service calculates an exact answer and returns its source evidence.</div><div class="meaning-flow"><div class="meaning-step"><strong>Ontology</strong><small>Defines Customer, Order, their relationships and the meaning of revenue.</small></div><div class="meaning-step"><strong>Knowledge graph</strong><small>Contains actual customers, orders and connected records from your files.</small></div><div class="meaning-step"><strong>Governance</strong><small>Filters records and properties before any result reaches a person or model.</small></div><div class="meaning-step"><strong>MCP tools</strong><small>Give agents the same governed definitions and deterministic calculations.</small></div></div>`,
    );
});
