from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))


def smoke_text(role: str, provider: str | None = None, model: str | None = None) -> dict:
    from app.model_gateway import generate_text

    result = generate_text(
        "你是设备检修系统的模型连通性测试器，只需要简短回答。",
        "请只回复：OK",
        "LOCAL_FALLBACK",
        role=role,
        provider=provider,
        model=model,
    )
    return {
        "role": role,
        "provider": result.get("provider"),
        "model": result.get("model"),
        "ok": result.get("ok"),
        "error": result.get("error", ""),
        "sample": (result.get("text") or "")[:80],
    }


def smoke_embedding(provider: str | None = None, model: str | None = None) -> dict:
    from app.model_gateway import agent_route_report, embed_texts
    from app.vector_index import local_embedding

    route = next((item for item in agent_route_report() if item["role"] == "embedding"), {})
    if route.get("provider") == "local":
        vector = local_embedding("motor bearing vibration fault")
        return {
            "role": "embedding",
            "provider": "local",
            "model": route.get("model", "local-hash-embedding-v1"),
            "ok": True,
            "error": "",
            "vector_dim": len(vector),
        }
    result = embed_texts(["motor bearing vibration fault"])
    if provider or model:
        return {
            "role": "embedding",
            "provider": result.get("provider"),
            "model": result.get("model"),
            "ok": result.get("ok"),
            "error": "direct provider/model override is only supported for text smoke tests",
            "vector_dim": len(result.get("vectors", [[]])[0]) if result.get("vectors") else 0,
        }
    return {
        "role": "embedding",
        "provider": result.get("provider"),
        "model": result.get("model"),
        "ok": result.get("ok"),
        "error": result.get("error", ""),
        "vector_dim": len(result.get("vectors", [[]])[0]) if result.get("vectors") else 0,
    }


def smoke_vision(image_path: str) -> dict:
    from app.model_gateway import caption_image_file

    result = caption_image_file(image_path, "LOCAL_IMAGE_FALLBACK")
    return {
        "role": "vision",
        "provider": result.get("provider"),
        "model": result.get("model"),
        "ok": result.get("ok"),
        "error": result.get("error", ""),
        "sample": (result.get("caption") or "")[:120],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Smoke-test configured model routes without printing API keys.")
    parser.add_argument("--provider", choices=["openai", "opencode", "codex", "spatialai"], help="Override text provider.")
    parser.add_argument(
        "--embedding-provider",
        choices=["local", "openai", "opencode", "codex", "openrouter"],
        help="Temporarily override EMBEDDING_AGENT_PROVIDER for this process.",
    )
    parser.add_argument("--embedding-model", help="Temporarily override EMBEDDING_AGENT_MODEL for this process.")
    parser.add_argument("--model", help="Override text model.")
    parser.add_argument("--role", default="text", choices=["text", "compliance", "knowledge"], help="Text role to test.")
    parser.add_argument("--image", help="Optional image path for the configured vision route.")
    args = parser.parse_args()
    if args.embedding_provider:
        import os

        os.environ["EMBEDDING_AGENT_PROVIDER"] = args.embedding_provider
    if args.embedding_model:
        import os

        os.environ["EMBEDDING_AGENT_MODEL"] = args.embedding_model

    if args.provider or args.model:
        from app.model_gateway import agent_route_report

        payload = {"routes": agent_route_report(), "smoke": [smoke_text(args.role, args.provider, args.model)]}
    else:
        from app.model_gateway import agent_route_report

        payload = {
            "routes": agent_route_report(),
            "smoke": [
                smoke_text("text"),
                smoke_text("compliance"),
                smoke_text("knowledge"),
                smoke_embedding(),
            ],
        }
    if args.image:
        payload["smoke"].append(smoke_vision(args.image))
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
