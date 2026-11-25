const { test, expect } = require("@playwright/test");
const AxeBuilder = require("@axe-core/playwright").default;

test("diagnostic screens expose permitted data and searchable tools", async ({
  page,
}) => {
  const errors = [];
  page.on("pageerror", (e) => errors.push(e.message));
  for (const route of ["validation", "audit", "mcp", "settings", "editor"]) {
    await page.goto(`/#${route}`);
    await expect(page.locator(".sidebar")).toBeVisible();
    await expect(page.locator(".loading")).toHaveCount(0);
    await expect(page.locator("#error")).toBeHidden();
    const result = await new AxeBuilder({ page })
      .withTags(["wcag2a", "wcag2aa", "wcag21aa"])
      .analyze();
    expect(result.violations, JSON.stringify(result.violations)).toEqual([]);
  }
  await page.getByRole("button", { name: "Search", exact: true }).click();
  await page.getByLabel("Concept, synonym or metric").fill("revenue");
  await page
    .getByRole("button", { name: "revenue · metric", exact: true })
    .click();
  await expect(page.getByLabel("Business metric")).toHaveValue("revenue");
  await page.getByText("Advanced mode · raw semantic tool request").click();
  await page.getByLabel("Semantic tool").selectOption("query_metric");
  await page
    .getByLabel("Arguments JSON")
    .fill(
      '{"metric_id":"revenue","start_date":"2026-10-01","end_date":"2026-11-01"}',
    );
  await page.getByRole("button", { name: "Test this tool" }).click();
  await expect(page.locator(".result-number")).toContainText("250");
  const download = page.waitForEvent("download");
  await page.getByRole("button", { name: "Export CSV" }).click();
  expect((await download).suggestedFilename()).toBe("revenue.csv");
  expect(errors).toEqual([]);
});

test("demo comparison and explicit draft certification", async ({ page }) => {
  await page.goto("/#access");
  await page.getByRole("button", { name: "Compare results" }).click();
  await expect(page.locator("#comparison")).toContainText("330");
  await expect(page.locator("#comparison")).toContainText("350");
  await page.getByLabel("Demo identity", { exact: true }).selectOption("admin");
  await page.getByRole("link", { name: "Draft & import" }).click();
  const doc = page.getByLabel("Draft ontology document");
  await expect(doc).toBeVisible();
  const candidate = JSON.parse(await doc.inputValue());
  candidate.description =
    "Retail demonstration ontology, reviewed through the workbench";
  await doc.fill(JSON.stringify(candidate, null, 2));
  await page.getByRole("button", { name: "Validate & preview draft" }).click();
  await expect(page.locator("#draft-preview")).toContainText(
    "validated records",
  );
  await expect(page.locator("#draft-preview")).toContainText("Mapping preview");
  await page.getByRole("button", { name: "Review certification" }).click();
  await page
    .getByRole("button", { name: "Certify & activate reviewed draft" })
    .click();
  await expect(page.getByLabel("Draft ontology document")).toBeVisible();
  await expect(page.locator(".breadcrumb")).toContainText(candidate.version);
  await page.getByLabel("Demo identity", { exact: true }).selectOption("north");
  await expect(
    page.getByRole("heading", { name: "Read-only identity" }),
  ).toBeVisible();
});
