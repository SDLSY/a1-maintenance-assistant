# 模型与多 Agent 编排

本项目不再把一个 `ACTIVE_MODEL_PROVIDER` 套到全部任务上，而是把模型配置拆成两层。

## 双配置档案

项目内置两套模型路由 profile，位置在：

```text
config/model_profiles.json
```

- `current`：现有高效果演示配置，文本、视觉、合规和知识沉淀走 `codex / gpt-5.5`，embedding 走 `openrouter / qwen/qwen3-embedding-8b`。
- `china`：国产模型适配配置，文本、合规和知识沉淀走 `opencode / qwen3.6-plus`，视觉走 `opencode / mimo-v2-omni`，embedding 走 `openrouter / qwen/qwen3-embedding-8b`。

切换命令：

```powershell
.\.venv\Scripts\python.exe .\scripts\apply_model_profile.py current
.\.venv\Scripts\python.exe .\scripts\apply_model_profile.py china
```

先查看将修改哪些路由，不写入 `.env.local`：

```powershell
.\.venv\Scripts\python.exe .\scripts\apply_model_profile.py china --dry-run
```

profile 只更新 provider/model 路由变量，不包含、不覆盖、不输出任何 API key。切换后重启服务，`/api/agent-routing` 会显示当前生效路由。

## 凭证层

- `OPENAI_BASE_URL` / `OPENAI_API_KEY`：标准 OpenAI 或 OpenAI-compatible 服务。
- `CODEX_BASE_URL` / `CODEX_API_KEY`：SpatialAI 的 Codex/OpenAI-compatible 中转；如果未设置，会兼容读取 `OPENAI_BASE_URL` / `OPENAI_API_KEY`。
- `OPENROUTER_BASE_URL` / `OPENROUTER_API_KEY`：OpenRouter embedding 中转。
- `OPENCODE_BASE_URL` / `OPENCODE_API_KEY`：OpenCode/Zen/Codex 风格的 OpenAI-compatible 中转。
- `ANTHROPIC_BASE_URL` / `ANTHROPIC_AUTH_TOKEN`：SpatialAI/Claude 的 Anthropic-compatible 中转。

这些变量只负责“连接哪里、用什么 key”，不直接决定哪个 Agent 使用它。

## 角色路由层

- `TEXT_AGENT_PROVIDER`：诊断、SOP 草案、普通文本生成。
- `VISION_AGENT_PROVIDER`：故障图片 caption。
- `EMBEDDING_AGENT_PROVIDER`：远程 embedding 索引和查询向量。
- `COMPLIANCE_AGENT_PROVIDER`：安全合规复核。
- `KNOWLEDGE_AGENT_PROVIDER`：案例沉淀、知识更新复核。

每个角色都有对应的 `*_MODEL`。如果某个 provider 没有可用模型名，先不要把角色路由到它。

## 当前实测编排

基于已提供的信息：

- SpatialAI Codex 线的 `/models` 已正常访问，已发现 `gpt-5.5`、`gpt-5.4`、`gpt-5.3-codex`、`gpt-5.2` 等模型。
- `gpt-5.5`、`gpt-5.4`、`gpt-5.3-codex` 的文本调用已通过冒烟测试。
- `gpt-5.5` 使用正常尺寸图片时已通过 chat-completions 多模态 caption 测试。
- OpenRouter embedding 默认使用 `qwen/qwen3-embedding-8b`，用于手册 chunk、案例和查询文本的语义向量。
- OpenCode/Zen 的 `/models` 在加入浏览器式 `User-Agent` 后可正常访问，已发现 `qwen3.6-plus`、`deepseek-v4-pro`、`kimi-k2.6`、`mimo-v2-omni` 等模型。
- `mimo-v2-omni` 的图片 caption 调用已通过冒烟测试，可作为视觉备用模型。
- SpatialAI Claude 线：`ANTHROPIC_AUTH_TOKEN` + `ANTHROPIC_BASE_URL=https://spatialai.vip`。
- SpatialAI Codex 线：`OPENAI_API_KEY`/`CODEX_API_KEY` + `CODEX_BASE_URL=https://spatialai.vip/v1`。
- Claude key 可以列出模型，但普通 HTTP 生成会被中转站返回 `Client not allowed`，因此暂不路由到运行时 Agent。
- 如果 OpenRouter embedding 调用失败，后端会自动回退到本地 `local-hash-embedding-v1`，避免检索链路中断。

推荐配置：

```env
TEXT_AGENT_PROVIDER=codex
TEXT_AGENT_MODEL=gpt-5.5
VISION_AGENT_PROVIDER=codex
VISION_AGENT_MODEL=gpt-5.5
EMBEDDING_AGENT_PROVIDER=openrouter
EMBEDDING_AGENT_MODEL=qwen/qwen3-embedding-8b
COMPLIANCE_AGENT_PROVIDER=codex
COMPLIANCE_AGENT_MODEL=gpt-5.5
KNOWLEDGE_AGENT_PROVIDER=codex
KNOWLEDGE_AGENT_MODEL=gpt-5.5
```

国产模型 profile：

```env
MODEL_PROFILE=china
ACTIVE_MODEL_PROVIDER=opencode
TEXT_AGENT_PROVIDER=opencode
TEXT_AGENT_MODEL=qwen3.6-plus
VISION_AGENT_PROVIDER=opencode
VISION_AGENT_MODEL=mimo-v2-omni
EMBEDDING_AGENT_PROVIDER=openrouter
EMBEDDING_AGENT_MODEL=qwen/qwen3-embedding-8b
COMPLIANCE_AGENT_PROVIDER=opencode
COMPLIANCE_AGENT_MODEL=qwen3.6-plus
KNOWLEDGE_AGENT_PROVIDER=opencode
KNOWLEDGE_AGENT_MODEL=qwen3.6-plus
```

注意：这套配置强调“国产模型能力”，不是“国产平台闭环”。OpenCode/OpenRouter 仍是中转网关；如果答辩需要强调国产云平台闭环，可以在同一 profile 机制下新增百炼、智谱或千帆 provider。

## 验证顺序

1. `python scripts/apply_model_profile.py --list`：查看两套 profile。
2. `python scripts/apply_model_profile.py china --dry-run`：确认要修改的路由。
3. `python scripts/probe_models.py`：查看 provider、角色路由、`/models` 结果。
4. `python scripts/smoke_models.py`：用当前角色路由跑最小调用。
5. `python scripts/smoke_models.py --provider opencode --model qwen3.6-plus --role text`：验证国产文本模型是否可调用。

`/models` 返回 401/403 时，不要直接认定服务不可用；部分中转站不开放模型列表，但仍可能允许指定模型调用。最终以冒烟调用为准。
