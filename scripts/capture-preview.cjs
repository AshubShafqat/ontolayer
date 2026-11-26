const { chromium } = require("@playwright/test");
const fs = require("node:fs/promises");
(async () => {
  const browser = await chromium.launch();
  try {
    const page = await browser.newPage({
      viewport: { width: 1440, height: 1100 },
      reducedMotion: "reduce",
    });
    await fs.mkdir("docs/media", { recursive: true });
    for (const route of [
      "overview",
      "explorer",
      "studio",
      "access",
      "validation",
      "mcp",
      "audit",
      "editor",
      "settings",
    ]) {
      await page.goto(`http://127.0.0.1:8000/#${route}`);
      await page.locator(".sidebar").waitFor();
      await page.waitForFunction(() => !document.querySelector(".loading"));
      if (route === "overview") await page.locator(".visual-grid").waitFor();
      if (route === "studio") {
        await page.getByLabel("Start date").fill("2026-10-01");
        await page.getByLabel("End date (exclusive)").fill("2026-11-01");
        await page
          .getByRole("button", { name: "Run query", exact: true })
          .click();
        await page.locator(".result-number").waitFor();
      }
      if (route === "editor") {
        await page
          .getByLabel("Demo identity", { exact: true })
          .selectOption("admin");
        await page.getByLabel("Draft ontology document").waitFor();
      }
      await page.screenshot({ path: `docs/media/v03-${route}.png` });
      if (route === "explorer") {
        if (await page.locator(".graph-placeholder").count())
          await page.locator(".graph-placeholder").scrollIntoViewIfNeeded();
        await page.getByRole("group", { name: /Concept map:/ }).waitFor();
        await page
          .locator(".graph")
          .locator("..")
          .screenshot({ path: "docs/media/v03-graph.png" });
      }
    }
    await page.goto("http://127.0.0.1:8000/");
    await page.locator(".visual-grid").waitFor();
    await page.getByLabel("Appearance").selectOption("dark");
    await page.screenshot({ path: "docs/media/v03-dark.png" });
    await page.setViewportSize({ width: 375, height: 900 });
    await page.goto("http://127.0.0.1:8000/#studio");
    await page.getByRole("heading", { name: "Ask with confidence." }).waitFor();
    await page.screenshot({ path: "docs/media/v03-mobile.png" });
  } finally {
    await browser.close();
  }
})().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
