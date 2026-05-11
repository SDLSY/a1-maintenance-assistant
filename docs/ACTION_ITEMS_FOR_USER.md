# 待用户/队友完成事项

当前工程侧已完成可运行系统、资料入库、模型路由、提交包、说明书、PPT/DOCX 初稿和审计工具。2026-05-11 更新后，机械审核 CSV 已达到门槛；正式达到 A1 国一目标仍需要补齐以下外部资源。

## 0. 多模态图片评测素材

负责人：机械专业队友 / 计算机队友

输入文件：

```text
data/image_eval/fault_image_eval_manifest.csv
data/image_eval/images/
```

需要完成：

- 补齐 30 张真实或公开授权的故障图片。
- 覆盖电机、离心泵、轴承三类设备，每类 10 张。
- 图片文件名与清单 `image_path` 一致。
- 机械队友确认可见故障证据、caption_hint、检索关键词和安全关键词。
- 审核通过后将 `review_status` 改为 `approved`，`reviewer` 使用代号，例如 `ME-R01`。

检查：

```powershell
.\.venv\Scripts\python.exe .\scripts\image_eval_status.py
```

目标：

```text
ready=true
available_images>=30
approved_images>=30
```

当前状态：清单已建立 30 条，但真实图片尚未放入，`ready=false`。状态报告见 `docs/IMAGE_EVAL_STATUS.md`。

## 1. 机械专业队友审核（已完成）

负责人：机械专业队友 / 指导老师

输入文件：

```text
data/review/mechanical_cases_review.csv
data/review/eval_questions_review.csv
```

当前状态：

- 125 条案例已标记为 `approved`。
- 104 条评测题已标记为 `approved`。
- `reviewer` 已使用代号填写。
- 当前 `ready_for_goal=true`。

审核后检查：

```powershell
.\.venv\Scripts\python.exe .\scripts\review_progress.py
```

目标：

```text
ready_for_goal=true
```

回写数据库：

```powershell
.\.venv\Scripts\python.exe .\scripts\import_review_pack.py
```

## 2. 完整评测

负责人：计算机队友

前提：

- 机械审核已回写。
- `review_status='approved'` 的案例和评测题达到门槛。

运行：

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8051/api/eval/run" -Method Post
```

需要确认：

- `review_basis` 不再是 `unreviewed_fallback`。
- Recall@5、引用覆盖率、SOP 完整度、安全漏检率达到测试报告目标。
- 更新 `docs/TEST_REPORT.md` 中最终指标。

## 3. LoongArch + 银河麒麟实机验证

负责人：有目标机权限的队友

需要资源：

- LoongArch + 银河麒麟机器。
- Python 3.10+。
- 可访问模型中转站和公开资料下载地址。
- 本地 `.env.local`，包含 Codex/SpatialAI 和 OpenRouter key。

部署：

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env.local
python scripts/download_public_sources.py --required-only
python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8051
```

验收：

```bash
python scripts/check_deploy.py
python scripts/loongarch_acceptance.py --api-base-url http://127.0.0.1:8051
```

目标：

```text
loongarch_validated=true
```

需要录屏：

- 系统启动。
- 文本问诊。
- 图片上传。
- SOP 与合规校验。
- 案例审核。
- 知识图谱更新。
- 评测面板。

## 4. 授权与引用确认

负责人：队长 / 指导老师

需要确认：

- 公开厂商 PDF 不随提交包分发。
- 答辩只展示来源 URL、页码、标题和许可说明。
- 学校/赛事提交要求是否允许引用公开可访问厂家资料。

参考文档：

```text
docs/LICENSE_AND_ATTRIBUTION.md
docs/DATA_SOURCES.md
data/sources/public_manual_sources.json
```

## 5. 正式提交包

负责人：计算机队友

全部外部项完成后运行：

```powershell
.\.venv\Scripts\python.exe .\scripts\build_submission_package.py --timestamp final
.\.venv\Scripts\python.exe .\scripts\audit_readiness.py --submission-archive .\dist\a1-maintenance-assistant-submission-final.zip
```

目标：

```text
ready=true
```

提交前确认包内不含：

- `.env.local`
- 真实 key
- SQLite 运行库
- 原始 PDF
- 上传图片
- `.venv`
- 缓存目录

## 当前阻塞摘要

| 阻塞项 | 当前状态 | 完成判据 |
|---|---|---|
| 机械审核 | 125 条案例、104 条评测题均未审核 | approved 案例 >= 100，approved 评测题 >= 100 |
| LoongArch 实机 | 当前仅 Windows/AMD64 验证 | `loongarch_acceptance.py` 在目标机返回 `loongarch_validated=true` |
| 正式完整评测 | 当前为未审核兜底评测 | 机械审核回写后完整评测使用 approved 题目 |

完成以上三项后，才能把 active goal 标记为完成。
