from __future__ import annotations

from pathlib import Path

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_AUTO_SHAPE_TYPE, MSO_CONNECTOR
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.util import Inches, Pt


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "materials" / "A1-maintenance-assistant-defense-final.pptx"
ASSET_DIR = ROOT / "materials" / "defense_final"
SHOT_DIR = ASSET_DIR / "screenshots"

WIDE = Inches(13.333)
HIGH = Inches(7.5)

NAVY = RGBColor(14, 33, 52)
NAVY_2 = RGBColor(20, 49, 74)
STEEL = RGBColor(77, 95, 113)
INK = RGBColor(35, 45, 55)
MUTED = RGBColor(103, 115, 128)
GRID = RGBColor(216, 223, 229)
PAPER = RGBColor(248, 250, 252)
WHITE = RGBColor(255, 255, 255)
GREEN = RGBColor(0, 146, 120)
CYAN = RGBColor(36, 131, 184)
AMBER = RGBColor(219, 143, 43)
RED = RGBColor(190, 62, 62)

FONT = "Microsoft YaHei"
TITLE_FONT = "Microsoft YaHei UI"


def set_run(run, size=18, color=INK, bold=False):
    run.font.name = FONT
    run.font.size = Pt(size)
    run.font.color.rgb = color
    run.font.bold = bold


def add_box(slide, x, y, w, h, fill=WHITE, line=GRID, radius=False):
    shape_type = MSO_AUTO_SHAPE_TYPE.ROUNDED_RECTANGLE if radius else MSO_AUTO_SHAPE_TYPE.RECTANGLE
    shp = slide.shapes.add_shape(shape_type, x, y, w, h)
    shp.fill.solid()
    shp.fill.fore_color.rgb = fill
    shp.line.color.rgb = line
    shp.line.width = Pt(0.9)
    return shp


def add_text(slide, text, x, y, w, h, size=18, color=INK, bold=False, align=PP_ALIGN.LEFT, valign=MSO_ANCHOR.TOP):
    tb = slide.shapes.add_textbox(x, y, w, h)
    tf = tb.text_frame
    tf.clear()
    tf.margin_left = Inches(0.05)
    tf.margin_right = Inches(0.05)
    tf.margin_top = Inches(0.02)
    tf.margin_bottom = Inches(0.02)
    tf.vertical_anchor = valign
    p = tf.paragraphs[0]
    p.alignment = align
    run = p.add_run()
    run.text = text
    set_run(run, size=size, color=color, bold=bold)
    return tb


def add_title(slide, title, kicker="中国软件杯 A1 | 多模态证据链作业系统"):
    add_text(slide, kicker, Inches(0.55), Inches(0.32), Inches(5.5), Inches(0.3), size=10.5, color=GREEN, bold=True)
    add_text(slide, title, Inches(0.55), Inches(0.62), Inches(8.2), Inches(0.62), size=26, color=NAVY, bold=True)
    slide.shapes.add_shape(MSO_AUTO_SHAPE_TYPE.RECTANGLE, Inches(0.55), Inches(1.28), Inches(1.0), Inches(0.045)).fill.solid()
    slide.shapes[-1].fill.fore_color.rgb = GREEN


def add_footer(slide, idx):
    add_text(slide, "A1-MAKG：面向设备检修的多模态证据链作业辅助系统", Inches(0.55), Inches(7.08), Inches(4.5), Inches(0.22), size=8.5, color=MUTED)
    add_text(slide, f"{idx:02d}", Inches(12.25), Inches(7.05), Inches(0.55), Inches(0.22), size=9, color=MUTED, align=PP_ALIGN.RIGHT)


def bullet_list(slide, items, x, y, w, h, size=14.5, color=INK, gap=0.07):
    tb = slide.shapes.add_textbox(x, y, w, h)
    tf = tb.text_frame
    tf.clear()
    tf.word_wrap = True
    tf.margin_left = Inches(0.02)
    tf.margin_right = Inches(0.02)
    tf.margin_top = Inches(0)
    for i, item in enumerate(items):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.text = item
        p.level = 0
        p.space_after = Pt(gap * 72)
        p.font.name = FONT
        p.font.size = Pt(size)
        p.font.color.rgb = color
    return tb


def metric_card(slide, label, value, x, y, w, h, accent=GREEN, note=None):
    card = add_box(slide, x, y, w, h, fill=WHITE, line=RGBColor(218, 226, 232), radius=True)
    slide.shapes.add_shape(MSO_AUTO_SHAPE_TYPE.RECTANGLE, x, y, Inches(0.08), h).fill.solid()
    slide.shapes[-1].fill.fore_color.rgb = accent
    add_text(slide, value, x + Inches(0.18), y + Inches(0.16), w - Inches(0.3), Inches(0.35), size=24, color=NAVY, bold=True)
    add_text(slide, label, x + Inches(0.18), y + Inches(0.58), w - Inches(0.3), Inches(0.24), size=10.5, color=MUTED, bold=True)
    if note:
        add_text(slide, note, x + Inches(0.18), y + Inches(0.9), w - Inches(0.3), Inches(0.24), size=8.8, color=MUTED)
    return card


def add_pill(slide, text, x, y, w, color=GREEN):
    shp = add_box(slide, x, y, w, Inches(0.33), fill=RGBColor(234, 247, 244), line=RGBColor(196, 230, 222), radius=True)
    add_text(slide, text, x + Inches(0.07), y + Inches(0.08), w - Inches(0.14), Inches(0.16), size=9.5, color=color, bold=True, align=PP_ALIGN.CENTER)
    return shp


def add_image(slide, path, x, y, w, h, border=True):
    if not path.exists():
        add_box(slide, x, y, w, h, fill=RGBColor(238, 242, 246), line=GRID, radius=True)
        add_text(slide, f"截图缺失\n{path.name}", x, y + h / 2 - Inches(0.2), w, Inches(0.5), size=13, color=MUTED, align=PP_ALIGN.CENTER)
        return None
    pic = slide.shapes.add_picture(str(path), x, y, width=w, height=h)
    if border:
        box = add_box(slide, x, y, w, h, fill=RGBColor(255, 255, 255), line=RGBColor(198, 208, 218), radius=False)
        slide.shapes._spTree.remove(box._element)
        slide.shapes._spTree.insert(2, box._element)
    return pic


def add_placeholder(slide, label, x, y, w, h, subtitle="前端重构后替换"):
    add_box(slide, x, y, w, h, fill=RGBColor(239, 244, 248), line=RGBColor(183, 197, 210), radius=True)
    # Use deterministic line decorations instead of fake screenshots at concept stage.
    for i in range(4):
        yy = y + Inches(0.32 + i * 0.42)
        slide.shapes.add_shape(MSO_AUTO_SHAPE_TYPE.RECTANGLE, x + Inches(0.32), yy, w - Inches(0.64), Inches(0.06)).fill.solid()
        slide.shapes[-1].fill.fore_color.rgb = RGBColor(210, 220, 229)
    add_box(slide, x + Inches(0.42), y + h - Inches(1.06), w - Inches(0.84), Inches(0.66), fill=WHITE, line=RGBColor(206, 217, 226), radius=True)
    add_text(slide, label, x + Inches(0.56), y + h - Inches(0.91), w - Inches(1.12), Inches(0.2), size=12.5, color=NAVY, bold=True, align=PP_ALIGN.CENTER)
    add_text(slide, subtitle, x + Inches(0.56), y + h - Inches(0.58), w - Inches(1.12), Inches(0.17), size=8.8, color=MUTED, align=PP_ALIGN.CENTER)


def add_connector(slide, x1, y1, x2, y2, color=RGBColor(130, 148, 166), width=1.4):
    conn = slide.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, x1, y1, x2, y2)
    conn.line.color.rgb = color
    conn.line.width = Pt(width)
    return conn


def add_bar_chart(slide, title, labels, values, x, y, w, h, color=GREEN, max_value=100):
    add_text(slide, title, x, y, w, Inches(0.3), size=12, color=NAVY, bold=True)
    y0 = y + Inches(0.48)
    row_h = h / len(labels)
    for i, (label, val) in enumerate(zip(labels, values)):
        yy = y0 + row_h * i
        add_text(slide, label, x, yy, Inches(1.25), Inches(0.23), size=8.8, color=INK)
        slide.shapes.add_shape(MSO_AUTO_SHAPE_TYPE.RECTANGLE, x + Inches(1.35), yy + Inches(0.06), w - Inches(2.05), Inches(0.12)).fill.solid()
        slide.shapes[-1].fill.fore_color.rgb = RGBColor(226, 232, 238)
        bw = (w - Inches(2.05)) * min(max(val, 0), max_value) / max_value
        slide.shapes.add_shape(MSO_AUTO_SHAPE_TYPE.RECTANGLE, x + Inches(1.35), yy + Inches(0.06), bw, Inches(0.12)).fill.solid()
        slide.shapes[-1].fill.fore_color.rgb = color
        add_text(slide, f"{val:g}%", x + w - Inches(0.6), yy, Inches(0.52), Inches(0.22), size=8.8, color=INK, bold=True, align=PP_ALIGN.RIGHT)


def new_slide(prs, title, idx):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    bg = slide.background.fill
    bg.solid()
    bg.fore_color.rgb = PAPER
    add_title(slide, title)
    add_footer(slide, idx)
    return slide


def cover(prs):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    slide.background.fill.solid()
    slide.background.fill.fore_color.rgb = NAVY
    add_box(slide, Inches(0.0), Inches(0.0), Inches(13.333), Inches(7.5), fill=NAVY, line=NAVY)
    add_box(slide, Inches(7.7), Inches(0.0), Inches(5.65), Inches(7.5), fill=NAVY_2, line=NAVY_2)
    add_placeholder(slide, "系统首页 / 问诊工作台截图", Inches(7.25), Inches(1.1), Inches(5.35), Inches(3.3), subtitle="前端重构完成后替换")
    add_box(slide, Inches(7.25), Inches(4.62), Inches(5.35), Inches(1.35), fill=RGBColor(23, 58, 82), line=RGBColor(46, 92, 116), radius=True)
    add_text(slide, "计划完成态答辩演示", Inches(0.65), Inches(0.58), Inches(3.0), Inches(0.25), size=10, color=RGBColor(129, 221, 201), bold=True)
    add_text(slide, "设备检修知识检索\n与作业辅助系统", Inches(0.62), Inches(1.25), Inches(6.2), Inches(1.45), size=34, color=WHITE, bold=True)
    add_text(slide, "多模态大模型 · 手册证据 · SOP 合规 · 知识沉淀", Inches(0.68), Inches(3.03), Inches(6.2), Inches(0.35), size=16, color=RGBColor(207, 226, 237))
    bullet_list(
        slide,
        ["面向电机、离心泵、轴承三类典型设备", "从故障输入到标准作业、合规校验、案例沉淀形成闭环", "公网可演示，数据、评测和提交包均可审计"],
        Inches(0.72),
        Inches(3.9),
        Inches(5.7),
        Inches(1.5),
        size=13.5,
        color=RGBColor(225, 235, 242),
    )
    add_pill(slide, "中国软件杯 A1", Inches(0.72), Inches(6.23), Inches(1.45), color=WHITE)
    add_pill(slide, "PC Web + 云模型 + Supabase", Inches(2.35), Inches(6.23), Inches(2.25), color=WHITE)
    add_text(slide, "01", Inches(12.2), Inches(7.06), Inches(0.6), Inches(0.22), size=9, color=RGBColor(170, 191, 205), align=PP_ALIGN.RIGHT)


def slide_problem(prs):
    slide = new_slide(prs, "从检修现场痛点出发", 2)
    add_text(slide, "优秀技术答辩的第一步不是展示模型，而是证明问题真实、场景足够窄、价值链路清楚。", Inches(0.58), Inches(1.55), Inches(7.2), Inches(0.32), size=13, color=MUTED)
    items = [
        ("知识分散", "手册、图纸、工单、老师傅经验互相割裂", GREEN),
        ("检索低效", "一线人员需要在长文档和历史案例中反复查找", CYAN),
        ("作业不规范", "断电挂牌、PPE、泄压降温等安全项容易遗漏", AMBER),
        ("经验难传承", "现场经验没有审核闭环，难以进入可复用知识库", RED),
    ]
    for i, (title, desc, color) in enumerate(items):
        x = Inches(0.75 + (i % 2) * 3.3)
        y = Inches(2.15 + (i // 2) * 1.65)
        add_box(slide, x, y, Inches(3.0), Inches(1.16), fill=WHITE, line=RGBColor(219, 227, 233), radius=True)
        add_text(slide, f"{i+1}", x + Inches(0.2), y + Inches(0.23), Inches(0.36), Inches(0.35), size=18, color=color, bold=True)
        add_text(slide, title, x + Inches(0.68), y + Inches(0.2), Inches(1.8), Inches(0.3), size=15, color=NAVY, bold=True)
        add_text(slide, desc, x + Inches(0.68), y + Inches(0.58), Inches(2.1), Inches(0.4), size=10.5, color=MUTED)
    add_box(slide, Inches(7.7), Inches(1.55), Inches(4.75), Inches(4.5), fill=RGBColor(239, 245, 248), line=RGBColor(210, 222, 230), radius=True)
    add_text(slide, "我们的切入边界", Inches(8.05), Inches(1.92), Inches(2.6), Inches(0.32), size=15.5, color=NAVY, bold=True)
    bullet_list(
        slide,
        ["只做电机、离心泵、轴承三类设备", "核心不是聊天，而是检修作业辅助", "所有输出都必须绑定证据、流程和安全项", "用审核和评测证明可落地"],
        Inches(8.05),
        Inches(2.52),
        Inches(3.75),
        Inches(1.5),
        size=13,
    )
    add_text(slide, "定位句", Inches(8.05), Inches(4.5), Inches(0.8), Inches(0.24), size=9.5, color=GREEN, bold=True)
    add_text(slide, "不是“维修问答机器人”，而是“可追溯、可审核、可评测的检修作业系统”。", Inches(8.05), Inches(4.86), Inches(3.95), Inches(0.72), size=16, color=NAVY, bold=True)


def slide_requirements(prs):
    slide = new_slide(prs, "A1 要求逐项覆盖", 3)
    rows = [
        ("Web/App 可视化", "PC Web 工作台，公网可演示", "已完成"),
        ("云端/本地大模型", "Codex/SpatialAI + OpenRouter，保留本地规则兜底", "已完成"),
        ("多模态知识检索", "文本、型号、图片 caption、手册、案例、图谱混合召回", "已完成"),
        ("标准化作业指引", "诊断、原因、SOP、安全确认、验收标准", "已完成"),
        ("知识沉淀更新", "案例上传、人工审核、图谱和索引更新", "已完成"),
        ("人工修正模型输出", "反馈记录进入后续问诊参考", "已完成"),
    ]
    x0, y0 = Inches(0.75), Inches(1.65)
    colw = [Inches(2.55), Inches(6.25), Inches(1.25)]
    add_box(slide, x0, y0, sum(colw), Inches(0.44), fill=NAVY, line=NAVY, radius=False)
    for i, head in enumerate(["赛题要求", "系统实现", "状态"]):
        add_text(slide, head, x0 + sum(colw[:i]) + Inches(0.13), y0 + Inches(0.12), colw[i] - Inches(0.2), Inches(0.17), size=10.5, color=WHITE, bold=True)
    for r, row in enumerate(rows):
        y = y0 + Inches(0.44 + 0.62 * r)
        fill = WHITE if r % 2 == 0 else RGBColor(242, 246, 249)
        add_box(slide, x0, y, sum(colw), Inches(0.62), fill=fill, line=RGBColor(224, 231, 237))
        for c, val in enumerate(row):
            color = GREEN if c == 2 else INK
            add_text(slide, val, x0 + sum(colw[:c]) + Inches(0.13), y + Inches(0.18), colw[c] - Inches(0.2), Inches(0.18), size=10.2 if c != 1 else 9.8, color=color, bold=(c == 0 or c == 2))
    add_box(slide, Inches(10.15), Inches(1.65), Inches(2.25), Inches(4.15), fill=RGBColor(236, 247, 244), line=RGBColor(197, 230, 222), radius=True)
    add_text(slide, "答辩表达重点", Inches(10.45), Inches(2.02), Inches(1.55), Inches(0.28), size=13, color=NAVY, bold=True)
    bullet_list(slide, ["覆盖不是堆功能", "每个要求都有真实链路", "评测和审核是可信度来源"], Inches(10.45), Inches(2.58), Inches(1.55), Inches(1.8), size=11.5, color=INK)
    add_text(slide, "一句话：A1 的四个动词“检索、指引、校验、更新”都已经落到系统闭环。", Inches(10.45), Inches(4.78), Inches(1.55), Inches(0.55), size=11, color=GREEN, bold=True)


def slide_workflow(prs):
    slide = new_slide(prs, "完整检修闭环", 4)
    steps = [
        ("输入", "故障文本 / 图片 / 型号"),
        ("检索", "手册 + 案例 + 图谱"),
        ("判断", "原因分析与风险等级"),
        ("SOP", "步骤、工具、备件"),
        ("合规", "LOTO、PPE、验收"),
        ("沉淀", "审核后更新知识库"),
    ]
    y = Inches(2.2)
    for i, (name, desc) in enumerate(steps):
        x = Inches(0.65 + i * 2.05)
        add_box(slide, x, y, Inches(1.55), Inches(1.05), fill=WHITE, line=RGBColor(209, 222, 231), radius=True)
        add_text(slide, name, x, y + Inches(0.2), Inches(1.55), Inches(0.28), size=16, color=NAVY, bold=True, align=PP_ALIGN.CENTER)
        add_text(slide, desc, x + Inches(0.12), y + Inches(0.58), Inches(1.31), Inches(0.28), size=8.9, color=MUTED, align=PP_ALIGN.CENTER)
        if i < len(steps) - 1:
            add_connector(slide, x + Inches(1.55), y + Inches(0.52), x + Inches(1.95), y + Inches(0.52), color=GREEN, width=2)
    add_box(slide, Inches(0.85), Inches(4.05), Inches(11.6), Inches(1.28), fill=RGBColor(238, 245, 249), line=RGBColor(213, 224, 231), radius=True)
    add_text(slide, "闭环价值", Inches(1.18), Inches(4.35), Inches(1.1), Inches(0.28), size=13, color=GREEN, bold=True)
    add_text(slide, "检修人员得到的不是一段泛泛回答，而是“证据 → 诊断 → 作业 → 安全 → 验收 → 知识更新”的可执行链路。", Inches(2.18), Inches(4.32), Inches(9.55), Inches(0.34), size=17, color=NAVY, bold=True)
    bullet_list(slide, ["适合现场演示：一次输入能看到引用、步骤、风险和合规项", "适合答辩追问：任何结论都可以回到手册、案例和审核记录", "适合落地扩展：增加设备类型只需补手册、案例和图谱模板"], Inches(1.18), Inches(5.07), Inches(10.7), Inches(0.72), size=11.2, color=INK)


def slide_system(prs):
    slide = new_slide(prs, "公网系统与核心界面", 5)
    add_placeholder(slide, "问诊结果界面截图", Inches(0.72), Inches(1.58), Inches(7.55), Inches(4.65), subtitle="展示诊断、SOP、引用与合规项")
    metric_card(slide, "公网入口", "Render", Inches(8.55), Inches(1.65), Inches(1.75), Inches(1.05), accent=GREEN, note="前后端同域")
    metric_card(slide, "数据持久化", "Supabase", Inches(10.55), Inches(1.65), Inches(1.75), Inches(1.05), accent=CYAN, note="案例/反馈")
    metric_card(slide, "模型路线", "Codex", Inches(8.55), Inches(2.95), Inches(1.75), Inches(1.05), accent=AMBER, note="文本/视觉")
    metric_card(slide, "检索向量", "Qwen", Inches(10.55), Inches(2.95), Inches(1.75), Inches(1.05), accent=GREEN, note="OpenRouter")
    add_box(slide, Inches(8.55), Inches(4.38), Inches(3.75), Inches(1.5), fill=WHITE, line=RGBColor(218, 226, 232), radius=True)
    add_text(slide, "现场演示策略", Inches(8.85), Inches(4.68), Inches(2.4), Inches(0.26), size=13, color=NAVY, bold=True)
    bullet_list(slide, ["先跑文本问诊", "再展示图片与知识图谱", "最后打开评测面板收束"], Inches(8.85), Inches(5.05), Inches(2.9), Inches(0.65), size=10.8, color=INK)


def slide_data(prs):
    slide = new_slide(prs, "数据资产与证据可追溯", 6)
    metrics = [
        ("文档资料", "13", "公开手册/规范/案例"),
        ("手册 chunk", "1108", "保留来源 URL 与页码"),
        ("案例库", "125", "机械审核包覆盖"),
        ("评测题", "104", "用于 Recall 与 SOP 评分"),
        ("向量索引", "1233", "OpenRouter embedding"),
        ("图片样本", "50", "计划完成态多模态集"),
    ]
    for i, (label, val, note) in enumerate(metrics):
        x = Inches(0.75 + (i % 3) * 3.05)
        y = Inches(1.65 + (i // 3) * 1.35)
        metric_card(slide, label, val, x, y, Inches(2.65), Inches(1.08), accent=[GREEN, CYAN, AMBER, GREEN, CYAN, RED][i], note=note)
    add_box(slide, Inches(10.1), Inches(1.65), Inches(2.25), Inches(2.5), fill=RGBColor(238, 245, 249), line=RGBColor(215, 226, 233), radius=True)
    add_text(slide, "证据策略", Inches(10.42), Inches(2.0), Inches(1.5), Inches(0.28), size=13, color=NAVY, bold=True)
    bullet_list(slide, ["回答必须带引用", "手册页码可回查", "案例有审核状态", "评测题可重复运行"], Inches(10.42), Inches(2.5), Inches(1.45), Inches(1.1), size=10.2, color=INK)
    add_text(slide, "答辩防守点", Inches(0.75), Inches(4.92), Inches(1.2), Inches(0.26), size=11, color=GREEN, bold=True)
    add_text(slide, "不把公开 PDF 放入提交包；提交包只保留来源清单、页码、许可说明与结构化索引，避免版权和密钥风险。", Inches(1.75), Inches(4.9), Inches(9.5), Inches(0.34), size=14.2, color=NAVY, bold=True)
    add_text(slide, "完成态假设：图片样本与多模态评测已补齐；正式提交前应以实际跑数替换。", Inches(1.75), Inches(5.35), Inches(8.6), Inches(0.25), size=10.2, color=MUTED)


def slide_multimodal(prs):
    slide = new_slide(prs, "多模态混合检索", 7)
    lanes = [
        ("故障文本", "分词 / 语义"),
        ("故障图片", "VLM caption"),
        ("设备型号", "型号过滤"),
        ("知识图谱", "邻居扩展"),
    ]
    for i, (name, desc) in enumerate(lanes):
        x = Inches(0.82)
        y = Inches(1.7 + i * 0.88)
        add_box(slide, x, y, Inches(2.1), Inches(0.55), fill=WHITE, line=RGBColor(214, 225, 232), radius=True)
        add_text(slide, name, x + Inches(0.16), y + Inches(0.11), Inches(0.9), Inches(0.2), size=12, color=NAVY, bold=True)
        add_text(slide, desc, x + Inches(1.05), y + Inches(0.14), Inches(0.85), Inches(0.2), size=8.8, color=MUTED)
        add_connector(slide, x + Inches(2.1), y + Inches(0.27), Inches(4.3), Inches(3.08), color=RGBColor(143, 160, 176), width=1)
    add_box(slide, Inches(4.1), Inches(2.45), Inches(2.35), Inches(1.2), fill=RGBColor(232, 247, 244), line=RGBColor(178, 224, 215), radius=True)
    add_text(slide, "检索中枢", Inches(4.1), Inches(2.75), Inches(2.35), Inches(0.28), size=17, color=NAVY, bold=True, align=PP_ALIGN.CENTER)
    add_text(slide, "BM25 + 向量 + 案例 + 图谱", Inches(4.1), Inches(3.16), Inches(2.35), Inches(0.18), size=9, color=GREEN, bold=True, align=PP_ALIGN.CENTER)
    outputs = [
        ("手册证据", "页码、来源 URL"),
        ("相似案例", "故障原因与措施"),
        ("SOP 指引", "作业步骤和验收"),
    ]
    for i, (name, desc) in enumerate(outputs):
        x = Inches(8.0)
        y = Inches(2.0 + i * 1.05)
        add_connector(slide, Inches(6.45), Inches(3.05), x, y + Inches(0.27), color=GREEN, width=1.5)
        add_box(slide, x, y, Inches(2.6), Inches(0.62), fill=WHITE, line=RGBColor(214, 225, 232), radius=True)
        add_text(slide, name, x + Inches(0.18), y + Inches(0.13), Inches(1.0), Inches(0.2), size=12, color=NAVY, bold=True)
        add_text(slide, desc, x + Inches(1.15), y + Inches(0.16), Inches(1.1), Inches(0.18), size=8.8, color=MUTED)
    add_box(slide, Inches(0.85), Inches(5.55), Inches(10.9), Inches(0.72), fill=WHITE, line=RGBColor(222, 230, 236), radius=True)
    add_text(slide, "关键设计：图片不直接让模型“猜答案”，而是先生成结构化故障描述，再进入统一检索链路；这样可以保留证据、降低幻觉。", Inches(1.12), Inches(5.77), Inches(10.2), Inches(0.24), size=13.5, color=NAVY, bold=True)


def slide_agents(prs):
    slide = new_slide(prs, "多 Agent 协同不是概念堆叠", 8)
    agents = [
        ("检索 Agent", "召回手册/案例/图谱"),
        ("视觉 Agent", "图片 caption 与标签"),
        ("诊断 Agent", "故障原因与风险"),
        ("SOP Agent", "步骤、工具、备件"),
        ("合规 Agent", "安全项和禁止项"),
        ("更新 Agent", "审核后写入知识库"),
    ]
    center_x, center_y = Inches(5.3), Inches(3.15)
    add_box(slide, center_x, center_y, Inches(2.4), Inches(1.05), fill=NAVY, line=NAVY, radius=True)
    add_text(slide, "检修任务", center_x, center_y + Inches(0.22), Inches(2.4), Inches(0.28), size=17, color=WHITE, bold=True, align=PP_ALIGN.CENTER)
    add_text(slide, "证据驱动的作业生成", center_x, center_y + Inches(0.62), Inches(2.4), Inches(0.18), size=8.8, color=RGBColor(196, 224, 236), align=PP_ALIGN.CENTER)
    positions = [
        (Inches(1.0), Inches(1.62)),
        (Inches(5.1), Inches(1.42)),
        (Inches(9.1), Inches(1.62)),
        (Inches(1.0), Inches(4.82)),
        (Inches(5.1), Inches(5.02)),
        (Inches(9.1), Inches(4.82)),
    ]
    for (name, desc), (x, y) in zip(agents, positions):
        add_box(slide, x, y, Inches(2.55), Inches(0.78), fill=WHITE, line=RGBColor(214, 225, 232), radius=True)
        add_text(slide, name, x + Inches(0.15), y + Inches(0.12), Inches(1.4), Inches(0.2), size=11.5, color=NAVY, bold=True)
        add_text(slide, desc, x + Inches(0.15), y + Inches(0.43), Inches(2.1), Inches(0.18), size=8.8, color=MUTED)
        add_connector(slide, x + Inches(1.25), y + Inches(0.39), center_x + Inches(1.2), center_y + Inches(0.52), color=RGBColor(147, 162, 178), width=1)
    add_text(slide, "答辩讲法：Agent 的边界对应 A1 功能要求，每一步都有可展示的输入、证据和输出。", Inches(1.05), Inches(6.25), Inches(10.7), Inches(0.28), size=13, color=GREEN, bold=True)


def slide_sop(prs):
    slide = new_slide(prs, "标准作业与合规校验", 9)
    add_placeholder(slide, "SOP 与合规校验结果截图", Inches(0.72), Inches(1.55), Inches(5.55), Inches(4.95), subtitle="前端重构后替换")
    add_box(slide, Inches(6.65), Inches(1.55), Inches(5.75), Inches(4.95), fill=WHITE, line=RGBColor(218, 226, 232), radius=True)
    add_text(slide, "固定输出结构", Inches(7.0), Inches(1.9), Inches(1.5), Inches(0.28), size=14, color=NAVY, bold=True)
    sop_items = ["故障判断", "可能原因", "安全确认", "工具备件", "步骤化 SOP", "合规提醒", "验收标准", "引用来源"]
    for i, item in enumerate(sop_items):
        x = Inches(7.0 + (i % 4) * 1.25)
        y = Inches(2.45 + (i // 4) * 0.68)
        add_pill(slide, item, x, y, Inches(1.05), color=GREEN if i < 4 else CYAN)
    add_text(slide, "安全底线", Inches(7.0), Inches(4.15), Inches(1.1), Inches(0.26), size=12, color=RED, bold=True)
    bullet_list(slide, ["断电、验电、挂牌、上锁", "PPE、防误启动、泄压降温", "复装后空载/带载试运行", "未覆盖安全项会被标记为需补充"], Inches(7.0), Inches(4.55), Inches(4.4), Inches(1.0), size=11.2, color=INK)


def slide_knowledge(prs):
    slide = new_slide(prs, "知识沉淀：从一次检修到可复用资产", 10)
    add_placeholder(slide, "知识图谱界面截图", Inches(7.1), Inches(1.55), Inches(5.1), Inches(4.55), subtitle="展示设备-部件-故障-措施关系")
    steps = [
        ("一线上传", "故障现象、原因、处置"),
        ("待审核", "未通过前不污染知识库"),
        ("审核通过", "机械人员确认可复用"),
        ("写入图谱", "设备-部件-故障-措施"),
        ("更新索引", "后续问诊可召回"),
    ]
    for i, (name, desc) in enumerate(steps):
        x = Inches(0.85)
        y = Inches(1.65 + i * 0.88)
        add_box(slide, x, y, Inches(4.85), Inches(0.55), fill=WHITE if i % 2 == 0 else RGBColor(242, 247, 250), line=RGBColor(216, 226, 233), radius=True)
        add_text(slide, f"{i+1}. {name}", x + Inches(0.18), y + Inches(0.11), Inches(1.35), Inches(0.2), size=11.5, color=NAVY, bold=True)
        add_text(slide, desc, x + Inches(1.65), y + Inches(0.13), Inches(2.7), Inches(0.2), size=9.5, color=MUTED)
    add_box(slide, Inches(0.85), Inches(6.12), Inches(11.35), Inches(0.45), fill=RGBColor(235, 247, 244), line=RGBColor(198, 230, 222), radius=True)
    add_text(slide, "关键点：系统允许知识增长，但必须经过审核门槛，避免错误经验被放大。", Inches(1.1), Inches(6.25), Inches(10.5), Inches(0.16), size=12, color=GREEN, bold=True)


def slide_eval(prs):
    slide = new_slide(prs, "量化评测：证明系统更稳", 11)
    add_bar_chart(slide, "Recall@5", ["无 RAG", "文本 RAG", "多模态 RAG", "本系统"], [32, 74, 84, 92], Inches(0.85), Inches(1.62), Inches(4.0), Inches(2.0), color=GREEN)
    add_bar_chart(slide, "SOP 完整度", ["无 RAG", "文本 RAG", "多模态 RAG", "本系统"], [45, 78, 86, 94], Inches(0.85), Inches(4.05), Inches(4.0), Inches(2.0), color=CYAN)
    add_bar_chart(slide, "幻觉率（越低越好）", ["无 RAG", "文本 RAG", "多模态 RAG", "本系统"], [28, 13, 8, 3], Inches(5.2), Inches(1.62), Inches(4.0), Inches(2.0), color=RED)
    add_bar_chart(slide, "安全漏检率（越低越好）", ["无 RAG", "文本 RAG", "多模态 RAG", "本系统"], [24, 11, 7, 2], Inches(5.2), Inches(4.05), Inches(4.0), Inches(2.0), color=AMBER)
    add_box(slide, Inches(9.65), Inches(1.62), Inches(2.55), Inches(4.4), fill=WHITE, line=RGBColor(218, 226, 232), radius=True)
    add_text(slide, "评测口径", Inches(9.98), Inches(1.95), Inches(1.4), Inches(0.28), size=13, color=NAVY, bold=True)
    bullet_list(slide, ["104 条审核评测题", "50 张多模态图片样本", "四组消融对比", "引用、SOP、安全项分开计分"], Inches(9.98), Inches(2.46), Inches(1.75), Inches(1.3), size=10.2, color=INK)
    add_text(slide, "完成态数据用于答辩版展示；正式提交前用评测脚本重跑并替换。", Inches(9.98), Inches(5.05), Inches(1.75), Inches(0.45), size=9.2, color=MUTED)


def slide_demo(prs):
    slide = new_slide(prs, "答辩演示路线", 12)
    demos = [
        ("01", "文本问诊", "电机振动 + 轴承温升"),
        ("02", "图片检索", "轴承剥落/泵体泄漏图片"),
        ("03", "SOP 合规", "生成作业步骤并拦截危险操作"),
        ("04", "案例审核", "上传案例并写入图谱"),
        ("05", "评测面板", "展示四组对比和 ready gate"),
    ]
    for i, (num, name, desc) in enumerate(demos):
        x = Inches(0.82 + i * 2.42)
        y = Inches(2.05)
        add_box(slide, x, y, Inches(2.0), Inches(2.65), fill=WHITE, line=RGBColor(213, 224, 232), radius=True)
        add_text(slide, num, x + Inches(0.18), y + Inches(0.22), Inches(0.5), Inches(0.28), size=15, color=GREEN, bold=True)
        add_text(slide, name, x + Inches(0.18), y + Inches(0.72), Inches(1.35), Inches(0.28), size=14, color=NAVY, bold=True)
        add_text(slide, desc, x + Inches(0.18), y + Inches(1.18), Inches(1.55), Inches(0.55), size=10.3, color=MUTED)
        add_text(slide, "现场只讲结果与证据", x + Inches(0.18), y + Inches(2.1), Inches(1.5), Inches(0.2), size=8.5, color=GREEN, bold=True)
    add_text(slide, "节奏建议：先跑 1 个真实问诊，再展示 3 张截图证明闭环，最后用评测面板收束。", Inches(1.05), Inches(5.65), Inches(10.9), Inches(0.35), size=16, color=NAVY, bold=True)


def slide_deploy(prs):
    slide = new_slide(prs, "部署、提交与安全", 13)
    add_placeholder(slide, "资源与模型配置界面截图", Inches(7.0), Inches(1.55), Inches(5.1), Inches(4.6), subtitle="后续替换为最终前端页面")
    left = [
        ("公网演示", "Render 托管 FastAPI + 前端静态资源"),
        ("数据持久化", "Supabase 保存案例、审核状态、人工反馈"),
        ("模型配置", "双路线：当前高质量路线 + 国产模型路线"),
        ("提交安全", "自动排除 .env、数据库、原始 PDF、缓存"),
        ("审计脚本", "final_validation ready=true，forbidden=0"),
    ]
    for i, (name, desc) in enumerate(left):
        y = Inches(1.62 + i * 0.76)
        add_box(slide, Inches(0.85), y, Inches(5.45), Inches(0.52), fill=WHITE, line=RGBColor(216, 226, 233), radius=True)
        add_text(slide, name, Inches(1.05), y + Inches(0.12), Inches(1.1), Inches(0.18), size=10.8, color=NAVY, bold=True)
        add_text(slide, desc, Inches(2.08), y + Inches(0.12), Inches(3.8), Inches(0.18), size=9.6, color=MUTED)
    add_box(slide, Inches(0.85), Inches(5.75), Inches(5.45), Inches(0.62), fill=RGBColor(236, 247, 244), line=RGBColor(198, 230, 222), radius=True)
    add_text(slide, "国产化说明：LoongArch/Galaxy Kylin 作为部署适配路线保留；主演示不让外部环境阻塞系统闭环。", Inches(1.08), Inches(5.94), Inches(5.0), Inches(0.18), size=10.5, color=GREEN, bold=True)


def slide_close(prs):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    slide.background.fill.solid()
    slide.background.fill.fore_color.rgb = NAVY
    add_text(slide, "核心创新点", Inches(0.7), Inches(0.58), Inches(3.0), Inches(0.32), size=18, color=RGBColor(154, 224, 209), bold=True)
    add_text(slide, "让多模态大模型真正进入\n设备检修作业闭环", Inches(0.68), Inches(1.25), Inches(6.8), Inches(1.2), size=32, color=WHITE, bold=True)
    innovations = [
        ("领域垂直", "电机、泵、轴承"),
        ("证据可追溯", "手册页码与案例编号"),
        ("多模态检索", "文本、图片、型号、图谱"),
        ("机械 SOP", "步骤、工具、备件、验收"),
        ("知识闭环", "上传、审核、更新、复用"),
        ("量化评测", "四组对比与 ready gate"),
    ]
    for i, (name, desc) in enumerate(innovations):
        x = Inches(0.85 + (i % 3) * 3.45)
        y = Inches(3.15 + (i // 3) * 1.08)
        add_box(slide, x, y, Inches(2.85), Inches(0.72), fill=RGBColor(23, 58, 82), line=RGBColor(48, 95, 119), radius=True)
        add_text(slide, name, x + Inches(0.18), y + Inches(0.12), Inches(0.95), Inches(0.2), size=12, color=WHITE, bold=True)
        add_text(slide, desc, x + Inches(1.08), y + Inches(0.15), Inches(1.38), Inches(0.18), size=9.4, color=RGBColor(196, 224, 236))
    add_text(slide, "Q & A", Inches(0.82), Inches(6.42), Inches(1.5), Inches(0.32), size=20, color=RGBColor(154, 224, 209), bold=True)
    add_text(slide, "谢谢各位老师", Inches(9.55), Inches(6.42), Inches(2.2), Inches(0.28), size=16, color=WHITE, bold=True, align=PP_ALIGN.RIGHT)
    add_text(slide, "14", Inches(12.2), Inches(7.06), Inches(0.6), Inches(0.22), size=9, color=RGBColor(170, 191, 205), align=PP_ALIGN.RIGHT)


def build() -> Path:
    prs = Presentation()
    prs.slide_width = WIDE
    prs.slide_height = HIGH

    cover(prs)
    slide_problem(prs)
    slide_requirements(prs)
    slide_workflow(prs)
    slide_system(prs)
    slide_data(prs)
    slide_multimodal(prs)
    slide_agents(prs)
    slide_sop(prs)
    slide_knowledge(prs)
    slide_eval(prs)
    slide_demo(prs)
    slide_deploy(prs)
    slide_close(prs)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    prs.save(OUT)
    return OUT


if __name__ == "__main__":
    print(build())
