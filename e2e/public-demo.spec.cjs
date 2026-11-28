const { test, expect } = require("@playwright/test");
const AxeBuilder = require("@axe-core/playwright").default;

test("public demo sign-in authenticates each read-only identity", async ({
  page,
}) => {
  await page.route("**/v1/config", async (route) => {
    const response = await route.fetch();
    const config = await response.json();
    await route.fulfill({
      response,
      json: {
        ...config,
        demo: false,
        public_demo_tokens: {
          north: "demo-north-token",
          south: "demo-south-token",
          analyst: "demo-analyst-token",
        },
      },
    });
  });
  await page.goto("/");
  for (const [role, total] of [
    ["north", "330"],
    ["south", "350"],
    ["analyst", "680"],
  ]) {
    await expect(page.locator(".demo-choice")).toHaveCount(3);
    await expect(page.locator('[data-public-role="admin"]')).toHaveCount(0);
    await page.locator(`[data-public-role="${role}"]`).click();
    await expect(page.locator(".insight-number")).toContainText(total);
    await expect(page.locator("#identity-role")).toHaveCount(0);
    await page.getByRole("button", { name: "Sign out", exact: true }).click();
  }
  for (const width of [320, 1280]) {
    await page.setViewportSize({ width, height: 960 });
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth,
      ),
    ).toBeTruthy();
    const result = await new AxeBuilder({ page })
      .withTags(["wcag2a", "wcag2aa", "wcag21aa"])
      .analyze();
    expect(result.violations).toEqual([]);
  }
});
