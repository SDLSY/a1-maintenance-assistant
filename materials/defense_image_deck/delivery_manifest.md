# A1 答辩材料交付清单

更新时间：2026-05-11  
用途：作为答辩 PPT、演示、讲稿、审计和复测材料的总入口。

## PPT 主文件

| 文件 | 用途 | 状态 |
|---|---|---|
| `D:\30726\Desktop\竞赛目录\a1-maintenance-assistant\materials\A1-defense-delivery-pack.zip` | 离线答辩材料包 | 已生成 |
| `D:\30726\Desktop\竞赛目录\a1-maintenance-assistant\materials\A1-maintenance-assistant-defense-image-only-final.pptx` | 最终全图像答辩版，18 页均为整页图片 | 已生成 |
| `D:\30726\Desktop\竞赛目录\a1-maintenance-assistant\materials\A1-maintenance-assistant-defense-gpt-image-2.pptx` | 原始 gpt-image-2 全图版母版 | 保留，不覆盖 |
| `D:\30726\Desktop\竞赛目录\a1-maintenance-assistant\materials\A1-maintenance-assistant-defense-gpt-image-2-polished.pptx` | 可编辑润色版，作为生成和修改底稿 | 已生成 |
| `D:\30726\Desktop\竞赛目录\A1全图版答辩PPT-基于原文件润色版.pptx` | 便捷打开版 | 已同步 |
| `D:\30726\Desktop\竞赛目录\a1-maintenance-assistant\tmp\ppt_polished_preview\A1-maintenance-assistant-defense-gpt-image-2-polished.pdf` | PDF 预览/兜底 | 已导出 |
| `D:\30726\Desktop\竞赛目录\a1-maintenance-assistant\tmp\ppt_polished_preview\contact_sheet.jpg` | 18 页总览预览 | 已生成 |
| `D:\30726\Desktop\竞赛目录\a1-maintenance-assistant\materials\defense_image_deck\final_image_only_contact_sheet.jpg` | 最终全图像版 18 页总览预览 | 已生成 |

## 上台材料

| 文件 | 用途 | 状态 |
|---|---|---|
| `speaker_notes_polished.md` | 18 页逐页备稿 | 已生成 |
| `speaker_notes_10min.md` | 8-10 分钟精简口播稿 | 已生成 |
| `defense_qna.md` | 评委追问 Q&A | 已生成 |
| `demo_runbook.md` | 4-5 分钟现场/视频演示脚本 | 已生成 |

## 证据与审计材料

| 文件 | 用途 | 状态 |
|---|---|---|
| `polish_notes.md` | 基于原 PPT 的逐页润色记录 | 已生成 |
| `final_image_only_delivery.md` | 最终全图像答辩版交付说明 | 已生成 |
| `slide_qa_report.md` | 18 页逐页 QA 报告 | 已生成 |
| `completion_audit.md` | active goal 完成度审计 | 已生成 |
| `verification_report.md` / `verification_report.json` | 自动验证报告 | overall_status=ok |
| `security_scan_report.md` | 敏感信息检查报告 | 未命中密钥模式 |
| `official_source_candidates.md` | A1 赛题来源候选与边界 | 已生成 |
| `rubric_alignment.md` | A1 赛题要求与答辩材料对齐表 | 已生成 |
| `final_resource_checklist.md` | 最终资源缺口清单 | 持续更新 |

## 数据与截图证据

| 文件/目录 | 用途 | 状态 |
|---|---|---|
| `real_screenshots/01_text_query.png` | 文本问诊截图 | 已补 |
| `real_screenshots/02_image_search.png` | 图片检索截图 | 已补 |
| `real_screenshots/03_sop_generation.png` | SOP 生成截图 | 已补 |
| `real_screenshots/04_compliance_check.png` | 合规校验截图 | 已补 |
| `real_screenshots/05_case_review_update.png` | 案例审核截图 | 已补 |
| `real_screenshots/06_public_deploy_home.png` | 公网首页截图 | 已补 |
| `real_screenshots/07_public_health.png` | 公网健康检查截图 | 已补 |
| `evaluation_summary.json` / `evaluation_summary.md` | 自动评测摘要 | 已补 |
| `mechanical_review_summary.json` / `mechanical_review_summary.md` | 机械审核摘要 | 已补 |
| `deployment_summary.json` / `deployment_summary.md` | 公网部署摘要 | 已补 |

## 脚本

| 文件 | 用途 | 状态 |
|---|---|---|
| `scripts/polish_gpt_image_deck.py` | 从原始 gpt-image-2 PPT 生成 polished PPT | 已更新 |
| `scripts/build_defense_image_only_final.py` | 从 polished/PDF 渲染结果生成最终全图像版 PPT | 已生成 |
| `scripts/verify_defense_materials.py` | 自动验证答辩材料完整性 | 已运行，status=ok |

## 待用户补充

| 文件 | 用途 | 状态 |
|---|---|---|
| `user_inputs_needed.md` | 用户待确认信息清单 | 待填写 |
| `team_info.template.json` | 封面信息机器可读模板 | 已提供 |
| `team_info.json` | 实际封面信息输入 | 待用户提供 |

## 当前不能宣称完成的点

1. 不能宣称封面已最终定稿：学校、队伍、成员、指导老师展示规则仍未确认。
2. 不能宣称公网部署长期稳定：第 18 页只代表当前检查时间，正式答辩前必须复测。
3. 不能宣称第 15 页是最终 UI：若前端重构，需重新截图替换。
4. 不能宣称官方官网截图已核验：当前只有来源候选，最终以官网/报名系统为准。
