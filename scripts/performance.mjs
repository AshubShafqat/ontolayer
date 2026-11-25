import lighthouse from "lighthouse";
import { createServer } from "node:net";
import { chromium } from "@playwright/test";
import { mkdir, writeFile, readFile, readdir } from "node:fs/promises";
import { gzipSync } from "node:zlib";
import { spawn } from "node:child_process";

const url = "http://127.0.0.1:8000";
let server, chrome;
try {
  try {
    if (!(await fetch(`${url}/health`)).ok) throw Error("Unavailable");
  } catch {
    server = spawn(
      "uv",
      [
        "run",
        "ontolayer",
        "serve",
        "--ontology",
        "examples/retail/ontology.yaml",
        "--credentials",
        "examples/retail/credentials.yaml",
        "--demo",
      ],
      { stdio: "ignore" },
    );
    let ready = false;
    for (let i = 0; i < 150; i++) {
      try {
        if ((await fetch(`${url}/health`)).ok) {
          ready = true;
          break;
        }
      } catch {}
      await new Promise((r) => setTimeout(r, 200));
    }
    if (!ready) throw Error("Preview did not start");
  }
  const listener = createServer();
  await new Promise((resolve) => listener.listen(0, "127.0.0.1", resolve));
  const port = listener.address().port;
  await new Promise((resolve) => listener.close(resolve));
  chrome = await chromium.launch({ args: [`--remote-debugging-port=${port}`] });
  const result = await lighthouse(url, {
    port,
    output: "json",
    logLevel: "error",
    onlyCategories: ["performance", "accessibility", "best-practices"],
  });
  await mkdir("test-results", { recursive: true });
  await writeFile("test-results/lighthouse.json", result.report);
  const scores = Object.fromEntries(
    Object.entries(result.lhr.categories).map(([key, value]) => [
      key,
      Math.round(value.score * 100),
    ]),
  );
  const bundles = [];
  for (const name of await readdir("src/ontolayer/static")) {
    const data = await readFile(`src/ontolayer/static/${name}`);
    bundles.push({ name, bytes: data.length, gzip: gzipSync(data).length });
  }
  await writeFile(
    "test-results/performance-summary.json",
    JSON.stringify({ scores, bundles }, null, 2),
  );
  console.log(JSON.stringify({ scores, bundles }, null, 2));
  if (Object.values(scores).some((score) => score < 90))
    throw Error("Lighthouse category below 90");
  if (bundles.reduce((n, b) => n + b.gzip, 0) > 80000)
    throw Error("Static gzip bundle exceeds 80 KB budget");
} finally {
  await chrome?.close();
  server?.kill();
}
