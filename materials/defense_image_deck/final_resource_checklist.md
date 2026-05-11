# A1 答辩 PPT 最终版资源清单

目标文件：

- 最终全图像 PPT：`D:\30726\Desktop\竞赛目录\a1-maintenance-assistant\materials\A1-maintenance-assistant-defense-image-only-final.pptx`
- 当前主线 PPT：`D:\30726\Desktop\竞赛目录\A1全图版答辩PPT-基于原文件润色版.pptx`
- 项目内同源文件：`D:\30726\Desktop\竞赛目录\a1-maintenance-assistant\materials\A1-maintenance-assistant-defense-gpt-image-2-polished.pptx`

## 必须补齐

| 优先级 | 资源 | 用途 | 谁提供/生成 | 状态 |
|---|---|---|---|---|
| P0 | 文本问诊真实截图 | 第 15 页真实演示截图 | 已由我截图 | 已补：`real_screenshots/01_text_query.png` |
| P0 | 图片检索真实截图 | 第 15 页真实演示截图 | 已由我截图 | 已补：`real_screenshots/02_image_search.png` |
| P0 | SOP 生成真实截图 | 第 15 页真实演示截图 | 已由我截图 | 已补：`real_screenshots/03_sop_generation.png` |
| P0 | 合规校验真实截图 | 第 15 页真实演示截图 | 已由我截图 | 已补：`real_screenshots/04_compliance_check.png` |
| P0 | 案例审核/知识更新截图 | 第 15 页真实演示截图 | 已由我截图 | 已补：`real_screenshots/05_case_review_update.png` |
| P0 | Recall@5 实测值 | 第 16 页自动评测结果 | 已由我跑后端评测 | 已补：104/104 已审核题，当前 100% |
| P0 | 图片/多模态命中相关指标 | 第 16 页自动评测结果 | 已由我跑后端评测 | 已补：多模态 RAG 对比组当前 100% Recall@5 |
| P0 | 引用覆盖率 | 第 16 页自动评测结果 | 已由我跑后端评测 | 已补：当前 100% |
| P0 | SOP 完整度评分 | 第 17 页机械审核摘要 | 已从 `mechanical_cases_review.csv` 汇总 | 已补：人工审核均值 3.94/5 |
| P0 | 安全合规评分 | 第 17 页机械审核摘要 | 已从 `mechanical_cases_review.csv` 汇总 | 已补：人工审核均值 4.27/5 |

## 建议补齐

| 优先级 | 资源 | 用途 | 谁提供/生成 | 状态 |
|---|---|---|---|---|
| P1 | 学校名称、队伍名称、成员代号 | 封面/提交材料 | 用户提供；已准备 `team_info.template.json` | 待用户填写 |
| P1 | 指导老师信息是否展示 | 封面/说明书 | 用户提供 | 待补 |
| P1 | 官方 A1 赛题截图或引用页 | 第 3 页可信度增强 | 我已整理来源候选，官网/报名系统截图仍需用户提供 | 部分已补：`official_source_candidates.md` |
| P1 | 公网部署 URL 最终确认 | 第 18 页公网部署验证 | 我已验证 | 已补：Render URL 200，`/api/health` status=ok |
| P1 | 演示视频脚本 | 提交材料 | 已生成 | 已补：`demo_runbook.md` |
| P1 | 答辩 PPT 讲稿精简版 | 现场讲稿 | 已生成精简版 | 已补：`speaker_notes_10min.md` |
| P1 | 评委追问 Q&A | 答辩准备 | 已生成初稿 | 可继续扩展 |
| P1 | 逐页 QA 报告 | PPT 最终审查 | 已生成 | 已补：`slide_qa_report.md` |
| P1 | 敏感信息检查报告 | 防止 API key 泄露 | 已扫描 | 已补：`security_scan_report.md` |
| P1 | 答辩材料自动验证报告 | 回归检查 | 已运行 | 已补：`verification_report.md`，overall_status=ok |
| P1 | 答辩材料交付清单 | 材料总入口 | 已整理 | 已补：`delivery_manifest.md` |
| P1 | 离线答辩材料包 | 拷贝/备份/答辩机兜底 | 已打包 | 已补：`materials/A1-defense-delivery-pack.zip` |
| P1 | 赛题要求对齐表 | 答辩自查 | 已整理 | 已补：`rubric_alignment.md` |
| P1 | 最终全图像答辩版 | 满足整页图片风格 | 已生成 | 已补：`A1-maintenance-assistant-defense-image-only-final.pptx` |

## 可作为加分项

| 优先级 | 资源 | 用途 | 谁提供/生成 | 状态 |
|---|---|---|---|---|
| P2 | 国产模型配置截图 | 国产化亮点 | 我可整理配置页 | 待补 |
| P2 | 银河麒麟/国产 Linux 部署截图 | 部署可信度 | 需要部署环境 | 可选 |
| P2 | 知识图谱动态更新动图 | 演示视频亮点 | 我可录制 | 待补 |
| P2 | 多 Agent 调用日志截图 | 技术可信度 | 我可生成 | 待补 |

## 当前不能假装完成的点

- 第 11/16 页评测已补当前自动跑数，但不能包装成第三方权威测试。
- 第 17 页已补机械审核摘要，但如果正式提交需要真实成员信息，仍需用户确认学校、队伍、指导老师是否展示。
- 第 12 页演示不能只用 gpt-image-2 概念图，最终版需要真实系统截图。
- 国产化部署如果没有真实环境记录，只能写成兼容路线，不能写成已完成部署。
- 公网部署已补当前验证截图，但正式答辩当天仍需复测冷启动和核心流程。
- SOP 完整度最好由机械专业队友打分，否则可信度不足。
