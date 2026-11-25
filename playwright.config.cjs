const { defineConfig } = require("@playwright/test");
module.exports = defineConfig({
  testDir: "./e2e",
  fullyParallel: false,
  workers: 1,
  updateSnapshots: "none",
  use: { baseURL: "http://127.0.0.1:8000", trace: "retain-on-failure" },
  reporter: [["list"]],
  webServer: process.env.ONTOLAYER_EXTERNAL_SERVER
    ? undefined
    : {
        command:
          "uv run ontolayer serve --ontology examples/retail/ontology.yaml --credentials examples/retail/credentials.yaml --demo",
        url: "http://127.0.0.1:8000/health",
        reuseExistingServer: !process.env.CI,
        timeout: 60000,
      },
});
