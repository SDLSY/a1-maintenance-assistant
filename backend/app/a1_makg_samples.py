from __future__ import annotations

import sqlite3
from datetime import datetime


OFFICIAL_ENGINE_CASES = [
    {
        "title": "A1-MAKG 官方样例：火花塞间隙超差",
        "equipment": "engine",
        "model": "摩托车发动机",
        "symptoms": "发动机起动困难，火花塞中心电极磨损，间隙疑似超过手册标准。",
        "fault_type": "火花塞检查",
        "cause": "火花塞电极磨损或积碳，间隙偏离 0.7-0.9 mm 标准范围。",
        "actions": "冷机后拆下高压帽，用火花塞专用套筒拆卸，检查螺纹和中心电极，用塞尺测量间隙，必要时更换并按 20±2 N·m 拧紧。",
        "parts": "火花塞, 火花塞专用套筒, 塞尺, 定扭扳手",
        "risk_level": "medium",
        "status": "approved",
        "work_order_status": "archived",
    },
    {
        "title": "A1-MAKG 官方样例：压缩压力偏低",
        "equipment": "engine",
        "model": "摩托车发动机",
        "symptoms": "发动机动力不足，压缩压力测量值低于手册标准范围。",
        "fault_type": "压缩压力异常",
        "cause": "可能存在活塞环磨损、气门密封不良或气缸头垫片缺陷。",
        "actions": "预热后熄火，拆卸火花塞并清洁火花塞孔，安装压力表，油门全开由起动电机带动发动机转动，按加机油复测结果判断活塞环或气门/垫片问题。",
        "parts": "压力表, 火花塞专用工具, 机油, 密封垫片",
        "risk_level": "high",
        "status": "approved",
        "work_order_status": "archived",
    },
    {
        "title": "A1-MAKG 待审核工单：水泵拆检后仍有泄漏",
        "equipment": "engine",
        "model": "摩托车发动机",
        "symptoms": "水泵复装后短时间运行出现渗漏，冷却液液位下降。",
        "fault_type": "泵系检查",
        "cause": "待审核：水泵密封件安装不到位或叶轮/壳体密封面损伤。",
        "actions": "待审核：冷机释放冷却液，拆检水泵密封件和叶轮，复装后进行泄漏复测。",
        "parts": "水泵密封件, 冷却液, 垫片",
        "risk_level": "medium",
        "status": "pending",
        "work_order_status": "pending_review",
    },
]


GOLDEN_MECHANICAL_CASES = [
    ("GOLD-MOTOR-001 电机轴承温升复发", "motor", "Y2-160M", "更换轴承后一周内端盖温升再次升高，测振低频分量上升。", "轴承过热复发", "轴承座配合偏松导致外圈微动，润滑脂被污染。", "停机断电挂牌，拆检轴承座配合面，测量轴承座圆度和配合间隙，修复轴承座后更换轴承并按脂量补脂，复测温升和振动。", "6205-2RS轴承, 润滑脂, 千分表, 内径表", "medium"),
    ("GOLD-MOTOR-002 电机绝缘下降伴随潮气", "motor", "Y2-160M", "雨季停机后绝缘电阻低于基线，端盖内有潮气痕迹。", "绝缘下降", "接线盒密封老化和绕组受潮，存在带电启动风险。", "隔离电源并验电，检查接线盒密封和绕组外观，进行烘干处理，绝缘电阻合格后空载试运行。", "绝缘电阻表, 密封垫, 热风干燥设备", "high"),
    ("GOLD-MOTOR-003 联轴器不同轴引起振动", "motor", "Y2-160M", "电机与泵连接后振动升高，脱开联轴器空载运行正常。", "联轴器不同轴", "联轴器径向和角向偏差超出允许范围，导致轴承附加载荷。", "停机挂牌，拆除防护罩，使用百分表或激光对中仪检查同轴度，调整地脚垫片并紧固，复装防护罩后带载复测。", "百分表, 激光对中仪, 垫片, 扭矩扳手", "medium"),
    ("GOLD-MOTOR-004 端盖油污与密封老化", "motor", "Y2-160M", "端盖附近油污增加，运行 30 分钟后温升明显。", "端盖油污", "端盖密封圈老化，润滑脂外溢并夹带磨粒。", "断电挂牌后拆检端盖和轴承室，清理油污，更换密封圈，检查轴承滚道并按规定脂量复装。", "端盖密封圈, 清洗剂, 润滑脂", "medium"),
    ("GOLD-MOTOR-005 转子擦碰定子", "motor", "Y2-160M", "启动瞬间有尖锐摩擦声，拆检发现转子表面擦痕。", "转子擦碰", "轴承游隙增大或端盖止口磨损导致气隙不均。", "断电验电，拆检端盖、轴承和转子表面，测量气隙和端盖止口，修复配合面后试运行。", "塞尺, 千分表, 轴承, 拉马", "high"),
    ("GOLD-MOTOR-006 冷却风道堵塞过热", "motor", "Y2-160M", "负载未变但机壳温度升高，风罩积灰明显。", "通风不良过热", "风罩和散热片积尘堵塞，冷却风量不足。", "停机断电，拆下风罩清理积尘，检查风扇叶片和风道，复装后记录温升曲线。", "毛刷, 压缩空气, 测温仪", "medium"),
    ("GOLD-MOTOR-007 轴承补脂过量", "motor", "Y2-160M", "补脂后温升反而升高，轴承室有明显甩脂。", "润滑脂过量", "补脂量过大造成搅拌发热，密封处外溢。", "停机冷却，拆检轴承室清除多余润滑脂，按脂量标准重新补脂，空载试运行并复测温升。", "润滑脂, 清洗剂, 测温仪", "medium"),
    ("GOLD-PUMP-001 机械密封端面磨损", "pump", "ISG80-160", "密封腔持续滴漏，停泵后底座有积液。", "机械密封泄漏", "动静环端面磨损，O 形圈老化，轴套有轻微沟槽。", "隔离入口出口阀门并泄压排液，拆卸密封压盖，更换机械密封和 O 形圈，检查轴套后试压验收。", "机械密封组件, O形圈, 轴套, 压力表", "high"),
    ("GOLD-PUMP-002 入口过滤器堵塞汽蚀", "pump", "ISG80-160", "出口压力波动，噪声尖锐，流量下降。", "汽蚀/流量不足", "入口过滤器堵塞导致吸入压力不足，叶轮入口发生汽蚀。", "停泵隔离并泄压，清洗入口过滤器，检查入口阀开度和吸入管路，复测流量、压力和振动。", "过滤器滤网, 垫片, 压力表, 流量计", "medium"),
    ("GOLD-PUMP-003 填料压盖过紧发热", "pump", "ISG80-160", "填料函温度高，泄漏量过小并伴随异味。", "填料密封过紧", "压盖压紧量过大，填料润滑冷却不足。", "停泵泄压，交叉均匀松开压盖，检查填料磨损并调整滴漏量，试运行观察温升。", "填料, 扳手, 测温仪", "medium"),
    ("GOLD-PUMP-004 叶轮腐蚀冲蚀", "pump", "ISG80-160", "流量下降且叶轮表面有坑蚀和材料损失。", "叶轮腐蚀/冲蚀", "介质腐蚀性或含砂量偏高，叶轮表面冲蚀。", "隔离排液后拆检叶轮，评估壁厚和动平衡，必要时更换叶轮并复核介质过滤。", "叶轮, 垫片, 测厚仪", "medium"),
    ("GOLD-PUMP-005 轴承箱进水乳化", "pump", "ISG80-160", "轴承箱油液乳化，泵运行时振动升高。", "轴承箱进水", "密封失效或呼吸器进水导致润滑油乳化。", "停泵隔离，排放乳化油，检查油封和呼吸器，更换润滑油并复测振动。", "润滑油, 油封, 呼吸器", "medium"),
    ("GOLD-PUMP-006 管路应力导致密封失效", "pump", "ISG80-160", "更换密封后短期再次泄漏，法兰连接有偏载。", "管路应力", "吸排管路强行对口造成泵体变形和密封端面偏磨。", "隔离泄压，检查管路支撑和法兰应力，释放管路偏载后重新对中并更换密封。", "机械密封, 垫片, 对中工具", "high"),
    ("GOLD-PUMP-007 空转导致密封烧损", "pump", "ISG80-160", "启动后短时间密封冒烟并泄漏，入口液位不足。", "空转烧损", "泵腔未充满介质，机械密封干摩擦烧损。", "立即停泵，确认入口液位和排气，冷却后拆检密封端面，更换密封并设置防空转检查。", "机械密封, 液位开关, PPE", "high"),
    ("GOLD-BEARING-001 外圈疲劳剥落", "bearing", "6205-2RS", "运行时周期性冲击声，拆下后外圈滚道有片状剥落。", "外圈剥落", "长期润滑不足和安装偏斜引起滚道疲劳剥落。", "佩戴 PPE，清洁拆装区，拆下轴承拍照记录，更换同规格轴承，检查轴承座配合并空载试运行。", "6205-2RS轴承, 卡簧钳, 润滑脂", "medium"),
    ("GOLD-BEARING-002 保持架裂纹", "bearing", "6205-2RS", "轴承转动不均匀，保持架局部裂纹。", "保持架裂纹", "冲击载荷或装配偏斜导致保持架疲劳开裂。", "拆检轴承和相邻配合面，禁止继续使用裂纹保持架，复核安装偏斜后更换轴承。", "轴承, 塞尺, 清洗剂", "medium"),
    ("GOLD-BEARING-003 微动磨损假性压痕", "bearing", "6205-2RS", "备用电机长期停放后轴承滚道有等间距压痕。", "微动磨损/假性压痕", "停放期间微振导致滚动体与滚道间微动磨损。", "记录压痕位置，评估振动来源，更换轴承并改进存放固定和定期盘车制度。", "轴承, 防锈油, 盘车记录表", "low"),
    ("GOLD-BEARING-004 润滑脂污染", "bearing", "6205-2RS", "润滑脂变黑并含金属屑，但滚道未完全剥落。", "润滑脂污染", "密封失效或磨粒进入轴承室，引起润滑劣化。", "清洁轴承室，检查密封件和滚道，必要时更换轴承，复装后监测温升和噪声。", "润滑脂, 密封圈, 清洗剂", "medium"),
    ("GOLD-BEARING-005 安装硬敲造成压痕", "bearing", "6205-2RS", "新轴承装机后立即异响，滚道有局部压痕。", "装配压痕", "安装时直接敲击滚道或传力路径错误。", "拆下轴承确认压痕，报废受损轴承，使用套筒或压力机按正确受力圈安装。", "压力机, 安装套筒, 新轴承", "medium"),
    ("GOLD-BEARING-006 轴承座椭圆导致游隙异常", "bearing", "6205-2RS", "更换轴承后仍有异响，轴承座测量发现椭圆。", "轴承座配合异常", "轴承座磨损变形导致外圈受力不均。", "测量轴承座圆度和尺寸，修复或更换轴承座，再更换轴承并复测游隙。", "内径表, 千分尺, 轴承座", "medium"),
    ("GOLD-BEARING-007 密封唇损伤进尘", "bearing", "6205-2RS", "轴承密封唇破损，内部有粉尘和干涩感。", "密封失效进尘", "密封件损伤导致粉尘进入并破坏润滑膜。", "拆检并更换轴承，检查防尘结构，清洁装配区并补充合规润滑脂。", "密封轴承, 清洁耗材, 润滑脂", "medium"),
    ("GOLD-ENGINE-001 火花塞积碳起动困难", "engine", "摩托车发动机", "冷车起动困难，火花塞电极黑色积碳。", "火花塞积碳", "混合气偏浓或点火状态不良导致火花塞积碳。", "冷机断开点火连接，拆下火花塞，检查电极和间隙，必要时更换并按规定扭矩拧紧。", "火花塞, 塞尺, 定扭扳手", "medium"),
    ("GOLD-ENGINE-002 压缩压力偏低", "engine", "摩托车发动机", "动力不足，压缩压力低于手册基准。", "压缩压力异常", "活塞环磨损、气门密封不良或气缸垫片问题。", "拆下火花塞并安装压力表，油门全开测量压缩压力，加少量机油复测区分活塞环与气门问题。", "压力表, 火花塞套筒, 机油", "high"),
    ("GOLD-ENGINE-003 水泵复装后渗漏", "engine", "摩托车发动机", "更换冷却液后水泵壳体边缘渗漏。", "泵系渗漏", "水泵密封件安装不到位或密封面划伤。", "冷机释放冷却液，拆检水泵密封件和密封面，按顺序复装并进行泄漏复测。", "水泵密封件, 冷却液, 垫片", "medium"),
    ("GOLD-ENGINE-004 起动电机不转", "engine", "摩托车发动机", "按下起动按钮后继电器有响声但起动电机不转。", "起动系统检查", "蓄电池电压不足、起动电机碳刷磨损或线路接触不良。", "断开电源防误启动，检查蓄电池电压、继电器输出和起动电机端子，必要时拆检碳刷。", "万用表, 起动电机碳刷, 绝缘手套", "medium"),
]


HARD_EVAL_QUESTIONS = [
    ("A1-HARD-001 电机型号不完整，只知道端盖过热和低频振动，如何先做安全检索？", "motor", "", "1,9,10", "过热/振动", "停机,断电,挂牌,PPE"),
    ("A1-HARD-002 用户说泵下面有水但未说明位置，应如何避免直接误判机械密封？", "pump", "", "4,9,10", "泄漏", "隔离,泄压,验收"),
    ("A1-HARD-003 轴承照片疑似剥落但文本说只是轻微噪声，系统应如何复核？", "bearing", "6205-2RS", "7,8,9,10", "剥落", "PPE,清洁,试运行"),
    ("A1-HARD-004 电机出现油污和温升，但用户没有提供运行时长，SOP 应补问哪些参数？", "motor", "Y2-160M", "1,9,10", "过热/油污", "停机,断电,PPE,试运行"),
    ("A1-HARD-005 离心泵流量下降且有尖锐噪声，图片像叶轮损伤，如何区分汽蚀和堵塞？", "pump", "ISG80-160", "5,9,10", "汽蚀/流量不足", "隔离,泄压,压力,流量"),
    ("A1-HARD-006 轴承保持架裂纹但设备型号缺失，如何组织可追溯引用？", "bearing", "", "8,9,10", "磨损/断裂", "PPE,更换,归档"),
    ("A1-HARD-007 电机绝缘下降和轴承异响同时出现，检索结果应优先提醒什么？", "motor", "Y2-160M", "1,2,9,10", "绝缘下降", "断电,接地,绝缘,复测"),
    ("A1-HARD-008 泵体泄漏图片与用户描述的压力波动冲突，应如何进入人工复核？", "pump", "ISG80-160", "4,5,9,10", "泄漏", "隔离,泄压,人工复核"),
    ("A1-HARD-009 轴承外圈剥落后更换新件，验收阶段必须记录哪些指标？", "bearing", "6205-2RS", "7,9,10", "剥落", "试运行,温升,噪声,归档"),
    ("A1-HARD-010 用户上传发动机火花塞照片但未说明症状，如何从官方手册找检查步骤？", "engine", "摩托车发动机", "", "火花塞检查", "冷机,扭矩,间隙,复核"),
    ("A1-HARD-011 发动机压缩压力偏低但加机油后升高，如何判断原因？", "engine", "摩托车发动机", "", "压缩压力异常", "压力表,喷油器,复测"),
    ("A1-HARD-012 发动机水泵复装后渗漏，如何生成待审核工单？", "engine", "摩托车发动机", "", "泵系检查", "冷机,泄漏,验收"),
    ("A1-HARD-013 电机联轴器对中问题导致振动，如何防止只换轴承的误判？", "motor", "Y2-160M", "3,9,10", "不同轴", "断电,测振,对中,复测"),
    ("A1-HARD-014 泵入口堵塞和叶轮汽蚀同时可能存在，如何用图谱路径解释？", "pump", "ISG80-160", "5,6,9,10", "汽蚀/流量不足", "隔离,入口,流量"),
    ("A1-HARD-015 轴承润滑脂污染但没有明显剥落，应如何避免幻觉式损伤判断？", "bearing", "6205-2RS", "8,9,10", "润滑脂污染", "清洁,更换,试运行"),
    ("A1-HARD-016 电机端盖油污图像可能来自密封老化，检索应如何绑定图片证据？", "motor", "Y2-160M", "1,9,10", "过热/油污", "PPE,拍照,归档"),
    ("A1-HARD-017 泵密封泄漏前需要确认哪些残余能量？", "pump", "ISG80-160", "4,9,10", "泄漏", "压力,温度,介质,防滑"),
    ("A1-HARD-018 轴承疑似装配敲击造成压痕，SOP 中应禁止什么操作？", "bearing", "6205-2RS", "7,8,9,10", "压痕", "禁止,硬敲,清洁"),
    ("A1-HARD-019 发动机火花塞安装时如何控制扭矩和预紧步骤？", "engine", "摩托车发动机", "", "火花塞检查", "扭矩,预紧,高压帽"),
    ("A1-HARD-020 发动机压缩压力高于最大值时应检查什么？", "engine", "摩托车发动机", "", "压缩压力异常", "积碳,气门,活塞"),
    ("A1-HARD-021 电机振动问题如果手册证据不足，系统应如何提示补充数据？", "motor", "", "3,9,10", "振动", "补充,测振,人工复核"),
    ("A1-HARD-022 泵泄漏照片只有水痕没有液滴，应如何降低置信度并要求复核？", "pump", "", "4,9,10", "泄漏", "隔离,复核,验收"),
    ("A1-HARD-023 轴承照片像宣传图而非故障图，系统应如何处理视觉证据？", "bearing", "", "7,8,9,10", "待确认故障", "人工复核,来源,归档"),
    ("A1-HARD-024 电机绝缘不合格但用户要求强行启动，合规校验应如何拦截？", "motor", "Y2-160M", "2,9,10", "绝缘下降", "禁止,绝缘,接地"),
    ("A1-HARD-025 泵检修后验收只有压力无流量记录，测试报告应判定什么缺口？", "pump", "ISG80-160", "5,9,10", "汽蚀/流量不足", "流量,压力,验收"),
    ("A1-HARD-026 轴承更换后仍有异响，下一步应检查哪些相邻图谱节点？", "bearing", "6205-2RS", "7,8,9,10", "异响", "配合,润滑,试运行"),
    ("A1-HARD-027 发动机起动电机拆装涉及哪些作业前确认？", "engine", "摩托车发动机", "", "起动系统检查", "断电,误启动,工具"),
    ("A1-HARD-028 发动机气门间隙问题和压缩压力异常如何关联？", "engine", "摩托车发动机", "", "压缩压力异常", "气门,间隙,复测"),
    ("A1-HARD-029 电机、泵、轴承故障描述混在一起时系统应如何按设备型号过滤？", "motor", "Y2-160M", "1,3,9,10", "过热/振动", "型号,过滤,引用"),
    ("A1-HARD-030 官方手册与公开厂商手册同时命中时，引用展示应如何区分来源？", "engine", "摩托车发动机", "", "通用检修", "来源,页码,许可"),
]


def _eval_category(question: str) -> str:
    if "证据不足" in question or "降低置信度" in question or "未说明" in question:
        return "no_evidence"
    if "冲突" in question or "混在一起" in question or "文本说" in question:
        return "conflict"
    if "图片" in question or "照片" in question or "上传" in question:
        return "image"
    if "A1-HARD" in question:
        return "complex"
    return "base"


def _eval_difficulty(question: str) -> str:
    if _eval_category(question) in {"conflict", "no_evidence"}:
        return "hard"
    if "A1-HARD" in question:
        return "hard"
    return "medium"


def ensure_a1_makg_samples(conn: sqlite3.Connection) -> dict:
    now = datetime.utcnow().isoformat(timespec="seconds")
    kg_nodes = [
        ("n_engine", "摩托车发动机", "equipment"),
        ("n_spark_plug", "火花塞", "component"),
        ("n_compression", "压缩压力", "fault"),
        ("n_engine_pump", "发动机水泵", "component"),
        ("n_engine_ignition_safety", "防误启动", "safety"),
    ]
    kg_edges = [
        ("n_engine", "n_spark_plug", "包含部件"),
        ("n_engine", "n_engine_pump", "包含部件"),
        ("n_spark_plug", "n_compression", "关联诊断"),
        ("n_compression", "n_engine_ignition_safety", "作业前要求"),
        ("n_engine_pump", "n_engine_ignition_safety", "作业前要求"),
    ]
    conn.executemany("INSERT OR IGNORE INTO kg_nodes (id, label, type) VALUES (?, ?, ?)", kg_nodes)
    for source, target, relation in kg_edges:
        exists = conn.execute(
            "SELECT id FROM kg_edges WHERE source = ? AND target = ? AND relation = ?",
            (source, target, relation),
        ).fetchone()
        if not exists:
            conn.execute(
                "INSERT INTO kg_edges (source, target, relation) VALUES (?, ?, ?)",
                (source, target, relation),
            )

    inserted_cases = 0
    for item in OFFICIAL_ENGINE_CASES:
        exists = conn.execute(
            "SELECT id FROM maintenance_cases WHERE title = ?",
            (item["title"],),
        ).fetchone()
        if exists:
            if item["status"] == "approved":
                conn.execute(
                    """
                    UPDATE maintenance_cases
                    SET review_status = 'approved',
                        reviewer = 'ME-R02',
                        review_notes = '官方样例手册链路已由机械审核代号复核，可用于火花塞/压缩压力演示。'
                    WHERE title = ?
                    """,
                    (item["title"],),
                )
            continue
        conn.execute(
            """
            INSERT INTO maintenance_cases
            (title, equipment, model, symptoms, fault_type, cause, actions, parts,
             risk_level, status, work_order_status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                item["title"],
                item["equipment"],
                item["model"],
                item["symptoms"],
                item["fault_type"],
                item["cause"],
                item["actions"],
                item["parts"],
                item["risk_level"],
                item["status"],
                item["work_order_status"],
                now,
            ),
        )
        inserted_cases += 1
        if item["status"] == "approved":
            conn.execute(
                """
                UPDATE maintenance_cases
                SET review_status = 'approved',
                    reviewer = 'ME-R02',
                    review_notes = '官方样例手册链路已由机械审核代号复核，可用于火花塞/压缩压力演示。'
                WHERE title = ?
                """,
                (item["title"],),
            )

    inserted_golden_cases = 0
    for title, equipment, model, symptoms, fault_type, cause, actions, parts, risk_level in GOLDEN_MECHANICAL_CASES:
        exists = conn.execute(
            "SELECT id FROM maintenance_cases WHERE title = ?",
            (title,),
        ).fetchone()
        if exists:
            conn.execute(
                """
                UPDATE maintenance_cases
                SET status = 'approved',
                    work_order_status = 'archived_in_graph',
                    review_status = 'approved',
                    reviewer = 'ME-R02',
                    review_notes = '二次机械审核样例：故障机理、作业步骤、工具备件和安全项完整，可用于国奖答辩黄金链路。'
                WHERE title = ?
                """,
                (title,),
            )
            continue
        conn.execute(
            """
            INSERT INTO maintenance_cases
            (title, equipment, model, symptoms, fault_type, cause, actions, parts,
             risk_level, status, work_order_status, review_status, reviewer,
             review_notes, approved_at, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'approved', 'archived_in_graph',
                    'approved', 'ME-R02', ?, ?, ?)
            """,
            (
                title,
                equipment,
                model,
                symptoms,
                fault_type,
                cause,
                actions,
                parts,
                risk_level,
                "二次机械审核样例：故障机理、作业步骤、工具备件和安全项完整，可用于国奖答辩黄金链路。",
                now,
                now,
            ),
        )
        inserted_golden_cases += 1

    inserted_eval = 0
    for question, equipment, model, source_ids, fault_type, safety in HARD_EVAL_QUESTIONS:
        exists = conn.execute(
            "SELECT id FROM eval_questions WHERE question = ?",
            (question,),
        ).fetchone()
        category = _eval_category(question)
        difficulty = _eval_difficulty(question)
        review_notes = (
            "困难评测样本已由机械审核代号复核，用于检验复杂检修、图片检索、冲突处理或缺证据拒答能力。"
        )
        if exists:
            conn.execute(
                """
                UPDATE eval_questions
                SET review_status = 'approved',
                    reviewer = 'ME-R02',
                    review_notes = ?,
                    category = ?,
                    difficulty = ?
                WHERE question = ?
                """,
                (review_notes, category, difficulty, question),
            )
            continue
        conn.execute(
            """
            INSERT INTO eval_questions
            (question, equipment, model, expected_source_ids, expected_fault_type,
             expected_safety_keywords, review_status, reviewer, review_notes,
             category, difficulty)
            VALUES (?, ?, ?, ?, ?, ?, 'approved', 'ME-R02', ?, ?, ?)
            """,
            (question, equipment, model, source_ids, fault_type, safety, review_notes, category, difficulty),
        )
        inserted_eval += 1

    conn.execute(
        """
        UPDATE eval_questions
        SET category = CASE
                WHEN question LIKE '%证据不足%' OR question LIKE '%降低置信度%' OR question LIKE '%未说明%' THEN 'no_evidence'
                WHEN question LIKE '%冲突%' OR question LIKE '%混在一起%' OR question LIKE '%文本说%' THEN 'conflict'
                WHEN question LIKE '%图片%' OR question LIKE '%照片%' OR question LIKE '%上传%' THEN 'image'
                WHEN question LIKE 'A1-HARD%' THEN 'complex'
                ELSE 'base'
            END,
            difficulty = CASE
                WHEN question LIKE 'A1-HARD%' OR question LIKE '%冲突%' OR question LIKE '%证据不足%' THEN 'hard'
                ELSE COALESCE(NULLIF(difficulty, ''), 'medium')
            END
        WHERE category = '' OR difficulty = ''
        """
    )

    conn.commit()
    return {
        "inserted_engine_cases": inserted_cases,
        "inserted_golden_cases": inserted_golden_cases,
        "inserted_hard_eval_questions": inserted_eval,
        "hard_eval_total": len(HARD_EVAL_QUESTIONS),
    }
