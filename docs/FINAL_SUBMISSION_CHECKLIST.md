# 最终提交检查清单

用途：正式提交前逐项确认，避免把开发环境完成度误判为参赛完成度。

## 1. 数据与授权

- [ ] 确认 `data/sources/public_manual_sources.json` 中 active 来源仍可访问。
- [ ] 执行公开来源检查：

```powershell
.\.venv\Scripts\python.exe .\scripts\validate_public_sources.py
```

- [ ] 确认提交包不包含原始 PDF。
- [ ] 确认答辩材料只展示来源 URL、页码和许可说明。
- [ ] 如需展示 PDF 原文，使用来源 URL 或目标机本地下载副本，不把 PDF 放入提交包。

## 2. 机械专业审核

- [ ] 导出审核包：

```powershell
.\.venv\Scripts\python.exe .\scripts\export_review_pack.py
```

- [ ] 机械专业队友审核 `data/review/mechanical_cases_review.csv`。
- [ ] 机械专业队友审核 `data/review/eval_questions_review.csv`。
- [ ] 每条通过项填写：

```text
decision=approve
review_status=approved
reviewer=审核人
review_notes=必要说明
```

- [ ] 检查审核进度：

```powershell
.\.venv\Scripts\python.exe .\scripts\review_progress.py
```

- [ ] 确认 `docs/MECHANICAL_REVIEW_STATUS.md` 中：

```text
ready_for_goal: true
```

- [ ] 回写审核结果：

```powershell
.\.venv\Scripts\python.exe .\scripts\import_review_pack.py
```

最低门槛：

- [ ] `maintenance_cases.review_status='approved'` 不少于 100 条。
- [ ] `eval_questions.review_status='approved'` 不少于 100 条。

## 3. 模型与环境配置

- [ ] 目标机 `.env.local` 已填写真实 key。
- [ ] 不把 `.env.local` 放入提交包。
- [ ] 当前推荐路由：

```env
TEXT_AGENT_PROVIDER=codex
VISION_AGENT_PROVIDER=codex
EMBEDDING_AGENT_PROVIDER=openrouter
COMPLIANCE_AGENT_PROVIDER=codex
KNOWLEDGE_AGENT_PROVIDER=codex
EMBEDDING_AGENT_MODEL=qwen/qwen3-embedding-8b
```

- [ ] 执行模型/环境检查：

```powershell
.\.venv\Scripts\python.exe .\scripts\check_deploy.py
.\.venv\Scripts\python.exe .\scripts\smoke_models.py --embedding-provider openrouter --embedding-model qwen/qwen3-embedding-8b
```

- [ ] 确认输出不包含真实 key，只显示 `key_present=true`。

## 4. 索引与评测

- [ ] 入库手册：

```powershell
Invoke-RestMethod -Uri http://127.0.0.1:8051/api/admin/ingest-manuals -Method Post
```

- [ ] 重建索引：

```powershell
Invoke-RestMethod -Uri http://127.0.0.1:8051/api/admin/rebuild-index -Method Post
```

- [ ] 快速评测：

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8051/api/eval/run?max_questions=20" -Method Post
```

- [ ] 完整评测：

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8051/api/eval/run" -Method Post
```

- [ ] 确认评测基准不再是 `unreviewed_fallback`，而是已审核题优先。
- [ ] 更新 `docs/TEST_REPORT.md` 中的最终评测指标。

## 5. LoongArch + 银河麒麟实机

- [ ] 在 LoongArch + 银河麒麟机器上解压提交包。
- [ ] 安装依赖：

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
```

- [ ] 填写 `.env.local`。
- [ ] 重新下载公开资料：

```bash
python scripts/download_public_sources.py --required-only
```

- [ ] 执行部署检查：

```bash
python scripts/check_deploy.py
```

- [ ] 确认 `machine` 或 `loongarch_like` 显示 LoongArch 相关信息。
- [ ] 启动服务：

```bash
python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8051
```

- [ ] 在目标机完整跑通：文本问诊、图片上传、SOP、合规、案例审核、图谱、评测。
- [ ] 录屏保留证据。

## 6. 浏览器与演示

- [ ] 打开：

```text
http://127.0.0.1:8051
```

- [ ] 检查首页无 console error。
- [ ] 按 `docs/DEMO_SCRIPT.md` 跑通五条链路。
- [ ] 按 `docs/PPT_OUTLINE.md` 完成 PPT。
- [ ] 确认演示中能展示：
  - [ ] 手册引用来源 URL 和页码。
  - [ ] 图片 caption 或规则兜底 caption。
  - [ ] SOP 和合规检查。
  - [ ] 案例审核后知识图谱更新。
  - [ ] 评测面板和 readiness audit。

## 7. 提交包

- [ ] 构建提交包：

```powershell
.\.venv\Scripts\python.exe .\scripts\build_submission_package.py --timestamp final
```

- [ ] 运行 readiness audit：

```powershell
.\.venv\Scripts\python.exe .\scripts\audit_readiness.py --submission-archive .\dist\a1-maintenance-assistant-submission-final.zip
```

- [ ] 确认：

```text
ready=true
```

- [ ] 确认提交包不包含：
  - [ ] `.env.local`
  - [ ] 真实 key
  - [ ] SQLite 运行数据库
  - [ ] 原始 PDF
  - [ ] 上传图片
  - [ ] 虚拟环境
  - [ ] 缓存目录

## 8. 最终材料

- [ ] 作品说明书：`docs/WORK_DESCRIPTION.md`
- [ ] 技术架构说明：`docs/TECHNICAL_ARCHITECTURE.md`
- [ ] 测试报告：`docs/TEST_REPORT.md`
- [ ] 授权与引用说明：`docs/LICENSE_AND_ATTRIBUTION.md`
- [ ] 演示脚本：`docs/DEMO_SCRIPT.md`
- [ ] PPT 大纲：`docs/PPT_OUTLINE.md`
- [ ] 完成度审计：`docs/COMPLETION_AUDIT.md`
- [ ] 机械审核状态：`docs/MECHANICAL_REVIEW_STATUS.md`
- [ ] readiness audit：`docs/READINESS_AUDIT.md`
- [ ] LoongArch 实机录屏
- [ ] 答辩 PPT

只有以上关键项全部完成，才能把 active goal 标记为完成。
