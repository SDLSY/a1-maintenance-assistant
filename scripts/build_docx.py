from __future__ import annotations

import argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE_MD = ROOT / "docs" / "WORK_DESCRIPTION.md"
DEFAULT_OUTPUT = ROOT / "materials" / "A1-maintenance-assistant-work-description.docx"


def _set_style_font(style, *, name: str = "Microsoft YaHei", size: int | None = None) -> None:
    from docx.oxml.ns import qn
    from docx.shared import Pt

    style.font.name = name
    style._element.rPr.rFonts.set(qn("w:eastAsia"), name)
    if size:
        style.font.size = Pt(size)


def _configure_document(document) -> None:
    from docx.shared import Inches

    section = document.sections[0]
    section.top_margin = Inches(0.75)
    section.bottom_margin = Inches(0.75)
    section.left_margin = Inches(0.85)
    section.right_margin = Inches(0.85)

    for style_name, size in (
        ("Normal", 10),
        ("Title", 20),
        ("Heading 1", 16),
        ("Heading 2", 13),
        ("Heading 3", 11),
    ):
        _set_style_font(document.styles[style_name], size=size)


def _is_table_separator(line: str) -> bool:
    stripped = line.strip()
    return stripped.startswith("|") and set(stripped.replace("|", "").replace(":", "").replace(" ", "")) <= {"-"}


def _parse_table_row(line: str) -> list[str]:
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def _add_table(document, rows: list[list[str]]) -> None:
    if not rows:
        return
    table = document.add_table(rows=0, cols=len(rows[0]))
    table.style = "Table Grid"
    for row_index, row_values in enumerate(rows):
        cells = table.add_row().cells
        for index, value in enumerate(row_values):
            cells[index].text = value
            for paragraph in cells[index].paragraphs:
                for run in paragraph.runs:
                    run.font.name = "Microsoft YaHei"
                    run.font.size = None
                    if row_index == 0:
                        run.bold = True
    document.add_paragraph()


def build_work_description_docx(
    source_path: Path | str = SOURCE_MD,
    output_path: Path | str = DEFAULT_OUTPUT,
) -> Path:
    try:
        from docx import Document
    except ModuleNotFoundError as exc:  # pragma: no cover - developer setup hint.
        raise SystemExit("python-docx is required: .\\.venv\\Scripts\\python.exe -m pip install python-docx") from exc

    source = Path(source_path)
    output = Path(output_path)
    lines = source.read_text(encoding="utf-8").splitlines()

    document = Document()
    _configure_document(document)

    in_code = False
    table_rows: list[list[str]] = []

    def flush_table() -> None:
        nonlocal table_rows
        if table_rows:
            _add_table(document, table_rows)
            table_rows = []

    for raw_line in lines:
        line = raw_line.rstrip()
        stripped = line.strip()

        if stripped.startswith("```"):
            flush_table()
            in_code = not in_code
            continue

        if in_code:
            if stripped:
                paragraph = document.add_paragraph(stripped)
                for run in paragraph.runs:
                    run.font.name = "Consolas"
            continue

        if not stripped:
            flush_table()
            continue

        if stripped.startswith("|") and stripped.endswith("|"):
            if not _is_table_separator(stripped):
                table_rows.append(_parse_table_row(stripped))
            continue

        flush_table()

        if stripped.startswith("# "):
            document.add_heading(stripped[2:].strip(), level=0)
        elif stripped.startswith("## "):
            document.add_heading(stripped[3:].strip(), level=1)
        elif stripped.startswith("### "):
            document.add_heading(stripped[4:].strip(), level=2)
        elif stripped.startswith("- "):
            document.add_paragraph(stripped[2:].strip(), style="List Bullet")
        elif stripped[:3].replace(".", "").isdigit() and ". " in stripped[:5]:
            document.add_paragraph(stripped.split(". ", 1)[1], style="List Number")
        else:
            document.add_paragraph(stripped)

    flush_table()
    output.parent.mkdir(parents=True, exist_ok=True)
    document.save(output)
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the A1 work description DOCX draft.")
    parser.add_argument("--source", type=Path, default=SOURCE_MD)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    output = build_work_description_docx(args.source, args.output)
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
