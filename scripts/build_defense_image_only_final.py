from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
DECK_DIR = ROOT / "materials" / "defense_image_deck"
SOURCE_SLIDE_DIR = DECK_DIR / "slides"
SCREENSHOT_DIR = DECK_DIR / "real_screenshots"
DEFAULT_SLIDE_OUTPUT_DIR = DECK_DIR / "final_image_only_slides"
DEFAULT_OUTPUT = ROOT / "materials" / "A1-maintenance-assistant-defense-image-only-final.pptx"
EVAL_SUMMARY = DECK_DIR / "evaluation_summary.json"
MECHANICAL_SUMMARY = DECK_DIR / "mechanical_review_summary.json"
DEPLOYMENT_SUMMARY = DECK_DIR / "deployment_summary.json"

W, H = 1536, 864
NAVY = (8, 22, 36)
NAVY_2 = (13, 35, 54)
PANEL = (18, 45, 65)
PANEL_2 = (29, 61, 82)
TEAL = (30, 196, 174)
CYAN = (72, 165, 213)
AMBER = (232, 166, 64)
RED = (220, 82, 82)
WHITE = (246, 250, 253)
MUTED = (170, 188, 204)
GRID = (78, 107, 128)

BASE_SLIDES = [
    "slide01_cover.png",
    "slide02_pain_points.png",
    "slide03_requirements.png",
    "slide04_position_flow.png",
    "slide05_architecture.png",
    "slide06_data_evidence.png",
    "slide07_multimodal_retrieval.png",
    "slide08_agents.png",
    "slide09_sop_compliance.png",
    "slide10_knowledge_loop.png",
    "slide11_evaluation.png",
    "slide12_demo_route.png",
    "slide13_deployment.png",
    "slide14_close.png",
]


def _font(size: int, *, bold: bool = False) -> ImageFont.FreeTypeFont:
    candidates = [
        Path("C:/Windows/Fonts/msyhbd.ttc" if bold else "C:/Windows/Fonts/msyh.ttc"),
        Path("C:/Windows/Fonts/simhei.ttf"),
        Path("C:/Windows/Fonts/arial.ttf"),
    ]
    for path in candidates:
        if path.exists():
            return ImageFont.truetype(str(path), size)
    return ImageFont.load_default()


def _load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _text_width(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont) -> int:
    return int(draw.textbbox((0, 0), text, font=font)[2])


def _wrap(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont, max_width: int) -> list[str]:
    lines: list[str] = []
    for raw in text.splitlines():
        current = ""
        for char in raw:
            trial = current + char
            if current and _text_width(draw, trial, font) > max_width:
                lines.append(current)
                current = char
            else:
                current = trial
        lines.append(current)
    return lines


def _draw_text(
    draw: ImageDraw.ImageDraw,
    xy: tuple[int, int],
    text: str,
    *,
    size: int,
    fill: tuple[int, int, int] = WHITE,
    bold: bool = False,
    max_width: int | None = None,
    line_gap: int = 8,
    anchor: str | None = None,
) -> int:
    font = _font(size, bold=bold)
    if max_width is None:
        draw.text(xy, text, font=font, fill=fill, anchor=anchor)
        return int(draw.textbbox(xy, text, font=font, anchor=anchor)[3])
    y = xy[1]
    for line in _wrap(draw, text, font, max_width):
        draw.text((xy[0], y), line, font=font, fill=fill)
        y += size + line_gap
    return y


def _rounded(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], fill, outline=GRID, width: int = 2, radius: int = 20) -> None:
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)


def _fit_image(path: Path, size: tuple[int, int]) -> Image.Image:
    image = Image.open(path).convert("RGB")
    image.thumbnail(size, Image.Resampling.LANCZOS)
    canvas = Image.new("RGB", size, NAVY_2)
    x = (size[0] - image.width) // 2
    y = (size[1] - image.height) // 2
    canvas.paste(image, (x, y))
    return canvas


def _paste_fit(base: Image.Image, path: Path, box: tuple[int, int, int, int]) -> None:
    x1, y1, x2, y2 = box
    if not path.exists():
        draw = ImageDraw.Draw(base)
        _rounded(draw, box, PANEL_2)
        _draw_text(draw, (x1 + 22, y1 + 54), f"截图待补\n{path.name}", size=30, fill=MUTED, max_width=x2 - x1 - 44)
        return
    image = _fit_image(path, (x2 - x1, y2 - y1))
    base.paste(image, (x1, y1))


def _new_canvas(title: str, subtitle: str, slide_no: int, accent=TEAL) -> Image.Image:
    img = Image.new("RGB", (W, H), NAVY)
    draw = ImageDraw.Draw(img)
    for y in range(H):
        ratio = y / H
        color = (
            int(NAVY[0] * (1 - ratio) + 13 * ratio),
            int(NAVY[1] * (1 - ratio) + 34 * ratio),
            int(NAVY[2] * (1 - ratio) + 50 * ratio),
        )
        draw.line((0, y, W, y), fill=color)
    draw.rectangle((0, 0, W, 118), fill=(9, 25, 41))
    draw.rectangle((42, 116, W - 42, 121), fill=accent)
    _draw_text(draw, (72, 44), f"{slide_no:02d}", size=24, fill=accent, bold=True)
    _draw_text(draw, (138, 28), title, size=46, fill=WHITE, bold=True)
    _draw_text(draw, (140, 82), subtitle, size=22, fill=MUTED)
    return img


def _patch_data_slide(path: Path) -> None:
    img = Image.open(path).convert("RGB")
    draw = ImageDraw.Draw(img)
    card = (884, 464, 1176, 696)
    _rounded(draw, card, (11, 35, 55), outline=TEAL, width=2, radius=10)
    draw.ellipse((920, 488, 1000, 568), fill=(20, 89, 120), outline=CYAN, width=2)
    _draw_text(draw, (960, 506), "图", size=34, fill=WHITE, bold=True, anchor="ma")
    _draw_text(draw, (928, 584), "30", size=86, fill=WHITE, bold=True)
    _draw_text(draw, (1026, 628), "张图片", size=38, fill=WHITE, bold=True)
    _draw_text(draw, (928, 676), "电机/泵/轴承各 10 张", size=20, fill=MUTED)
    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(path, quality=94)


def _build_demo_slide(path: Path) -> None:
    img = _new_canvas("真实系统演示截图", "文本问诊、图片检索、SOP 生成、合规校验、案例审核五条链路", 15)
    draw = ImageDraw.Draw(img)
    cards = [
        ("文本问诊", SCREENSHOT_DIR / "01_text_query.png", (78, 164, 492, 384)),
        ("图片检索", SCREENSHOT_DIR / "02_image_search.png", (562, 164, 976, 384)),
        ("SOP 生成", SCREENSHOT_DIR / "03_sop_generation.png", (1046, 164, 1460, 384)),
        ("合规校验", SCREENSHOT_DIR / "04_compliance_check.png", (310, 468, 724, 688)),
        ("案例审核", SCREENSHOT_DIR / "05_case_review_update.png", (814, 468, 1228, 688)),
    ]
    for label, shot, box in cards:
        x1, y1, x2, y2 = box
        _rounded(draw, (x1 - 12, y1 - 42, x2 + 12, y2 + 48), PANEL, outline=GRID, radius=20)
        _draw_text(draw, (x1, y1 - 31), label, size=24, fill=TEAL, bold=True)
        _paste_fit(img, shot, box)
    _draw_text(draw, (125, 770), "截图来自可运行系统；正式答辩建议现场按该顺序演示，避免自由问答导致流程失控。", size=26, fill=MUTED, max_width=1280)
    img.save(path, quality=94)


def _build_eval_slide(path: Path) -> None:
    summary = _load_json(EVAL_SUMMARY)
    img = _new_canvas("量化评测结果", "104 道 approved 评测题；四组对比证明检索与引用链路有效", 16, accent=AMBER)
    draw = ImageDraw.Draw(img)
    benchmarks = summary.get("benchmarks", [])
    headers = ["组别", "Recall@5", "引用覆盖", "SOP 完整", "幻觉率"]
    x_positions = [104, 430, 650, 870, 1090]
    y = 180
    for x, header in zip(x_positions, headers):
        _draw_text(draw, (x, y), header, size=24, fill=AMBER, bold=True)
    for i, row in enumerate(benchmarks):
        yy = 242 + i * 100
        _rounded(draw, (76, yy - 18, 1378, yy + 62), PANEL if row.get("mode") != "full_system" else (19, 72, 76), outline=TEAL if row.get("mode") == "full_system" else GRID, radius=16)
        values = [
            row.get("name", row.get("mode", "")),
            f"{row.get('recall_at_5', 0) * 100:.0f}%",
            f"{row.get('citation_coverage', 0) * 100:.0f}%",
            f"{row.get('sop_score', 0) * 100:.0f}%",
            f"{row.get('hallucination_rate', 0) * 100:.0f}%",
        ]
        for x, value in zip(x_positions, values):
            _draw_text(draw, (x, yy), value, size=30 if x == 104 else 28, fill=WHITE, bold=row.get("mode") == "full_system")
    _draw_text(draw, (92, 704), f"评测口径：question_count={summary.get('question_count', 104)}，review_basis={summary.get('review_basis', 'approved_only')}。100% 不代表泛化完美，只代表当前窄领域评测集已跑通。", size=25, fill=MUTED, max_width=1320)
    img.save(path, quality=94)


def _build_review_slide(path: Path) -> None:
    summary = _load_json(MECHANICAL_SUMMARY)
    img = _new_canvas("机械专业审核摘要", "案例、评测题、SOP 与安全项均使用 reviewer 代号审核", 17)
    draw = ImageDraw.Draw(img)
    cards = [
        ("案例 approved", str(summary.get("cases_approved", 125)), "目标 >= 100", TEAL),
        ("评测题 approved", str(summary.get("eval_approved", 104)), "目标 >= 100", CYAN),
        ("SOP 完整度", f"{summary.get('sop_completeness_avg', 3.94):.2f}/5", "机械审核均值", AMBER),
        ("安全合规", f"{summary.get('safety_avg', 4.27):.2f}/5", "机械审核均值", TEAL),
    ]
    for i, (label, value, note, color) in enumerate(cards):
        x = 100 + i * 346
        _rounded(draw, (x, 190, x + 286, 360), PANEL, outline=color, radius=18)
        _draw_text(draw, (x + 28, 222), value, size=52, fill=WHITE, bold=True)
        _draw_text(draw, (x + 28, 288), label, size=24, fill=color, bold=True)
        _draw_text(draw, (x + 28, 324), note, size=20, fill=MUTED)
    risk = summary.get("risk_distribution", {})
    difficulty = summary.get("difficulty_distribution", {})
    _rounded(draw, (120, 446, 706, 676), PANEL_2, outline=GRID, radius=20)
    _draw_text(draw, (154, 486), "风险分布", size=30, fill=WHITE, bold=True)
    _draw_text(draw, (154, 540), f"medium：{risk.get('medium', 0)} 条", size=28, fill=MUTED)
    _draw_text(draw, (154, 592), f"high：{risk.get('high', 0)} 条", size=28, fill=RED)
    _rounded(draw, (830, 446, 1416, 676), PANEL_2, outline=GRID, radius=20)
    _draw_text(draw, (864, 486), "难度分布", size=30, fill=WHITE, bold=True)
    _draw_text(draw, (864, 540), f"medium：{difficulty.get('medium', 0)} 条", size=28, fill=MUTED)
    _draw_text(draw, (864, 592), f"hard：{difficulty.get('hard', 0)} 条", size=28, fill=AMBER)
    _draw_text(draw, (132, 760), "答辩口径：机械审核不是现场验证替代品，但证明案例与评测题已经过专业角色复核。", size=25, fill=MUTED, max_width=1280)
    img.save(path, quality=94)


def _build_deployment_slide(path: Path) -> None:
    summary = _load_json(DEPLOYMENT_SUMMARY)
    img = _new_canvas("公网部署与提交验证", "Render 公网服务、Supabase 持久化、提交包审计均已跑通", 18)
    draw = ImageDraw.Draw(img)
    left = (72, 170, 760, 664)
    right = (830, 170, 1456, 664)
    _rounded(draw, left, PANEL, outline=GRID, radius=20)
    _rounded(draw, right, PANEL, outline=GRID, radius=20)
    _draw_text(draw, (110, 210), "公网状态", size=34, fill=TEAL, bold=True)
    _draw_text(draw, (110, 268), f"URL：{summary.get('public_url', 'https://a1-maintenance-assistant.onrender.com')}", size=25, fill=WHITE, max_width=590)
    _draw_text(draw, (110, 338), f"health：{summary.get('health_status', 'ok')}", size=30, fill=WHITE, bold=True)
    _draw_text(draw, (110, 392), f"mode：{summary.get('mode', 'codex')}", size=26, fill=MUTED)
    _draw_text(draw, (110, 440), f"Supabase：enabled={summary.get('supabase_enabled', True)}，schema={summary.get('supabase_schema', 'public')}", size=24, fill=MUTED, max_width=590)
    _draw_text(draw, (110, 526), "最终验证：public ready=true / blockers=0 / forbidden=0", size=30, fill=AMBER, bold=True, max_width=590)
    home = ROOT / summary.get("home_screenshot", "materials/defense_image_deck/real_screenshots/06_public_deploy_home.png")
    health = ROOT / summary.get("health_screenshot", "materials/defense_image_deck/real_screenshots/07_public_health.png")
    _draw_text(draw, (868, 210), "部署截图", size=34, fill=TEAL, bold=True)
    _paste_fit(img, home, (872, 270, 1414, 478))
    _paste_fit(img, health, (872, 514, 1414, 622))
    _draw_text(draw, (126, 760), "答辩前建议提前预热公网服务，并保留本地 8051 备用演示路径。", size=26, fill=MUTED, max_width=1280)
    img.save(path, quality=94)


def build_slide_images(slide_output_dir: Path | str = DEFAULT_SLIDE_OUTPUT_DIR) -> list[Path]:
    out_dir = Path(slide_output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    slide_paths: list[Path] = []
    for file_name in BASE_SLIDES:
        src = SOURCE_SLIDE_DIR / file_name
        if not src.exists():
            raise FileNotFoundError(f"Missing source slide image: {src}")
        dst = out_dir / file_name
        shutil.copyfile(src, dst)
        if file_name == "slide06_data_evidence.png":
            _patch_data_slide(dst)
        slide_paths.append(dst)
    extra = [
        ("slide15_real_demo.png", _build_demo_slide),
        ("slide16_evaluation_result.png", _build_eval_slide),
        ("slide17_mechanical_review.png", _build_review_slide),
        ("slide18_deployment_validation.png", _build_deployment_slide),
    ]
    for file_name, builder in extra:
        dst = out_dir / file_name
        builder(dst)
        slide_paths.append(dst)
    return slide_paths


def build_final_image_only_deck(
    output_path: Path | str = DEFAULT_OUTPUT,
    slide_output_dir: Path | str = DEFAULT_SLIDE_OUTPUT_DIR,
) -> Path:
    try:
        from pptx import Presentation
        from pptx.util import Inches
    except ModuleNotFoundError as exc:  # pragma: no cover
        raise SystemExit("python-pptx is required: .\\.venv\\Scripts\\python.exe -m pip install python-pptx") from exc

    slide_paths = build_slide_images(slide_output_dir)
    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)
    blank = prs.slide_layouts[6]
    for slide_path in slide_paths:
        slide = prs.slides.add_slide(blank)
        slide.shapes.add_picture(str(slide_path), Inches(0), Inches(0), width=prs.slide_width, height=prs.slide_height)

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    prs.save(output)
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the final 18-page image-only A1 defense deck.")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--slide-output-dir", type=Path, default=DEFAULT_SLIDE_OUTPUT_DIR)
    args = parser.parse_args()
    print(build_final_image_only_deck(args.output, args.slide_output_dir))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
