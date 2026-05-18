from __future__ import annotations

import json
from pathlib import Path

from PIL import Image
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_AUTO_SHAPE_TYPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Inches, Pt


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "materials" / "A1-maintenance-assistant-defense-gpt-image-2.pptx"
OUTPUT = ROOT / "materials" / "A1-maintenance-assistant-defense-gpt-image-2-polished.pptx"
NOTES = ROOT / "materials" / "defense_image_deck" / "polish_notes.md"
TEAM_INFO = ROOT / "materials" / "defense_image_deck" / "team_info.json"
REAL_SCREENSHOT_DIR = ROOT / "materials" / "defense_image_deck" / "real_screenshots"
EVAL_SUMMARY = ROOT / "materials" / "defense_image_deck" / "evaluation_summary.json"
MECHANICAL_REVIEW_SUMMARY = ROOT / "materials" / "defense_image_deck" / "mechanical_review_summary.json"
DEPLOYMENT_SUMMARY = ROOT / "materials" / "defense_image_deck" / "deployment_summary.json"

FONT = "Microsoft YaHei"
TITLE_FONT = "Microsoft YaHei UI"

NAVY = RGBColor(8, 23, 38)
NAVY_2 = RGBColor(13, 36, 56)
WHITE = RGBColor(255, 255, 255)
MUTED = RGBColor(175, 190, 204)
TEAL = RGBColor(28, 190, 168)
AMBER = RGBColor(235, 167, 58)
RED = RGBColor(222, 82, 82)


SLIDE_COPY = [
    {
        "title": "A1-MAKG：面向设备检修的多模态证据链作业辅助系统",
        "subtitle": "多模态输入 -> 手册证据 -> SOP 合规 -> 知识沉淀",
        "point": "一句话：面向电机-泵-轴承检修，把多模态故障信息转成可追溯、可执行、可更新的作业辅助。",
        "tag": "国一定位：不是聊天机器人",
    },
    {
        "title": "检修现场的四个核心痛点",
        "subtitle": "知识分散、检索低效、作业不规范、经验难传承",
        "point": "答辩时把问题讲成“执行链路缺失”：资料要能找准，步骤要能执行，经验要能沉淀。",
        "tag": "行业价值",
    },
    {
        "title": "A1 赛题要求逐项覆盖",
        "subtitle": "可视化界面、多模态检索、标准作业指引、知识更新",
        "point": "先证明不偏题：每个赛题要求都有系统模块、数据证据和演示动作对应。",
        "tag": "赛题贴合",
        "source_note": "赛题依据：第十五届中国软件杯相关通知与 A1 赛题发布页；最终以官网/报名系统为准。",
    },
    {
        "title": "不是维修问答，而是作业闭环",
        "subtitle": "输入 -> 检索 -> 判断 -> SOP -> 合规 -> 沉淀",
        "point": "核心链路要讲清楚：系统不是给一句答案，而是把检修任务推进到可复核的作业流程。",
        "tag": "产品定位",
    },
    {
        "title": "系统架构：轻量部署 + 模型编排",
        "subtitle": "Web 工作台、FastAPI、混合检索、知识库、云端模型、Supabase",
        "point": "架构答辩重点：重型模型不上本地，应用、索引和数据闭环可部署、可恢复、可演示。",
        "tag": "工程可落地",
    },
    {
        "title": "数据资产与证据追溯",
        "subtitle": "手册、案例、图片、评测问答、向量索引全部保留来源",
        "point": "评委追问时要强调：回答必须绑定来源、页码或案例编号，低置信度触发人工复核。",
        "tag": "可信 AI",
    },
    {
        "title": "多模态混合检索",
        "subtitle": "文本 + 故障图片 + 设备型号 + 图谱邻居 + 重排序",
        "point": "图片不是直接看图编答案，而是先结构化成缺陷标签，再回到手册和案例证据。",
        "tag": "技术亮点",
    },
    {
        "title": "多 Agent 协同",
        "subtitle": "检索、视觉、诊断、SOP、合规、更新分工协作",
        "point": "把大模型拆成多个可控岗位：每个 Agent 输出结构化结果，后续模块可以检查和落库。",
        "tag": "可控生成",
    },
    {
        "title": "标准作业与安全合规",
        "subtitle": "断电挂牌、PPE、能量释放、工具备件、验收标准",
        "point": "这一页要体现机械专业深度：真正加分的是 SOP 和安全拦截，而不是模型回答流畅。",
        "tag": "机械专业优势",
        "point_y": 5.88,
    },
    {
        "title": "知识沉淀闭环",
        "subtitle": "上传案例 -> 人工审核 -> 写入图谱 -> 更新索引 -> 反馈修正",
        "point": "A1 第四项要求的核心：系统上线后如何持续吸收一线经验，而不是一次性知识库。",
        "tag": "持续更新",
    },
    {
        "title": "量化评测：证明系统有效",
        "subtitle": "Recall@5、引用覆盖、图片命中、SOP 完整度、幻觉率",
        "point": "不要伪造实测值；最终版需用真实实验替换目标值，并展示与普通 RAG 的对比。",
        "tag": "待补真实数据",
        "accent": AMBER,
    },
    {
        "title": "答辩演示路线",
        "subtitle": "文本问诊、图片检索、SOP 生成、合规拦截、案例更新",
        "point": "演示应控制在 5 分钟内：每一步只证明一个能力，避免现场临时自由问答失控。",
        "tag": "待补真实截图",
        "accent": AMBER,
    },
    {
        "title": "部署与提交准备",
        "subtitle": "Render 在线演示、Supabase 持久化、SQLite 备份、评测报告",
        "point": "提交前重点不是堆功能，而是保证冷启动、数据恢复、截图、视频和说明书全部可复现。",
        "tag": "交付可信",
    },
    {
        "title": "核心创新点",
        "subtitle": "领域垂直、证据可追溯、多模态检索、机械 SOP、知识闭环、量化评测",
        "point": "收束成一句话：我们把通用多模态大模型落到设备检修的证据链、作业链和知识链。",
        "tag": "Q&A 收束",
    },
]

REAL_SCREENSHOTS = [
    ("文本问诊", REAL_SCREENSHOT_DIR / "01_text_query.png"),
    ("图片检索", REAL_SCREENSHOT_DIR / "02_image_search.png"),
    ("SOP 生成", REAL_SCREENSHOT_DIR / "03_sop_generation.png"),
    ("合规校验", REAL_SCREENSHOT_DIR / "04_compliance_check.png"),
    ("案例审核", REAL_SCREENSHOT_DIR / "05_case_review_update.png"),
]


def add_rect(slide, x, y, w, h, color: RGBColor, transparency: int = 0, radius: bool = False):
    shape_type = MSO_AUTO_SHAPE_TYPE.ROUNDED_RECTANGLE if radius else MSO_AUTO_SHAPE_TYPE.RECTANGLE
    shp = slide.shapes.add_shape(shape_type, x, y, w, h)
    shp.fill.solid()
    shp.fill.fore_color.rgb = color
    shp.fill.transparency = transparency
    shp.line.fill.background()
    return shp


def add_text(slide, text, x, y, w, h, *, size=12, color=WHITE, bold=False, align=PP_ALIGN.LEFT, valign=MSO_ANCHOR.TOP, font=FONT):
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
    run.font.name = font
    run.font.size = Pt(size)
    run.font.color.rgb = color
    run.font.bold = bold
    return box


def resolve_path(value: str) -> Path:
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
    frame_ratio = w / h
    image_ratio = iw / ih
    if image_ratio >= frame_ratio:
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


def add_header(slide, idx: int, spec: dict) -> None:
    if idx == 1:
        add_rect(slide, Inches(0.6), Inches(6.42), Inches(12.15), Inches(0.48), NAVY, transparency=12, radius=True)
        add_text(slide, spec["point"], Inches(0.88), Inches(6.55), Inches(10.2), Inches(0.18), size=10.7, color=WHITE, bold=True)
        add_text(slide, spec["tag"], Inches(11.05), Inches(6.55), Inches(1.3), Inches(0.18), size=9.5, color=TEAL, bold=True, align=PP_ALIGN.RIGHT)
        return

    add_rect(slide, Inches(0.24), Inches(0.14), Inches(12.86), Inches(0.86), NAVY, transparency=0)
    add_rect(slide, Inches(0.24), Inches(0.98), Inches(12.86), Inches(0.035), spec.get("accent", TEAL), transparency=0)
    add_text(slide, f"{idx:02d}", Inches(0.58), Inches(0.4), Inches(0.45), Inches(0.18), size=9.5, color=TEAL, bold=True)
    add_text(slide, spec["title"], Inches(1.08), Inches(0.29), Inches(7.2), Inches(0.25), size=16.5, color=WHITE, bold=True, font=TITLE_FONT)
    add_text(slide, spec["subtitle"], Inches(1.1), Inches(0.63), Inches(8.45), Inches(0.16), size=8.8, color=MUTED)
    add_rect(slide, Inches(10.9), Inches(0.37), Inches(1.45), Inches(0.28), spec.get("accent", TEAL), transparency=0, radius=True)
    add_text(slide, spec["tag"], Inches(10.96), Inches(0.435), Inches(1.32), Inches(0.1), size=7.3, color=WHITE, bold=True, align=PP_ALIGN.CENTER)


def add_point(slide, idx: int, spec: dict) -> None:
    if idx == 1:
        return
    y = Inches(spec.get("point_y", 6.52))
    add_rect(slide, Inches(0.58), y, Inches(12.18), Inches(0.48), NAVY_2, transparency=8, radius=True)
    add_text(slide, "答辩口径", Inches(0.86), y + Inches(0.14), Inches(0.85), Inches(0.16), size=8.5, color=spec.get("accent", TEAL), bold=True)
    add_text(slide, spec["point"], Inches(1.72), y + Inches(0.13), Inches(10.58), Inches(0.18), size=10.2, color=WHITE)


def add_source_note(slide, spec: dict) -> None:
    source_note = spec.get("source_note")
    if not source_note:
        return
    add_text(slide, source_note, Inches(0.72), Inches(1.08), Inches(11.8), Inches(0.13), size=7.3, color=MUTED, align=PP_ALIGN.CENTER)


def load_team_info() -> dict | None:
    if not TEAM_INFO.exists():
        return None
    data = json.loads(TEAM_INFO.read_text(encoding="utf-8-sig"))
    has_cover_info = any(
        [
            data.get("school"),
            data.get("college"),
            data.get("team_name"),
            data.get("advisor_name") if data.get("advisor_display") else "",
        ]
    )
    if not has_cover_info:
        return None
    return data


def add_cover_team_info(slide, team_info: dict | None) -> None:
    if not team_info:
        return
    org_parts = [team_info.get("school"), team_info.get("college"), team_info.get("team_name")]
    org_line = " / ".join(part for part in org_parts if part)

    mode = team_info.get("member_display_mode", "code")
    member_labels = []
    if mode != "hidden":
        for member in team_info.get("members", []):
            if mode == "name" and member.get("name"):
                label = member["name"]
            else:
                label = member.get("code") or member.get("name")
            if label and member.get("role"):
                label = f"{label}（{member['role']}）"
            if label:
                member_labels.append(label)

    advisor = ""
    if team_info.get("advisor_display") and team_info.get("advisor_name"):
        advisor = f"指导老师：{team_info['advisor_name']}"
        if team_info.get("advisor_title"):
            advisor += f"（{team_info['advisor_title']}）"

    lines = [line for line in [org_line, "；".join(member_labels), advisor, team_info.get("footer_note")] if line]
    if not lines:
        return

    add_rect(slide, Inches(0.72), Inches(5.78), Inches(11.9), Inches(0.42), NAVY_2, transparency=14, radius=True)
    add_text(slide, " | ".join(lines), Inches(0.95), Inches(5.91), Inches(11.4), Inches(0.13), size=8.5, color=WHITE, bold=True, align=PP_ALIGN.CENTER)


def append_real_screenshot_slide(prs: Presentation) -> None:
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    add_rect(slide, 0, 0, prs.slide_width, prs.slide_height, NAVY, transparency=0)
    add_text(slide, "15", Inches(0.58), Inches(0.42), Inches(0.45), Inches(0.18), size=9.5, color=TEAL, bold=True)
    add_text(slide, "真实系统演示截图", Inches(1.08), Inches(0.3), Inches(5.2), Inches(0.28), size=18, color=WHITE, bold=True, font=TITLE_FONT)
    add_text(slide, "用于替换概念图：文本问诊、图片检索、SOP、合规校验、案例审核", Inches(1.1), Inches(0.67), Inches(8.2), Inches(0.18), size=9.2, color=MUTED)
    add_rect(slide, Inches(0.24), Inches(0.98), Inches(12.86), Inches(0.035), TEAL, transparency=0)

    positions = [
        (Inches(0.68), Inches(1.35), Inches(3.95), Inches(2.1)),
        (Inches(4.78), Inches(1.35), Inches(3.95), Inches(2.1)),
        (Inches(8.88), Inches(1.35), Inches(3.95), Inches(2.1)),
        (Inches(2.28), Inches(4.15), Inches(3.95), Inches(2.1)),
        (Inches(7.08), Inches(4.15), Inches(3.95), Inches(2.1)),
    ]
    for (label, path), (x, y, w, h) in zip(REAL_SCREENSHOTS, positions):
        add_rect(slide, x, y, w, h, NAVY_2, transparency=0, radius=True)
        ok = add_fit_image(slide, path, x + Inches(0.08), y + Inches(0.16), w - Inches(0.16), h - Inches(0.46))
        if not ok:
            add_text(slide, "截图待补", x, y + Inches(0.85), w, Inches(0.24), size=12, color=MUTED, align=PP_ALIGN.CENTER)
        add_text(slide, label, x + Inches(0.12), y + h - Inches(0.24), w - Inches(0.24), Inches(0.12), size=8.5, color=TEAL, bold=True, align=PP_ALIGN.CENTER)
    add_text(slide, "说明：本页截图来自本地可运行系统 127.0.0.1:8051，最终答辩前可替换为公网部署截图。", Inches(0.9), Inches(6.82), Inches(11.6), Inches(0.18), size=8.8, color=MUTED, align=PP_ALIGN.CENTER)


def load_eval_summary() -> dict | None:
    if not EVAL_SUMMARY.exists():
        return None
    return json.loads(EVAL_SUMMARY.read_text(encoding="utf-8-sig"))


def pct(value: float | int) -> str:
    return f"{float(value) * 100:.0f}%"


def append_eval_result_slide(prs: Presentation) -> None:
    summary = load_eval_summary()
    if not summary:
        return
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    add_rect(slide, 0, 0, prs.slide_width, prs.slide_height, NAVY, transparency=0)
    add_text(slide, "16", Inches(0.58), Inches(0.42), Inches(0.45), Inches(0.18), size=9.5, color=AMBER, bold=True)
    add_text(slide, "当前自动评测结果", Inches(1.08), Inches(0.3), Inches(5.2), Inches(0.28), size=18, color=WHITE, bold=True, font=TITLE_FONT)
    add_text(
        slide,
        f"{summary['question_count']}/{summary['question_total']} 道已审核题 · 口径：{summary['review_basis']} · 生成时间：{summary['generated_at']}",
        Inches(1.1),
        Inches(0.67),
        Inches(9.2),
        Inches(0.18),
        size=9.2,
        color=MUTED,
    )
    add_rect(slide, Inches(0.24), Inches(0.98), Inches(12.86), Inches(0.035), AMBER, transparency=0)

    headers = ["组别", "Recall@5", "引用覆盖", "SOP 完整", "幻觉率", "安全漏检"]
    x0, y0 = Inches(0.8), Inches(1.55)
    col_w = [Inches(2.25), Inches(1.7), Inches(1.7), Inches(1.7), Inches(1.7), Inches(1.7)]
    row_h = Inches(0.56)
    for col, head in enumerate(headers):
        x = x0 + sum(col_w[:col])
        add_rect(slide, x, y0, col_w[col], row_h, NAVY_2, transparency=0)
        add_text(slide, head, x + Inches(0.05), y0 + Inches(0.19), col_w[col] - Inches(0.1), Inches(0.1), size=8.8, color=TEAL, bold=True, align=PP_ALIGN.CENTER)

    for row, item in enumerate(summary["benchmarks"], start=1):
        y = y0 + row_h * row
        fill = RGBColor(18, 45, 67) if row % 2 else RGBColor(14, 38, 58)
        values = [
            item["name"],
            pct(item["recall_at_5"]),
            pct(item["citation_coverage"]),
            pct(item["sop_score"]),
            pct(item["hallucination_rate"]),
            pct(item["safety_miss_rate"]),
        ]
        for col, value in enumerate(values):
            x = x0 + sum(col_w[:col])
            add_rect(slide, x, y, col_w[col], row_h, fill, transparency=0)
            color = WHITE
            if col in {4, 5} and value == "0%":
                color = TEAL
            if item["mode"] == "full_system" and col == 0:
                color = AMBER
            add_text(slide, value, x + Inches(0.05), y + Inches(0.19), col_w[col] - Inches(0.1), Inches(0.1), size=9.6, color=color, bold=item["mode"] == "full_system", align=PP_ALIGN.CENTER)

    add_rect(slide, Inches(0.95), Inches(4.65), Inches(11.4), Inches(1.08), NAVY_2, transparency=0, radius=True)
    add_text(slide, "答辩口径", Inches(1.25), Inches(4.92), Inches(1.0), Inches(0.15), size=9, color=AMBER, bold=True)
    add_text(
        slide,
        "这页只表达“系统具备自动评测闭环和当前跑数”。由于当前评测题来自项目内已审核集，正式答辩前仍建议机械队友抽样复核 SOP 完整度，避免过度宣称。",
        Inches(2.2),
        Inches(4.84),
        Inches(9.65),
        Inches(0.32),
        size=11.2,
        color=WHITE,
    )
    add_text(slide, "待补：机械专业人工评分签名/代号、抽样复核记录、最终公网环境跑数截图。", Inches(1.0), Inches(6.62), Inches(11.2), Inches(0.18), size=9.3, color=MUTED, align=PP_ALIGN.CENTER)


def load_mechanical_review_summary() -> dict | None:
    if not MECHANICAL_REVIEW_SUMMARY.exists():
        return None
    return json.loads(MECHANICAL_REVIEW_SUMMARY.read_text(encoding="utf-8-sig"))


def append_mechanical_review_slide(prs: Presentation) -> None:
    summary = load_mechanical_review_summary()
    if not summary:
        return
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    add_rect(slide, 0, 0, prs.slide_width, prs.slide_height, NAVY, transparency=0)
    add_text(slide, "17", Inches(0.58), Inches(0.42), Inches(0.45), Inches(0.18), size=9.5, color=TEAL, bold=True)
    add_text(slide, "机械专业审核摘要", Inches(1.08), Inches(0.3), Inches(5.2), Inches(0.28), size=18, color=WHITE, bold=True, font=TITLE_FONT)
    add_text(slide, "reviewer 使用代号，不展示真实姓名；用于证明案例和评测题不是未审核演示数据", Inches(1.1), Inches(0.67), Inches(9.8), Inches(0.18), size=9.2, color=MUTED)
    add_rect(slide, Inches(0.24), Inches(0.98), Inches(12.86), Inches(0.035), TEAL, transparency=0)

    cards = [
        ("案例审核", f"{summary['cases_approved']}/{summary['cases_total']}", "maintenance_cases approved"),
        ("评测题审核", f"{summary['eval_approved']}/{summary['eval_total']}", "eval_questions approved"),
        ("审核代号", ", ".join(sorted(set(summary["case_reviewers"] + summary["eval_reviewers"]))), "不使用真实姓名"),
    ]
    for i, (title, value, note) in enumerate(cards):
        x = Inches(0.82 + i * 4.15)
        add_rect(slide, x, Inches(1.55), Inches(3.6), Inches(1.12), NAVY_2, transparency=0, radius=True)
        add_text(slide, value, x + Inches(0.18), Inches(1.82), Inches(3.22), Inches(0.22), size=18, color=WHITE, bold=True, align=PP_ALIGN.CENTER)
        add_text(slide, title, x + Inches(0.18), Inches(2.22), Inches(3.22), Inches(0.13), size=8.8, color=TEAL, bold=True, align=PP_ALIGN.CENTER)
        add_text(slide, note, x + Inches(0.18), Inches(2.43), Inches(3.22), Inches(0.11), size=7.5, color=MUTED, align=PP_ALIGN.CENTER)

    score_rows = [
        ("故障机理准确性", summary["mechanical_accuracy_avg"]),
        ("SOP 完整度", summary["sop_completeness_avg"]),
        ("安全合规", summary["safety_avg"]),
    ]
    add_text(slide, "案例评分均值（5 分制）", Inches(0.9), Inches(3.18), Inches(3.0), Inches(0.18), size=11.5, color=WHITE, bold=True)
    for i, (label, score) in enumerate(score_rows):
        y = Inches(3.62 + i * 0.62)
        add_text(slide, label, Inches(1.05), y + Inches(0.08), Inches(2.0), Inches(0.15), size=9.6, color=MUTED)
        add_rect(slide, Inches(3.0), y + Inches(0.07), Inches(5.2), Inches(0.16), RGBColor(34, 58, 78), transparency=0, radius=True)
        add_rect(slide, Inches(3.0), y + Inches(0.07), Inches(5.2 * min(float(score) / 5.0, 1.0)), Inches(0.16), TEAL if score >= 4 else AMBER, transparency=0, radius=True)
        add_text(slide, f"{score}/5", Inches(8.4), y + Inches(0.02), Inches(0.8), Inches(0.16), size=9.5, color=WHITE, bold=True)

    add_rect(slide, Inches(0.95), Inches(5.75), Inches(11.4), Inches(0.72), NAVY_2, transparency=0, radius=True)
    add_text(slide, "答辩口径", Inches(1.25), Inches(5.98), Inches(1.0), Inches(0.15), size=9, color=TEAL, bold=True)
    add_text(slide, "机械审核已覆盖案例库和评测题，但分数不是满分，说明我们保留了复核意见；最终 SOP 仍应按机械队友意见继续打磨。", Inches(2.2), Inches(5.9), Inches(9.65), Inches(0.25), size=11, color=WHITE)
    add_text(slide, "待补：如果学校允许，最终版可在说明书中写明机械队友职责；PPT 继续使用代号保护隐私。", Inches(1.0), Inches(6.72), Inches(11.2), Inches(0.16), size=8.8, color=MUTED, align=PP_ALIGN.CENTER)


def load_deployment_summary() -> dict | None:
    if not DEPLOYMENT_SUMMARY.exists():
        return None
    return json.loads(DEPLOYMENT_SUMMARY.read_text(encoding="utf-8-sig"))


def append_deployment_slide(prs: Presentation) -> None:
    summary = load_deployment_summary()
    if not summary:
        return
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    add_rect(slide, 0, 0, prs.slide_width, prs.slide_height, NAVY, transparency=0)
    add_text(slide, "18", Inches(0.58), Inches(0.42), Inches(0.45), Inches(0.18), size=9.5, color=TEAL, bold=True)
    add_text(slide, "公网部署验证", Inches(1.08), Inches(0.3), Inches(5.2), Inches(0.28), size=18, color=WHITE, bold=True, font=TITLE_FONT)
    add_text(slide, "Render 在线服务 + Supabase 持久化；用于答辩前稳定性和可访问性证明", Inches(1.1), Inches(0.67), Inches(9.8), Inches(0.18), size=9.2, color=MUTED)
    add_rect(slide, Inches(0.24), Inches(0.98), Inches(12.86), Inches(0.035), TEAL, transparency=0)

    home = resolve_path(summary["home_screenshot"])
    add_rect(slide, Inches(0.75), Inches(1.35), Inches(5.75), Inches(3.5), NAVY_2, transparency=0, radius=True)
    add_fit_image(slide, home, Inches(0.92), Inches(1.67), Inches(5.4), Inches(2.72))
    add_text(slide, "公网首页实测截图", Inches(0.95), Inches(4.55), Inches(5.35), Inches(0.12), size=8.5, color=TEAL, bold=True, align=PP_ALIGN.CENTER)

    add_rect(slide, Inches(6.85), Inches(1.35), Inches(5.75), Inches(3.5), NAVY_2, transparency=0, radius=True)
    add_text(slide, "健康检查结构化返回", Inches(7.15), Inches(1.72), Inches(3.0), Inches(0.2), size=13.2, color=WHITE, bold=True)
    rows = [
        ("status", summary["health_status"]),
        ("model mode", summary["mode"]),
        ("Supabase", "enabled" if summary["supabase_enabled"] else "disabled"),
        ("schema / prefix", f"{summary['supabase_schema']} / {summary['supabase_table_prefix']}"),
        ("SQLite backup", summary["db"]),
    ]
    for i, (label, value) in enumerate(rows):
        y = Inches(2.12 + i * 0.42)
        add_text(slide, label, Inches(7.18), y, Inches(1.45), Inches(0.14), size=8.3, color=MUTED)
        add_text(slide, value, Inches(8.78), y, Inches(3.38), Inches(0.14), size=8.5, color=WHITE, bold=(i == 0))
    add_rect(slide, Inches(7.12), Inches(4.24), Inches(5.1), Inches(0.35), TEAL, transparency=0, radius=True)
    add_text(slide, "公网可访问 + 持久化可恢复 + 本地备份可兜底", Inches(7.22), Inches(4.35), Inches(4.9), Inches(0.1), size=8.4, color=WHITE, bold=True, align=PP_ALIGN.CENTER)

    host = summary["public_url"].replace("https://", "").replace("http://", "")
    status_cards = [
        ("公网地址", host),
        ("健康检查", "/api/health -> ok"),
        ("正式答辩动作", "提前预热 + 本地备用"),
    ]
    for i, (label, value) in enumerate(status_cards):
        x = Inches(0.95 + i * 4.15)
        add_rect(slide, x, Inches(5.25), Inches(3.65), Inches(0.72), NAVY_2, transparency=0, radius=True)
        add_text(slide, value, x + Inches(0.14), Inches(5.44), Inches(3.37), Inches(0.12), size=8.6, color=WHITE, bold=True, align=PP_ALIGN.CENTER)
        add_text(slide, label, x + Inches(0.14), Inches(5.71), Inches(3.37), Inches(0.1), size=7.2, color=MUTED, align=PP_ALIGN.CENTER)
    add_text(slide, f"检查时间：{summary['checked_at']}；这页证明当前在线服务可访问，最终提交前仍需复测冷启动、检索、生成、上传、审核闭环。", Inches(0.95), Inches(6.58), Inches(11.5), Inches(0.18), size=8.6, color=MUTED, align=PP_ALIGN.CENTER)


def build() -> Path:
    prs = Presentation(SOURCE)
    if len(prs.slides) != len(SLIDE_COPY):
        raise RuntimeError(f"Expected {len(SLIDE_COPY)} slides, got {len(prs.slides)}")

    team_info = load_team_info()
    for idx, slide in enumerate(prs.slides, start=1):
        spec = SLIDE_COPY[idx - 1]
        add_header(slide, idx, spec)
        add_point(slide, idx, spec)
        add_source_note(slide, spec)
        if idx == 1:
            add_cover_team_info(slide, team_info)
    append_real_screenshot_slide(prs)
    append_eval_result_slide(prs)
    append_mechanical_review_slide(prs)
    append_deployment_slide(prs)

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    prs.save(OUTPUT)
    write_notes()
    return OUTPUT


def write_notes() -> None:
    lines = [
        "# 基于 gpt-image-2 全图版的润色记录",
        "",
        f"- 源文件：`{SOURCE}`",
        f"- 输出文件：`{OUTPUT}`",
        "- 处理方式：保留每页原始 gpt-image-2 整图，在其上叠加可编辑标题校正层和答辩口径层。",
        "- 原文件不覆盖；如需继续重跑某页图片，应先修改 `materials/defense_image_deck/gpt_image_2_prompts.jsonl`。",
        "- 已追加第 15 页真实系统演示截图，截图来自本地可运行系统 `127.0.0.1:8051`。",
        "- 已追加第 16 页当前自动评测结果，数据来自 `POST /api/eval/run-comparison?max_questions=0`，评测集为 104 道已审核题；该页明确标注为自动评测，正式答辩前仍需机械队友抽样复核。",
        "- 已追加第 17 页机械专业审核摘要，数据来自 `data/review` 下的审核 CSV，reviewer 仅使用代号。",
        "- 已追加第 18 页公网部署验证，数据来自 Render 服务健康检查与公网截图；正式提交前建议再跑一次冷启动验证。",
        "",
        "## 逐页润色点",
        "",
    ]
    for idx, spec in enumerate(SLIDE_COPY, start=1):
        lines.extend(
            [
                f"### {idx:02d}. {spec['title']}",
                "",
                f"- 校正标题：{spec['title']}",
                f"- 页内口径：{spec['point']}",
                f"- 标签：{spec['tag']}",
            ]
        )
        if spec.get("source_note"):
            lines.append(f"- 来源说明：{spec['source_note']}")
        lines.append("")
    NOTES.write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    print(build())
