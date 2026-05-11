from __future__ import annotations

import hashlib
import json
import re
import subprocess
from pathlib import Path

from pptx import Presentation


ROOT = Path(__file__).resolve().parents[1]
DESKTOP_ROOT = ROOT.parent
MATERIALS = ROOT / "materials"
DECK_DIR = MATERIALS / "defense_image_deck"
PREVIEW_DIR = ROOT / "tmp" / "ppt_polished_preview"

SOURCE_PPT = MATERIALS / "A1-maintenance-assistant-defense-gpt-image-2.pptx"
POLISHED_PPT = MATERIALS / "A1-maintenance-assistant-defense-gpt-image-2-polished.pptx"
FINAL_IMAGE_ONLY_PPT = MATERIALS / "A1-maintenance-assistant-defense-image-only-final.pptx"
ROOT_COPY_PPT = DESKTOP_ROOT / "A1全图版答辩PPT-基于原文件润色版.pptx"
PDF_PREVIEW = PREVIEW_DIR / "A1-maintenance-assistant-defense-gpt-image-2-polished.pdf"
FINAL_IMAGE_ONLY_SLIDE_DIR = DECK_DIR / "final_image_only_slides"

REPORT_JSON = DECK_DIR / "verification_report.json"
REPORT_MD = DECK_DIR / "verification_report.md"

SENSITIVE_PATTERNS = [
    "sk-",
    "API_KEY",
    "AUTH_TOKEN",
    "ANTHROPIC",
    "OPENAI",
    "OPENROUTER",
    "OPENCODE",
    "SPATIALAI",
    ".env.local",
]

SENSITIVE_SCAN_EXCLUDED_FILES = {
    "security_scan_report.md",
    "verification_report.md",
    "verification_report.json",
}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def inspect_ppt(path: Path) -> dict:
    if not path.exists():
        return {
            "exists": False,
            "slides": 0,
            "pictures": 0,
            "text_shapes": 0,
            "xml_has_text": False,
            "sha256": "",
            "sensitive_hits": [],
        }

    prs = Presentation(str(path))
    pictures = 0
    text_shapes = 0
    text = []
    for slide in prs.slides:
        for shape in slide.shapes:
            if shape.shape_type == 13:
                pictures += 1
            if getattr(shape, "has_text_frame", False) and shape.text.strip():
                text_shapes += 1
                text.append(shape.text)
    return {
        "exists": path.exists(),
        "slides": len(prs.slides),
        "pictures": pictures,
        "text_shapes": text_shapes,
        "xml_has_text": ppt_xml_has_text(path),
        "sha256": sha256(path),
        "sensitive_hits": sensitive_hits("\n".join(text)),
    }


def ppt_xml_has_text(path: Path) -> bool:
    import zipfile

    with zipfile.ZipFile(path) as archive:
        slide_names = [
            name
            for name in archive.namelist()
            if name.startswith("ppt/slides/slide") and name.endswith(".xml")
        ]
        return any("<a:t>" in archive.read(name).decode("utf-8", errors="ignore") for name in slide_names)


def sensitive_hits(text: str) -> list[str]:
    lower = text.lower()
    return [pattern for pattern in SENSITIVE_PATTERNS if pattern.lower() in lower]


def markdown_heading_count(path: Path, pattern: str) -> int:
    if not path.exists():
        return -1
    regex = re.compile(pattern)
    return sum(1 for line in path.read_text(encoding="utf-8-sig").splitlines() if regex.search(line))


def pdf_pages(path: Path) -> int | None:
    if not path.exists():
        return None
    result = subprocess.run(
        ["pdfinfo", str(path)],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="ignore",
    )
    if result.returncode != 0:
        return None
    match = re.search(r"^Pages:\s+(\d+)$", result.stdout, re.MULTILINE)
    return int(match.group(1)) if match else None


def scan_materials_for_sensitive() -> list[str]:
    hits = []
    for path in DECK_DIR.rglob("*"):
        if not path.is_file() or path.suffix.lower() in {".png", ".jpg", ".jpeg", ".pptx", ".pdf"}:
            continue
        if path.name in SENSITIVE_SCAN_EXCLUDED_FILES:
            continue
        try:
            text = path.read_text(encoding="utf-8-sig")
        except UnicodeDecodeError:
            continue
        if sensitive_hits(text):
            hits.append(str(path.relative_to(ROOT)))
    return hits


def required_file_status() -> dict[str, bool]:
    required = [
        DECK_DIR / "polish_notes.md",
        DECK_DIR / "speaker_notes_polished.md",
        DECK_DIR / "speaker_notes_10min.md",
        DECK_DIR / "defense_qna.md",
        DECK_DIR / "demo_runbook.md",
        DECK_DIR / "slide_qa_report.md",
        DECK_DIR / "completion_audit.md",
        DECK_DIR / "delivery_manifest.md",
        DECK_DIR / "final_image_only_delivery.md",
        DECK_DIR / "final_resource_checklist.md",
        DECK_DIR / "official_source_candidates.md",
        DECK_DIR / "rubric_alignment.md",
        DECK_DIR / "security_scan_report.md",
        DECK_DIR / "verification_report.md",
        DECK_DIR / "verification_report.json",
        DECK_DIR / "team_info.template.json",
        FINAL_IMAGE_ONLY_PPT,
        MATERIALS / "A1-defense-delivery-pack.zip",
        ROOT / "scripts" / "build_defense_delivery_pack.py",
        ROOT / "scripts" / "build_defense_image_only_final.py",
        ROOT / "scripts" / "polish_gpt_image_deck.py",
        ROOT / "scripts" / "verify_defense_materials.py",
        PREVIEW_DIR / "contact_sheet.jpg",
        DECK_DIR / "final_image_only_contact_sheet.jpg",
    ]
    screenshots = [
        DECK_DIR / "real_screenshots" / "01_text_query.png",
        DECK_DIR / "real_screenshots" / "02_image_search.png",
        DECK_DIR / "real_screenshots" / "03_sop_generation.png",
        DECK_DIR / "real_screenshots" / "04_compliance_check.png",
        DECK_DIR / "real_screenshots" / "05_case_review_update.png",
        DECK_DIR / "real_screenshots" / "06_public_deploy_home.png",
        DECK_DIR / "real_screenshots" / "07_public_health.png",
    ]
    return {str(path.relative_to(ROOT)): path.exists() for path in required + screenshots}


def final_slide_image_count() -> int:
    if not FINAL_IMAGE_ONLY_SLIDE_DIR.exists():
        return 0
    return len([path for path in FINAL_IMAGE_ONLY_SLIDE_DIR.glob("slide*.png") if path.is_file()])


def build_report() -> dict:
    source = inspect_ppt(SOURCE_PPT)
    polished = inspect_ppt(POLISHED_PPT)
    final_image_only = inspect_ppt(FINAL_IMAGE_ONLY_PPT)
    root_copy = inspect_ppt(ROOT_COPY_PPT)
    files = required_file_status()
    checks = {
        "source_ppt_is_original_full_image_deck": source["slides"] == 14 and source["pictures"] == 14 and source["text_shapes"] == 0,
        "polished_ppt_shape": polished["slides"] == 18 and polished["pictures"] >= 20 and polished["text_shapes"] >= 160,
        "final_image_only_deck_shape": final_image_only["slides"] == 18 and final_image_only["pictures"] == 18 and final_image_only["text_shapes"] == 0,
        "final_image_only_xml_has_no_text": not final_image_only["xml_has_text"],
        "final_slide_images_exist": final_slide_image_count() == 18,
        "root_copy_matches_polished": polished["sha256"] == root_copy["sha256"],
        "pdf_preview_pages": pdf_pages(PDF_PREVIEW) == 18,
        "speaker_notes_pages": markdown_heading_count(DECK_DIR / "speaker_notes_polished.md", r"^## \d{2} ") == 18,
        "qna_count": markdown_heading_count(DECK_DIR / "defense_qna.md", r"^## \d+\. ") == 18,
        "all_required_files_exist": all(files.values()),
        "ppt_sensitive_hits_empty": (
            not source["sensitive_hits"]
            and not polished["sensitive_hits"]
            and not final_image_only["sensitive_hits"]
            and not root_copy["sensitive_hits"]
        ),
        "materials_sensitive_hits_empty": not scan_materials_for_sensitive(),
    }
    return {
        "status": "ok" if all(checks.values()) else "needs_attention",
        "checks": checks,
        "source_ppt": source,
        "polished_ppt": polished,
        "final_image_only_ppt": final_image_only,
        "root_copy_ppt": root_copy,
        "pdf_preview_pages": pdf_pages(PDF_PREVIEW),
        "final_slide_image_count": final_slide_image_count(),
        "markdown_counts": {
            "speaker_notes_polished": markdown_heading_count(DECK_DIR / "speaker_notes_polished.md", r"^## \d{2} "),
            "defense_qna": markdown_heading_count(DECK_DIR / "defense_qna.md", r"^## \d+\. "),
        },
        "required_files": files,
        "material_sensitive_hits": scan_materials_for_sensitive(),
        "remaining_blockers": [
            "school/team/member/advisor display rules are still user-provided and missing",
            "public deployment should be rechecked on the formal defense day",
            "final frontend screenshots should replace slide 15 if the UI is rebuilt",
        ],
    }


def write_markdown(report: dict) -> str:
    lines = [
        "# A1 答辩材料验证报告",
        "",
        f"- overall_status: `{report['status']}`",
        f"- source_slides: `{report['source_ppt']['slides']}`",
        f"- polished_slides: `{report['polished_ppt']['slides']}`",
        f"- final_image_only_slides: `{report['final_image_only_ppt']['slides']}`",
        f"- final_image_only_text_shapes: `{report['final_image_only_ppt']['text_shapes']}`",
        f"- final_slide_image_count: `{report['final_slide_image_count']}`",
        f"- root_copy_matches_polished: `{report['checks']['root_copy_matches_polished']}`",
        f"- pdf_preview_pages: `{report['pdf_preview_pages']}`",
        "",
        "## Checks",
        "",
        "| check | result |",
        "|---|---:|",
    ]
    for key, value in report["checks"].items():
        lines.append(f"| {key} | {value} |")
    lines.extend(["", "## Remaining Blockers", ""])
    for item in report["remaining_blockers"]:
        lines.append(f"- {item}")
    lines.extend(["", "## Sensitive Scan", ""])
    lines.append(f"- PPT sensitive hits empty: `{report['checks']['ppt_sensitive_hits_empty']}`")
    lines.append(f"- Material sensitive hits: `{report['material_sensitive_hits']}`")
    return "\n".join(lines) + "\n"


def main() -> None:
    report = build_report()
    REPORT_JSON.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    REPORT_MD.write_text(write_markdown(report), encoding="utf-8")
    print(REPORT_JSON)
    print(REPORT_MD)
    print(report["status"])


if __name__ == "__main__":
    main()
