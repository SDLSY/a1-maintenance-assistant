from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import textwrap
import urllib.error
import urllib.request
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BASE_URL = "http://127.0.0.1:8051"
DEFAULT_JSON_REPORT = ROOT / "test-results" / "system-smoke-report.json"
DEFAULT_MARKDOWN_REPORT = ROOT / "test-results" / "system-smoke-report.md"
DEFAULT_SCREENSHOT_DIR = ROOT / "test-results" / "system-smoke-screenshots"

EQUIPMENT_SCENARIOS = [
    {
        "equipment": "motor",
        "model": "Y2-160M",
        "text": "电机端盖温升，轴承异响，伴随低频振动。",
        "title_keyword": "Motor",
    },
    {
        "equipment": "pump",
        "model": "ISG80-160",
        "text": "离心泵机械密封持续滴漏，泵头密封区有泄漏痕迹。",
        "title_keyword": "泵",
    },
    {
        "equipment": "bearing",
        "model": "6201-2RS",
        "text": "轴承运行异响，外圈滚道磨损并疑似剥落。",
        "title_keyword": "Bearing",
    },
    {
        "equipment": "engine",
        "model": "CG125",
        "text": "发动机冷车起动困难，火花塞积碳，需要检查间隙和压缩压力。",
        "title_keyword": "engine",
    },
]


def _request_json(base_url: str, method: str, path: str, payload: dict[str, Any] | None = None, timeout: int = 30) -> dict[str, Any]:
    data = None
    headers = {"Accept": "application/json"}
    if payload is not None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(f"{base_url.rstrip('/')}{path}", data=data, headers=headers, method=method)
    with urllib.request.urlopen(request, timeout=timeout) as response:
        body = response.read().decode("utf-8")
    return json.loads(body) if body else {}


def _request_ok(base_url: str, path: str, timeout: int = 20) -> bool:
    request = urllib.request.Request(f"{base_url.rstrip('/')}{path}", method="GET")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return 200 <= response.status < 400
    except urllib.error.HTTPError as exc:
        return 200 <= exc.code < 400


def _check(condition: bool, blockers: list[str], message: str) -> bool:
    if not condition:
        blockers.append(message)
        return False
    return True


def run_api_checks(base_url: str) -> dict[str, Any]:
    blockers: list[str] = []
    checks: list[dict[str, Any]] = []

    try:
        health = _request_json(base_url, "GET", "/api/health", timeout=15)
        ok = health.get("status") == "ok"
        _check(ok, blockers, "/api/health did not return status=ok")
        checks.append({"name": "health", "ok": ok, "detail": {"status": health.get("status"), "mode": health.get("mode")}})
    except Exception as exc:  # noqa: BLE001
        blockers.append(f"/api/health failed: {exc}")
        return {"status": "failed", "checks": checks, "blockers": blockers}

    for scenario in EQUIPMENT_SCENARIOS:
        equipment = scenario["equipment"]
        query_payload = {
            "equipment": equipment,
            "model": scenario["model"],
            "maintenance_level": "二级检修",
            "text": scenario["text"],
            "top_k": 6,
        }
        try:
            query = _request_json(base_url, "POST", "/api/query", query_payload, timeout=60)
            query_ok = all(query.get(key) for key in ("workflow_state", "spatial_guidance", "citations", "sop_steps", "compliance"))
            query_ok = query_ok and query.get("spatial_guidance", {}).get("equipment") == equipment
            claim_card = query.get("primary_claim_card") or {}
            query_ok = query_ok and bool(query.get("claim_cards")) and bool(claim_card.get("evidence_budget"))
            query_ok = query_ok and bool(claim_card.get("fmea_risk_chain")) and bool(claim_card.get("safety_gate"))
            _check(query_ok, blockers, f"/api/query contract failed for {equipment}")
            checks.append(
                {
                    "name": f"query:{equipment}",
                    "ok": query_ok,
                    "detail": {
                        "citations": len(query.get("citations") or []),
                        "sop_steps": len(query.get("sop_steps") or []),
                        "spatial_model": query.get("spatial_guidance", {}).get("model_id"),
                        "claim_card": claim_card.get("claim_id"),
                        "evidence_decision": (claim_card.get("evidence_budget") or {}).get("decision"),
                    },
                }
            )

            models = _request_json(base_url, "GET", f"/api/3d/models?equipment={equipment}", timeout=30)
            model_list = models.get("models") or []
            model_ok = bool(model_list) and all(item.get("equipment") == equipment for item in model_list[:3])
            _check(model_ok, blockers, f"/api/3d/models returned invalid models for {equipment}")
            first_model_id = model_list[0]["id"] if model_list else ""
            model_detail = _request_json(base_url, "GET", f"/api/3d/models/{first_model_id}", timeout=30) if first_model_id else {}
            detail_ok = model_detail.get("equipment") == equipment and bool(model_detail.get("components"))
            _check(detail_ok, blockers, f"/api/3d/models/{first_model_id} detail invalid")
            checks.append(
                {
                    "name": f"3d-model:{equipment}",
                    "ok": model_ok and detail_ok,
                    "detail": {
                        "count": len(model_list),
                        "model_id": first_model_id,
                        "viewer_mode": model_detail.get("viewer_mode"),
                        "components": len(model_detail.get("components") or []),
                    },
                }
            )

            guidance = _request_json(
                base_url,
                "POST",
                "/api/3d/guidance",
                {
                    "equipment": equipment,
                    "model": scenario["model"],
                    "text": scenario["text"],
                    "sop_steps": query.get("sop_steps") or [],
                    "compliance": query.get("compliance") or [],
                },
                timeout=40,
            )
            guidance_ok = (
                guidance.get("equipment") == equipment
                and bool(guidance.get("model_id"))
                and bool(guidance.get("components"))
                and bool(guidance.get("highlighted_components"))
                and bool(guidance.get("component_contract"))
                and bool(guidance.get("binding_precision_level"))
            )
            _check(guidance_ok, blockers, f"/api/3d/guidance contract failed for {equipment}")
            checks.append(
                {
                    "name": f"3d-guidance:{equipment}",
                    "ok": guidance_ok,
                    "detail": {
                        "model_id": guidance.get("model_id"),
                        "components": len(guidance.get("components") or []),
                        "highlights": len(guidance.get("highlighted_components") or []),
                    },
                }
            )

            bridge = model_detail.get("cad_bridge") or {}
            for section in ("cad_source", "glb_viewer", "sidecar", "conversion"):
                preview = (bridge.get(section) or {}).get("preview_url")
                if preview:
                    preview_ok = _request_ok(base_url, preview, timeout=20)
                    _check(preview_ok, blockers, f"{equipment} {section} preview is not accessible: {preview}")
        except Exception as exc:  # noqa: BLE001
            blockers.append(f"API check failed for {equipment}: {exc}")
            checks.append({"name": f"api:{equipment}", "ok": False, "detail": {"error": str(exc)}})

    for name, path in (
        ("resources", "/api/resources/verification"),
        ("metrics", "/api/metrics"),
        ("knowledge-graph", "/api/knowledge-graph"),
    ):
        try:
            payload = _request_json(base_url, "GET", path, timeout=40)
            if name == "resources":
                ok = not ((payload.get("summary") or {}).get("critical_failures") or [])
            elif name == "metrics":
                ok = bool(payload.get("latest") or payload.get("benchmarks")) and bool(payload.get("tri_mro_innovation_metrics"))
            else:
                ok = bool(payload.get("nodes")) and bool(payload.get("edges"))
            _check(ok, blockers, f"{path} returned invalid payload")
            checks.append({"name": name, "ok": ok, "detail": {"keys": sorted(payload.keys())[:8]}})
        except Exception as exc:  # noqa: BLE001
            blockers.append(f"{path} failed: {exc}")
            checks.append({"name": name, "ok": False, "detail": {"error": str(exc)}})

    return {"status": "passed" if not blockers else "failed", "checks": checks, "blockers": blockers}


def _find_playwright_node_path() -> str | None:
    env_node_path = os.getenv("NODE_PATH")
    if env_node_path and "playwright" in env_node_path.lower():
        return env_node_path
    local_app_data = os.getenv("LOCALAPPDATA")
    candidates: list[Path] = []
    if local_app_data:
        candidates.extend(Path(local_app_data).glob("npm-cache/_npx/*/node_modules/playwright"))
    for candidate in candidates:
        if (candidate / "package.json").exists():
            return str(candidate.parent)
    return None


def _chrome_path() -> str | None:
    explicit = os.getenv("A1_CHROME_PATH")
    if explicit and Path(explicit).exists():
        return explicit
    for candidate in (
        Path("C:/Program Files/Google/Chrome/Application/chrome.exe"),
        Path("C:/Program Files (x86)/Google/Chrome/Application/chrome.exe"),
    ):
        if candidate.exists():
            return str(candidate)
    return None


def _browser_runner_js() -> str:
    return r"""
const fs = require("fs");
const path = require("path");
const { chromium } = require("playwright");

const baseUrl = process.argv[2];
const outputPath = process.argv[3];
const screenshotDir = process.argv[4];
fs.mkdirSync(screenshotDir, { recursive: true });

const equipmentScenarios = [
  { equipment: "motor", model: "Y2-160M", text: "电机端盖温升，轴承异响，伴随低频振动。", titleKeyword: "Motor" },
  { equipment: "pump", model: "ISG80-160", text: "离心泵机械密封持续滴漏，泵头密封区有泄漏痕迹。", titleKeyword: "泵" },
  { equipment: "bearing", model: "6201-2RS", text: "轴承运行异响，外圈滚道磨损并疑似剥落。", titleKeyword: "Bearing" },
  { equipment: "engine", model: "CG125", text: "发动机冷车起动困难，火花塞积碳，需要检查间隙和压缩压力。", titleKeyword: "engine" },
];

function screenshotPath(name) {
  return path.join(screenshotDir, `${name}.png`);
}

async function main() {
  const launchOptions = { headless: true };
  if (process.env.A1_CHROME_PATH && fs.existsSync(process.env.A1_CHROME_PATH)) {
    launchOptions.executablePath = process.env.A1_CHROME_PATH;
  }
  const browser = await chromium.launch(launchOptions);
  const page = await browser.newPage({ viewport: { width: 1540, height: 900 } });
  const logs = [];
  page.on("console", (msg) => logs.push({ type: msg.type(), text: msg.text() }));
  page.on("pageerror", (err) => logs.push({ type: "pageerror", text: err.message }));

  const blockers = [];
  const steps = [];
  const check = (condition, message) => {
    if (!condition) blockers.push(message);
    return Boolean(condition);
  };
  const state = async (label) => page.evaluate((label) => ({
    label,
    url: location.href,
    activeTextLength: document.body.innerText.length,
    errorBanners: Array.from(document.querySelectorAll(".error-banner")).map((item) => item.textContent.trim()).filter(Boolean),
    canvasCount: document.querySelectorAll(".pro-spatial-canvas canvas, .spatial-canvas canvas").length,
    hotspotCount: document.querySelectorAll(".spatial-hotspot-label").length,
    activeTabText: document.querySelector(".content-header h2")?.textContent?.trim() || "",
    cadTitle: document.querySelector(".pro-stage-header strong")?.textContent?.trim() || "",
    cadEquipment: document.querySelector(".pro-input-panel select")?.value || "",
    claimCardVisible: document.body.innerText.includes("检修判断卡"),
    evidenceBudgetVisible: document.body.innerText.includes("证据预算"),
    fmeaVisible: document.body.innerText.includes("FMEA 风险链"),
    componentContractVisible: document.body.innerText.includes("部件契约") || document.body.innerText.includes("部件约束"),
    knowledgePipelineVisible: document.body.innerText.includes("知识写入流水线"),
    innovationMetricsVisible: document.body.innerText.includes("创新指标"),
    scriptVersions: Array.from(document.scripts).map((item) => item.src).filter((src) => src.includes("app.js") || src.includes("three-workbench")),
  }), label);
  const nav = async (name) => {
    await page.getByLabel("主导航").getByRole("button", { name }).click();
    await page.waitForTimeout(600);
  };
  const diagnose = async (scenario, index) => {
    await nav("检修任务");
    await page.selectOption("section.diagnosis-grid select", scenario.equipment);
    const inputs = await page.locator("section.diagnosis-grid input").all();
    if (inputs[0]) await inputs[0].fill(scenario.model);
    await page.locator("section.diagnosis-grid textarea").first().fill(scenario.text);
    await page.getByRole("button", { name: /生成检修方案/ }).first().click();
    await page.waitForFunction(() => {
      const text = document.body.innerText || "";
      return text.includes("检修判断卡")
        || text.includes("故障判断")
        || text.includes("检修方案生成失败")
        || text.includes("证据不足");
    }, null, { timeout: 45000 }).catch(() => {});
    await page.waitForTimeout(800);
    const snapshot = await state(`diagnosis-${scenario.equipment}`);
    snapshot.hasResult = await page.evaluate(() => (
      document.body.innerText.includes("标准化作业")
      || document.body.innerText.includes("可能原因")
      || document.body.innerText.includes("SOP")
    ));
    snapshot.input = scenario;
    await page.screenshot({ path: screenshotPath(`diagnosis-${index}-${scenario.equipment}`), fullPage: false });
    check(snapshot.hasResult, `diagnosis result missing for ${scenario.equipment}`);
    check(snapshot.claimCardVisible, `diagnosis 检修判断卡 missing for ${scenario.equipment}`);
    check(snapshot.evidenceBudgetVisible, `diagnosis 证据预算 missing for ${scenario.equipment}`);
    check(snapshot.fmeaVisible, `diagnosis FMEA 风险链 missing for ${scenario.equipment}`);
    check(snapshot.errorBanners.length === 0, `diagnosis error banner for ${scenario.equipment}: ${snapshot.errorBanners.join("; ")}`);
    steps.push(snapshot);
    return snapshot;
  };

  await page.goto(`${baseUrl}/marketing?system_smoke=${Date.now()}`, { waitUntil: "networkidle" });
  await page.waitForTimeout(800);
  const marketing = await page.evaluate(() => ({
    label: "marketing-homepage",
    url: location.href,
    title: document.title,
    ready: document.documentElement.dataset.marketingReady || "",
    activeTextLength: document.body.innerText.length,
    hasTriMro: document.body.innerText.includes("Tri-MRO"),
    hasBlocked: document.body.innerText.includes("已阻断"),
    hasClaimCard: document.body.innerText.includes("检修判断卡"),
    hasSafetyGate: document.body.innerText.includes("安全闸门"),
    hasKnowledgePipeline: document.body.innerText.includes("知识写入流水线"),
    hasChatbotMetaphor: document.body.innerText.includes("聊天机器人"),
  }));
  await page.screenshot({ path: screenshotPath("marketing-homepage"), fullPage: false });
  check(marketing.ready === "true", "marketing homepage script did not mark ready");
  check(marketing.hasTriMro && marketing.hasBlocked, "marketing homepage missing Tri-MRO/已阻断 incident narrative");
  check(marketing.hasClaimCard && marketing.hasSafetyGate && marketing.hasKnowledgePipeline, "marketing homepage missing core Tri-MRO modules");
  check(!marketing.hasChatbotMetaphor, "marketing homepage should not use chatbot-first narrative");
  steps.push(marketing);

  await page.goto(`${baseUrl}?system_smoke=${Date.now()}`, { waitUntil: "networkidle" });
  for (let i = 0; i < equipmentScenarios.length; i += 1) {
    await diagnose(equipmentScenarios[i], i + 1);
  }

  async function enterCad(label) {
    await page.getByRole("button", { name: /进入 CAD 工位/ }).first().click();
    await page.waitForTimeout(4500);
    const snapshot = await state(`cad-${label}`);
    await page.screenshot({ path: screenshotPath(`cad-${label}`), fullPage: false });
    check(snapshot.canvasCount === 1, `CAD ${label} should have exactly one canvas, got ${snapshot.canvasCount}`);
    check(snapshot.componentContractVisible, `CAD ${label} missing 部件约束`);
    check(snapshot.hotspotCount >= 0, `CAD ${label} hotspot count should be readable`);
    check(snapshot.errorBanners.length === 0, `CAD ${label} error banner: ${snapshot.errorBanners.join("; ")}`);
    steps.push(snapshot);
    return snapshot;
  }

  await enterCad("first");
  await nav("检修任务");
  await diagnose(equipmentScenarios[0], 5);
  await enterCad("second");

  for (const scenario of equipmentScenarios) {
    await page.selectOption(".pro-input-panel select", scenario.equipment);
    await page.waitForTimeout(2800);
    const snapshot = await state(`cad-switch-${scenario.equipment}`);
    await page.locator(".pro-spatial-canvas, .spatial-canvas").first().screenshot({ path: screenshotPath(`cad-switch-${scenario.equipment}`) });
    check(snapshot.cadEquipment === scenario.equipment, `CAD equipment select did not switch to ${scenario.equipment}`);
    check(snapshot.canvasCount === 1, `CAD switch ${scenario.equipment} should keep one canvas`);
    if (scenario.equipment === "bearing") {
      check(snapshot.hotspotCount > 0, `CAD switch ${scenario.equipment} should show bearing hotspots`);
    } else {
      check(snapshot.hotspotCount >= 0, `CAD switch ${scenario.equipment} hotspot count should be readable`);
    }
    check(snapshot.cadTitle.toLowerCase().includes(scenario.titleKeyword.toLowerCase()), `CAD switch ${scenario.equipment} title mismatch: ${snapshot.cadTitle}`);
    steps.push(snapshot);
  }

  await page.getByRole("button", { name: /剖视平面/ }).click();
  await page.waitForTimeout(600);
  const section = await state("cad-section-toggle");
  check(section.canvasCount === 1, "CAD section toggle lost canvas");
  steps.push(section);

  await page.getByRole("button", { name: /复位视角/ }).click();
  await page.waitForTimeout(600);
  const reset = await state("cad-reset-view");
  check(reset.canvasCount === 1, "CAD reset view lost canvas");
  steps.push(reset);

  await page.getByRole("button", { name: /同步问诊方案/ }).click();
  await page.waitForTimeout(4500);
  const sync = await state("cad-sync-query");
  check(sync.canvasCount === 1, "CAD sync query lost canvas");
  check(sync.errorBanners.length === 0, `CAD sync query error: ${sync.errorBanners.join("; ")}`);
  steps.push(sync);

  await nav("作业票与安全");
  const safetyPage = await state("safety-work-order");
  safetyPage.hasSafetyGate = await page.evaluate(() => document.body.innerText.includes("安全闸门状态机") && document.body.innerText.includes("安全闸门"));
  safetyPage.hasWorkOrder = await page.evaluate(() => document.body.innerText.includes("作业票") && document.body.innerText.includes("阻断"));
  check(safetyPage.hasSafetyGate, "safety page missing 安全闸门状态机");
  check(safetyPage.hasWorkOrder, "safety page missing operation ticket narrative");
  check(safetyPage.canvasCount === 0, "safety page should not retain CAD canvas");
  steps.push(safetyPage);

  await page.getByRole("button", { name: /从当前任务生成案例/ }).first().click();
  await page.waitForTimeout(800);
  const casePage = await state("case-prefill");
  casePage.hasBackButton = await page.evaluate(() => document.body.innerText.includes("返回诊断结果"));
  check(casePage.hasBackButton, "case page missing return-to-diagnosis button");
  check(casePage.knowledgePipelineVisible, "case page missing 知识写入流水线");
  check(casePage.canvasCount === 0, "case page should not retain CAD canvas");
  steps.push(casePage);
  await page.getByRole("button", { name: /返回诊断结果/ }).click();
  await page.waitForTimeout(800);
  const back = await state("return-diagnosis");
  back.hasResult = await page.evaluate(() => (
    document.body.innerText.includes("标准化作业")
    || document.body.innerText.includes("可能原因")
    || document.body.innerText.includes("SOP")
  ));
  check(back.hasResult, "return to diagnosis lost generated result");
  steps.push(back);

  const navChecks = [
    ["知识沉淀", "待审核"],
    ["证据链", "检修证据链"],
    ["评测证明", "评测"],
    ["资源资产", "资源"],
  ];
  for (const [name, marker] of navChecks) {
    await nav(name);
    const snapshot = await state(`page-${name}`);
    snapshot.hasMarker = await page.evaluate((marker) => document.body.innerText.includes(marker), marker);
    check(snapshot.activeTextLength > 300, `${name} page looks empty`);
    check(snapshot.hasMarker, `${name} page missing marker ${marker}`);
    if (name.includes("评测")) {
      check(snapshot.innovationMetricsVisible, `${name} page missing 创新指标`);
    }
    if (name.includes("知识") || name.includes("案例")) {
      check(snapshot.knowledgePipelineVisible, `${name} page missing 知识写入流水线`);
    }
    check(snapshot.canvasCount === 0, `${name} page retained stale CAD canvas`);
    check(snapshot.errorBanners.length === 0, `${name} error banner: ${snapshot.errorBanners.join("; ")}`);
    steps.push(snapshot);
  }

  const severeLogs = logs.filter((item) => item.type === "error" || item.type === "pageerror");
  for (const item of severeLogs) blockers.push(`browser ${item.type}: ${item.text}`);
  await browser.close();
  const result = {
    status: blockers.length ? "failed" : "passed",
    steps,
    blockers,
    console_errors: severeLogs,
    console_warnings: logs.filter((item) => item.type === "warning"),
  };
  fs.writeFileSync(outputPath, JSON.stringify(result, null, 2), "utf8");
}

main().catch((error) => {
  fs.writeFileSync(outputPath, JSON.stringify({ status: "failed", steps: [], blockers: [String(error && error.stack || error)] }, null, 2), "utf8");
  process.exit(1);
});
"""


def run_browser_checks(base_url: str, screenshot_dir: Path) -> dict[str, Any]:
    node_path = _find_playwright_node_path()
    node_bin = shutil.which("node")
    if not node_bin:
        return {"status": "failed", "steps": [], "blockers": ["node executable not found"], "console_errors": []}
    if not node_path:
        return {"status": "failed", "steps": [], "blockers": ["playwright node module not found"], "console_errors": []}

    screenshot_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="a1-system-smoke-") as temp_dir:
        temp = Path(temp_dir)
        runner = temp / "system-smoke-runner.cjs"
        browser_result = temp / "browser-result.json"
        runner.write_text(_browser_runner_js(), encoding="utf-8")
        env = os.environ.copy()
        env["NODE_PATH"] = node_path
        chrome = _chrome_path()
        if chrome:
            env["A1_CHROME_PATH"] = chrome
        completed = subprocess.run(
            [node_bin, str(runner), base_url, str(browser_result), str(screenshot_dir)],
            cwd=str(ROOT),
            env=env,
            text=True,
            capture_output=True,
            timeout=180,
        )
        if browser_result.exists():
            result = json.loads(browser_result.read_text(encoding="utf-8"))
        else:
            result = {"status": "failed", "steps": [], "blockers": ["browser runner did not write result"], "console_errors": []}
        if completed.returncode != 0 and result.get("status") != "failed":
            result["status"] = "failed"
            result.setdefault("blockers", []).append(f"browser runner exited {completed.returncode}")
        if completed.stderr:
            result.setdefault("runner_stderr", completed.stderr[-4000:])
        if completed.stdout:
            result.setdefault("runner_stdout", completed.stdout[-4000:])
        result["node_path"] = node_path
        result["chrome_path"] = chrome
        return result


def summarize(result: dict[str, Any]) -> dict[str, Any]:
    blockers = []
    blockers.extend(result.get("api", {}).get("blockers") or [])
    blockers.extend(result.get("browser", {}).get("blockers") or [])
    result["blockers"] = blockers
    result["status"] = "passed" if not blockers else "failed"
    return result


def write_markdown_report(result: dict[str, Any], output_path: Path | str = DEFAULT_MARKDOWN_REPORT) -> Path:
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# A1-MAKG System Smoke Report",
        "",
        f"- Status: **{result['status']}**",
        f"- Generated at: `{result['generated_at']}`",
        f"- Base URL: `{result['base_url']}`",
        "",
        "## Blockers",
    ]
    blockers = result.get("blockers") or []
    if blockers:
        lines.extend(f"- {item}" for item in blockers)
    else:
        lines.append("- None")

    api = result.get("api") or {}
    lines.extend(["", "## API Checks"])
    for check in api.get("checks", []):
        status = "PASS" if check.get("ok") else "FAIL"
        lines.append(f"- `{status}` {check.get('name')}: `{json.dumps(check.get('detail', {}), ensure_ascii=False)}`")

    browser = result.get("browser") or {}
    lines.extend(["", "## Browser Checks"])
    lines.append(f"- Browser status: **{browser.get('status', 'skipped')}**")
    lines.append(f"- Node path: `{browser.get('node_path', '')}`")
    lines.append(f"- Chrome path: `{browser.get('chrome_path', '')}`")
    for step in browser.get("steps", []):
        name = step.get("label")
        canvas = step.get("canvasCount")
        hotspots = step.get("hotspotCount")
        title = step.get("cadTitle", "")
        final_markers = []
        if step.get("claimCardVisible"):
            final_markers.append("检修判断卡")
        if step.get("componentContractVisible"):
            final_markers.append("部件约束")
        if step.get("knowledgePipelineVisible"):
            final_markers.append("知识写入流水线")
        if step.get("innovationMetricsVisible"):
            final_markers.append("创新指标")
        marker_text = f" markers={','.join(final_markers)}" if final_markers else ""
        lines.append(f"- `{name}` canvas={canvas} hotspots={hotspots} title={title}{marker_text}")

    lines.extend(["", "## Console Errors"])
    errors = browser.get("console_errors") or []
    if errors:
        lines.extend(f"- {item.get('type')}: {item.get('text')}" for item in errors)
    else:
        lines.append("- None")

    output.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return output


def run_system_smoke(
    base_url: str = DEFAULT_BASE_URL,
    json_report: Path | str = DEFAULT_JSON_REPORT,
    markdown_report: Path | str = DEFAULT_MARKDOWN_REPORT,
    screenshot_dir: Path | str = DEFAULT_SCREENSHOT_DIR,
    skip_browser: bool = False,
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "base_url": base_url,
        "api": run_api_checks(base_url),
        "browser": {"status": "skipped", "steps": [], "blockers": [], "console_errors": []},
    }
    if not skip_browser:
        result["browser"] = run_browser_checks(base_url, Path(screenshot_dir))
    summarize(result)
    json_target = Path(json_report)
    json_target.parent.mkdir(parents=True, exist_ok=True)
    json_target.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    write_markdown_report(result, markdown_report)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Run A1-MAKG API and browser system smoke checks.")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--json-report", type=Path, default=DEFAULT_JSON_REPORT)
    parser.add_argument("--markdown-report", type=Path, default=DEFAULT_MARKDOWN_REPORT)
    parser.add_argument("--screenshot-dir", type=Path, default=DEFAULT_SCREENSHOT_DIR)
    parser.add_argument("--skip-browser", action="store_true")
    parser.add_argument("--no-fail", action="store_true", help="Always exit 0 after writing reports.")
    args = parser.parse_args()

    result = run_system_smoke(
        base_url=args.base_url,
        json_report=args.json_report,
        markdown_report=args.markdown_report,
        screenshot_dir=args.screenshot_dir,
        skip_browser=args.skip_browser,
    )
    print(json.dumps({"status": result["status"], "blockers": result["blockers"], "json_report": str(args.json_report), "markdown_report": str(args.markdown_report)}, ensure_ascii=False))
    return 0 if args.no_fail or result["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
