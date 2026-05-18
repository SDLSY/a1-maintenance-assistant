from __future__ import annotations

import json
from pathlib import Path

from PIL import Image, ImageEnhance, ImageFilter
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_AUTO_SHAPE_TYPE, MSO_CONNECTOR
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Inches, Pt


ROOT = Path(__file__).resolve().parents[1]
SRC_SLIDES = ROOT / "materials" / "defense_image_deck" / "slides"
OUT_DIR = ROOT / "materials" / "defense_v2"
BG_DIR = OUT_DIR / "backgrounds"
SCREENSHOT_DIR = OUT_DIR / "screenshots"
OUT_PPTX = ROOT / "materials" / "A1-maintenance-assistant-defense-v2-editable.pptx"
AUDIT_MD = OUT_DIR / "slide_audit.md"
README_MD = OUT_DIR / "README.md"
INPUT_TEMPLATE = OUT_DIR / "final_inputs.template.json"
INPUT_FILE = OUT_DIR / "final_inputs.json"

WIDE = Inches(13.333)
HIGH = Inches(7.5)

NAVY = RGBColor(9, 24, 39)
NAVY_2 = RGBColor(14, 35, 55)
PANEL = RGBColor(21, 43, 62)
PANEL_2 = RGBColor(243, 247, 250)
WHITE = RGBColor(255, 255, 255)
TEXT = RGBColor(232, 239, 245)
MUTED = RGBColor(162, 176, 190)
INK = RGBColor(24, 35, 46)
GRID = RGBColor(190, 203, 214)
TEAL = RGBColor(25, 176, 158)
CYAN = RGBColor(78, 166, 207)
AMBER = RGBColor(231, 166, 68)
RED = RGBColor(209, 78, 78)
GREEN = RGBColor(54, 188, 126)

FONT = "Microsoft YaHei"
TITLE_FONT = "Microsoft YaHei UI"


SLIDES = [
    {
        "image": "slide01_cover.png",
        "title": "A1-MAKG：面向设备检修的多模态证据链作业辅助系统",
        "subtitle": "面向电机-泵-轴承系统的多模态 RAG + SOP 合规闭环",
        "kicker": "中国软件杯 A1 赛题 | 多模态大模型技术",
    },
    {
        "image": "slide02_pain_points.png",
        "title": "检修现场为什么需要这个系统",
        "subtitle": "传统检修不是缺少资料，而是缺少可追溯、可执行、可更新的作业辅助链路",
    },
    {
        "image": "slide03_requirements.png",
        "title": "A1 赛题要求逐项闭环",
        "subtitle": "所有功能都映射到赛题原文，不做偏题的通用聊天机器人",
    },
    {
        "image": "slide04_position_flow.png",
        "title": "不是聊天机器人，是检修作业系统",
        "subtitle": "输入故障信息后，系统给出证据、判断、SOP、合规检查与知识沉淀动作",
    },
    {
        "image": "slide05_architecture.png",
        "title": "系统架构：轻量部署 + 云端模型 + 持久化闭环",
        "subtitle": "前端工作台负责操作体验，FastAPI 负责检索、编排、评测和数据同步",
    },
    {
        "image": "slide06_data_evidence.png",
        "title": "数据资产与证据追溯",
        "subtitle": "每条回答必须带来源、页码、案例编号或评测编号，降低幻觉风险",
    },
    {
        "image": "slide07_multimodal_retrieval.png",
        "title": "多模态混合检索",
        "subtitle": "文本、故障图片、设备型号同时参与召回，最终答案必须回到手册和案例证据",
    },
    {
        "image": "slide08_agents.png",
        "title": "多 Agent 编排：把大模型拆成可控岗位",
        "subtitle": "每个 Agent 只负责一个环节，降低一次性生成导致的遗漏和幻觉",
    },
    {
        "image": "slide09_sop_compliance.png",
        "title": "SOP 与安全合规是核心差异",
        "subtitle": "评委看到的不是会聊天的系统，而是能约束现场作业的系统",
    },
    {
        "image": "slide10_knowledge_loop.png",
        "title": "知识沉淀闭环",
        "subtitle": "一线案例先审核，再进入案例库、知识图谱和检索索引",
    },
    {
        "image": "slide11_evaluation.png",
        "title": "评测设计：用数据证明系统有效",
        "subtitle": "国一答辩需要讲清楚系统比普通 RAG 好在哪里，以及如何量化",
    },
    {
        "image": "slide12_demo_route.png",
        "title": "答辩演示路线",
        "subtitle": "用 5 分钟跑通文本问诊、图片检索、SOP 生成、合规拦截和知识更新",
    },
    {
        "image": "slide13_deployment.png",
        "title": "部署与提交准备",
        "subtitle": "比赛提交重点是稳定可演示、数据可恢复、评测可复现",
    },
    {
        "image": "slide14_close.png",
        "title": "为什么这套方案有机会冲国一",
        "subtitle": "差异点不是模型更大，而是场景更窄、证据更强、闭环更完整",
    },
]

DEFAULT_INPUTS = {
    "meta": {
        "school": "学校名称待补",
        "team": "队伍名称待补",
        "advisor": "指导老师待补",
        "version": "V2 可编辑优化版",
    },
    "metrics": {
        "retrieval_recall_at_5": ">= 85%",
        "citation_coverage": "100%",
        "image_top5_hit": ">= 80%",
        "sop_completeness": ">= 90%",
        "safety_miss_rate": "<= 5%",
        "status": "目标值，等待真实评测替换",
    },
    "screenshots": {
        "text_query": "materials/defense_v2/screenshots/01_text_query.png",
        "image_search": "materials/defense_v2/screenshots/02_image_search.png",
        "sop_generation": "materials/defense_v2/screenshots/03_sop_generation.png",
        "compliance_block": "materials/defense_v2/screenshots/04_compliance_block.png",
        "knowledge_update": "materials/defense_v2/screenshots/05_knowledge_update.png",
    },
    "deployment": {
        "public_url": "https://a1-maintenance-assistant.onrender.com",
        "database": "Supabase + SQLite backup",
        "runtime": "Render Web Service",
        "domestic_path": "国产化兼容路线待补",
    },
}

INPUTS = DEFAULT_INPUTS


def rgb_tuple(color: RGBColor) -> tuple[int, int, int]:
    return color[0], color[1], color[2]


def prepare_backgrounds() -> None:
    BG_DIR.mkdir(parents=True, exist_ok=True)
    for i, spec in enumerate(SLIDES, start=1):
        src = SRC_SLIDES / spec["image"]
        dst = BG_DIR / f"slide{i:02d}_bg.jpg"
        if not src.exists():
            continue
        img = Image.open(src).convert("RGB").resize((1536, 864))
        img = img.filter(ImageFilter.GaussianBlur(radius=3.2))
        img = ImageEnhance.Brightness(img).enhance(0.31)
        overlay = Image.new("RGB", img.size, rgb_tuple(NAVY))
        img = Image.blend(img, overlay, 0.28)
        img.save(dst, quality=88)


def write_input_template() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
    if not INPUT_TEMPLATE.exists():
        INPUT_TEMPLATE.write_text(json.dumps(DEFAULT_INPUTS, ensure_ascii=False, indent=2), encoding="utf-8")


def merge_dict(base: dict, override: dict) -> dict:
    merged = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = merge_dict(merged[key], value)
        else:
            merged[key] = value
    return merged


def load_inputs() -> dict:
    write_input_template()
    if not INPUT_FILE.exists():
        return DEFAULT_INPUTS
    data = json.loads(INPUT_FILE.read_text(encoding="utf-8-sig"))
    return merge_dict(DEFAULT_INPUTS, data)


def set_text(run, size: float, color: RGBColor = TEXT, bold: bool = False, font: str = FONT) -> None:
    run.font.name = font
    run.font.size = Pt(size)
    run.font.color.rgb = color
    run.font.bold = bold


def add_text(
    slide,
    text: str,
    x,
    y,
    w,
    h,
    *,
    size: float = 16,
    color: RGBColor = TEXT,
    bold: bool = False,
    align=PP_ALIGN.LEFT,
    valign=MSO_ANCHOR.TOP,
    font: str = FONT,
):
    box = slide.shapes.add_textbox(x, y, w, h)
    tf = box.text_frame
    tf.clear()
    tf.word_wrap = True
    tf.margin_left = Inches(0.03)
    tf.margin_right = Inches(0.03)
    tf.margin_top = Inches(0.02)
    tf.margin_bottom = Inches(0.02)
    tf.vertical_anchor = valign
    p = tf.paragraphs[0]
    p.alignment = align
    run = p.add_run()
    run.text = text
    set_text(run, size, color, bold, font)
    return box


def add_rect(slide, x, y, w, h, fill: RGBColor, *, line: RGBColor | None = None, transparency: int = 0, radius: bool = False):
    shape_type = MSO_AUTO_SHAPE_TYPE.ROUNDED_RECTANGLE if radius else MSO_AUTO_SHAPE_TYPE.RECTANGLE
    shp = slide.shapes.add_shape(shape_type, x, y, w, h)
    shp.fill.solid()
    shp.fill.fore_color.rgb = fill
    shp.fill.transparency = transparency
    if line is None:
        shp.line.fill.background()
    else:
        shp.line.color.rgb = line
        shp.line.width = Pt(0.8)
    return shp


def add_header(slide, idx: int, title: str, subtitle: str | None = None) -> None:
    add_text(slide, "A1-MAKG 证据链作业系统", Inches(0.55), Inches(0.34), Inches(4.2), Inches(0.25), size=9.5, color=TEAL, bold=True)
    add_text(slide, title, Inches(0.55), Inches(0.68), Inches(8.9), Inches(0.52), size=24, color=WHITE, bold=True, font=TITLE_FONT)
    if subtitle:
        add_text(slide, subtitle, Inches(0.58), Inches(1.23), Inches(8.6), Inches(0.34), size=11.5, color=MUTED)
    add_rect(slide, Inches(0.55), Inches(1.65), Inches(1.0), Inches(0.04), TEAL)
    add_text(slide, f"{idx:02d}", Inches(12.15), Inches(0.42), Inches(0.55), Inches(0.24), size=10, color=MUTED, align=PP_ALIGN.RIGHT)


def add_background(slide, idx: int) -> None:
    bg = BG_DIR / f"slide{idx:02d}_bg.jpg"
    if bg.exists():
        slide.shapes.add_picture(str(bg), 0, 0, width=WIDE, height=HIGH)
    else:
        add_rect(slide, 0, 0, WIDE, HIGH, NAVY)
    add_rect(slide, 0, 0, WIDE, HIGH, NAVY, transparency=20)


def resolve_input_path(value: str) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    return ROOT / path


def add_fit_image(slide, path: Path, x, y, w, h) -> bool:
    if not path.exists():
        return False
    with Image.open(path) as img:
        iw, ih = img.size
    if iw <= 0 or ih <= 0:
        return False
    box_ratio = w / h
    image_ratio = iw / ih
    if image_ratio >= box_ratio:
        draw_w = w
        draw_h = w / image_ratio
        draw_x = x
        draw_y = y + (h - draw_h) / 2
    else:
        draw_h = h
        draw_w = h * image_ratio
        draw_x = x + (w - draw_w) / 2
        draw_y = y
    slide.shapes.add_picture(str(path), draw_x, draw_y, width=draw_w, height=draw_h)
    return True


def bullet_list(slide, items: list[str], x, y, w, h, *, size: float = 13.5, color: RGBColor = TEXT, gap: float = 5):
    box = slide.shapes.add_textbox(x, y, w, h)
    tf = box.text_frame
    tf.clear()
    tf.word_wrap = True
    tf.margin_left = Inches(0.02)
    tf.margin_right = Inches(0.02)
    tf.margin_top = Inches(0)
    for i, item in enumerate(items):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.text = item
        p.level = 0
        p.space_after = Pt(gap)
        p.font.name = FONT
        p.font.size = Pt(size)
        p.font.color.rgb = color
    return box


def card(slide, x, y, w, h, title: str, body: str, *, accent: RGBColor = TEAL):
    add_rect(slide, x, y, w, h, PANEL, line=RGBColor(54, 82, 104), transparency=5, radius=True)
    add_rect(slide, x, y, Inches(0.08), h, accent)
    add_text(slide, title, x + Inches(0.22), y + Inches(0.18), w - Inches(0.35), Inches(0.26), size=14, color=WHITE, bold=True)
    add_text(slide, body, x + Inches(0.22), y + Inches(0.54), w - Inches(0.35), h - Inches(0.68), size=10.5, color=MUTED)


def metric(slide, x, y, w, h, value: str, label: str, note: str = "", *, accent: RGBColor = TEAL):
    add_rect(slide, x, y, w, h, PANEL, line=RGBColor(55, 84, 108), transparency=3, radius=True)
    add_text(slide, value, x + Inches(0.18), y + Inches(0.16), w - Inches(0.3), Inches(0.35), size=22, color=WHITE, bold=True)
    add_text(slide, label, x + Inches(0.18), y + Inches(0.56), w - Inches(0.3), Inches(0.26), size=10, color=accent, bold=True)
    if note:
        add_text(slide, note, x + Inches(0.18), y + Inches(0.86), w - Inches(0.3), Inches(0.22), size=8.6, color=MUTED)


def connector(slide, x1, y1, x2, y2, *, color: RGBColor = TEAL):
    line = slide.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, x1, y1, x2, y2)
    line.line.color.rgb = color
    line.line.width = Pt(1.4)
    return line


def footer(slide, text: str = "最终版需替换真实截图与实测结果") -> None:
    add_text(slide, text, Inches(0.55), Inches(7.12), Inches(5.8), Inches(0.18), size=8.5, color=MUTED)


def slide_cover(prs):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    add_background(slide, 1)
    meta = INPUTS["meta"]
    add_rect(slide, Inches(0.62), Inches(0.72), Inches(6.45), Inches(5.72), NAVY, transparency=8, radius=True)
    add_text(slide, "中国软件杯 A1 赛题", Inches(0.94), Inches(1.0), Inches(3.0), Inches(0.28), size=11, color=TEAL, bold=True)
    add_text(slide, "设备检修知识检索\n与作业辅助系统", Inches(0.9), Inches(1.46), Inches(5.9), Inches(1.65), size=33, color=WHITE, bold=True, font=TITLE_FONT)
    add_text(slide, "面向电机-泵-轴承系统的多模态 RAG + SOP 合规闭环", Inches(0.94), Inches(3.35), Inches(5.6), Inches(0.42), size=15.5, color=TEXT)
    for i, tag in enumerate(["手册证据", "图片检索", "标准作业", "安全合规", "知识沉淀"]):
        card(slide, Inches(0.94 + i * 1.08), Inches(4.25), Inches(0.92), Inches(0.62), tag, "", accent=TEAL)
    info = f"{meta['school']} | {meta['team']} | {meta['advisor']} | {meta['version']}"
    add_text(slide, info, Inches(0.94), Inches(5.7), Inches(5.6), Inches(0.25), size=10.2, color=MUTED)
    return slide


def slide_pain(prs):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    add_background(slide, 2)
    add_header(slide, 2, SLIDES[1]["title"], SLIDES[1]["subtitle"])
    items = [
        ("知识分散", "手册、案例、经验记录分散在不同文件和人员经验中，现场检索成本高。"),
        ("检索低效", "普通关键词搜索难处理型号、症状、图片和部件之间的语义关联。"),
        ("作业不规范", "诊断结果如果不能落到 SOP、工具、备件和验收标准，就难以指导现场。"),
        ("经验难传承", "一线人员的有效经验缺少审核、结构化和持续进入知识库的机制。"),
    ]
    for idx, (t, b) in enumerate(items):
        x = Inches(0.75 + (idx % 2) * 5.95)
        y = Inches(2.12 + (idx // 2) * 1.68)
        card(slide, x, y, Inches(5.3), Inches(1.18), t, b, accent=[TEAL, CYAN, AMBER, RED][idx])
    add_text(slide, "本项目的切入点：把“找资料”升级为“有证据的检修作业辅助”。", Inches(1.1), Inches(5.82), Inches(10.8), Inches(0.38), size=18, color=WHITE, bold=True, align=PP_ALIGN.CENTER)
    footer(slide, "优化判断：痛点页需要少字强表达，避免堆概念。")


def slide_requirements(prs):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    add_background(slide, 3)
    add_header(slide, 3, SLIDES[2]["title"], SLIDES[2]["subtitle"])
    rows = [
        ("PC Web / App 可视化", "Web 工作台：问诊、上传、审核、图谱、评测", "已覆盖"),
        ("多模态知识检索", "文本 + 图片 caption + 型号过滤 + 混合召回", "已覆盖"),
        ("标准化作业指引", "故障判断、安全确认、工具备件、步骤、验收", "已覆盖"),
        ("知识沉淀与更新", "案例上传、人工审核、反馈修正、索引更新", "已覆盖"),
    ]
    x, y, w, h = Inches(0.85), Inches(2.0), Inches(11.65), Inches(3.7)
    table = slide.shapes.add_table(len(rows) + 1, 3, x, y, w, h).table
    widths = [Inches(3.2), Inches(6.2), Inches(2.25)]
    for col, width in enumerate(widths):
        table.columns[col].width = width
    headers = ["赛题要求", "系统实现", "状态"]
    for c, text in enumerate(headers):
        cell = table.cell(0, c)
        cell.text = text
        cell.fill.solid()
        cell.fill.fore_color.rgb = TEAL if c == 2 else NAVY_2
        for p in cell.text_frame.paragraphs:
            p.font.name = FONT
            p.font.size = Pt(12)
            p.font.color.rgb = WHITE
            p.font.bold = True
    for r, row in enumerate(rows, start=1):
        for c, text in enumerate(row):
            cell = table.cell(r, c)
            cell.text = text
            cell.fill.solid()
            cell.fill.fore_color.rgb = RGBColor(236, 243, 247) if c != 2 else RGBColor(226, 247, 241)
            for p in cell.text_frame.paragraphs:
                p.font.name = FONT
                p.font.size = Pt(10.5)
                p.font.color.rgb = INK if c != 2 else RGBColor(0, 122, 101)
                p.font.bold = c == 2
    add_text(slide, "答辩策略：先证明不偏题，再证明做得比基础 RAG 更完整。", Inches(1.1), Inches(6.0), Inches(10.8), Inches(0.35), size=16, color=WHITE, bold=True, align=PP_ALIGN.CENTER)
    footer(slide)


def slide_flow(prs):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    add_background(slide, 4)
    add_header(slide, 4, SLIDES[3]["title"], SLIDES[3]["subtitle"])
    nodes = ["输入", "检索", "诊断", "SOP", "合规", "沉淀"]
    desc = ["文本/图片/型号", "手册+案例+图谱", "故障原因排序", "步骤化作业", "安全与禁忌", "审核后更新"]
    start_x, y = Inches(0.85), Inches(2.55)
    box_w, gap = Inches(1.65), Inches(0.42)
    for i, node in enumerate(nodes):
        x = start_x + i * (box_w + gap)
        add_rect(slide, x, y, box_w, Inches(1.05), PANEL, line=RGBColor(63, 94, 118), transparency=2, radius=True)
        add_text(slide, node, x, y + Inches(0.18), box_w, Inches(0.25), size=15, color=WHITE, bold=True, align=PP_ALIGN.CENTER)
        add_text(slide, desc[i], x + Inches(0.08), y + Inches(0.58), box_w - Inches(0.16), Inches(0.22), size=8.8, color=MUTED, align=PP_ALIGN.CENTER)
        if i < len(nodes) - 1:
            connector(slide, x + box_w, y + Inches(0.52), x + box_w + gap, y + Inches(0.52))
    add_rect(slide, Inches(1.25), Inches(4.65), Inches(10.7), Inches(0.92), NAVY_2, line=RGBColor(58, 86, 108), transparency=5, radius=True)
    add_text(slide, "核心判断", Inches(1.55), Inches(4.84), Inches(1.2), Inches(0.25), size=12, color=TEAL, bold=True)
    add_text(slide, "评委不会只看模型回答是否流畅，而会看系统能否把答案落实到“证据 + 标准步骤 + 安全约束 + 更新机制”。", Inches(2.55), Inches(4.82), Inches(8.95), Inches(0.32), size=13.2, color=WHITE)
    footer(slide)


def slide_architecture(prs):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    add_background(slide, 5)
    add_header(slide, 5, SLIDES[4]["title"], SLIDES[4]["subtitle"])
    layers = [
        ("交互层", "PC Web 工作台：问诊检索、图片上传、案例审核、评测面板"),
        ("编排层", "FastAPI：会话管理、Agent 调度、合规规则、索引更新"),
        ("检索层", "BM25 + 向量检索 + 型号过滤 + 图谱邻居 + 重排序"),
        ("知识层", "手册 chunk、图片 caption、案例库、反馈库、知识图谱"),
        ("模型层", "文本模型、视觉模型、embedding 模型，支持中转或国产模型切换"),
    ]
    for i, (name, body) in enumerate(layers):
        y = Inches(1.92 + i * 0.82)
        add_rect(slide, Inches(0.85), y, Inches(1.45), Inches(0.55), TEAL if i == 0 else NAVY_2, transparency=0, radius=True)
        add_text(slide, name, Inches(0.92), y + Inches(0.15), Inches(1.3), Inches(0.18), size=11, color=WHITE, bold=True, align=PP_ALIGN.CENTER)
        add_rect(slide, Inches(2.48), y, Inches(7.6), Inches(0.55), PANEL, line=RGBColor(62, 91, 114), transparency=4, radius=True)
        add_text(slide, body, Inches(2.66), y + Inches(0.15), Inches(7.2), Inches(0.18), size=10.6, color=TEXT)
    add_rect(slide, Inches(10.55), Inches(2.1), Inches(1.85), Inches(3.55), PANEL, line=RGBColor(62, 91, 114), transparency=4, radius=True)
    add_text(slide, "持久化", Inches(10.82), Inches(2.38), Inches(1.3), Inches(0.28), size=14, color=WHITE, bold=True, align=PP_ALIGN.CENTER)
    bullet_list(slide, ["Supabase", "SQLite 备份", "文件索引", "部署日志"], Inches(10.88), Inches(2.92), Inches(1.2), Inches(1.6), size=10.5, color=MUTED, gap=7)
    footer(slide, "优化判断：架构页必须可编辑，便于现场按评委问题展开。")


def slide_data(prs):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    add_background(slide, 6)
    add_header(slide, 6, SLIDES[5]["title"], SLIDES[5]["subtitle"])
    metrics = [
        ("9", "公开 PDF 手册", "电机、泵、轴承"),
        ("4", "领域 Markdown", "人工整理样例"),
        ("1233", "向量索引", "chunk embeddings"),
        ("125", "检修案例", "机械审核 CSV"),
        ("104", "评测问答", "检索与 SOP"),
        ("30", "故障图片", "多模态评测"),
    ]
    for i, (v, l, n) in enumerate(metrics):
        x = Inches(0.82 + (i % 3) * 4.05)
        y = Inches(2.02 + (i // 3) * 1.45)
        metric(slide, x, y, Inches(3.45), Inches(1.02), v, l, n, accent=[TEAL, CYAN, TEAL, AMBER, TEAL, CYAN][i])
    add_rect(slide, Inches(1.05), Inches(5.48), Inches(11.1), Inches(0.56), NAVY_2, line=RGBColor(61, 90, 111), transparency=2, radius=True)
    add_text(slide, "证据链要求：回答必须显示手册来源、页码或案例编号；无法命中证据时，系统提示人工复核。", Inches(1.32), Inches(5.65), Inches(10.4), Inches(0.2), size=12.5, color=WHITE, align=PP_ALIGN.CENTER)
    footer(slide, "这些数字来自当前项目目录，正式提交前可替换为最终审计数。")


def slide_retrieval(prs):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    add_background(slide, 7)
    add_header(slide, 7, SLIDES[6]["title"], SLIDES[6]["subtitle"])
    left = [("故障文本", "症状、工况、异常描述"), ("故障图片", "视觉模型生成结构化 caption"), ("设备型号", "型号过滤和部件约束")]
    mid = [("BM25", "关键词召回"), ("Vector", "语义召回"), ("KG", "图谱邻居扩展")]
    right = [("重排序", "证据可信度排序"), ("生成", "引用驱动回答"), ("复核", "低置信度人工确认")]
    for col, group in enumerate([left, mid, right]):
        for row, (t, b) in enumerate(group):
            x = Inches(0.85 + col * 4.15)
            y = Inches(2.1 + row * 1.05)
            card(slide, x, y, Inches(3.35), Inches(0.78), t, b, accent=[TEAL, CYAN, AMBER][row])
        if col < 2:
            connector(slide, Inches(4.32 + col * 4.15), Inches(3.2), Inches(4.78 + col * 4.15), Inches(3.2), color=TEAL)
    add_text(slide, "关键亮点：图片不是直接“看图说话”，而是先结构化为可检索标签，再回到手册和案例证据。", Inches(1.2), Inches(5.9), Inches(10.8), Inches(0.32), size=15, color=WHITE, bold=True, align=PP_ALIGN.CENTER)
    footer(slide)


def slide_agents(prs):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    add_background(slide, 8)
    add_header(slide, 8, SLIDES[7]["title"], SLIDES[7]["subtitle"])
    agents = [
        ("检索 Agent", "负责召回证据，不负责编造答案"),
        ("视觉 Agent", "把图片转为缺陷、部件、痕迹标签"),
        ("诊断 Agent", "给出故障原因排序和置信度"),
        ("SOP Agent", "把诊断转成步骤、工具、备件"),
        ("合规 Agent", "检查断电挂牌、PPE、释放能量等"),
        ("更新 Agent", "审核后写入案例库、图谱和索引"),
    ]
    for i, (t, b) in enumerate(agents):
        x = Inches(0.8 + (i % 3) * 4.05)
        y = Inches(2.02 + (i // 3) * 1.42)
        card(slide, x, y, Inches(3.46), Inches(1.0), t, b, accent=[TEAL, CYAN, AMBER, TEAL, RED, GREEN][i])
    add_rect(slide, Inches(1.15), Inches(5.55), Inches(10.9), Inches(0.58), NAVY_2, line=RGBColor(61, 90, 111), transparency=3, radius=True)
    add_text(slide, "编排原则：每个 Agent 都输出结构化结果，后续模块可检查、可引用、可落库。", Inches(1.4), Inches(5.72), Inches(10.35), Inches(0.22), size=13, color=WHITE, align=PP_ALIGN.CENTER)
    footer(slide)


def slide_sop(prs):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    add_background(slide, 9)
    add_header(slide, 9, SLIDES[8]["title"], SLIDES[8]["subtitle"])
    checklist = [
        "断电挂牌 / 防误启动",
        "PPE 与隔离措施",
        "温度、压力、残余能量释放",
        "工具、备件、量具准备",
        "拆检步骤与禁止事项",
        "复装、试运行、验收标准",
    ]
    add_rect(slide, Inches(0.95), Inches(2.0), Inches(5.35), Inches(3.75), PANEL, line=RGBColor(62, 91, 114), transparency=4, radius=True)
    add_text(slide, "合规检查清单", Inches(1.25), Inches(2.28), Inches(4.5), Inches(0.32), size=18, color=WHITE, bold=True)
    bullet_list(slide, checklist, Inches(1.35), Inches(2.85), Inches(4.7), Inches(2.5), size=13.3, color=TEXT, gap=8)
    add_rect(slide, Inches(6.85), Inches(2.0), Inches(5.35), Inches(3.75), PANEL, line=RGBColor(62, 91, 114), transparency=4, radius=True)
    add_text(slide, "输出固定结构", Inches(7.15), Inches(2.28), Inches(4.6), Inches(0.32), size=18, color=WHITE, bold=True)
    bullet_list(slide, ["故障判断", "可能原因", "作业步骤", "风险等级", "引用来源", "是否人工复核"], Inches(7.25), Inches(2.85), Inches(4.5), Inches(2.5), size=13.3, color=TEXT, gap=8)
    footer(slide, "优化判断：这一页要让评委感到机械专业参与了，而不是纯算法展示。")


def slide_loop(prs):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    add_background(slide, 10)
    add_header(slide, 10, SLIDES[9]["title"], SLIDES[9]["subtitle"])
    steps = ["上传案例", "结构抽取", "人工审核", "写入图谱", "更新索引", "反馈修正"]
    x0, y = Inches(0.9), Inches(3.05)
    for i, step in enumerate(steps):
        x = x0 + i * Inches(2.05)
        add_rect(slide, x, y, Inches(1.45), Inches(0.82), PANEL, line=RGBColor(62, 91, 114), transparency=4, radius=True)
        add_text(slide, step, x + Inches(0.08), y + Inches(0.27), Inches(1.28), Inches(0.22), size=11.2, color=WHITE, bold=True, align=PP_ALIGN.CENTER)
        if i < len(steps) - 1:
            connector(slide, x + Inches(1.45), y + Inches(0.41), x + Inches(2.05), y + Inches(0.41))
    card(slide, Inches(1.2), Inches(5.05), Inches(10.8), Inches(0.76), "为什么重要", "知识沉淀闭环能回答“系统上线后怎么越来越懂现场”的问题，是 A1 赛题第四项要求的核心。", accent=TEAL)
    footer(slide)


def slide_evaluation(prs):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    add_background(slide, 11)
    add_header(slide, 11, SLIDES[10]["title"], SLIDES[10]["subtitle"])
    metrics = INPUTS["metrics"]
    rows = [
        ("检索 Recall@5", "104 条问答", metrics["retrieval_recall_at_5"], "证明能找对证据"),
        ("引用覆盖率", "所有生成回答", metrics["citation_coverage"], "证明回答可追溯"),
        ("图片 Top-5 命中", "30 张故障图片", metrics["image_top5_hit"], "证明多模态有效"),
        ("SOP 完整度", "机械队友评分", metrics["sop_completeness"], "证明能指导作业"),
        ("安全漏检率", "合规规则集", metrics["safety_miss_rate"], "证明风险可控"),
    ]
    table = slide.shapes.add_table(len(rows) + 1, 4, Inches(0.75), Inches(1.95), Inches(11.85), Inches(3.95)).table
    widths = [Inches(2.55), Inches(2.75), Inches(2.15), Inches(4.4)]
    for c, width in enumerate(widths):
        table.columns[c].width = width
    headers = ["指标", "评测集", "目标", "答辩证明点"]
    for c, text in enumerate(headers):
        cell = table.cell(0, c)
        cell.text = text
        cell.fill.solid()
        cell.fill.fore_color.rgb = NAVY_2
        for p in cell.text_frame.paragraphs:
            p.font.name = FONT
            p.font.size = Pt(11)
            p.font.color.rgb = WHITE
            p.font.bold = True
    for r, row in enumerate(rows, start=1):
        for c, text in enumerate(row):
            cell = table.cell(r, c)
            cell.text = text
            cell.fill.solid()
            cell.fill.fore_color.rgb = RGBColor(235, 243, 247) if r % 2 else RGBColor(224, 236, 242)
            for p in cell.text_frame.paragraphs:
                p.font.name = FONT
                p.font.size = Pt(9.8)
                p.font.color.rgb = INK
                p.font.bold = c == 2
    status = metrics.get("status", "目标值，等待真实评测替换")
    add_text(slide, f"当前指标状态：{status}", Inches(1.1), Inches(6.15), Inches(11.0), Inches(0.3), size=12.5, color=AMBER, bold=True, align=PP_ALIGN.CENTER)
    footer(slide, "若已完成真实评测，请填写 materials/defense_v2/final_inputs.json 后重建。")


def slide_demo(prs):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    add_background(slide, 12)
    add_header(slide, 12, SLIDES[11]["title"], SLIDES[11]["subtitle"])
    steps = [
        ("1 文本问诊", "输入：泵振动增大、温升异常", "text_query"),
        ("2 图片检索", "上传：轴承/泵体故障图片", "image_search"),
        ("3 SOP 生成", "输出：检查步骤与工具备件", "sop_generation"),
        ("4 合规拦截", "缺少断电挂牌时给出阻断提醒", "compliance_block"),
        ("5 知识更新", "审核案例后进入图谱与索引", "knowledge_update"),
    ]
    screenshots = INPUTS["screenshots"]
    for i, (t, b, key) in enumerate(steps):
        x = Inches(0.75 + i * 2.48)
        add_rect(slide, x, Inches(2.0), Inches(2.12), Inches(2.6), PANEL, line=RGBColor(62, 91, 114), transparency=4, radius=True)
        add_text(slide, t, x + Inches(0.16), Inches(2.24), Inches(1.8), Inches(0.24), size=11.5, color=WHITE, bold=True, align=PP_ALIGN.CENTER)
        add_rect(slide, x + Inches(0.18), Inches(2.68), Inches(1.76), Inches(0.95), NAVY_2, line=RGBColor(76, 105, 126), transparency=5)
        shot_path = resolve_input_path(screenshots[key])
        if not add_fit_image(slide, shot_path, x + Inches(0.2), Inches(2.7), Inches(1.72), Inches(0.91)):
            add_text(slide, "截图占位", x + Inches(0.4), Inches(3.05), Inches(1.3), Inches(0.18), size=9.5, color=MUTED, align=PP_ALIGN.CENTER)
        add_text(slide, b, x + Inches(0.18), Inches(3.88), Inches(1.76), Inches(0.42), size=8.7, color=MUTED, align=PP_ALIGN.CENTER)
    add_text(slide, "等前端重构完成后，优先替换这页的 5 张截图。", Inches(1.25), Inches(5.7), Inches(10.9), Inches(0.35), size=15, color=WHITE, bold=True, align=PP_ALIGN.CENTER)
    footer(slide)


def slide_deploy(prs):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    add_background(slide, 13)
    add_header(slide, 13, SLIDES[12]["title"], SLIDES[12]["subtitle"])
    deploy = INPUTS["deployment"]
    columns = [
        ("已具备", [deploy["runtime"], deploy["database"], "SQLite 本地备份", "图片与评测数据目录"]),
        ("还需固化", ["一键启动脚本", "环境变量模板", "最终评测报告", "演示视频与答辩脚本"]),
        ("提交风险", ["API 额度和稳定性", "截图与实测数据缺失", "中文小字与错字", "部署冷启动时间"]),
    ]
    for i, (t, items) in enumerate(columns):
        x = Inches(0.9 + i * 4.1)
        add_rect(slide, x, Inches(2.02), Inches(3.55), Inches(3.55), PANEL, line=RGBColor(62, 91, 114), transparency=4, radius=True)
        add_text(slide, t, x + Inches(0.25), Inches(2.28), Inches(3.05), Inches(0.3), size=16, color=[GREEN, TEAL, AMBER][i], bold=True, align=PP_ALIGN.CENTER)
        bullet_list(slide, items, x + Inches(0.35), Inches(2.95), Inches(2.9), Inches(1.8), size=11, color=TEXT, gap=8)
    add_text(slide, f"公网演示：{deploy['public_url']} | 兼容路线：{deploy['domestic_path']}", Inches(1.0), Inches(5.98), Inches(11.1), Inches(0.24), size=10.5, color=MUTED, align=PP_ALIGN.CENTER)
    footer(slide, "国产化部署可作为加分路线，但不应压过作品稳定性。")


def slide_close(prs):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    add_background(slide, 14)
    add_header(slide, 14, SLIDES[13]["title"], SLIDES[13]["subtitle"])
    points = [
        ("领域垂直", "只做电机、泵、轴承，避免泛化空泛"),
        ("证据可追溯", "所有答案回到手册页码和案例编号"),
        ("多模态检索", "图片 caption 与文本/型号共同召回"),
        ("机械 SOP", "输出能被机械队友审查的步骤"),
        ("知识闭环", "案例审核后进入图谱和索引"),
        ("量化评测", "用指标对比普通 RAG 与本系统"),
    ]
    for i, (t, b) in enumerate(points):
        x = Inches(0.85 + (i % 3) * 4.05)
        y = Inches(2.0 + (i // 3) * 1.35)
        card(slide, x, y, Inches(3.45), Inches(0.95), t, b, accent=[TEAL, CYAN, AMBER, GREEN, TEAL, CYAN][i])
    add_text(slide, "下一轮 PPT 优化重点：真实截图、真实评测数值、演示视频脚本、答辩追问页。", Inches(1.0), Inches(5.85), Inches(11.3), Inches(0.36), size=15, color=WHITE, bold=True, align=PP_ALIGN.CENTER)
    footer(slide, "结论页要收束为“为什么值得给高奖”的证据链。")


BUILDERS = [
    slide_cover,
    slide_pain,
    slide_requirements,
    slide_flow,
    slide_architecture,
    slide_data,
    slide_retrieval,
    slide_agents,
    slide_sop,
    slide_loop,
    slide_evaluation,
    slide_demo,
    slide_deploy,
    slide_close,
]


def write_audit() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    audit = """# A1 答辩 PPT 第一轮优化审查

## 当前全图版的主要问题

- 文字由图片模型生成，存在错字、伪字、不可编辑风险。
- 第 9、11、12 页信息过密，远看有视觉冲击，近看答辩可信度不足。
- 评测页不能使用模型臆造数据，必须区分“目标指标”和“真实实测”。
- 演示页需要真实系统截图，否则容易被认为只是概念设计。
- 架构页和赛题覆盖页适合被评委追问，必须改成可编辑文本和表格。

## V2 优化策略

- 保留 gpt-image-2 全图版的工业视觉，作为暗化背景。
- 将标题、表格、指标、演示路径、合规清单全部改为可编辑 PPT 元素。
- 数据页使用当前项目真实资产数量：9 份公开 PDF、4 份领域 Markdown、1233 条向量索引、125 条案例、104 条评测问答、30 张故障图片。
- 对尚未完成的真实截图和实测结果明确标注为后续替换，避免答辩时被追问数据来源。
- 输出新的可编辑版本，不覆盖原始全图版。

## 下一轮需要资源

- 前端重构后的 5 张核心截图：文本问诊、图片检索、SOP 生成、合规拦截、案例审核。
- 真实评测结果：Recall@5、图片 Top-5、SOP 完整度、安全漏检率、引用覆盖率。
- 队伍信息、指导老师、学校名称和是否需要匿名。
- 最终提交环境说明：Render/Supabase 是否继续使用，是否补国产化兼容截图。
"""
    AUDIT_MD.write_text(audit, encoding="utf-8")
    README_MD.write_text(
        "# A1 答辩 PPT V2\n\n"
        "本目录保存可编辑版 PPT 的背景图和审查记录。V2 不覆盖 gpt-image-2 全图版，"
        "而是在其视觉基础上重建可校对、可替换、可答辩的关键内容。\n",
        encoding="utf-8",
    )


def build() -> None:
    prepare_backgrounds()
    write_audit()
    prs = Presentation()
    prs.slide_width = WIDE
    prs.slide_height = HIGH
    for builder in BUILDERS:
        builder(prs)
    OUT_PPTX.parent.mkdir(parents=True, exist_ok=True)
    prs.save(OUT_PPTX)
    print(OUT_PPTX)


if __name__ == "__main__":
    build()
