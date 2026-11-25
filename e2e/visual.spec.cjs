const { test, expect } = require("@playwright/test");
for (const width of [375, 768, 1280]) {
  test(`query studio visual baseline ${width}`, async ({ page }) => {
    await page.setViewportSize({ width, height: 900 });
    await page.addInitScript(() =>
      localStorage.setItem("ontolayer-theme-demo-north", "light"),
    );
    await page.goto("/#studio");
    await expect(
      page.getByRole("heading", { name: "Ask with confidence." }),
    ).toBeVisible();
    await expect(page.locator("#menu-toggle")).toBeAttached();
    await expect(page).toHaveScreenshot(`studio-${width}.png`, {
      animations: "disabled",
      maxDiffPixelRatio: 0.01,
      mask: [
        page.locator(".breadcrumb > .tag"),
        page.locator(".side-footer"),
        page.locator(".footer"),
      ],
    });
  });
}
