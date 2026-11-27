const { test, expect } = require("@playwright/test");
const AxeBuilder = require("@axe-core/playwright").default;
for (const width of [320, 375, 768, 1280]) {
  test(`About accessible at ${width}`, async ({ page }) => {
    await page.setViewportSize({ width, height: 960 });
    await page.goto("/#about");
    await expect(
      page.getByRole("heading", { name: "About OntoLayer" }),
    ).toBeVisible();
    await expect(page.locator('[data-nav="about"]')).toHaveAttribute(
      "aria-current",
      "page",
    );
    const live = page.getByRole("link", { name: "Live app", exact: true });
    await expect(live).toHaveAttribute("href", "http://127.0.0.1:8000");
    await live.focus();
    await expect(live).toBeFocused();
    for (const theme of ["light", "dark"]) {
      if (width <= 1024)
        await page.getByRole("button", { name: "Menu", exact: true }).click();
      await page.getByLabel("Appearance").selectOption(theme);
      if (width <= 1024)
        await page.getByRole("button", { name: "Menu", exact: true }).click();
      expect(
        await page.evaluate(
          () => document.documentElement.scrollWidth <= innerWidth,
        ),
      ).toBeTruthy();
      const results = await new AxeBuilder({ page })
        .withTags(["wcag2a", "wcag2aa", "wcag21aa"])
        .analyze();
      expect(results.violations).toEqual([]);
    }
    for (const link of await page.locator(".about-links a").all()) {
      await expect(link).toHaveAttribute("rel", "noopener noreferrer");
    }
    await page.getByLabel("About page language").selectOption("ur");
    await expect(page.locator(".about-page")).toHaveAttribute("dir", "rtl");
    await expect(page.locator(".about-page")).toHaveAttribute("lang", "ur");
    await expect(page.locator(".about-page h1")).toContainText("اونٹو");
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth,
      ),
    ).toBeTruthy();
  });
}
test("Undated query displays All dates with unchanged JSON", async ({
  page,
}) => {
  await page.goto("/#studio");
  await page.getByRole("button", { name: "Run query", exact: true }).click();
  await expect(page.locator("#query-result")).toContainText("All dates");
});
