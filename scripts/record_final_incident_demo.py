from __future__ import annotations

import shutil
import subprocess
import time
from pathlib import Path

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "materials" / "demo_videos"
RECORD_DIR = OUT_DIR / "tri_mro_final_recordings"
BASE_URL = "http://127.0.0.1:8051"
EDGE = Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe")
CHROME = Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe")
FFMPEG_CANDIDATES = [
    Path(r"C:\Users\30672\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1.1-full_build\bin\ffmpeg.exe"),
    Path(r"C:\Program Files (x86)\Lenovo\LegionZone\2.0.23.3251\SEGamingAI\services\editor\ffmpeg.exe"),
]


def find_browser() -> str | None:
    for candidate in (EDGE, CHROME):
        if candidate.exists():
            return str(candidate)
    return None


def find_ffmpeg() -> Path | None:
    from_path = shutil.which("ffmpeg")
    if from_path:
        return Path(from_path)
    for candidate in FFMPEG_CANDIDATES:
        if candidate.exists():
            return candidate
    return None


def wait(seconds: float) -> None:
    time.sleep(seconds)


def safe_click(locator, *, timeout: int = 8000) -> bool:
    try:
        locator.click(timeout=timeout)
        return True
    except PlaywrightTimeoutError:
        return False


def set_caption(page, title: str, body: str) -> None:
    page.evaluate(
        """([title, body]) => {
          let el = document.getElementById('tri-mro-demo-caption');
          if (!el) {
            el = document.createElement('div');
            el.id = 'tri-mro-demo-caption';
            el.style.cssText = `
              position: fixed;
              left: 30px;
              right: 30px;
              bottom: 22px;
              z-index: 2147483647;
              display: grid;
              grid-template-columns: 260px 1fr;
              gap: 18px;
              align-items: center;
              padding: 18px 22px;
              border-radius: 16px;
              background: rgba(9, 24, 38, 0.94);
              color: #fff;
              font-family: "Microsoft YaHei", "PingFang SC", Arial, sans-serif;
              box-shadow: 0 22px 58px rgba(15, 23, 42, 0.32);
              border: 1px solid rgba(255,255,255,0.18);
              pointer-events: none;
            `;
            document.body.appendChild(el);
          }
          el.innerHTML = `
            <div style="font-size:21px;font-weight:900;color:#67e8f9;">${title}</div>
            <div style="font-size:24px;line-height:1.45;font-weight:700;">${body}</div>
          `;
        }""",
        [title, body],
    )


def hide_caption(page) -> None:
    page.evaluate("""() => document.getElementById('tri-mro-demo-caption')?.remove()""")


def scroll_to(page, selector: str) -> None:
    try:
        page.locator(selector).first.scroll_into_view_if_needed(timeout=8000)
    except PlaywrightTimeoutError:
        pass


def goto_nav(page, label: str) -> None:
    page.get_by_label("主导航").get_by_role("button", name=label).click()
    wait(1.2)


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    RECORD_DIR.mkdir(parents=True, exist_ok=True)

    raw_video: Path | None = None
    browser_path = find_browser()

    with sync_playwright() as p:
        launch_options = {"headless": True, "args": ["--autoplay-policy=no-user-gesture-required"]}
        if browser_path:
            launch_options["executable_path"] = browser_path
        browser = p.chromium.launch(**launch_options)
        context = browser.new_context(
            viewport={"width": 1540, "height": 900},
            record_video_dir=str(RECORD_DIR),
            record_video_size={"width": 1540, "height": 900},
            device_scale_factor=1,
        )
        page = context.new_page()

        page.goto(f"{BASE_URL}/marketing?demo_video=final_incident", wait_until="networkidle")
        set_caption(page, "01 / 事故阻断叙事", "Tri-MRO 的首屏不是聊天框，而是高风险拆卸被 Safety Gate 直接 BLOCKED。")
        wait(4.0)

        scroll_to(page, "#safety")
        set_caption(page, "02 / 可信作业控制", "系统先判断现在能不能修：未断电、未泄压、未确认 PPE 时禁止进入拆卸步骤。")
        wait(4.0)

        scroll_to(page, "#workflow")
        set_caption(page, "03 / 三链对齐主线", "现场输入进入 Claim Card，再落到 CAD 部件、SOP 作业票、案例审核和评测证明。")
        wait(4.0)

        page.goto(f"{BASE_URL}/?demo_video=final_incident", wait_until="networkidle")
        set_caption(page, "04 / 检修任务台", "固定主演示：离心泵机械密封持续滴漏，现场人员想直接拆卸端盖。")
        wait(2.0)
        safe_click(page.get_by_role("button", name="生成检修方案").first)
        page.wait_for_function(
            """() => document.body.innerText.includes('Claim Card') && document.body.innerText.includes('Evidence Budget')""",
            timeout=60000,
        )
        set_caption(page, "05 / Claim Card", "故障判断卡同时展示证据预算、FMEA 风险链、结构链和 Safety Gate 决策。")
        wait(5.0)

        safe_click(page.get_by_role("button", name="进入 CAD 工位").first)
        wait(5.5)
        set_caption(page, "06 / CAD 结构工位", "结构链把故障落到 pump.mechanical_seal，并明确当前是部件级/语义热点绑定。")
        wait(5.0)

        goto_nav(page, "作业票与安全")
        set_caption(page, "07 / Safety Gate", "作业票不是安全提醒，而是状态机：缺少断电、泄压、PPE 时高风险步骤 BLOCKED。")
        wait(4.0)
        for label in ("确认断电", "确认泄压", "确认 PPE"):
            safe_click(page.get_by_role("button", name=label).first, timeout=3000)
            wait(0.7)
        set_caption(page, "08 / 审计留痕", "每次人工确认都会进入安全审计记录，形成可追责的作业票过程。")
        wait(4.0)

        goto_nav(page, "检修任务")
        safe_click(page.get_by_role("button", name="从当前任务生成案例").first)
        wait(1.2)
        set_caption(page, "09 / 知识写入流水线", "案例不会直接污染知识库，必须经历草稿、审核、影响分析、图谱/索引更新和回滚记录。")
        wait(5.0)

        goto_nav(page, "证据链")
        set_caption(page, "10 / 当前任务证据链", "图谱页只展示当前 Claim Card 的证据路径，而不是杂乱全量图。")
        wait(4.0)

        goto_nav(page, "评测证明")
        set_caption(page, "11 / 创新指标证明", "评测页把可追溯率、三链对齐覆盖率、高风险阻断率和知识污染拦截率集中展示。")
        wait(4.0)

        goto_nav(page, "资源资产")
        set_caption(page, "12 / 资源与可信边界", "手册、图片、CAD/GLB、许可证和模型 fallback 状态都作为答辩证据链展示。")
        wait(4.0)

        set_caption(page, "结论", "Tri-MRO 把“能回答”升级为“有证据、能定位、可执行、可阻断、可沉淀”。")
        wait(4.5)
        hide_caption(page)
        wait(0.5)

        video = page.video
        context.close()
        browser.close()
        if video:
            raw_video = Path(video.path())

    if raw_video is None or not raw_video.exists():
        raise RuntimeError("Playwright video was not produced")

    webm_out = OUT_DIR / "tri_mro_final_incident_demo.webm"
    mp4_out = OUT_DIR / "tri_mro_final_incident_demo.mp4"
    if webm_out.exists():
        webm_out.unlink()
    raw_video.replace(webm_out)

    ffmpeg = find_ffmpeg()
    if ffmpeg:
        subprocess.run(
            [
                str(ffmpeg),
                "-y",
                "-i",
                str(webm_out),
                "-vf",
                "format=yuv420p",
                "-c:v",
                "libx264",
                "-preset",
                "medium",
                "-crf",
                "22",
                "-movflags",
                "+faststart",
                str(mp4_out),
            ],
            cwd=str(ROOT),
            check=True,
        )

    subtitle_path = OUT_DIR / "tri_mro_final_incident_demo_subtitles.txt"
    subtitle_path.write_text(
        "\n".join(
            [
                "01 事故阻断叙事：高风险拆卸请求被 Safety Gate BLOCKED。",
                "02 可信作业控制：未断电、未泄压、未确认 PPE 时禁止拆卸。",
                "03 三链对齐：Claim Card 统一证据链、结构链和作业链。",
                "04 检修任务台：离心泵机械密封泄漏主演示。",
                "05 Claim Card：证据预算、FMEA、结构链和安全决策集中展示。",
                "06 CAD 结构工位：故障落到 pump.mechanical_seal，显示绑定可信边界。",
                "07 Safety Gate：作业票状态机阻断高风险步骤。",
                "08 审计留痕：人工确认进入安全审计记录。",
                "09 知识写入流水线：案例经审核后才进入知识库、图谱和索引。",
                "10 证据链：只展示当前 Claim Card 的证据路径。",
                "11 评测证明：用创新指标证明可信、安全和闭环能力。",
                "12 资源资产：展示手册、图片、CAD/GLB、许可证和 fallback 状态。",
            ]
        ),
        encoding="utf-8",
    )

    print(mp4_out if mp4_out.exists() else webm_out)
    print(subtitle_path)


if __name__ == "__main__":
    main()
