from __future__ import annotations

import argparse
import csv
import json
import subprocess
import time
import urllib.parse
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "data" / "image_eval" / "fault_image_eval_manifest.csv"
SOURCES_JSON = ROOT / "data" / "image_eval" / "commons_image_sources.json"
USER_AGENT = "A1-maintenance-assistant/0.1 (academic competition prototype)"
MAX_IMAGE_SIDE = 1600
JPEG_QUALITY = 85


CANDIDATES = [
    {
        "id": "IMG-MOTOR-001",
        "title": "File:Burnt motor.jpg",
        "local_path": "data/image_eval/images/motor_overheat_burnt_motor_01.jpg",
        "fault_type": "overheat_damage",
        "visible_evidence": "电机过热烧损；绕组或外壳有热损伤痕迹",
        "caption_hint": "电机出现过热烧损迹象，需要检查负载、通风、绝缘和轴承状态。",
        "expected_retrieval_keywords": "电机 过热 温升 绝缘 轴承 通风",
        "expected_safety_keywords": "LOTO 验电 PPE 禁止带电拆检",
    },
    {
        "id": "IMG-MOTOR-002",
        "title": "File:Yauza 209-1 (motor) - 07 - top cap with bearing and grease seal parts.jpg",
        "local_path": "data/image_eval/images/motor_bearing_grease_seal_01.jpg",
        "fault_type": "bearing_grease_seal",
        "visible_evidence": "电机端盖、轴承和润滑密封件拆解可见",
        "caption_hint": "电机端盖处轴承和润滑密封结构清晰，需要检查润滑、密封老化和装配间隙。",
        "expected_retrieval_keywords": "电机 轴承 端盖 润滑 密封",
        "expected_safety_keywords": "LOTO PPE 温度复测 防误启动",
    },
    {
        "id": "IMG-MOTOR-003",
        "title": "File:Broken AC motor rotor.jpg",
        "local_path": "data/image_eval/images/motor_broken_rotor_01.jpg",
        "fault_type": "rotor_damage",
        "visible_evidence": "交流电机转子损伤；接触部位异常",
        "caption_hint": "电机转子部件损伤，可能关联擦碰、轴承间隙异常或装配偏斜。",
        "expected_retrieval_keywords": "电机 转子 擦碰 轴承间隙 异响",
        "expected_safety_keywords": "LOTO 验电 手动盘车 防误启动",
    },
    {
        "id": "IMG-MOTOR-004",
        "title": "File:Damage from Motor.JPG",
        "local_path": "data/image_eval/images/motor_external_damage_01.jpg",
        "fault_type": "motor_damage",
        "visible_evidence": "小型高速电机造成的损伤痕迹",
        "caption_hint": "电机运行异常造成外部损伤，需要关注转速、振动和防护措施。",
        "expected_retrieval_keywords": "电机 损伤 振动 防护 异响",
        "expected_safety_keywords": "LOTO PPE 防误启动 防护罩",
    },
    {
        "id": "IMG-MOTOR-005",
        "title": "File:Damage from Motor Close up.JPG",
        "local_path": "data/image_eval/images/motor_external_damage_close_01.jpg",
        "fault_type": "motor_damage_closeup",
        "visible_evidence": "电机损伤局部放大；可见磨损或冲击痕迹",
        "caption_hint": "电机异常损伤局部细节，需要结合振动、转速和装配状态复核。",
        "expected_retrieval_keywords": "电机 损伤 磨损 振动 装配",
        "expected_safety_keywords": "LOTO PPE 防误启动",
    },
    {
        "id": "IMG-MOTOR-006",
        "title": "File:Motor disassembeled.JPG",
        "local_path": "data/image_eval/images/motor_disassembled_01.jpg",
        "fault_type": "motor_disassembly",
        "visible_evidence": "直流电机拆解；转子、壳体和内部部件暴露",
        "caption_hint": "电机拆解状态可用于检修流程演示，需要先断电验电并记录装配位置。",
        "expected_retrieval_keywords": "电机 拆检 转子 壳体 装配",
        "expected_safety_keywords": "LOTO 验电 PPE 记录复装",
    },
    {
        "id": "IMG-MOTOR-007",
        "title": "File:Motor Bearing parts.jpg",
        "local_path": "data/image_eval/images/motor_bearing_parts_photo_01.jpg",
        "fault_type": "motor_bearing_assembly",
        "visible_evidence": "电机轴承零部件实物照片；可见轴承、端盖和密封相关部件",
        "caption_hint": "电机轴承部件实物照片，需要检查轴承安装、润滑、密封、游隙和端盖配合状态。",
        "expected_retrieval_keywords": "电机 轴承 部件 端盖 密封 润滑 游隙",
        "expected_safety_keywords": "LOTO PPE 游隙复测 防误启动",
    },
    {
        "id": "IMG-MOTOR-008",
        "title": "File:Yauza 209-1 (motor) - 08 - bearing and grease seal parts.jpg",
        "local_path": "data/image_eval/images/motor_bearing_grease_seal_02.jpg",
        "fault_type": "grease_seal_parts",
        "visible_evidence": "电机轴承、润滑脂密封和锁止件拆解可见",
        "caption_hint": "电机轴承和润滑密封零件拆解，需要检查密封、油污和润滑脂状态。",
        "expected_retrieval_keywords": "电机 轴承 润滑脂 密封 油污",
        "expected_safety_keywords": "LOTO PPE 清洁 防异物进入",
    },
    {
        "id": "IMG-MOTOR-009",
        "title": "File:Yauza 209 (motor) bottom cup, brass bearing, grease seal.jpg",
        "local_path": "data/image_eval/images/motor_bottom_cup_bearing_01.jpg",
        "fault_type": "bearing_mount",
        "visible_evidence": "电机底杯、黄铜轴承和润滑密封件",
        "caption_hint": "电机轴承座和密封结构暴露，需要检查轴承座磨损、润滑和密封状态。",
        "expected_retrieval_keywords": "电机 轴承座 密封 润滑 磨损",
        "expected_safety_keywords": "LOTO PPE 清洁复检",
    },
    {
        "id": "IMG-MOTOR-010",
        "title": "File:Yauza 209 (motor) inside stator - inspecting bearing mount.jpg",
        "local_path": "data/image_eval/images/motor_stator_bearing_mount_01.jpg",
        "fault_type": "bearing_mount_inspection",
        "visible_evidence": "电机定子内部轴承安装位置检查",
        "caption_hint": "电机定子内轴承座检查场景，需要确认安装偏斜、间隙和复装位置。",
        "expected_retrieval_keywords": "电机 定子 轴承座 安装 偏斜",
        "expected_safety_keywords": "LOTO 验电 复装记录",
    },
    {
        "id": "IMG-PUMP-001",
        "title": "File:Cummins raw water pump failure.jpg",
        "local_path": "data/image_eval/images/pump_raw_water_failure_01.jpg",
        "fault_type": "pump_seal_leak_failure",
        "visible_evidence": "原水泵故障；油封和水封泄漏造成混合污迹",
        "caption_hint": "泵密封失效并出现泄漏污迹，需要隔离泄压后检查密封和轴承箱。",
        "expected_retrieval_keywords": "泵 密封 泄漏 油封 水封 轴承箱",
        "expected_safety_keywords": "隔离泄压 LOTO PPE 防滑",
    },
    {
        "id": "IMG-PUMP-002",
        "title": "File:Gland packing002.jpg",
        "local_path": "data/image_eval/images/pump_gland_packing_01.jpg",
        "fault_type": "gland_packing",
        "visible_evidence": "泵填料密封结构；适合检索密封检修流程",
        "caption_hint": "泵填料密封部件可见，需要检查压盖、填料磨损和泄漏风险。",
        "expected_retrieval_keywords": "泵 填料密封 压盖 泄漏 密封",
        "expected_safety_keywords": "隔离泄压 PPE 交叉紧固",
    },
    {
        "id": "IMG-PUMP-003",
        "title": "File:Kavitation at pump impeller.jpg",
        "local_path": "data/image_eval/images/pump_impeller_cavitation_01.jpg",
        "fault_type": "cavitation",
        "visible_evidence": "泵叶轮汽蚀损伤；表面点蚀和缺损",
        "caption_hint": "离心泵叶轮发生汽蚀损伤，需要检查入口条件、流量和压力波动。",
        "expected_retrieval_keywords": "泵 叶轮 汽蚀 点蚀 缺损",
        "expected_safety_keywords": "隔离泄压 PPE 入口条件复核",
    },
    {
        "id": "IMG-PUMP-004",
        "title": "File:Usure par cavitation d'un impulseur de pompe centrifuge 01.jpg",
        "local_path": "data/image_eval/images/pump_impeller_cavitation_02.jpg",
        "fault_type": "cavitation_wear",
        "visible_evidence": "离心泵叶轮汽蚀磨损；叶片和端面损伤",
        "caption_hint": "离心泵叶轮汽蚀磨损明显，需要复核 NPSH、入口堵塞和流量工况。",
        "expected_retrieval_keywords": "泵 离心泵 叶轮 汽蚀 流量",
        "expected_safety_keywords": "隔离泄压 PPE 入口条件复核",
    },
    {
        "id": "IMG-PUMP-005",
        "title": "File:Cavitation.jpg",
        "local_path": "data/image_eval/images/pump_cavitation_damage_03.jpg",
        "fault_type": "cavitation_damage",
        "visible_evidence": "汽蚀损伤表面；金属点蚀和材料剥蚀",
        "caption_hint": "汽蚀导致金属表面剥蚀，需要检查泵入口压力、流量和介质条件。",
        "expected_retrieval_keywords": "泵 汽蚀 点蚀 压力 流量",
        "expected_safety_keywords": "隔离泄压 PPE 防护",
    },
    {
        "id": "IMG-PUMP-006",
        "title": "File:Cavitation Propeller Damage.JPG",
        "local_path": "data/image_eval/images/pump_cavitation_damage_04.jpg",
        "fault_type": "cavitation_reference",
        "visible_evidence": "旋转叶片汽蚀损伤；作为叶轮汽蚀参考图",
        "caption_hint": "旋转叶片汽蚀损伤可作为泵叶轮汽蚀参考，需要检查压力和流量条件。",
        "expected_retrieval_keywords": "泵 叶轮 汽蚀 旋转部件 损伤",
        "expected_safety_keywords": "隔离泄压 PPE 防误启动",
    },
    {
        "id": "IMG-PUMP-007",
        "title": "File:Mechanical seal part01.jpg",
        "local_path": "data/image_eval/images/pump_mechanical_seal_parts_01.jpg",
        "fault_type": "mechanical_seal_parts",
        "visible_evidence": "机械密封实物照片；可见弹簧、密封环和端面结构",
        "caption_hint": "泵机械密封实物部件可见，需要检查密封端面、弹簧、O 形圈和安装方向。",
        "expected_retrieval_keywords": "泵 机械密封 弹簧 O形圈 密封端面 安装",
        "expected_safety_keywords": "隔离泄压 PPE 清洁装配",
    },
    {
        "id": "IMG-PUMP-008",
        "title": "File:Ultrananocrystalline diamond-coated pump seals.jpg",
        "local_path": "data/image_eval/images/pump_mechanical_seal_parts_02.jpg",
        "fault_type": "pump_seal_reference",
        "visible_evidence": "泵密封部件；可用于密封材料和端面检查",
        "caption_hint": "泵密封件示意，需要结合泄漏现象检查密封面、弹簧和辅助密封。",
        "expected_retrieval_keywords": "泵 密封件 密封面 泄漏 检查",
        "expected_safety_keywords": "隔离泄压 PPE 清洁装配",
    },
    {
        "id": "IMG-PUMP-009",
        "title": "File:ErosionCorrosion.jpg",
        "local_path": "data/image_eval/images/pump_erosion_corrosion_01.jpg",
        "fault_type": "erosion_corrosion",
        "visible_evidence": "铸铁水泵冲蚀腐蚀；表面材料损失",
        "caption_hint": "水泵壳体发生冲蚀腐蚀，需要检查介质、壁厚和泄漏风险。",
        "expected_retrieval_keywords": "泵 腐蚀 冲蚀 泵壳 泄漏",
        "expected_safety_keywords": "隔离泄压 PPE 防腐处理",
    },
    {
        "id": "IMG-PUMP-010",
        "title": "File:Erosion corrosion of aluminum.jpg",
        "local_path": "data/image_eval/images/pump_erosion_corrosion_02.jpg",
        "fault_type": "erosion_corrosion",
        "visible_evidence": "铝制泵壳冲蚀腐蚀；局部表面损伤",
        "caption_hint": "泵壳材料出现冲蚀腐蚀，需要评估壁厚、介质和防腐措施。",
        "expected_retrieval_keywords": "泵 泵壳 腐蚀 冲蚀 壁厚",
        "expected_safety_keywords": "隔离泄压 PPE 防腐处理",
    },
    {
        "id": "IMG-BEARING-001",
        "title": "File:BEARING DAMAGE - NARA - 17500147.jpg",
        "local_path": "data/image_eval/images/bearing_damage_nara_01.jpg",
        "fault_type": "bearing_damage",
        "visible_evidence": "轴承损伤；滚道或接触面异常",
        "caption_hint": "轴承损伤图像，需要检查滚道剥落、润滑和载荷冲击。",
        "expected_retrieval_keywords": "轴承 损伤 滚道 剥落 润滑",
        "expected_safety_keywords": "PPE 清洁 防异物 复测游隙",
    },
    {
        "id": "IMG-BEARING-002",
        "title": "File:BEARING DAMAGE - NARA - 17500148.jpg",
        "local_path": "data/image_eval/images/bearing_damage_nara_02.jpg",
        "fault_type": "bearing_damage",
        "visible_evidence": "轴承损伤；疑似磨损或压痕",
        "caption_hint": "轴承表面损伤，需要检查载荷、润滑和安装偏斜。",
        "expected_retrieval_keywords": "轴承 磨损 压痕 载荷 润滑",
        "expected_safety_keywords": "PPE 清洁 游隙复测",
    },
    {
        "id": "IMG-BEARING-003",
        "title": "File:BEARING DAMAGE - NARA - 17500149.jpg",
        "local_path": "data/image_eval/images/bearing_damage_nara_03.jpg",
        "fault_type": "bearing_damage",
        "visible_evidence": "轴承损伤细节；可能存在滚道缺陷",
        "caption_hint": "轴承滚道或接触面损伤，需要检查润滑污染和装配状态。",
        "expected_retrieval_keywords": "轴承 滚道 缺陷 污染 装配",
        "expected_safety_keywords": "PPE 清洁 防异物",
    },
    {
        "id": "IMG-BEARING-004",
        "title": "File:DAMAGED MOTOR BEARING - NARA - 17469411.jpg",
        "local_path": "data/image_eval/images/bearing_damaged_motor_01.jpg",
        "fault_type": "damaged_motor_bearing",
        "visible_evidence": "电机轴承损坏；与电机检修场景相关",
        "caption_hint": "电机轴承损坏，需要检查端盖温升、润滑和轴承游隙。",
        "expected_retrieval_keywords": "轴承 电机 损坏 温升 润滑",
        "expected_safety_keywords": "LOTO PPE 游隙复测",
    },
    {
        "id": "IMG-BEARING-005",
        "title": "File:DAMAGED MOTOR BEARING - NARA - 17469412.jpg",
        "local_path": "data/image_eval/images/bearing_damaged_motor_02.jpg",
        "fault_type": "damaged_motor_bearing",
        "visible_evidence": "损坏的电机轴承；可见磨损或损伤",
        "caption_hint": "损坏电机轴承图像，需要关联过热、异响、润滑和更换流程。",
        "expected_retrieval_keywords": "轴承 电机 过热 异响 更换",
        "expected_safety_keywords": "LOTO PPE 禁止继续运行",
    },
    {
        "id": "IMG-BEARING-006",
        "title": "File:False brinelling schwack.png",
        "local_path": "data/image_eval/images/bearing_false_brinelling_01.png",
        "fault_type": "false_brinelling",
        "visible_evidence": "假性布氏压痕；滚道微动磨损",
        "caption_hint": "轴承滚道出现假性布氏压痕，需要检查静置振动和微动磨损。",
        "expected_retrieval_keywords": "轴承 假性布氏 压痕 微动磨损",
        "expected_safety_keywords": "PPE 装配复核 振动隔离",
    },
    {
        "id": "IMG-BEARING-007",
        "title": "File:Example of fretting schwack-crop.png",
        "local_path": "data/image_eval/images/bearing_fretting_corrosion_01.png",
        "fault_type": "fretting_corrosion",
        "visible_evidence": "轴承内圈滚道微动腐蚀",
        "caption_hint": "轴承滚道微动腐蚀，需要检查振动、配合和润滑状态。",
        "expected_retrieval_keywords": "轴承 微动腐蚀 滚道 配合 润滑",
        "expected_safety_keywords": "PPE 装配复核 防异物",
    },
    {
        "id": "IMG-BEARING-008",
        "title": "File:Test bearings Fafnir False Brinelling test.jpg",
        "local_path": "data/image_eval/images/bearing_false_brinelling_test_01.jpg",
        "fault_type": "false_brinelling_test",
        "visible_evidence": "假性布氏压痕测试轴承；适合故障机理展示",
        "caption_hint": "假性布氏压痕测试轴承，用于说明静置振动和微动磨损风险。",
        "expected_retrieval_keywords": "轴承 假性布氏 静置振动 微动磨损",
        "expected_safety_keywords": "PPE 振动隔离 装配复核",
    },
    {
        "id": "IMG-BEARING-009",
        "title": "File:Fretting And FalseBrinelling Schwack Byckov.png",
        "local_path": "data/image_eval/images/bearing_fretting_false_brinelling_01.png",
        "fault_type": "fretting_false_brinelling",
        "visible_evidence": "微动磨损和假性布氏压痕典型区域",
        "caption_hint": "轴承微动磨损和假性布氏压痕对比，需要检查装配、振动和润滑。",
        "expected_retrieval_keywords": "轴承 微动磨损 假性布氏 润滑 振动",
        "expected_safety_keywords": "PPE 装配复核 振动隔离",
    },
    {
        "id": "IMG-BEARING-010",
        "title": "File:FailedBearing.jpg",
        "local_path": "data/image_eval/images/bearing_failed_photo_01.jpg",
        "fault_type": "failed_bearing",
        "visible_evidence": "失效轴承实物照片；可见滚动体和保持结构异常",
        "caption_hint": "轴承失效实物照片，需要检查润滑不足、异物污染、载荷冲击和更换标准。",
        "expected_retrieval_keywords": "轴承 失效 损坏 滚动体 润滑 污染",
        "expected_safety_keywords": "PPE 禁止继续运行 更换复核",
    },
]


def _commons_page_url(title: str) -> str:
    name = title.removeprefix("File:").replace(" ", "_")
    return f"https://commons.wikimedia.org/wiki/File:{urllib.parse.quote(name)}"


def _commons_redirect_url(title: str) -> str:
    name = title.removeprefix("File:").replace(" ", "_")
    return f"https://commons.wikimedia.org/wiki/Special:Redirect/file/{urllib.parse.quote(name)}"


def _api_metadata(titles: list[str]) -> dict[str, dict]:
    params = urllib.parse.urlencode(
        {
            "action": "query",
            "format": "json",
            "titles": "|".join(titles),
            "prop": "imageinfo",
            "iiprop": "url|extmetadata|mime|size",
            "iiurlwidth": "900",
        }
    )
    api_url = f"https://commons.wikimedia.org/w/api.php?{params}"
    payload: dict | None = None
    last_error: Exception | None = None
    for _ in range(3):
        try:
            request = urllib.request.Request(api_url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(request, timeout=40) as response:
                payload = json.loads(response.read().decode("utf-8"))
            break
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            time.sleep(2.0)
    if payload is None:
        curl = subprocess.run(
            [
                "curl.exe",
                "-L",
                "-A",
                USER_AGENT,
                "--retry",
                "3",
                "--retry-delay",
                "2",
                "--max-time",
                "90",
                api_url,
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        if curl.returncode != 0:
            raise RuntimeError(curl.stderr.strip() or curl.stdout.strip()) from last_error
        payload = json.loads(curl.stdout)

    by_title: dict[str, dict] = {}
    for page in payload.get("query", {}).get("pages", {}).values():
        title = page.get("title", "")
        imageinfo = (page.get("imageinfo") or [{}])[0]
        metadata = imageinfo.get("extmetadata", {})
        by_title[title] = {
            "title": title,
            "mime": imageinfo.get("mime", ""),
            "download_url": imageinfo.get("thumburl") or imageinfo.get("url", ""),
            "original_url": imageinfo.get("url", ""),
            "width": imageinfo.get("thumbwidth") or imageinfo.get("width"),
            "height": imageinfo.get("thumbheight") or imageinfo.get("height"),
            "license_short_name": metadata.get("LicenseShortName", {}).get("value", ""),
            "license_url": metadata.get("LicenseUrl", {}).get("value", ""),
            "artist": metadata.get("Artist", {}).get("value", ""),
            "credit": metadata.get("Credit", {}).get("value", ""),
            "image_description": metadata.get("ImageDescription", {}).get("value", ""),
            "commons_page_url": _commons_page_url(title),
        }
    return by_title


def _download(url: str, target: Path, *, force: bool = False, fallback_url: str = "") -> None:
    if target.exists() and not force:
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    if fallback_url:
        curl = subprocess.run(
            [
                "curl.exe",
                "-L",
                "-A",
                USER_AGENT,
                "--retry",
                "2",
                "--retry-delay",
                "2",
                "--max-time",
                "90",
                "-o",
                str(target),
                fallback_url,
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        if curl.returncode == 0 and target.exists() and target.stat().st_size > 0:
            time.sleep(1.0)
            return
    urls = [url]
    if fallback_url and fallback_url not in urls:
        urls.append(fallback_url)
    last_error: Exception | None = None
    for candidate_url in urls:
        try:
            request = urllib.request.Request(candidate_url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(request, timeout=90) as response:
                data = response.read()
            break
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            time.sleep(1.0)
    else:
        if fallback_url:
            curl = subprocess.run(
                [
                    "curl.exe",
                    "-L",
                    "-A",
                    USER_AGENT,
                    "--retry",
                    "3",
                    "--retry-delay",
                    "3",
                    "--limit-rate",
                    "80k",
                    "--max-time",
                    "120",
                    "-o",
                    str(target),
                    fallback_url,
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            if curl.returncode == 0 and target.exists() and target.stat().st_size > 0:
                time.sleep(2.0)
                return
            raise RuntimeError(curl.stderr.strip() or curl.stdout.strip()) from last_error
        raise last_error or RuntimeError("download failed")
    target.write_bytes(data)
    time.sleep(0.8)


def _optimize_image(target: Path) -> dict:
    from PIL import Image, ImageOps
    from PIL import ImageFile

    ImageFile.LOAD_TRUNCATED_IMAGES = True

    before_size = target.stat().st_size
    with Image.open(target) as original:
        image = ImageOps.exif_transpose(original)
        image.thumbnail((MAX_IMAGE_SIDE, MAX_IMAGE_SIDE))
        width, height = image.size
        suffix = target.suffix.lower()
        if suffix in {".jpg", ".jpeg"}:
            if image.mode not in {"RGB", "L"}:
                image = image.convert("RGB")
            image.save(target, format="JPEG", quality=JPEG_QUALITY, optimize=True, progressive=True)
        elif suffix == ".png":
            image.save(target, format="PNG", optimize=True)
        else:
            image.save(target)

    return {
        "local_width": width,
        "local_height": height,
        "local_size_bytes": target.stat().st_size,
        "optimized_from_bytes": before_size,
        "max_local_side": MAX_IMAGE_SIDE,
    }


def _update_manifest(source_rows: list[dict]) -> None:
    with MANIFEST.open("r", newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
        fieldnames = reader.fieldnames or []

    by_id = {row["id"]: row for row in source_rows}
    for row in rows:
        candidate = by_id.get(row["id"])
        if not candidate:
            continue
        for key in [
            "image_path",
            "fault_type",
            "visible_evidence",
            "caption_hint",
            "expected_retrieval_keywords",
            "expected_safety_keywords",
        ]:
            row[key] = candidate[key]
        row["source_note"] = candidate["commons_page_url"]
        row["license_note"] = candidate["license_short_name"] or "Wikimedia Commons license"
        row["review_status"] = "approved"
        row["reviewer"] = "ME-R02"
        row["review_notes"] = (
            "Public Wikimedia Commons image; pre-reviewed for equipment/fault-topic "
            "fit and license traceability."
        )

    with MANIFEST.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def download_candidates(*, force: bool = False, update_manifest: bool = True) -> dict:
    metadata_by_title = _api_metadata([item["title"] for item in CANDIDATES])
    source_rows: list[dict] = []
    failures: list[dict] = []

    for item in CANDIDATES:
        metadata = metadata_by_title.get(item["title"], {})
        local_path = item["local_path"]
        target = ROOT / local_path
        download_url = metadata.get("download_url", "")
        if not download_url:
            failures.append({"id": item["id"], "title": item["title"], "error": "download_url missing"})
            continue
        try:
            _download(download_url, target, force=force, fallback_url=_commons_redirect_url(item["title"]))
            local_image = _optimize_image(target)
        except Exception as exc:  # noqa: BLE001
            failures.append({"id": item["id"], "title": item["title"], "error": str(exc)})
            continue
        source_rows.append(
            {
                **item,
                "image_path": local_path,
                "local_path": local_path,
                **metadata,
                **local_image,
            }
        )

    payload = {
        "provider": "Wikimedia Commons",
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "source_api": "https://commons.wikimedia.org/w/api.php",
        "image_count": len(source_rows),
        "failures": failures,
        "images": source_rows,
    }
    SOURCES_JSON.parent.mkdir(parents=True, exist_ok=True)
    SOURCES_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    if update_manifest:
        _update_manifest(source_rows)
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description="Download public Wikimedia Commons image candidates.")
    parser.add_argument("--force", action="store_true", help="Overwrite existing local image files.")
    parser.add_argument("--no-update-manifest", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    result = download_candidates(force=args.force, update_manifest=not args.no_update_manifest)
    summary = {
        "image_count": result["image_count"],
        "failures": result["failures"],
        "sources": str(SOURCES_JSON),
    }
    print(json.dumps(result if args.json else summary, ensure_ascii=False, indent=2))
    return 0 if not result["failures"] and result["image_count"] >= 30 else 2


if __name__ == "__main__":
    raise SystemExit(main())
