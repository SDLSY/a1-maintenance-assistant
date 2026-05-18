from __future__ import annotations

import shutil
import subprocess
import time
from pathlib import Path

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "materials" / "demo_video"
RECORD_DIR = OUT_DIR / "cad_toolchain_recordings"
EDGE = Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe")
FFMPEG_CANDIDATES = [
    Path(r"C:\Users\30672\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1.1-full_build\bin\ffmpeg.exe"),
    Path(r"C:\Program Files (x86)\Lenovo\LegionZone\2.0.23.3251\SEGamingAI\services\editor\ffmpeg.exe"),
]


def find_ffmpeg() -> Path:
    from_path = shutil.which("ffmpeg")
    if from_path:
        return Path(from_path)
    for candidate in FFMPEG_CANDIDATES:
        if candidate.exists():
            return candidate
    raise RuntimeError("ffmpeg.exe not found")


def wait(seconds: float) -> None:
    time.sleep(seconds)


def safe_click(page, locator, *, timeout: int = 7000) -> bool:
    try:
        locator.click(timeout=timeout)
        return True
    except PlaywrightTimeoutError:
        return False


def set_caption(page, title: str, body: str) -> None:
    page.evaluate(
        """([title, body]) => {
          let el = document.getElementById('codex-demo-caption');
          if (!el) {
            el = document.createElement('div');
            el.id = 'codex-demo-caption';
            el.style.cssText = `
              position: fixed;
              left: 28px;
              right: 28px;
              bottom: 24px;
              z-index: 2147483647;
              display: grid;
              grid-template-columns: 220px 1fr;
              gap: 18px;
              align-items: center;
              padding: 18px 22px;
              border-radius: 14px;
              background: rgba(7, 18, 31, 0.92);
              color: white;
              font-family: "Microsoft YaHei", "PingFang SC", Arial, sans-serif;
              box-shadow: 0 18px 42px rgba(15, 23, 42, 0.25);
              border: 1px solid rgba(255,255,255,0.16);
              pointer-events: none;
            `;
            document.body.appendChild(el);
          }
          el.innerHTML = `
            <div style="font-size:22px;font-weight:800;color:#7dd3fc;">${title}</div>
            <div style="font-size:25px;line-height:1.45;font-weight:650;">${body}</div>
          `;
        }""",
        [title, body],
    )


def zoom_to(page, selector: str) -> None:
    try:
        locator = page.locator(selector)
        if locator.count() > 1:
            locator = locator.first
        locator.scroll_into_view_if_needed(timeout=7000)
    except PlaywrightTimeoutError:
        pass


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    RECORD_DIR.mkdir(parents=True, exist_ok=True)
    ffmpeg = find_ffmpeg()
    raw_video: Path | None = None

    with sync_playwright() as p:
        browser = p.chromium.launch(
            executable_path=str(EDGE),
            headless=True,
            args=["--autoplay-policy=no-user-gesture-required"],
        )
        context = browser.new_context(
            viewport={"width": 1280, "height": 720},
            record_video_dir=str(RECORD_DIR),
            record_video_size={"width": 1280, "height": 720},
            device_scale_factor=1,
        )
        page = context.new_page()
        page.goto("http://127.0.0.1:8051/?demo_cad_toolchain_video=1", wait_until="networkidle")

        set_caption(page, "01 / 主线定位", "Tri-MRO 将检修问题收束到证据链、结构链和作业链，而不是只让大模型直接回答。")
        wait(3.2)

        set_caption(page, "02 / 进入资源与模型", "这里展示本次新增的真实 CAD 工具链：FreeCAD 校验、OpenSCAD 导出、Blender 多视角渲染。")
        safe_click(page, page.get_by_role("button", name="资源与模型"))
        wait(2.0)

        zoom_to(page, ".candidate-cad-panel")
        set_caption(page, "03 / 候选 CAD 资产池", "现场照片经 OCR/VLM 提取部件线索后，生成 CAD spec、CadQuery 和 OpenSCAD 候选代码。")
        wait(3.2)

        if page.locator(".candidate-cad-card").count() > 0:
            safe_click(page, page.locator(".candidate-cad-card").first)
        wait(1.0)

        zoom_to(page, ".candidate-cad-review-workbench")
        set_caption(page, "04 / real_render 模式", "运行模式已升级为 real_render；候选资产必须经过真实工具链产物验证后，才能进入审核。")
        wait(3.8)

        zoom_to(page, ".candidate-render-grid")
        set_caption(page, "05 / Blender 四视图", "主预览不再使用 SVG，而是显示 Blender 正交渲染：iso、front、side、top 四个视角。")
        wait(4.2)

        zoom_to(page, ".candidate-cad-links")
        set_caption(page, "06 / 工程产物可追溯", "页面提供 STEP、STL、OpenSCAD STL、GLB、FreeCAD 校验和 Blender 报告链接。")
        wait(4.0)

        zoom_to(page, ".candidate-cad-actions")
        set_caption(page, "07 / 人工审核闸门", "候选 CAD 只作为结构理解草稿；必须经机械审核，才能晋升为结构链资产。")
        wait(3.8)

        safe_click(page, page.get_by_role("button", name="CAD 结构工位"))
        wait(1.5)
        set_caption(page, "08 / 与 CAD 工位联动", "成熟资产进入 CAD 结构工位后，才用于部件定位、SOP 绑定和安全闸门展示。")
        wait(4.0)

        set_caption(page, "结论", "这条链路的卖点不是“单图制造级重建”，而是可验证、可审核、可追溯的结构链增强。")
        wait(4.5)

        video = page.video
        context.close()
        browser.close()
        if video:
            raw_video = Path(video.path())

    if raw_video is None or not raw_video.exists():
        raise RuntimeError("Playwright video was not produced")

    webm_out = OUT_DIR / "cad_toolchain_demo_raw.webm"
    mp4_out = OUT_DIR / "cad_toolchain_demo.mp4"
    if webm_out.exists():
        webm_out.unlink()
    raw_video.replace(webm_out)

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

    subtitle_path = OUT_DIR / "cad_toolchain_demo_subtitles.txt"
    subtitle_path.write_text(
        "\n".join(
            [
                "01 主线定位：Tri-MRO 不是普通问答，而是三链对齐检修系统。",
                "02 真实工具链：FreeCAD / OpenSCAD / Blender 已接入。",
                "03 候选 CAD：现场照片生成可审核 CAD spec 和工程产物。",
                "04 real_render：不再只展示 SVG 或 Python 预览。",
                "05 Blender 四视图：iso / front / side / top。",
                "06 产物追溯：STEP / STL / GLB / 校验报告 / 渲染报告。",
                "07 人工审核：候选 CAD 不用于制造、测量或安全放行。",
                "08 结构链联动：审核后进入 CAD 工位，服务 SOP 和安全闸门。",
            ]
        ),
        encoding="utf-8",
    )
    print(mp4_out)


if __name__ == "__main__":
    main()
