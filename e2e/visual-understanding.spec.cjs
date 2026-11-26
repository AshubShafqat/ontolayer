const { test, expect } = require("@playwright/test");
const AxeBuilder = require("@axe-core/playwright").default;
test("visual explanations reflect governed data and support reduced motion", async ({
  page,
}) => {
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.goto("/");
  await expect(page.locator(".visual-grid")).toContainText("330");
  await expect(page.locator(".ring-chart")).toHaveAttribute(
    "aria-label",
    /7 of 7/,
  );
  await page.getByRole("button", { name: /How it works/ }).click();
  await expect(page.getByRole("dialog")).toContainText("dictionary, a map");
  await page.keyboard.press("Escape");
  await expect(page.getByRole("dialog")).not.toBeVisible();
  await page.getByLabel("Appearance").selectOption("dark");
  const result = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa", "wcag21aa"])
    .analyze();
  expect(result.violations, JSON.stringify(result.violations)).toEqual([]);
  expect(
    await page
      .locator(".chart-fill")
      .first()
      .evaluate((el) => getComputedStyle(el).animationName),
  ).toBe("none");
});
test("rapid identity switches never render old graph callbacks", async ({
  page,
}) => {
  const errors = [];
  page.on("pageerror", (e) => errors.push(e.message));
  await page.goto("/");
  for (const role of ["admin", "guest", "north", "south", "guest"]) {
    await page.getByLabel("Demo identity", { exact: true }).selectOption(role);
    await expect(page.locator(".visual-grid")).toBeVisible();
  }
  await expect(page.locator(".chart-row")).toHaveCount(0);
  await expect(page.locator(".ring-chart")).toHaveAttribute(
    "aria-label",
    "0 of 0 visible definitions are certified",
  );
  expect(errors).toEqual([]);
});
