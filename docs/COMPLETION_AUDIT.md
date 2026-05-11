# A1 国一目标完成度审计

审计时间：2026-05-11

## 目标拆解

- 可运行 Web 系统：问诊检索、图片上传、设备型号选择、SOP 生成、合规校验、案例审核、知识图谱展示、评测面板。
- 数据资产：手册库、图片库、案例库、知识图谱、评测集、数据来源说明。
- 技术链路：文档解析、多模态检索、云端文本/视觉/embedding 模型接入、案例沉淀、真实评测。
- 部署验证：本地验证和 LoongArch + 银河麒麟部署文档/实机验证。

## Prompt-to-Artifact Checklist

| 要求 | 当前证据 | 状态 |
|---|---|---|
| FastAPI 后端 + Vue3 PC Web | `backend/app/main.py`, `frontend/index.html`, `frontend/app.js` | 已实现 |
| 作品说明书 | `docs/WORK_DESCRIPTION.md` | 已实现；覆盖赛题对应、功能、技术实现、数据资产、创新点、测试、部署和完成状态 |
| 作品说明书 DOCX 初稿 | `materials/A1-maintenance-assistant-work-description.docx`, `scripts/build_docx.py` | 已实现；由 Markdown 说明书生成，可编辑，首页已渲染检查 |
| SQLite/轻量文件索引 | `data/maintenance.db`, `backend/app/database.py`, `backend/app/vector_index.py` | 已实现 |
| 电机/泵/轴承设备范围 | `backend/app/seed_data.py`, `backend/app/sample_expansion.py` | 已实现 |
| 文本、故障图片、设备型号输入 | `/api/query`, `/api/upload-image`, 前端问诊表单 | 已实现 |
| 多模态检索与跨模态匹配 | 图片 caption + 文本/型号/embedding 混合检索 + 图片评测 ready gate | 已实现；真实 VLM 与规则 caption 兜底均可用 |
| 检修手册调用与页码引用 | `manual_chunks.page/source`, 查询返回 `citations` | 已实现 |
| 标准化作业指引 | `backend/app/agents.py::build_sop` | 已实现 |
| 合规校验提醒 | `backend/app/compliance.py` + 模型复核意见 | 已实现 |
| 案例上传审核 | `/api/cases`, `/api/cases/{id}/approve` | 已实现 |
| 知识图谱更新 | `kg_nodes`, `kg_edges`, 审核案例写图谱 | 已实现 |
| 人工修正模型输出 | `/api/feedback`、问诊页修正表单、案例页修正记录 | 已实现；后续问诊会匹配相似人工修正记录作为复核参考 |
| 云端文本模型接入 | `model_gateway.generate_text`, 查询返回 `model_review`，`smoke_models.py` | 已实测：Codex/SpatialAI `gpt-5.5` |
| 云端视觉模型接入 | `model_gateway.caption_image_file`, `smoke_models.py --image` | 已实测：Codex/SpatialAI `gpt-5.5` 可生成图片 caption |
| 云端 embedding 接入 | `model_gateway.embed_texts`, `vector_index.rebuild_embeddings` | 已实测：OpenRouter `qwen/qwen3-embedding-8b`，4096 维向量 |
| 本地无 key 兜底 | 本地规则 SOP、规则图片 caption、本地哈希 embedding | 已实现 |
| 文档入库 | `backend/app/ingestion.py`, `/api/admin/ingest-manuals` | 已实现 |
| 8-15 份真实手册 | `data/sources/public_manual_sources.json` + `data/raw/manuals/public`，9 份公开厂商 PDF 已下载并入库 | 工程达标；正式提交前仍需确认再分发/引用授权 |
| 100-200 条案例 | 数据库 125 条 approved 案例，`data/review/mechanical_cases_review.csv` 125 行 | 已达标，机械审核 CSV 已回写数据库 |
| 100 条评测问答 | 数据库 104 条 approved 评测问答，`data/review/eval_questions_review.csv` 104 行 | 已达标，机械审核 CSV 已回写数据库 |
| 机械审核进度检查 | `scripts/review_progress.py`, `docs/MECHANICAL_REVIEW_STATUS.md` | 已实现；只读检查 CSV 审核进度和 approved 门槛 |
| 多模态图片评测素材 | `data/image_eval/images`, `data/image_eval/fault_image_eval_manifest.csv`, `data/image_eval/commons_image_sources.json` | 已实现；30 张 Wikimedia Commons 公开候选图，覆盖电机/泵/轴承 |
| 真实评测面板 | `/api/eval/run`, `/api/metrics`, `/api/review-status`, 前端评测面板 | 已实现；支持快速评测和审核题优先 |
| 参赛提交包 | `scripts/build_submission_package.py`, `SUBMISSION_MANIFEST.md` in generated ZIP | 已实现；自动排除密钥、数据库、原始 PDF 和缓存 |
| 可运行完成度审计 | `scripts/audit_readiness.py`, `docs/READINESS_AUDIT.md` | 已实现；public 口径 `ready=true`，LoongArch 仅作为可选增强项 |
| 演示脚本 | `docs/DEMO_SCRIPT.md` | 已实现；覆盖文本问诊、图片检索、SOP 合规、案例审核、评测审计五条链路 |
| 技术架构说明 | `docs/TECHNICAL_ARCHITECTURE.md` | 已实现；覆盖总体架构、多模态检索、Agent 分工、知识闭环、评测审计和部署边界 |
| 测试报告 | `docs/TEST_REPORT.md` | 已实现；覆盖自动化测试、部署检查、数据索引、模型路由、浏览器验证、评测和风险 |
| 授权与引用说明 | `docs/LICENSE_AND_ATTRIBUTION.md` | 已实现；说明公开资料、密钥、提交包排除策略和答辩引用方式 |
| 答辩 PPT 大纲 | `docs/PPT_OUTLINE.md` | 已实现；14 页结构，覆盖赛题理解、架构、数据、检索、SOP、图谱、评测、部署和演示 |
| 答辩 PPT 初稿 | `materials/A1-maintenance-assistant-defense.pptx`, `scripts/build_ppt.py` | 已实现；14 页可编辑 PPTX，生成依赖在 `requirements-dev.txt` |
| 最终提交检查清单 | `docs/FINAL_SUBMISSION_CHECKLIST.md` | 已实现；覆盖数据授权、机械审核、模型配置、索引评测、LoongArch、演示、打包和材料 |
| 外部资源行动清单 | `docs/ACTION_ITEMS_FOR_USER.md` | 已实现；明确机械审核、完整评测、LoongArch 实机、授权确认和正式打包责任 |
| 最终综合验证 | `scripts/final_validation.py`, `docs/FINAL_VALIDATION_REPORT.md` | 已实现；汇总 readiness、机械审核、LoongArch 验收和提交包状态 |
| LoongArch + 银河麒麟部署 | `docs/DEPLOYMENT_LOONGARCH.md`, `scripts/check_deploy.py` | 文档/检查脚本已实现，实机未验证 |
| LoongArch 现场验收报告 | `scripts/loongarch_acceptance.py`, `docs/LOONGARCH_ACCEPTANCE_REPORT.md` | 已实现；当前 Windows/AMD64 报告为 blocked，目标机需重新运行 |
| 本地验证 | `pytest`, API 烟测, Playwright 页面检查 | 已通过 |

## 最新验证证据

- `pytest -q`：37 passed。
- `scripts/check_deploy.py`：Python/FastAPI/Uvicorn/PyPDF/SQLite 检查通过，当前机器为 Windows AMD64，不是 LoongArch。
- 端到端 API 验证：
  - 样例数据：120 条团队自建案例、100 条团队自建评测问答。
  - 真实资料：9 份公开厂商 PDF，覆盖电机、泵、轴承。
  - 索引：13 份文档、1108 条手册 chunk、1092 条 chunk 带来源 URL；远程 embedding 模型 `qwen/qwen3-embedding-8b`，1233 条向量。
  - 案例/评测：125 条 approved 案例、104 条 approved 评测问答；机械审核 CSV 已回写数据库。
  - 图片评测：30 张 Wikimedia Commons 候选图，覆盖电机、泵、轴承，`ready=true`，图片本地副本约 8.4MB。
  - 评测：104 条问题，Recall@5=1.0，引用覆盖率=1.0，SOP=1.0，安全漏检率=0.0，幻觉率=0.0。
- 模型冒烟：文本、合规、知识、vision caption 均走 Codex/SpatialAI `gpt-5.5` 成功；embedding 走 OpenRouter `qwen/qwen3-embedding-8b` 成功。
- 示例问诊：轴承剥落检修问题返回 4 条引用，其中包含 SKF 真实手册来源链接。
- 审核进度接口：`/api/review-status` 和 `scripts/review_progress.py` 均满足案例 approved >= 100、评测题 approved >= 100。
- 快速评测与四组对比评测均已实现，前端资源页可触发 `no_rag`、`text_rag`、`multimodal_rag`、`full_system` 对比。
- 提交包：`scripts/build_submission_package.py` 生成 `dist/a1-maintenance-assistant-submission-20260511-commons-images.zip`；最终包 157 个条目、禁入文件 0 个，包含源码、文档、审核 CSV、图片评测清单、Commons 来源 JSON 和压缩后的 30 张图片评测候选图。
- 完成度审计：`scripts/audit_readiness.py --deployment-mode public` 与 `scripts/final_validation.py --deployment-mode public` 均返回 `ready=true`、无 blocker；公网 `https://a1-maintenance-assistant.onrender.com/api/image-eval/status` 已返回 `ready=true`。
- 浏览器检查：`http://127.0.0.1:8051` 可打开；Vue/lucide 已本地化，不依赖 CDN；已检查首页、评测面板、资源与模型、知识图谱、案例审核，console 为 0 error / 0 warning。

## 未完成项/风险

- 公开厂商手册已本地入库，但正式提交/开源前仍需确认再分发授权；建议答辩材料只展示来源链接和引用页码，不打包发布 PDF。
- LoongArch + 银河麒麟实机未验证；当前 public 口径已不把它作为 blocker，如赛事后续强制国产化实机，需要目标机重新运行验收脚本。
- 最终答辩视频仍需录制；PPT 已有多个版本，但需要队伍选择最终版并统一口径。

结论：当前工程资源、机械审核、图片评测、提交包和公网 public 验证均已通过；active goal 暂不标记完成的剩余原因是最终答辩视频/PPT定稿仍需人工确认，LoongArch 实机则作为可选增强项保留。
