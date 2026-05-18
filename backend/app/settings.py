from __future__ import annotations

import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
ENV_FILES = [PROJECT_ROOT / ".env.local", PROJECT_ROOT / ".env"]
PROVIDER_NAMES = {"local", "openai", "opencode", "codex", "spatialai", "openrouter"}
GRAPH_BACKENDS = {"sqlite", "neo4j"}


def load_env_files() -> None:
    for path in ENV_FILES:
        if not path.exists():
            continue
        for raw in path.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            os.environ.setdefault(key, value)


def _provider_env(name: str, default: str) -> str:
    value = os.getenv(name, default).strip().lower()
    return value if value in PROVIDER_NAMES else default


def _model_env(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip()


def _graph_backend_env(name: str, default: str = "sqlite") -> str:
    value = os.getenv(name, default).strip().lower()
    return value if value in GRAPH_BACKENDS else default


def _csv_env(name: str, default: str) -> list[str]:
    raw = os.getenv(name, default)
    values = [item.strip().rstrip("/") for item in raw.split(",") if item.strip()]
    return values or [default]


def _float_env(name: str, default: float) -> float:
    raw = os.getenv(name, "").strip()
    if not raw:
        return default
    try:
        return float(raw)
    except ValueError:
        return default


def _bool_env(name: str, default: bool = False) -> bool:
    raw = os.getenv(name, "").strip().lower()
    if not raw:
        return default
    return raw in {"1", "true", "yes", "on"}


load_env_files()


class Settings:
    app_name = "A1-MAKG：面向设备检修的多模态证据链作业辅助系统"

    openai_base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
    openai_api_key_present = bool(os.getenv("OPENAI_API_KEY"))
    openai_text_model = os.getenv("OPENAI_TEXT_MODEL", "gpt-5.2")
    openai_vision_model = os.getenv("OPENAI_VISION_MODEL", "gpt-5.2")
    openai_embedding_model = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")

    opencode_base_url = os.getenv("OPENCODE_BASE_URL", "").rstrip("/")
    opencode_api_key_present = bool(os.getenv("OPENCODE_API_KEY"))
    opencode_text_model = os.getenv("OPENCODE_TEXT_MODEL", "")
    opencode_vision_model = os.getenv("OPENCODE_VISION_MODEL", "")
    opencode_embedding_model = os.getenv("OPENCODE_EMBEDDING_MODEL", "")

    codex_base_url = os.getenv(
        "CODEX_BASE_URL",
        os.getenv("OPENAI_BASE_URL", "https://spatialai.vip/v1"),
    ).rstrip("/")
    codex_api_key_present = bool(os.getenv("CODEX_API_KEY") or os.getenv("OPENAI_API_KEY"))
    codex_text_model = os.getenv("CODEX_TEXT_MODEL", "gpt-5.5")
    codex_vision_model = os.getenv("CODEX_VISION_MODEL", "")
    codex_embedding_model = os.getenv("CODEX_EMBEDDING_MODEL", "")

    openrouter_base_url = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1").rstrip("/")
    openrouter_api_key_present = bool(os.getenv("OPENROUTER_API_KEY"))
    openrouter_embedding_model = os.getenv(
        "OPENROUTER_EMBEDDING_MODEL", "qwen/qwen3-embedding-8b"
    )

    anthropic_base_url = os.getenv("ANTHROPIC_BASE_URL", "").rstrip("/")
    anthropic_key_present = bool(os.getenv("ANTHROPIC_AUTH_TOKEN") or os.getenv("ANTHROPIC_API_KEY"))
    anthropic_model = os.getenv("ANTHROPIC_MODEL", "")

    active_provider = _provider_env("ACTIVE_MODEL_PROVIDER", "local")

    text_agent_provider = _provider_env("TEXT_AGENT_PROVIDER", active_provider)
    text_agent_model = _model_env("TEXT_AGENT_MODEL")
    vision_agent_provider = _provider_env("VISION_AGENT_PROVIDER", active_provider)
    vision_agent_model = _model_env("VISION_AGENT_MODEL")
    embedding_agent_provider = _provider_env("EMBEDDING_AGENT_PROVIDER", active_provider)
    embedding_agent_model = _model_env("EMBEDDING_AGENT_MODEL")
    compliance_agent_provider = _provider_env("COMPLIANCE_AGENT_PROVIDER", text_agent_provider)
    compliance_agent_model = _model_env("COMPLIANCE_AGENT_MODEL")
    knowledge_agent_provider = _provider_env("KNOWLEDGE_AGENT_PROVIDER", text_agent_provider)
    knowledge_agent_model = _model_env("KNOWLEDGE_AGENT_MODEL")
    cors_allowed_origins = _csv_env("CORS_ALLOWED_ORIGINS", "*")
    model_request_timeout_seconds = _float_env("MODEL_REQUEST_TIMEOUT_SECONDS", 18.0)
    compliance_request_timeout_seconds = _float_env("COMPLIANCE_REQUEST_TIMEOUT_SECONDS", 6.0)
    vision_request_timeout_seconds = _float_env("VISION_REQUEST_TIMEOUT_SECONDS", 20.0)
    embedding_request_timeout_seconds = _float_env("EMBEDDING_REQUEST_TIMEOUT_SECONDS", 8.0)
    remote_query_embedding_enabled = _bool_env("REMOTE_QUERY_EMBEDDING_ENABLED", False)
    graph_backend = _graph_backend_env("GRAPH_BACKEND", "sqlite")
    neo4j_uri = os.getenv("NEO4J_URI", "").strip()
    neo4j_user = os.getenv("NEO4J_USER", "neo4j").strip()
    neo4j_password = os.getenv("NEO4J_PASSWORD", "").strip()
    neo4j_database = os.getenv("NEO4J_DATABASE", "neo4j").strip()
    graph_sync_on_startup = _bool_env("GRAPH_SYNC_ON_STARTUP", False)

    def provider_for_role(self, role: str) -> str:
        return {
            "text": self.text_agent_provider,
            "vision": self.vision_agent_provider,
            "embedding": self.embedding_agent_provider,
            "compliance": self.compliance_agent_provider,
            "knowledge": self.knowledge_agent_provider,
        }.get(role, self.active_provider)

    def model_for_role(self, role: str) -> str:
        return {
            "text": self.text_agent_model,
            "vision": self.vision_agent_model,
            "embedding": self.embedding_agent_model,
            "compliance": self.compliance_agent_model,
            "knowledge": self.knowledge_agent_model,
        }.get(role, "")


settings = Settings()
