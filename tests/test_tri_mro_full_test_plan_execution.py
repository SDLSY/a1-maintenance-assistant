from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


REQUIRED_CASE_IDS = {
    "T01",
    "T02",
    "T03",
    "T04",
    "T05",
    "T20",
    "T25",
    "T30",
    "T40",
    "T41",
    "T42",
    "T45",
    "T46",
    "T50",
    "T53",
    "T60",
    "T63",
    "T68",
    "T71",
    "T76",
    "T78",
    "T90",
    "T110",
    "T120",
    "T130",
}


def test_full_test_plan_assets_cover_numbered_cases() -> None:
    plan = ROOT / "docs" / "TRI_MRO_TEST_PLAN.md"
    cases_path = ROOT / "data" / "demo" / "tri_mro_test_cases.json"
    runner = ROOT / "scripts" / "execute_tri_mro_test_plan.py"

    assert plan.exists()
    assert cases_path.exists()
    assert runner.exists()

    plan_text = plan.read_text(encoding="utf-8")
    for marker in ("Claim Card", "Evidence Budget", "Safety Gate", "Knowledge Write Pipeline", "LoongArch"):
        assert marker in plan_text

    payload = json.loads(cases_path.read_text(encoding="utf-8"))
    case_ids = {case["id"] for case in payload["test_cases"]}
    assert REQUIRED_CASE_IDS <= case_ids
    assert {case["id"] for case in payload["golden_cases"]} == {"G01", "G02", "G03", "G04"}
    assert {"A01", "A02", "A03", "A04", "A05", "A06", "A07", "A08"} <= {
        case["id"] for case in payload["adverse_cases"]
    }


def test_full_test_cases_have_execution_modes_and_exit_criteria() -> None:
    payload = json.loads((ROOT / "data" / "demo" / "tri_mro_test_cases.json").read_text(encoding="utf-8"))
    valid_modes = {"automated", "browser_smoke", "manual", "environment", "not_implemented"}
    valid_priorities = {"P0", "P1", "P2"}
    for case in payload["test_cases"]:
        assert case["id"]
        assert case["priority"] in valid_priorities
        assert case["execution_mode"] in valid_modes
        assert case["objective"]
        assert case["expected"]
        assert case["acceptance"]
    assert any(case["execution_mode"] == "environment" for case in payload["test_cases"])
    assert any(case["execution_mode"] == "manual" for case in payload["test_cases"])


def test_full_test_plan_runner_generates_execution_report(tmp_path: Path) -> None:
    from scripts.execute_tri_mro_test_plan import execute_plan

    result = execute_plan(output_dir=tmp_path)
    assert result["summary"]["total"] >= 60
    assert result["summary"]["automated_passed"] >= 20
    assert result["summary"]["failed"] == 0
    assert result["summary"]["manual_or_environment"] >= 1
    assert (tmp_path / "tri-mro-full-test-execution.json").exists()
    assert (tmp_path / "tri-mro-full-test-execution.md").exists()
