from __future__ import annotations

import base64
import json
import mimetypes
import os
import urllib.error
import urllib.request
from dataclasses import dataclass

from .settings import settings


@dataclass
class ProviderStatus:
    name: str
    kind: str
    base_url: str
    key_present: bool
    default_model: str


TEXT_ROLES = {"text", "compliance", "knowledge"}


def providers() -> list[ProviderStatus]:
    return [
        ProviderStatus(
            "openai",
            "openai-compatible",
            settings.openai_base_url,
            settings.openai_api_key_present,
            settings.openai_text_model,
        ),
        ProviderStatus(
            "opencode",
            "openai-compatible",
            settings.opencode_base_url,
            settings.opencode_api_key_present,
            settings.opencode_text_model,
        ),
        ProviderStatus(
            "codex",
            "openai-compatible",
            settings.codex_base_url,
            settings.codex_api_key_present,
            settings.codex_text_model,
        ),
        ProviderStatus(
            "openrouter",
            "embeddings",
            settings.openrouter_base_url,
            settings.openrouter_api_key_present,
            settings.openrouter_embedding_model,
        ),
        ProviderStatus(
            "spatialai",
            "anthropic-compatible",
            settings.anthropic_base_url,
            settings.anthropic_key_present,
            settings.anthropic_model,
        ),
        ProviderStatus("local", "deterministic", "", True, "local-rule-engine"),
    ]


def _provider_status(name: str) -> ProviderStatus:
    return {provider.name: provider for provider in providers()}[name]


def _key_for(provider: str) -> str:
    if provider == "openai":
        return os.getenv("OPENAI_API_KEY", "")
    if provider == "opencode":
        return os.getenv("OPENCODE_API_KEY", "")
    if provider == "codex":
        return os.getenv("CODEX_API_KEY") or os.getenv("OPENAI_API_KEY", "")
    if provider == "openrouter":
        return os.getenv("OPENROUTER_API_KEY", "")
    if provider == "spatialai":
        return os.getenv("ANTHROPIC_AUTH_TOKEN") or os.getenv("ANTHROPIC_API_KEY") or ""
    return ""


def _anthropic_headers(*, content_type: bool = False) -> dict[str, str]:
    headers = {
        "anthropic-version": "2023-06-01",
        "Accept": "application/json",
    }
    auth_token = os.getenv("ANTHROPIC_AUTH_TOKEN")
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if auth_token:
        headers["Authorization"] = f"Bearer {auth_token}"
    elif api_key:
        headers["x-api-key"] = api_key
    if content_type:
        headers["Content-Type"] = "application/json"
    return headers


def _default_model_for(provider: str, role: str) -> str:
    if provider == "openai":
        if role == "vision":
            return settings.openai_vision_model
        if role == "embedding":
            return settings.openai_embedding_model
        return settings.openai_text_model
    if provider == "opencode":
        if role == "vision":
            return settings.opencode_vision_model or settings.opencode_text_model
        if role == "embedding":
            return settings.opencode_embedding_model or settings.opencode_text_model
        return settings.opencode_text_model
    if provider == "codex":
        if role == "vision":
            return settings.codex_vision_model or settings.codex_text_model
        if role == "embedding":
            return settings.codex_embedding_model or settings.codex_text_model
        return settings.codex_text_model
    if provider == "openrouter":
        return settings.openrouter_embedding_model if role == "embedding" else ""
    if provider == "spatialai":
        return settings.anthropic_model if role in TEXT_ROLES else ""
    if provider == "local":
        if role == "embedding":
            return "local-hash-embedding-v1"
        if role == "vision":
            return "local-image-caption"
        return "local-rule-engine"
    return ""


def _role_supported(provider: str, role: str) -> bool:
    if provider == "local":
        return True
    if provider in {"openai", "opencode", "codex"}:
        return role in {"text", "vision", "embedding", "compliance", "knowledge"}
    if provider == "openrouter":
        return role == "embedding"
    if provider == "spatialai":
        return role in TEXT_ROLES
    return False


def agent_route_report() -> list[dict]:
    labels = {
        "text": "诊断与SOP",
        "vision": "图片描述",
        "embedding": "向量检索",
        "compliance": "合规复核",
        "knowledge": "知识沉淀",
    }
    routes = []
    for role, label in labels.items():
        provider = settings.provider_for_role(role)
        provider_status = _provider_status(provider)
        model = settings.model_for_role(role) or _default_model_for(provider, role)
        routes.append(
            {
                "role": role,
                "label": label,
                "provider": provider,
                "kind": provider_status.kind,
                "base_url": provider_status.base_url,
                "key_present": provider_status.key_present,
                "model": model or "(not configured)",
                "supported": _role_supported(provider, role),
            }
        )
    return routes


def safe_provider_report() -> list[dict]:
    roles_by_provider: dict[str, list[str]] = {}
    for route in agent_route_report():
        roles_by_provider.setdefault(route["provider"], []).append(route["role"])
    return [
        {
            "name": p.name,
            "kind": p.kind,
            "base_url": p.base_url,
            "key_present": p.key_present,
            "default_model": p.default_model or "(not configured)",
            "active": p.name in roles_by_provider or p.name == settings.active_provider,
            "roles": roles_by_provider.get(p.name, []),
        }
        for p in providers()
    ]


def _request_json(url: str, headers: dict[str, str], payload: dict | None = None) -> dict:
    request_headers = dict(headers)
    if not any(key.lower() == "user-agent" for key in request_headers):
        request_headers["User-Agent"] = (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 Chrome/124 Safari/537.36"
        )
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(url, data=data, headers=request_headers, method="GET" if data is None else "POST")
    with urllib.request.urlopen(request, timeout=90) as response:
        return json.loads(response.read().decode("utf-8"))


def _openai_base_key_model(provider: str, role: str, model: str | None) -> tuple[str, str, str]:
    status = _provider_status(provider)
    return status.base_url, _key_for(provider), model or _default_model_for(provider, role)


def _anthropic_url(path: str) -> str:
    base_url = settings.anthropic_base_url.rstrip("/")
    if base_url.endswith("/v1") and path.startswith("/v1/"):
        return f"{base_url}{path[3:]}"
    return f"{base_url}{path}"


def generate_text(
    system: str,
    user: str,
    fallback: str,
    *,
    role: str = "text",
    provider: str | None = None,
    model: str | None = None,
) -> dict:
    """Generate text through the role route, returning fallback on failure."""
    selected_provider = provider or settings.provider_for_role(role)
    selected_model = model or settings.model_for_role(role) or _default_model_for(selected_provider, role)
    if selected_provider == "local":
        return {"ok": True, "provider": "local", "model": selected_model, "text": fallback}
    if not _role_supported(selected_provider, role):
        return {
            "ok": False,
            "provider": selected_provider,
            "model": selected_model,
            "error": f"{selected_provider} does not support role {role}",
            "text": fallback,
        }
    if not selected_model:
        return {
            "ok": False,
            "provider": selected_provider,
            "model": "",
            "error": f"model not configured for role {role}",
            "text": fallback,
        }

    if selected_provider in {"openai", "opencode", "codex"}:
        base_url, api_key, selected_model = _openai_base_key_model(
            selected_provider, role, selected_model
        )
        if not base_url or not api_key:
            return {
                "ok": False,
                "provider": selected_provider,
                "model": selected_model,
                "error": "base_url or key missing",
                "text": fallback,
            }
        try:
            data = _request_json(
                f"{base_url.rstrip('/')}/chat/completions",
                {
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                },
                {
                    "model": selected_model,
                    "messages": [
                        {"role": "system", "content": system},
                        {"role": "user", "content": user},
                    ],
                    "temperature": 0.2,
                },
            )
            text = data["choices"][0]["message"]["content"]
            return {"ok": True, "provider": selected_provider, "model": selected_model, "text": text}
        except Exception as exc:  # noqa: BLE001 - relay compatibility varies.
            return {
                "ok": False,
                "provider": selected_provider,
                "model": selected_model,
                "error": str(exc),
                "text": fallback,
            }

    if selected_provider == "spatialai":
        api_key = _key_for("spatialai")
        if not settings.anthropic_base_url or not api_key:
            return {
                "ok": False,
                "provider": "spatialai",
                "model": selected_model,
                "error": "base_url or key missing",
                "text": fallback,
            }
        try:
            data = _request_json(
                _anthropic_url("/v1/messages"),
                _anthropic_headers(content_type=True),
                {
                    "model": selected_model,
                    "max_tokens": 1200,
                    "temperature": 0.2,
                    "system": system,
                    "messages": [{"role": "user", "content": user}],
                },
            )
            text = "".join(part.get("text", "") for part in data.get("content", []))
            return {"ok": True, "provider": "spatialai", "model": selected_model, "text": text}
        except Exception as exc:  # noqa: BLE001
            return {
                "ok": False,
                "provider": "spatialai",
                "model": selected_model,
                "error": str(exc),
                "text": fallback,
            }

    return {"ok": True, "provider": "local", "model": "local-rule-engine", "text": fallback}


def caption_image_file(path: str, fallback_caption: str) -> dict:
    selected_provider = settings.provider_for_role("vision")
    selected_model = settings.model_for_role("vision") or _default_model_for(selected_provider, "vision")
    mime = mimetypes.guess_type(path)[0] or "image/png"
    if selected_provider not in {"openai", "opencode", "codex"}:
        return {
            "ok": False,
            "provider": selected_provider,
            "model": selected_model,
            "error": f"{selected_provider} vision route is not enabled",
            "caption": fallback_caption,
        }
    if not selected_model:
        return {
            "ok": False,
            "provider": selected_provider,
            "model": "",
            "error": "vision model not configured",
            "caption": fallback_caption,
        }

    base_url, api_key, selected_model = _openai_base_key_model(
        selected_provider, "vision", selected_model
    )
    if not base_url or not api_key:
        return {
            "ok": False,
            "provider": selected_provider,
            "model": selected_model,
            "error": "base_url or key missing",
            "caption": fallback_caption,
        }
    try:
        with open(path, "rb") as handle:
            image_bytes = handle.read()
        image_url = f"data:{mime};base64,{base64.b64encode(image_bytes).decode('ascii')}"
        data = _request_json(
            f"{base_url.rstrip('/')}/chat/completions",
            {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            {
                "model": selected_model,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": "请作为工业设备检修专家，用一句中文描述图片中的设备、部件、故障迹象和可能风险。",
                            },
                            {"type": "image_url", "image_url": {"url": image_url}},
                        ],
                    }
                ],
                "temperature": 0.1,
            },
        )
        return {
            "ok": True,
            "provider": selected_provider,
            "model": selected_model,
            "caption": data["choices"][0]["message"]["content"],
        }
    except Exception as exc:  # noqa: BLE001
        return {
            "ok": False,
            "provider": selected_provider,
            "model": selected_model,
            "error": str(exc),
            "caption": fallback_caption,
        }


def embed_texts(texts: list[str]) -> dict:
    selected_provider = settings.provider_for_role("embedding")
    selected_model = settings.model_for_role("embedding") or _default_model_for(
        selected_provider, "embedding"
    )
    if selected_provider not in {"openai", "opencode", "codex", "openrouter"}:
        return {
            "ok": False,
            "provider": selected_provider,
            "model": selected_model,
            "error": "remote embedding disabled",
            "vectors": [],
        }
    if not selected_model:
        return {
            "ok": False,
            "provider": selected_provider,
            "model": "",
            "error": "embedding model not configured",
            "vectors": [],
        }

    base_url, api_key, selected_model = _openai_base_key_model(
        selected_provider, "embedding", selected_model
    )
    if not base_url or not api_key:
        return {
            "ok": False,
            "provider": selected_provider,
            "model": selected_model,
            "error": "base_url or key missing",
            "vectors": [],
        }
    try:
        data = _request_json(
            f"{base_url.rstrip('/')}/embeddings",
            {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            {
                "model": selected_model,
                "input": texts,
            },
        )
        ordered = sorted(data.get("data", []), key=lambda item: item.get("index", 0))
        return {
            "ok": True,
            "provider": selected_provider,
            "model": selected_model,
            "vectors": [item.get("embedding", []) for item in ordered],
        }
    except Exception as exc:  # noqa: BLE001
        return {
            "ok": False,
            "provider": selected_provider,
            "model": selected_model,
            "error": str(exc),
            "vectors": [],
        }


def list_openai_compatible_models(name: str, base_url: str, env_key: str) -> dict:
    api_key = os.getenv(env_key)
    if not base_url or not api_key:
        return {"provider": name, "ok": False, "error": "base_url or key missing", "models": []}
    try:
        data = _request_json(
            f"{base_url.rstrip('/')}/models",
            {"Authorization": f"Bearer {api_key}", "Accept": "application/json"},
        )
        models = data.get("data", [])
        return {
            "provider": name,
            "ok": True,
            "models": sorted(
                [item.get("id", "") for item in models if item.get("id")],
                key=str.lower,
            ),
        }
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        return {"provider": name, "ok": False, "error": str(exc), "models": []}


def list_anthropic_models() -> dict:
    api_key = _key_for("spatialai")
    if not settings.anthropic_base_url or not api_key:
        return {"provider": "spatialai", "ok": False, "error": "base_url or key missing", "models": []}
    try:
        data = _request_json(
            _anthropic_url("/v1/models"),
            _anthropic_headers(),
        )
        models = data.get("data", [])
        return {
            "provider": "spatialai",
            "ok": True,
            "models": sorted(
                [item.get("id", item.get("name", "")) for item in models if item.get("id") or item.get("name")],
                key=str.lower,
            ),
        }
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        return {"provider": "spatialai", "ok": False, "error": str(exc), "models": []}


def list_openrouter_embedding_models() -> dict:
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not settings.openrouter_base_url or not api_key:
        return {
            "provider": "openrouter",
            "ok": False,
            "error": "base_url or key missing",
            "models": [],
        }
    try:
        data = _request_json(
            f"{settings.openrouter_base_url.rstrip('/')}/embeddings/models",
            {"Authorization": f"Bearer {api_key}", "Accept": "application/json"},
        )
        models = data.get("data", [])
        return {
            "provider": "openrouter",
            "ok": True,
            "models": sorted(
                [item.get("id", item.get("canonical_slug", "")) for item in models if item.get("id") or item.get("canonical_slug")],
                key=str.lower,
            ),
        }
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        return {"provider": "openrouter", "ok": False, "error": str(exc), "models": []}


def probe_all_models() -> list[dict]:
    results = [
        list_openai_compatible_models("openai", settings.openai_base_url, "OPENAI_API_KEY"),
    ]
    if settings.opencode_base_url:
        results.append(
            list_openai_compatible_models("opencode", settings.opencode_base_url, "OPENCODE_API_KEY")
        )
    if settings.codex_base_url:
        results.append(
            list_openai_compatible_models("codex", settings.codex_base_url, "CODEX_API_KEY")
            if os.getenv("CODEX_API_KEY")
            else list_openai_compatible_models("codex", settings.codex_base_url, "OPENAI_API_KEY")
        )
    if settings.openrouter_base_url:
        results.append(list_openrouter_embedding_models())
    if settings.anthropic_base_url:
        results.append(list_anthropic_models())
    return results
