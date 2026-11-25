const { test, expect } = require("@playwright/test");
const AxeBuilder = require("@axe-core/playwright").default;

test("workspace loads live values and switches identity without stale data", async ({
  page,
}) => {
  const errors = [];
  page.on("pageerror", (error) => errors.push(error.message));
  await page.goto("/");
  await expect(
    page.getByRole("heading", { name: "Business knowledge, connected." }),
  ).toBeVisible();
  await expect(page.locator(".insight-number")).toContainText("330");
  await page.getByLabel("Demo identity").selectOption("admin");
  await expect(page.locator(".insight-number")).toContainText("680");
  await page.getByLabel("Demo identity").selectOption("guest");
  await expect(
    page.getByRole("heading", { name: "No executable metrics" }),
  ).toBeVisible();
  await expect(page.locator(".insight-number")).toHaveCount(0);
  expect(errors).toEqual([]);
});

test("query form computes scoped revenue and exports actual evidence", async ({
  page,
}) => {
  await page.goto("/#studio");
  await page.getByLabel("Business metric").selectOption("revenue");
  await page.getByLabel("Start date").fill("2026-10-01");
  await page.getByLabel("End date (exclusive)").fill("2026-11-01");
  await page.getByRole("button", { name: "Run query" }).click();
  await expect(page.locator(".result-number")).toContainText("250");
  await expect(page.locator("#query-result")).toContainText("lines.csv");
  const downloadPromise = page.waitForEvent("download");
  await page.getByRole("button", { name: "Download result" }).click();
  const download = await downloadPromise;
  expect(download.suggestedFilename()).toBe("ontolayer-revenue.json");
  await page.getByLabel("Ask your business data").fill("revenue last month");
  await page.getByRole("button", { name: "Ask", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "Please clarify your question" }),
  ).toBeVisible();
});

test("explorer filters PII and exposes real lineage; denied records stay hidden", async ({
  page,
}) => {
  await page.goto("/#explorer");
  await expect(page.locator("#entity-list")).toContainText("Customer:C1");
  await expect(page.locator("#entity-list")).not.toContainText("Customer:C2");
  await expect(page.locator("#entity-list")).not.toContainText("email");
  await page.getByRole("button", { name: "Lineage" }).click();
  await expect(page.locator("#entity-detail")).toContainText("customers.csv");
  await page.getByRole("link", { name: "Access & lineage" }).click();
  await page.getByLabel("Entity identifier").fill("Customer:C2");
  await page.getByRole("button", { name: "Inspect record" }).click();
  await expect(page.locator("#access-result")).toContainText(
    "Not available to this caller",
  );
  await expect(page.locator("#access-result pre")).toHaveCount(0);
});

test("sign out clears visible information and rejects bad credentials", async ({
  page,
}) => {
  await page.goto("/");
  await page.getByRole("button", { name: "Sign out" }).click();
  await expect(
    page.getByRole("heading", { name: "Open your workspace" }),
  ).toBeVisible();
  await page.getByLabel("Access token").fill("invalid");
  await page.getByRole("button", { name: "Connect to workspace" }).click();
  await expect(page.locator("#login-error")).toContainText(
    "Invalid credential",
  );
  await page.getByLabel("Access token").fill("demo-south-token");
  await page.getByRole("button", { name: "Connect to workspace" }).click();
  await expect(page.locator(".insight-number")).toContainText("350");
});

test("mobile layout stays within viewport and navigation works", async ({
  page,
}) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/");
  await expect(page.locator(".insight-number")).toContainText("330");
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBeTruthy();
  await page.getByRole("button", { name: "Menu", exact: true }).click();
  await page.getByRole("link", { name: "Query studio" }).click();
  await expect(
    page.getByRole("heading", { name: "Ask with confidence." }),
  ).toBeVisible();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBeTruthy();
});

test("workspace pages meet automated WCAG AA checks", async ({ page }) => {
  for (const route of ["overview", "explorer", "studio", "access"]) {
    await page.goto("/#" + route);
    await expect(page.locator(".sidebar")).toBeVisible();
    await expect(page.locator(".loading")).toHaveCount(0);
    const result = await new AxeBuilder({ page })
      .withTags(["wcag2a", "wcag2aa", "wcag21aa"])
      .analyze();
    expect(
      result.violations,
      JSON.stringify(result.violations, null, 2),
    ).toEqual([]);
  }
  await page.getByRole("button", { name: "Sign out" }).click();
  const signIn = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa", "wcag21aa"])
    .analyze();
  expect(signIn.violations, JSON.stringify(signIn.violations, null, 2)).toEqual(
    [],
  );
});
