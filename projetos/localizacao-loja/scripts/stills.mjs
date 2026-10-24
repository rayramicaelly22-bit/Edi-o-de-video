// Renderiza frames avulsos de uma composição (um bundle só) para revisão visual.
// Uso: node scripts/stills.mjs <compositionId> <saida_dir> <frame> [frame...]
import path from "node:path";
import fs from "node:fs";
import {bundle} from "@remotion/bundler";
import {renderStill, selectComposition, openBrowser} from "@remotion/renderer";

const [compositionId, outDir, ...frames] = process.argv.slice(2);
const root = path.resolve(path.dirname(new URL(import.meta.url).pathname), "..");
const defaultBrowser = "/opt/pw-browsers/chromium_headless_shell-1243/chrome-headless-shell-linux64/chrome-headless-shell";
const browserExecutable = process.env.REMOTION_BROWSER ?? (fs.existsSync(defaultBrowser) ? defaultBrowser : null);
const chromiumOptions = {gl: "swangle"};

fs.mkdirSync(outDir, {recursive: true});
const serveUrl = await bundle({entryPoint: path.join(root, "src/index.ts")});
const browser = await openBrowser("chrome", {browserExecutable, chromiumOptions});
const composition = await selectComposition({serveUrl, id: compositionId, puppeteerInstance: browser, chromiumOptions});
for (const f of frames) {
  const t0 = Date.now();
  const output = path.join(outDir, `${compositionId}-${String(f).padStart(4, "0")}.png`);
  await renderStill({composition, serveUrl, frame: Number(f), output, puppeteerInstance: browser, chromiumOptions, timeoutInMilliseconds: 180000});
  console.log(`frame ${f} -> ${output} (${((Date.now() - t0) / 1000).toFixed(1)}s)`);
}
await browser.close({silent: true});
