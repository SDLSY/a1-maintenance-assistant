from __future__ import annotations

import argparse
import base64
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
import os
from pathlib import Path
import time
import urllib.error
import urllib.request

from pptx import Presentation
from pptx.util import Inches


ROOT = Path(__file__).resolve().parents[1]
DECK_DIR = ROOT / "materials" / "defense_image_deck"
SLIDE_DIR = DECK_DIR / "slides"
DESIGN_MD = DECK_DIR / "slide_designs.md"
PROMPTS_JSONL = DECK_DIR / "gpt_image_2_prompts.jsonl"
PROMPTS_JSON = DECK_DIR / "gpt_image_2_prompts.json"
OUTPUT_PPTX = ROOT / "materials" / "A1-maintenance-assistant-defense-gpt-image-2.pptx"


GLOBAL_STYLE = (
    "16:9 full-slide Chinese defense presentation page, mature industrial engineering style, "
    "quiet premium consulting layout, no neon cyberpunk, no generic AI poster look, "
    "deep navy and steel gray base, restrained teal accent, small amount of amber/red for risk, "
    "large legible Chinese text only, strong hierarchy, clean grid, realistic maintenance context, "
    "all content, text, diagrams and layout are rendered inside this single image"
)


SLIDES = [
    {
        "no": 1,
        "file": "slide01_cover.png",
        "title": "封面",
        "goal": "建立国赛答辩的第一印象：这是一个面向真实设备检修作业的系统，不是通用 AI 聊天工具。",
        "layout": "左侧 55% 放大标题和副标题；右侧 45% 是工业检修台场景，包含电机、泵、轴承、手册和检修工单；底部放赛题和关键词。",
        "visual": "深蓝背景，右侧工业设备照片级质感但不过暗；标题区留足呼吸感；青绿色细线做技术感，不使用发光球、赛博网格或夸张机器人。",
        "text": ["A1-MAKG：面向设备检修的多模态证据链作业辅助系统", "多模态大模型 · 手册证据 · SOP 合规 · 知识沉淀", "中国软件杯 A1 赛题"],
        "prompt": (
            f"{GLOBAL_STYLE}. Create slide 1 cover. Main title exactly: A1-MAKG：面向设备检修的多模态证据链作业辅助系统. "
            "Subtitle exactly: 多模态大模型 · 手册证据 · SOP 合规 · 知识沉淀. "
            "Footer text exactly: 中国软件杯 A1 赛题. "
            "Composition: left side has large title and subtitle, right side shows a realistic industrial maintenance workbench with an electric motor, centrifugal pump, bearing parts, service manual pages and a work order. "
            "Style: sober national competition defense deck, premium industrial consulting, no logos, no watermark, no extra text, no random English, no garbled characters."
        ),
    },
    {
        "no": 2,
        "file": "slide02_pain_points.png",
        "title": "检修现场痛点",
        "goal": "说明为什么该赛题有真实行业价值，把问题压缩成四个评委能立刻理解的痛点。",
        "layout": "页面左上为标题；中部四个大卡片横向排列；背景是低透明度的检修资料、工具、零部件和工单。",
        "visual": "白底或浅灰底，四个痛点卡片用不同小色条区分；图标使用线性工业图标；避免大段文字。",
        "text": ["检修现场的四个痛点", "知识分散", "检索低效", "作业不规范", "经验难传承"],
        "prompt": (
            f"{GLOBAL_STYLE}. Create slide 2 about maintenance pain points. Title exactly: 检修现场的四个痛点. "
            "Four large cards with exact labels: 知识分散, 检索低效, 作业不规范, 经验难传承. "
            "Background: subtle maintenance manuals, work orders, tools and mechanical parts on a clean workbench. "
            "Use simple industrial line icons, one per card. Text must be large and readable. No paragraphs, no extra words, no logos, no watermark, no random English."
        ),
    },
    {
        "no": 3,
        "file": "slide03_requirements.png",
        "title": "A1 要求覆盖",
        "goal": "用一页证明作品没有偏题，A1 功能要求全部能在系统中找到对应实现。",
        "layout": "三列表格：赛题要求、系统实现、完成状态。右侧加一个小结论章。",
        "visual": "咨询风表格，深蓝表头，状态列使用绿色勾选；整体像审计表而不是宣传海报。",
        "text": ["A1 要求逐项覆盖", "可视化界面", "多模态检索", "标准作业指引", "知识沉淀更新", "全部覆盖"],
        "prompt": (
            f"{GLOBAL_STYLE}. Create slide 3 as a clean audit-style table. Title exactly: A1 要求逐项覆盖. "
            "Use a three-column table feeling: 赛题要求, 系统实现, 状态. "
            "Show four key rows with large labels: 可视化界面, 多模态检索, 标准作业指引, 知识沉淀更新. "
            "Right-side conclusion stamp text exactly: 全部覆盖. "
            "Professional table layout, green check marks, deep navy header, no tiny text, no extra text, no logo, no watermark."
        ),
    },
    {
        "no": 4,
        "file": "slide04_position_flow.png",
        "title": "产品定位与闭环流程",
        "goal": "把作品从聊天机器人中区分出来，强调它是检修作业辅助系统。",
        "layout": "一条从左到右的六步流程，底部一句定位语；两侧有设备和作业单视觉元素。",
        "visual": "流程节点清楚，每个节点一个图标；箭头克制；流程在页面中轴线上，留白充足。",
        "text": ["不是聊天机器人，是检修作业系统", "输入", "检索", "判断", "SOP", "合规", "沉淀"],
        "prompt": (
            f"{GLOBAL_STYLE}. Create slide 4. Main title exactly: 不是聊天机器人，是检修作业系统. "
            "Center flow diagram from left to right with six nodes exactly: 输入, 检索, 判断, SOP, 合规, 沉淀. "
            "Add visual hints of equipment model input, maintenance manual evidence, standardized work order and knowledge graph. "
            "Clean engineering workflow, large readable Chinese labels, no extra text, no logos, no watermark."
        ),
    },
    {
        "no": 5,
        "file": "slide05_architecture.png",
        "title": "系统架构",
        "goal": "展示技术方案清晰、模块边界明确，便于评委追问时展开。",
        "layout": "五层架构图从上到下排列：Web、FastAPI、混合检索、知识库、云端模型；右侧小模块显示 Supabase 和部署。",
        "visual": "层级图不要复杂连线；每层横向模块，颜色从浅到深；右侧用窄栏表示公网部署和数据持久化。",
        "text": ["系统架构", "Web 工作台", "FastAPI 编排", "混合检索", "SQLite 知识库", "云端模型", "Supabase"],
        "prompt": (
            f"{GLOBAL_STYLE}. Create slide 5 architecture diagram. Title exactly: 系统架构. "
            "Use five horizontal layers with exact labels: Web 工作台, FastAPI 编排, 混合检索, SQLite 知识库, 云端模型. "
            "Add a right-side slim module labeled Supabase. "
            "Professional system architecture, restrained navy gray teal palette, clear hierarchy, no tiny code, no extra text, no logos, no watermark."
        ),
    },
    {
        "no": 6,
        "file": "slide06_data_evidence.png",
        "title": "数据资产与证据追溯",
        "goal": "证明系统不是空壳，有文档、案例、评测题和向量索引支撑。",
        "layout": "六个 KPI 卡片组成 3x2 网格，底部一条证据链说明。",
        "visual": "数字要大，单位清楚；背景可放淡化的手册页、轴承剖面、泵结构图。",
        "text": ["数据资产与证据追溯", "13 份文档", "1108 条 chunk", "125 条案例", "104 条评测", "1233 条向量", "50 张图片"],
        "prompt": (
            f"{GLOBAL_STYLE}. Create slide 6 KPI evidence page. Title exactly: 数据资产与证据追溯. "
            "Six KPI cards with exact text: 13 份文档, 1108 条 chunk, 125 条案例, 104 条评测, 1233 条向量, 50 张图片. "
            "Bottom statement exactly: 回答必须绑定来源、页码、案例编号. "
            "Subtle background of manuals, bearing diagram and pump structure. Large numbers, clear Chinese, no extra text, no logos, no watermark."
        ),
    },
    {
        "no": 7,
        "file": "slide07_multimodal_retrieval.png",
        "title": "多模态混合检索",
        "goal": "解释图片、文本、型号和图谱如何统一进入检索，降低幻觉。",
        "layout": "左侧四个输入卡片，中间检索中枢，右侧三个输出卡片；箭头从左到右。",
        "visual": "信息流图；图片输入处用故障照片缩略图的抽象占位；检索中枢用机械核心或雷达状图形。",
        "text": ["多模态混合检索", "故障文本", "故障图片", "设备型号", "知识图谱", "检索中枢", "手册证据", "相似案例", "作业步骤"],
        "prompt": (
            f"{GLOBAL_STYLE}. Create slide 7 information flow. Title exactly: 多模态混合检索. "
            "Left input cards exactly: 故障文本, 故障图片, 设备型号, 知识图谱. "
            "Center node exactly: 检索中枢. Right output cards exactly: 手册证据, 相似案例, 作业步骤. "
            "Use arrows and industrial UI feel, clean and legible, no extra text, no random English, no logos, no watermark."
        ),
    },
    {
        "no": 8,
        "file": "slide08_agents.png",
        "title": "多 Agent 协同",
        "goal": "把多 Agent 从概念变成可解释的工作分工，对应 A1 各项功能要求。",
        "layout": "中心是检修任务，周围六个 Agent 模块环绕，每个模块一句职责短语。",
        "visual": "不要画拟人机器人；用模块化工业控制台、线性节点和任务流表达协同。",
        "text": ["多 Agent 协同", "检索 Agent", "视觉 Agent", "诊断 Agent", "SOP Agent", "合规 Agent", "更新 Agent"],
        "prompt": (
            f"{GLOBAL_STYLE}. Create slide 8 multi-agent orchestration. Title exactly: 多 Agent 协同. "
            "Center node: 检修任务. Six surrounding modules exactly: 检索 Agent, 视觉 Agent, 诊断 Agent, SOP Agent, 合规 Agent, 更新 Agent. "
            "Do not draw humanoid robots. Use industrial control-console modules and clean network lines. Large readable labels, no extra text, no logos, no watermark."
        ),
    },
    {
        "no": 9,
        "file": "slide09_sop_compliance.png",
        "title": "SOP 与安全合规",
        "goal": "突出机械专业价值：输出不是建议，而是可执行、可审核的检修步骤和安全项。",
        "layout": "左侧是标准化作业单，右侧是安全清单；底部红色细条强调禁止带电拆检。",
        "visual": "严肃安全风格，PPE、挂牌、验电、验收图标；避免火花、事故等戏剧化画面。",
        "text": ["标准作业与安全合规", "故障判断", "工具备件", "步骤化 SOP", "验收标准", "LOTO", "PPE", "防误启动", "禁止带电拆检"],
        "prompt": (
            f"{GLOBAL_STYLE}. Create slide 9 SOP and compliance. Title exactly: 标准作业与安全合规. "
            "Left panel is a standardized work order with exact labels: 故障判断, 工具备件, 步骤化 SOP, 验收标准. "
            "Right safety checklist with exact labels: LOTO, PPE, 防误启动. "
            "Bottom red warning strip exactly: 禁止带电拆检. "
            "Serious safety style, clear Chinese, no extra text, no logos, no watermark."
        ),
    },
    {
        "no": 10,
        "file": "slide10_knowledge_loop.png",
        "title": "知识沉淀闭环",
        "goal": "证明系统能持续成长，现场案例经过审核后进入案例库、图谱和索引。",
        "layout": "中心循环流程图，五个节点；右下角有知识图谱小视图。",
        "visual": "循环箭头清楚；节点有审核态颜色区分；背景为浅色工业数据工作台。",
        "text": ["知识沉淀闭环", "上传案例", "人工审核", "写入图谱", "更新索引", "反馈修正"],
        "prompt": (
            f"{GLOBAL_STYLE}. Create slide 10 knowledge loop. Title exactly: 知识沉淀闭环. "
            "Center circular process with five nodes exactly: 上传案例, 人工审核, 写入图谱, 更新索引, 反馈修正. "
            "Add a small abstract knowledge graph in the bottom right. "
            "Clean industrial data workspace, no extra text, no logos, no watermark, large readable Chinese."
        ),
    },
    {
        "no": 11,
        "file": "slide11_evaluation.png",
        "title": "量化评测",
        "goal": "用四组对比证明本系统比普通问答和普通 RAG 更可信。",
        "layout": "左侧四组对比，右侧四个指标柱状图；底部写评测口径。",
        "visual": "专业仪表盘风格；本系统用青绿色高亮；幻觉率和安全漏检率越低越好用下降箭头。",
        "text": ["量化评测", "无 RAG", "文本 RAG", "多模态 RAG", "本系统", "Recall@5", "引用覆盖", "SOP 完整", "幻觉率"],
        "prompt": (
            f"{GLOBAL_STYLE}. Create slide 11 evaluation dashboard. Title exactly: 量化评测. "
            "Comparison groups exactly: 无 RAG, 文本 RAG, 多模态 RAG, 本系统. "
            "Metric labels exactly: Recall@5, 引用覆盖, SOP 完整, 幻觉率. "
            "Use clean bar charts and dashboard cards, highlight 本系统 in teal. No tiny numbers, no extra text, no logos, no watermark."
        ),
    },
    {
        "no": 12,
        "file": "slide12_demo_route.png",
        "title": "答辩演示路线",
        "goal": "把现场演示控制在评委容易跟随的五步链路内。",
        "layout": "横向时间线五步，每一步一个编号、图标和短标题。",
        "visual": "路线图清晰，背景可以是抽象系统界面和检修工作台，不使用真实截图。",
        "text": ["答辩演示路线", "文本问诊", "图片检索", "SOP 生成", "案例审核", "指标评测"],
        "prompt": (
            f"{GLOBAL_STYLE}. Create slide 12 demo route. Title exactly: 答辩演示路线. "
            "Horizontal five-step timeline with exact labels: 文本问诊, 图片检索, SOP 生成, 案例审核, 指标评测. "
            "Each step has a simple industrial icon. Abstract UI and maintenance workbench background, no real screenshots, no extra text, no logos, no watermark."
        ),
    },
    {
        "no": 13,
        "file": "slide13_deployment.png",
        "title": "部署与提交安全",
        "goal": "说明作品可上线、可审计、不会泄露密钥或违规分发资料。",
        "layout": "左侧部署架构，右侧安全清单；底部 ready gate 状态条。",
        "visual": "工程部署图，Render、Supabase、模型 API 用抽象云模块表达，不放品牌 logo。",
        "text": ["部署与提交安全", "Render 公网演示", "Supabase 持久化", "云端模型 API", "提交包审计", "ready = true", "forbidden = 0"],
        "prompt": (
            f"{GLOBAL_STYLE}. Create slide 13 deployment and submission safety. Title exactly: 部署与提交安全. "
            "Left deployment modules exactly: Render 公网演示, Supabase 持久化, 云端模型 API. "
            "Right safety checklist exactly: 提交包审计, ready = true, forbidden = 0. "
            "Use abstract cloud modules, no brand logos, no keys, no random English except ready=true and forbidden=0, no watermark."
        ),
    },
    {
        "no": 14,
        "file": "slide14_close.png",
        "title": "创新点收束",
        "goal": "用六个创新点收束答辩，形成可记忆的最终印象。",
        "layout": "深色收尾页，大标题在左上，中间六个创新点标签，右下 Q&A。",
        "visual": "稳重、克制、有结束感；背景为工业设备轮廓和知识网络淡纹理。",
        "text": ["核心创新点", "领域垂直", "证据可追溯", "多模态检索", "机械 SOP", "知识闭环", "量化评测", "Q&A"],
        "prompt": (
            f"{GLOBAL_STYLE}. Create slide 14 closing page. Title exactly: 核心创新点. "
            "Six innovation labels exactly: 领域垂直, 证据可追溯, 多模态检索, 机械 SOP, 知识闭环, 量化评测. "
            "Bottom right text exactly: Q&A. "
            "Dark navy closing slide, subtle industrial equipment silhouette and knowledge network texture, no extra text, no logos, no watermark."
        ),
    },
]


def write_sources() -> None:
    DECK_DIR.mkdir(parents=True, exist_ok=True)
    SLIDE_DIR.mkdir(parents=True, exist_ok=True)

    md_lines = [
        "# A1 答辩全图 PPT 逐页设计说明",
        "",
        "本文件用于指导 `gpt-image-2` 生成每一页 16:9 全图 PPT。每页都把文字、图形、排版和视觉风格直接生成到图片里，最终再按顺序合成为 PPTX。",
        "",
        "全局风格：成熟工业答辩风，深蓝、钢灰、青绿色为主，少量警示橙/红；少字大字号；避免赛博霓虹、通用 AI 海报、过度装饰和随机英文。",
        "",
    ]
    json_rows = []
    json_payload = {"deck_mode": "full-image-slides", "model": "gpt-image-2", "size": "1536x864", "slides": []}

    for slide in SLIDES:
        md_lines.extend(
            [
                f"## {slide['no']:02d}. {slide['title']}",
                "",
                f"- 目标：{slide['goal']}",
                f"- 版式：{slide['layout']}",
                f"- 风格：{slide['visual']}",
                f"- 页面文字：{' / '.join(slide['text'])}",
                f"- 输出文件：`{slide['file']}`",
                "",
                "生成提示词：",
                "",
                "```text",
                slide["prompt"],
                "```",
                "",
            ]
        )
        row = {
            "prompt": slide["prompt"],
            "model": "gpt-image-2",
            "size": "1536x864",
            "quality": "high" if slide["no"] in {1, 6, 7, 9, 14} else "medium",
            "output_format": "png",
            "out": str((SLIDE_DIR / slide["file"]).as_posix()),
        }
        json_rows.append(row)
        json_payload["slides"].append(
            {
                "slide": slide["no"],
                "title": slide["title"],
                "file": slide["file"],
                "goal": slide["goal"],
                "layout": slide["layout"],
                "visual": slide["visual"],
                "text": slide["text"],
                "prompt": slide["prompt"],
            }
        )

    DESIGN_MD.write_text("\n".join(md_lines), encoding="utf-8")
    PROMPTS_JSONL.write_text("\n".join(json.dumps(row, ensure_ascii=False) for row in json_rows) + "\n", encoding="utf-8")
    PROMPTS_JSON.write_text(json.dumps(json_payload, ensure_ascii=False, indent=2), encoding="utf-8")


def load_env_file(path: Path) -> None:
    if not path.exists():
        return
    for raw in path.read_text(encoding="utf-8-sig", errors="replace").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


def image_api_url() -> str:
    base = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1").strip().rstrip("/")
    if not base.endswith("/v1"):
        base = f"{base}/v1"
    return f"{base}/images/generations"


def generate_one_image(job: dict, *, force: bool, attempts: int) -> tuple[str, Path, int, float]:
    out_path = Path(job["out"])
    if out_path.exists() and not force:
        return "skipped", out_path, out_path.stat().st_size, 0.0

    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not set")

    payload = {
        "model": job.get("model", "gpt-image-2"),
        "prompt": job["prompt"],
        "size": job.get("size", "1536x864"),
        "quality": job.get("quality", "high"),
        "output_format": job.get("output_format", "png"),
        "n": 1,
    }
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    last_error: Exception | None = None
    started = time.time()
    for attempt in range(1, attempts + 1):
        try:
            request = urllib.request.Request(image_api_url(), data=body, method="POST", headers=headers)
            with urllib.request.urlopen(request, timeout=240) as response:
                data = json.loads(response.read().decode("utf-8", "replace"))
            item = data.get("data", [{}])[0]
            image_b64 = item.get("b64_json")
            if not image_b64:
                raise RuntimeError(f"image response did not include b64_json; keys={list(item.keys())}")
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_bytes(base64.b64decode(image_b64))
            return "saved", out_path, out_path.stat().st_size, time.time() - started
        except urllib.error.HTTPError as exc:
            body_text = exc.read(1200).decode("utf-8", "replace")
            last_error = RuntimeError(f"HTTP {exc.code}: {body_text}")
        except Exception as exc:  # pragma: no cover - network path
            last_error = exc
        if attempt < attempts:
            time.sleep(2 * attempt)
    raise RuntimeError(f"{out_path.name} failed after {attempts} attempt(s): {last_error}")


def generate_images(*, start: int, end: int, force: bool, concurrency: int, attempts: int) -> None:
    load_env_file(ROOT / ".env.local")
    write_sources()
    selected = [
        job
        for job in json.loads(PROMPTS_JSON.read_text(encoding="utf-8"))["slides"]
        if start <= int(job["slide"]) <= end
    ]
    if not selected:
        raise ValueError(f"No slides selected for range {start}-{end}")

    jobs_by_slide = []
    for slide in selected:
        jobs_by_slide.append(
            {
                "slide_no": slide["slide"],
                "prompt": slide["prompt"],
                "model": "gpt-image-2",
                "size": "1536x864",
                "quality": "high" if slide["slide"] in {1, 6, 7, 9, 14} else "medium",
                "output_format": "png",
                "out": str(SLIDE_DIR / slide["file"]),
            }
        )

    print(f"Using image endpoint: {image_api_url()}")
    print(f"Selected slides: {jobs_by_slide[0]['slide_no']}-{jobs_by_slide[-1]['slide_no']}, concurrency={concurrency}")
    with ThreadPoolExecutor(max_workers=max(1, concurrency)) as executor:
        futures = {
            executor.submit(generate_one_image, job, force=force, attempts=attempts): job
            for job in jobs_by_slide
        }
        for future in as_completed(futures):
            job = futures[future]
            label = f"slide{int(job['slide_no']):02d}"
            status, out_path, size, elapsed = future.result()
            print(f"{label}: {status} {out_path.name} {size} bytes {elapsed:.1f}s")


def build_pptx() -> Path:
    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)
    blank = prs.slide_layouts[6]

    missing = []
    for slide in SLIDES:
        image_path = SLIDE_DIR / slide["file"]
        if not image_path.exists():
            missing.append(str(image_path))
            continue
        page = prs.slides.add_slide(blank)
        page.shapes.add_picture(
            str(image_path),
            Inches(0),
            Inches(0),
            width=prs.slide_width,
            height=prs.slide_height,
        )

    if missing:
        raise FileNotFoundError("Missing generated slide images:\n" + "\n".join(missing))

    OUTPUT_PPTX.parent.mkdir(parents=True, exist_ok=True)
    prs.save(OUTPUT_PPTX)
    return OUTPUT_PPTX


def main() -> int:
    parser = argparse.ArgumentParser(description="Prepare prompts and build the gpt-image-2 full-image defense deck.")
    parser.add_argument("command", choices=["prepare", "generate-images", "build", "all"], nargs="?", default="all")
    parser.add_argument("--start", type=int, default=1)
    parser.add_argument("--end", type=int, default=len(SLIDES))
    parser.add_argument("--concurrency", type=int, default=2)
    parser.add_argument("--attempts", type=int, default=2)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    if args.command in {"prepare", "all"}:
        write_sources()
        print(DESIGN_MD)
        print(PROMPTS_JSONL)
    if args.command == "generate-images":
        generate_images(
            start=args.start,
            end=args.end,
            force=args.force,
            concurrency=args.concurrency,
            attempts=args.attempts,
        )
    if args.command in {"build", "all"}:
        print(build_pptx())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
