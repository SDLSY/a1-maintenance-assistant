from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


ROLE_KEYS = {
    "TEXT_AGENT_PROVIDER",
    "TEXT_AGENT_MODEL",
    "VISION_AGENT_PROVIDER",
    "VISION_AGENT_MODEL",
    "EMBEDDING_AGENT_PROVIDER",
    "EMBEDDING_AGENT_MODEL",
    "COMPLIANCE_AGENT_PROVIDER",
    "COMPLIANCE_AGENT_MODEL",
    "KNOWLEDGE_AGENT_PROVIDER",
    "KNOWLEDGE_AGENT_MODEL",
}


def test_model_profiles_define_current_and_china_without_secrets() -> None:
    catalog = json.loads((ROOT / "config" / "model_profiles.json").read_text(encoding="utf-8"))

    assert set(catalog["profiles"]) >= {"current", "china"}
    for name, profile in catalog["profiles"].items():
        variables = profile["variables"]
        assert ROLE_KEYS <= set(variables)
        assert variables["MODEL_PROFILE"] == name
        assert not any("KEY" in key or "TOKEN" in key or "SECRET" in key for key in variables)
        assert all(value.strip() for value in variables.values())

    china_vars = catalog["profiles"]["china"]["variables"]
    assert china_vars["TEXT_AGENT_PROVIDER"] == "opencode"
    assert china_vars["VISION_AGENT_PROVIDER"] == "opencode"
    assert china_vars["EMBEDDING_AGENT_PROVIDER"] == "openrouter"
    assert "qwen" in china_vars["EMBEDDING_AGENT_MODEL"].lower()
    assert any(
        marker in china_vars[key].lower()
        for key in ["TEXT_AGENT_MODEL", "VISION_AGENT_MODEL", "COMPLIANCE_AGENT_MODEL", "KNOWLEDGE_AGENT_MODEL"]
        for marker in ["qwen", "deepseek", "glm", "kimi", "mimo", "minimax"]
    )


def test_apply_model_profile_preserves_keys_and_updates_routes(tmp_path: Path) -> None:
    from scripts.apply_model_profile import apply_profile

    env_file = tmp_path / ".env.local"
    env_file.write_text(
        "\n".join(
            [
                "OPENCODE_API_KEY=keep-opencode-key",
                "OPENROUTER_API_KEY=keep-openrouter-key",
                "TEXT_AGENT_PROVIDER=codex",
                "TEXT_AGENT_MODEL=gpt-5.5",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    result = apply_profile("china", env_file=env_file, dry_run=False)
    content = env_file.read_text(encoding="utf-8")

    assert result["profile"] == "china"
    assert "OPENCODE_API_KEY=keep-opencode-key" in content
    assert "OPENROUTER_API_KEY=keep-openrouter-key" in content
    assert "MODEL_PROFILE=china" in content
    assert "TEXT_AGENT_PROVIDER=opencode" in content
    assert "EMBEDDING_AGENT_PROVIDER=openrouter" in content
