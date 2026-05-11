from __future__ import annotations

import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MATERIALS = ROOT / "materials"
DECK_DIR = MATERIALS / "defense_image_deck"
PREVIEW_DIR = ROOT / "tmp" / "ppt_polished_preview"

OUTPUT = MATERIALS / "A1-defense-delivery-pack.zip"
FINAL_PPT = MATERIALS / "A1-maintenance-assistant-defense-image-only-final.pptx"
POLISHED_PPT = MATERIALS / "A1-maintenance-assistant-defense-gpt-image-2-polished.pptx"
LEGACY_GPT_IMAGE_PPT = MATERIALS / "A1-maintenance-assistant-defense-gpt-image-2.pptx"


DOCS = [
    "completion_audit.md",
    "defense_qna.md",
    "delivery_manifest.md",
    "demo_runbook.md",
    "final_image_only_delivery.md",
    "final_resource_checklist.md",
    "official_source_candidates.md",
    "polish_notes.md",
    "rubric_alignment.md",
    "security_scan_report.md",
    "slide_qa_report.md",
    "speaker_notes_10min.md",
    "speaker_notes_polished.md",
    "team_info.template.json",
    "user_inputs_needed.md",
    "verification_report.md",
    "verification_report.json",
]

SCRIPTS = [
    "build_defense_delivery_pack.py",
    "build_defense_image_only_final.py",
    "polish_gpt_image_deck.py",
    "verify_defense_materials.py",
]

SUMMARY_FILES = [
    "deployment_summary.json",
    "deployment_summary.md",
    "evaluation_summary.json",
    "evaluation_summary.md",
    "mechanical_review_summary.json",
    "mechanical_review_summary.md",
]

SCREENSHOTS = [
    "01_text_query.png",
    "02_image_search.png",
    "02_image_upload_caption.png",
    "03_sop_generation.png",
    "04_compliance_check.png",
    "05_case_review_update.png",
    "06_public_deploy_home.png",
    "07_public_health.png",
]


def _add_if_exists(archive: zipfile.ZipFile, source: Path, arcname: str) -> None:
    if source.exists():
        archive.write(source, arcname)


def build_delivery_pack(output: Path | str = OUTPUT) -> Path:
    target = Path(output)
    target.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        _add_if_exists(archive, FINAL_PPT, "ppt/A1-maintenance-assistant-defense-image-only-final.pptx")
        _add_if_exists(archive, POLISHED_PPT, "ppt/A1-maintenance-assistant-defense-gpt-image-2-polished.pptx")
        _add_if_exists(archive, LEGACY_GPT_IMAGE_PPT, "ppt/A1-maintenance-assistant-defense-gpt-image-2-source.pptx")
        _add_if_exists(archive, PREVIEW_DIR / "A1-maintenance-assistant-defense-gpt-image-2-polished.pdf", "ppt/A1-maintenance-assistant-defense-gpt-image-2-polished.pdf")
        _add_if_exists(archive, PREVIEW_DIR / "contact_sheet.jpg", "ppt/contact_sheet.jpg")
        _add_if_exists(archive, DECK_DIR / "final_image_only_contact_sheet.jpg", "ppt/final-image-only-contact-sheet.jpg")
        _add_if_exists(archive, DECK_DIR / "contact_sheet.jpg", "ppt/gpt-image-2-contact-sheet.jpg")

        for slide in sorted((DECK_DIR / "final_image_only_slides").glob("slide*.png")):
            _add_if_exists(archive, slide, f"final_slides/{slide.name}")
        for doc in DOCS:
            _add_if_exists(archive, DECK_DIR / doc, f"docs/{doc}")
        for summary in SUMMARY_FILES:
            _add_if_exists(archive, DECK_DIR / summary, f"data_summaries/{summary}")
        for shot in SCREENSHOTS:
            _add_if_exists(archive, DECK_DIR / "real_screenshots" / shot, f"screenshots/{shot}")
        for script in SCRIPTS:
            _add_if_exists(archive, ROOT / "scripts" / script, f"scripts/{script}")

    return target


def main() -> int:
    print(build_delivery_pack())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
