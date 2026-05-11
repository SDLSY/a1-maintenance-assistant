from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.model_gateway import agent_route_report, probe_all_models, safe_provider_report  # noqa: E402


def main() -> None:
    print("Provider config, redacted:")
    print(json.dumps(safe_provider_report(), ensure_ascii=False, indent=2))
    print("\nAgent routing, redacted:")
    print(json.dumps(agent_route_report(), ensure_ascii=False, indent=2))
    print("\nModel discovery:")
    print(json.dumps(probe_all_models(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
