from __future__ import annotations

import sqlite3
from datetime import datetime

from .vector_index import rebuild_embeddings

EQUIPMENT_SCENARIOS = [
    {
        "equipment": "motor",
        "model": "Y2-160M",
        "faults": [
            ("轴承过热", "润滑脂老化或轴承游隙增大", "停机断电挂牌，拆检轴承，清洗轴承室，更换轴承或补脂"),
            ("低频振动", "联轴器不同轴或地脚松动", "检查地脚螺栓，使用百分表或激光对中仪调整同轴度"),
            ("绝缘下降", "绕组受潮或端子盒进水", "测量绝缘电阻，烘干绕组，复测合格后试运行"),
            ("端盖油污", "轴承密封老化或润滑脂过量", "拆检端盖和密封圈，清洁油污，按规定补充润滑脂"),
        ],
        "parts": ["6205-2RS 轴承", "润滑脂", "端盖密封圈", "地脚螺栓", "绝缘电阻表"],
        "safety": "停机,断电,挂牌,PPE,试运行",
        "source_ids": "1,2,3,9,10",
    },
    {
        "equipment": "pump",
        "model": "ISG80-160",
        "faults": [
            ("机械密封泄漏", "动静环磨损、O 形圈老化或轴套沟槽", "隔离介质并泄压，更换机械密封和 O 形圈，试压检查"),
            ("出口压力波动", "入口过滤器堵塞或汽蚀", "清洗入口过滤器，检查入口阀门和吸入管路，复测流量"),
            ("泵组振动", "联轴器对中不良、轴承磨损或基础松动", "检查地脚螺栓、联轴器对中、泵轴弯曲和轴承状态"),
            ("流量不足", "叶轮磨损、入口堵塞或阀门开度不足", "停泵隔离后检查叶轮和入口管路，恢复阀门开度"),
        ],
        "parts": ["机械密封组件", "O 形圈", "过滤器滤网", "垫片", "轴套"],
        "safety": "隔离,泄压,停机,断电,验收",
        "source_ids": "4,5,6,9,10",
    },
    {
        "equipment": "bearing",
        "model": "6205-2RS",
        "faults": [
            ("外圈剥落", "疲劳载荷、润滑不足或安装偏斜", "拆下轴承拍照记录，更换同规格轴承，检查配合间隙"),
            ("保持架损伤", "异物侵入、润滑不足或过载冲击", "检查滚动体和保持架，清洁轴承座并更换轴承"),
            ("滚动体压痕", "装配敲击或运输冲击", "复核安装工具和装配流程，禁止硬敲滚道"),
            ("润滑脂污染", "密封失效或粉尘侵入", "清洗轴承室，更换密封件和润滑脂"),
        ],
        "parts": ["6205-2RS 轴承", "卡簧", "润滑脂", "清洗剂", "密封圈"],
        "safety": "PPE,清洁,更换,试运行",
        "source_ids": "7,8,9,10",
    },
]


def generate_sample_data(
    conn: sqlite3.Connection,
    case_count: int = 120,
    eval_count: int = 100,
    rebuild_index: bool = True,
) -> dict:
    now = datetime.utcnow().isoformat(timespec="seconds")
    existing_cases = conn.execute(
        "SELECT COUNT(*) AS c FROM maintenance_cases WHERE title LIKE 'EXP-%'"
    ).fetchone()["c"]
    inserted_cases = 0
    if existing_cases < case_count:
        for index in range(existing_cases + 1, case_count + 1):
            scenario = EQUIPMENT_SCENARIOS[(index - 1) % len(EQUIPMENT_SCENARIOS)]
            fault, cause, action = scenario["faults"][(index - 1) % len(scenario["faults"])]
            load_desc = ["运行 20 分钟后", "检修复装后", "高负荷工况下", "巡检点检时"][
                (index - 1) % 4
            ]
            title = f"EXP-{index:03d} {scenario['model']} {fault}案例"
            symptoms = f"{load_desc}发现{fault}，伴随温升、噪声、振动、泄漏或性能波动之一。"
            conn.execute(
                """
                INSERT INTO maintenance_cases
                (title, equipment, model, symptoms, fault_type, cause, actions, parts,
                 risk_level, status, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'approved', ?)
                """,
                (
                    title,
                    scenario["equipment"],
                    scenario["model"],
                    symptoms,
                    fault,
                    cause,
                    action,
                    ", ".join(scenario["parts"][:3]),
                    "high" if "泄漏" in fault or "绝缘" in fault else "medium",
                    now,
                ),
            )
            inserted_cases += 1

    existing_eval = conn.execute(
        "SELECT COUNT(*) AS c FROM eval_questions WHERE question LIKE 'EXP-%'"
    ).fetchone()["c"]
    inserted_eval = 0
    if existing_eval < eval_count:
        for index in range(existing_eval + 1, eval_count + 1):
            scenario = EQUIPMENT_SCENARIOS[(index - 1) % len(EQUIPMENT_SCENARIOS)]
            fault, _, _ = scenario["faults"][(index - 1) % len(scenario["faults"])]
            question = f"EXP-{index:03d} {scenario['model']} 出现{fault}时，如何检索手册并形成标准化检修作业？"
            conn.execute(
                """
                INSERT INTO eval_questions
                (question, equipment, model, expected_source_ids, expected_fault_type,
                 expected_safety_keywords)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    question,
                    scenario["equipment"],
                    scenario["model"],
                    scenario["source_ids"],
                    fault,
                    scenario["safety"],
                ),
            )
            inserted_eval += 1

    conn.commit()
    index_result = (
        rebuild_embeddings(conn)
        if rebuild_index
        else {"skipped": True, "reason": "rebuild_index=false"}
    )
    return {
        "inserted_cases": inserted_cases,
        "inserted_eval_questions": inserted_eval,
        "target_cases": case_count,
        "target_eval_questions": eval_count,
        "index": index_result,
        "note": "数据为团队自建样例，用于开发与评测，不代表真实厂家资料。",
    }
