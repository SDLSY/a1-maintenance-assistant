from __future__ import annotations

import argparse
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PROFILE_CATALOG = ROOT / "config" / "model_profiles.json"
DEFAULT_ENV_FILE = ROOT / ".env.local"


def load_profiles(catalog_path: Path = PROFILE_CATALOG) -> dict:
    return json.loads(catalog_path.read_text(encoding="utf-8"))


def _parse_env_lines(lines: list[str]) -> dict[str, int]:
    indexes: dict[str, int] = {}
    for index, raw in enumerate(lines):
        stripped = raw.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key = stripped.split("=", 1)[0].strip()
        indexes[key] = index
    return indexes


def _render_line(key: str, value: str) -> str:
    return f"{key}={value}"


def apply_profile(
    profile_name: str,
    *,
    env_file: Path | str = DEFAULT_ENV_FILE,
    dry_run: bool = False,
    catalog_path: Path = PROFILE_CATALOG,
) -> dict:
    catalog = load_profiles(catalog_path)
    profiles = catalog["profiles"]
    if profile_name not in profiles:
        available = ", ".join(sorted(profiles))
        raise KeyError(f"Unknown profile {profile_name!r}. Available profiles: {available}")

    variables: dict[str, str] = profiles[profile_name]["variables"]
    forbidden = [key for key in variables if "KEY" in key or "TOKEN" in key or "SECRET" in key]
    if forbidden:
        raise ValueError(f"Profile variables must not contain secrets: {forbidden}")

    target = Path(env_file)
    lines = target.read_text(encoding="utf-8").splitlines() if target.exists() else []
    indexes = _parse_env_lines(lines)
    changes: list[dict] = []

    for key, value in variables.items():
        new_line = _render_line(key, value)
        if key in indexes:
            old_line = lines[indexes[key]]
            if old_line != new_line:
                changes.append({"key": key, "action": "update"})
                lines[indexes[key]] = new_line
        else:
            changes.append({"key": key, "action": "append"})
            lines.append(new_line)

    if not dry_run:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")

    return {
        "profile": profile_name,
        "env_file": str(target),
        "dry_run": dry_run,
        "changed": len(changes),
        "changes": changes,
        "summary": profiles[profile_name].get("summary", ""),
    }


def list_profiles(catalog_path: Path = PROFILE_CATALOG) -> dict:
    catalog = load_profiles(catalog_path)
    return {
        name: {
            "label": profile.get("label", name),
            "summary": profile.get("summary", ""),
            "variables": profile["variables"],
        }
        for name, profile in catalog["profiles"].items()
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Apply a model routing profile to .env.local.")
    parser.add_argument("profile", nargs="?", help="Profile name, for example current or china.")
    parser.add_argument("--env-file", type=Path, default=DEFAULT_ENV_FILE)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--list", action="store_true", help="List available profiles and exit.")
    args = parser.parse_args()

    if args.list:
        print(json.dumps(list_profiles(), ensure_ascii=False, indent=2))
        return 0
    if not args.profile:
        parser.error("profile is required unless --list is used")

    result = apply_profile(args.profile, env_file=args.env_file, dry_run=args.dry_run)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
