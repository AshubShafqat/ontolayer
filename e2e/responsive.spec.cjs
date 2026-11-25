const { test, expect } = require("@playwright/test");
const AxeBuilder = require("@axe-core/playwright").default;
for (const width of [320, 375, 768, 1280]) {
  test(`responsive and keyboard regions at ${width}`, async ({ page }) => {
    await page.setViewportSize({ width, height: 960 });
    for (const route of ["overview", "explorer", "studio", "access"]) {
      await page.goto(`/#${route}`);
      await expect(page.locator(".sidebar")).toBeVisible();
      await expect(page.locator(".loading")).toHaveCount(0);
      expect(
        await page.evaluate(
          () => document.documentElement.scrollWidth <= innerWidth,
        ),
      ).toBeTruthy();
      const results = await new AxeBuilder({ page })
        .withTags(["wcag2a", "wcag2aa", "wcag21aa"])
        .analyze();
      expect(results.violations, JSON.stringify(results.violations)).toEqual(
        [],
      );
      await page.screenshot({
        path: `test-results/${route}-${width}.png`,
        fullPage: true,
      });
    }
  });
}
test("theme persists and offline errors recover", async ({ page, context }) => {
  await page.goto("/#explorer");
  await expect(page.locator("#entity-list")).toContainText("Customer:C1");
  await page.getByLabel("Appearance").selectOption("dark");
  await page.reload();
  await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
  await expect(page.locator(".loading")).toHaveCount(0);
  const result = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa", "wcag21aa"])
    .analyze();
  expect(result.violations, JSON.stringify(result.violations)).toEqual([]);
  await context.setOffline(true);
  await page
    .getByRole("button", { name: "Order", exact: false })
    .first()
    .click();
  await expect(page.locator("#error")).toContainText("offline");
  await expect(page.locator(".loading")).toHaveCount(0);
  await context.setOffline(false);
  await page.getByRole("button", { name: "Retry page" }).click();
  await expect(page.locator("#entity-list")).toContainText("Order:");
});
