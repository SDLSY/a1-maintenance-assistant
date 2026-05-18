import fs from "node:fs/promises";
import path from "node:path";
import { createRequire } from "node:module";

const require = createRequire(import.meta.url);
let chromium;
try {
  ({ chromium } = await import("playwright"));
} catch {
  const bundledPlaywright =
    process.env.PLAYWRIGHT_BUNDLE ||
    path.join(process.cwd(), "materials", "demo_video", ".node-tools", "node_modules", "playwright");
  ({ chromium } = require(bundledPlaywright));
}

const ROOT = path.resolve(process.cwd());
const OUT_DIR = path.join(ROOT, "materials", "demo_video");
const RAW_DIR = path.join(OUT_DIR, "raw");
const BASE_URL = process.env.A1_DEMO_URL || "http://127.0.0.1:8051/?candidate_cad_final_video=1";
const IMAGE_PATH =
  process.env.A1_DEMO_IMAGE ||
  path.join(ROOT, "data", "image_eval", "images", "pump_mechanical_seal_parts_02.jpg");

const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

function stampName() {
  const now = new Date();
  const pad = (value) => String(value).padStart(2, "0");
  return `${now.getFullYear()}${pad(now.getMonth() + 1)}${pad(now.getDate())}_${pad(now.getHours())}${pad(now.getMinutes())}${pad(now.getSeconds())}`;
}

function srtTime(seconds) {
  const safe = Math.max(0, seconds);
  const h = Math.floor(safe / 3600);
  const m = Math.floor((safe % 3600) / 60);
  const s = Math.floor(safe % 60);
  const ms = Math.floor((safe - Math.floor(safe)) * 1000);
  return `${String(h).padStart(2, "0")}:${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")},${String(ms).padStart(3, "0")}`;
}

function buildSrt(markers, duration) {
  return markers
    .map((marker, index) => {
      const start = marker.at;
      const next = markers[index + 1]?.at ?? duration;
      const end = Math.max(start + 2.2, next - 0.2);
      return `${index + 1}\n${srtTime(start)} --> ${srtTime(Math.min(end, duration))}\n${marker.text}\n`;
    })
    .join("\n");
}

async function clickText(page, text, exact = true) {
  const target = page.getByText(text, { exact });
  await target.waitFor({ state: "visible", timeout: 20000 });
  await target.click();
}

async function main() {
  await fs.mkdir(RAW_DIR, { recursive: true });
  const runName = `candidate_cad_demo_${stampName()}`;
  const launchOptions = { headless: true };
  const chromePath = process.env.PLAYWRIGHT_CHROME_PATH || "C:/Program Files/Google/Chrome/Application/chrome.exe";
  try {
    await fs.access(chromePath);
    launchOptions.executablePath = chromePath;
  } catch {
    // Fall back to Playwright's managed browser when it is installed.
  }
  const browser = await chromium.launch(launchOptions);
  const context = await browser.newContext({
    viewport: { width: 1600, height: 900 },
    recordVideo: { dir: RAW_DIR, size: { width: 1600, height: 900 } },
  });
  const page = await context.newPage();
  const consoleErrors = [];
  page.on("console", (msg) => {
    if (msg.type() === "error") consoleErrors.push(msg.text());
  });
  page.on("pageerror", (error) => consoleErrors.push(error.message));

  const t0 = Date.now();
  const markers = [];
  const mark = (text) => markers.push({ at: (Date.now() - t0) / 1000, text });

  await page.goto(BASE_URL, { waitUntil: "load" });
  await page.waitForSelector("text=检修任务台", { timeout: 20000 });
  mark("这是候选 CAD 最终版演示：从现场照片进入检修任务，再生成可审核的结构链资产。");
  await sleep(2500);

  mark("第一步：在检修任务台选择离心泵，输入型号和故障现象。");
  await page.locator("select").first().selectOption("pump");
  await page.locator("input[placeholder*='Y2-160M']").fill("ISG80-160");
  await page
    .locator("textarea[placeholder*='电机']")
    .fill("离心泵机械密封连续滴漏，密封端有油污和泄漏痕迹，运行后轴承区温升明显。");
  await sleep(1500);

  mark("第二步：上传真实设备照片，系统会做 OCR/VLM 视觉分析并沉淀为视觉资产。");
  await page.locator("input[type='file']").setInputFiles(IMAGE_PATH);
  await page.waitForSelector("text=视觉资产", { timeout: 30000 });
  await sleep(2200);

  mark("第三步：生成检修方案，系统同时输出证据链、SOP 和安全闸门。");
  await page.getByRole("button", { name: "生成检修方案" }).click();
  await page.waitForSelector("text=故障判断", { timeout: 45000 });
  await sleep(3200);

  mark("第四步：进入资源与模型页，把刚才的现场照片转换为候选 CAD 资产。");
  await page.getByRole("button", { name: "资源与模型" }).click();
  await page.locator(".candidate-cad-panel").scrollIntoViewIfNeeded();
  await sleep(1200);
  await page.getByRole("button", { name: "从当前照片生成候选 CAD" }).click();
  await page.waitForSelector("text=候选 CAD 审核工位", { timeout: 45000 });
  await page.waitForSelector("text=STEP", { timeout: 45000 });
  await sleep(2500);

  mark("审核工位会展示运行模式、四视图渲染，以及 STEP、STL、GLB 和 artifact manifest。");
  await page.locator(".candidate-cad-review-workbench").scrollIntoViewIfNeeded();
  await sleep(3500);

  mark("机械审核人员可以编辑 CAD spec；修改后重新渲染，形成新的产物和对比报告。");
  const workbench = page.locator(".candidate-cad-review-workbench");
  const textarea = workbench.locator("textarea");
  await textarea.waitFor({ state: "visible", timeout: 10000 });
  const specText = await textarea.inputValue();
  const spec = JSON.parse(specText);
  spec.parameters = { ...(spec.parameters || {}), body_length: 132, port_diameter: 28 };
  await textarea.fill(JSON.stringify(spec, null, 2));
  await workbench.getByRole("button", { name: "保存修正" }).click();
  await page.waitForTimeout(800);
  await workbench.getByRole("button", { name: "重新渲染" }).click();
  await page.waitForSelector("text=已重新生成", { timeout: 45000 });
  await sleep(2500);

  mark("通过审核后，候选模型才能晋升为 CAD 结构工位资产；未审核的结果不能用于安全放行。");
  await workbench.getByRole("button", { name: "批准候选" }).click();
  await page.waitForTimeout(1000);
  await workbench.getByRole("button", { name: "晋升为结构链资产" }).click();
  await page.waitForSelector("text=已晋升为结构链资产", { timeout: 45000 });
  await sleep(2800);

  mark("最终形成闭环：照片识别、候选 CAD、人工审核、结构链晋升，全程保留证据和风险边界。");
  await sleep(3500);

  const duration = (Date.now() - t0) / 1000;
  const srt = buildSrt(markers, duration);
  const srtPath = path.join(OUT_DIR, `${runName}.srt`);
  const metaPath = path.join(OUT_DIR, `${runName}.json`);
  await fs.writeFile(srtPath, srt, "utf8");
  await fs.writeFile(
    metaPath,
    JSON.stringify({ runName, baseUrl: BASE_URL, imagePath: IMAGE_PATH, duration, markers, consoleErrors }, null, 2),
    "utf8",
  );

  const video = page.video();
  const rawPath = path.join(OUT_DIR, `${runName}.webm`);
  await page.close();
  await video.saveAs(rawPath);
  await context.close();
  await browser.close();

  console.log(JSON.stringify({ rawPath, srtPath, metaPath, duration, consoleErrors }, null, 2));
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
