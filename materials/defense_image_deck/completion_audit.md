# A1 答辩 PPT 完成度审计

审计时间：2026-05-11  
目标：持续优化 A1 答辩 PPT，在现有 gpt-image-2 全图版基础上逐页审查文字、结构、可信度和答辩表达，形成更适合国一目标的最终版 PPT，并在缺少用户资源时明确反馈。

## 结论

当前 PPT 已经完成“基于原 gpt-image-2 全图版的可交付润色版”，但 active goal 还不能标记 complete。

不能完成的原因不是 PPT 主体缺失，而是最终提交版仍需要用户确认学校/队伍/成员/指导老师展示规则，并建议在正式答辩前再次复测公网部署和核心流程。若要继续增强可信度，还应补中国软件杯官网/报名系统内的 A1 页面截图、国产化配置/部署证据。

## Prompt-to-Artifact Checklist

| 要求 | 证据 | 当前状态 | 判断 |
|---|---|---:|---|
| 基于现有 gpt-image-2 全图版优化 | 源文件 `materials/A1-maintenance-assistant-defense-gpt-image-2.pptx`，14 页、14 张图片、0 个文本框 | 已验证 | 通过 |
| 不另起一套 V2，而是在源文件基础上润色 | 脚本 `scripts/polish_gpt_image_deck.py` 的 `SOURCE` 指向原文件；输出为 `A1-maintenance-assistant-defense-gpt-image-2-polished.pptx` | 已验证 | 通过 |
| 逐页审查文字和答辩表达 | `materials/defense_image_deck/polish_notes.md` 覆盖 1-14 页逐页校正点；PPT 上有可编辑标题/口径层 | 已验证 | 通过 |
| 保留全图版视觉风格 | polished PPT：18 页、20 张图片、171 个文本对象；前 14 页保留原始整页图 | 已验证 | 通过 |
| 可编辑关键页 | 1-14 页新增可编辑标题/答辩口径；15-18 页为可编辑证据页 | 已验证 | 通过 |
| 真实系统截图 | `real_screenshots/01_text_query.png` 至 `05_case_review_update.png`；第 15 页展示 | 已验证 | 通过 |
| 技术证据 | 第 15 页真实截图，第 17 页机械审核，第 18 页公网部署验证 | 已验证 | 通过 |
| 评测页优化 | `evaluation_summary.json`：104/104 已审核题；第 16 页自动评测表 | 已验证 | 通过，但需说明边界 |
| 演示页优化 | 第 12 页演示路线，第 15 页真实系统截图 | 已验证 | 通过 |
| 现场/视频演示脚本 | `demo_runbook.md` 已给出 5 分钟演示路线、固定输入、兜底截图和答辩当天检查清单 | 已验证 | 通过 |
| 官方赛题依据 | `official_source_candidates.md` 已整理高校通知、龙芯中科认证账号赛题页和转载备份；第 3 页已加入审慎来源说明 | 已验证 | 通过，但仍建议补官网截图 |
| 机械专业审核证据 | `mechanical_review_summary.json`：125/125 案例审核，104/104 评测题审核，reviewer 代号 `ME-R01` | 已验证 | 通过 |
| 公网部署验证 | `deployment_summary.json`：Render URL、health `ok`、Supabase enabled；第 18 页已结构化展示 | 已验证 | 通过，但正式答辩前需复测 |
| PDF 导出验证 | `tmp/ppt_polished_preview/A1-maintenance-assistant-defense-gpt-image-2-polished.pdf`，pdfinfo 显示 18 页 | 已验证 | 通过 |
| 可视预览 | `tmp/ppt_polished_preview/contact_sheet.jpg` | 已生成 | 通过 |
| 逐页 QA 审查 | `slide_qa_report.md` 已逐页标注当前状态、QA 结论和后续动作 | 已验证 | 通过 |
| 逐页讲稿 | `speaker_notes_polished.md`，18 个页标题 | 已验证 | 通过 |
| 8-10 分钟精简口播稿 | `speaker_notes_10min.md` 已覆盖开场、2-18 页讲法、结尾和禁用说法 | 已验证 | 通过 |
| 答辩追问 Q&A | `defense_qna.md`，18 个问题 | 已验证 | 通过 |
| 敏感信息检查 | `security_scan_report.md` 已扫描 PPT 文本和 `materials/defense_image_deck`，未命中密钥模式 | 已验证 | 通过 |
| 自动验证脚本 | `scripts/verify_defense_materials.py` 已生成 `verification_report.md/json`，overall_status=ok | 已验证 | 通过 |
| 封面信息注入准备 | `team_info.template.json` 已提供；`polish_gpt_image_deck.py` 支持读取可选 `team_info.json` 后自动注入封面 | 已验证 | 等用户填写 |
| 交付清单总入口 | `delivery_manifest.md` 已汇总 PPT、讲稿、演示、证据、脚本、待用户补充项 | 已验证 | 通过 |
| 离线答辩材料包 | `materials/A1-defense-delivery-pack.zip` 已生成，包含 PPT/PDF、文档、截图和数据摘要；压缩包条目已验证 | 已验证 | 通过 |
| 赛题要求对齐 | `rubric_alignment.md` 已把 A1 功能要求、PPT 页码、证据文件和答辩口径对应起来 | 已验证 | 通过 |
| 最终全图像答辩版 | `A1-maintenance-assistant-defense-image-only-final.pptx` 已生成；18 页、18 张整页图片、0 文本框、slide XML 无文本节点 | 已验证 | 通过 |
| 最终全图像版预览 | `final_image_only_contact_sheet.jpg` 已生成，可快速检查 18 页主推版本 | 已验证 | 通过 |
| 需要用户提供资源时及时反馈 | `final_resource_checklist.md` 和 `user_inputs_needed.md` | 已生成 | 未完全闭环 |

## 当前主线文件

- 源 PPT：`D:\30726\Desktop\竞赛目录\a1-maintenance-assistant\materials\A1-maintenance-assistant-defense-gpt-image-2.pptx`
- 项目内润色版：`D:\30726\Desktop\竞赛目录\a1-maintenance-assistant\materials\A1-maintenance-assistant-defense-gpt-image-2-polished.pptx`
- 便捷复制版：`D:\30726\Desktop\竞赛目录\A1全图版答辩PPT-基于原文件润色版.pptx`
- 预览图：`D:\30726\Desktop\竞赛目录\a1-maintenance-assistant\tmp\ppt_polished_preview\contact_sheet.jpg`

## 已验证数据

- 原始全图版：14 页，14 张图片，0 个文本框，约 20.34 MB。
- 润色版：18 页，20 张图片，171 个文本对象，约 22.03 MB。
- PDF：18 页，16:9 页面尺寸，LibreOffice 可导出。
- 逐页 QA：18 页状态、风险和后续动作已记录。
- 讲稿：18 页。
- 精简口播稿：8-10 分钟版本。
- Q&A：18 条。
- 敏感信息扫描：PPT 和答辩材料未命中密钥模式。
- 自动验证报告：overall_status=ok。
- 封面信息模板：已提供机器可读 `team_info.template.json`。
- 交付清单：`delivery_manifest.md` 已汇总所有主线材料。
- 离线答辩材料包：`materials/A1-defense-delivery-pack.zip` 已生成。
- 赛题要求对齐表：`rubric_alignment.md` 已生成。
- 最终全图像答辩版：18 页整页图片版已生成。
- 演示 Runbook：5 分钟路线、固定输入、录制建议和兜底清单。
- 自动评测：104 道已审核题。
- 机械审核：125 条案例、104 道评测题。
- 公网部署：`/api/health` 当前返回 `ok`，Supabase enabled。

## 未闭环项

| 优先级 | 缺口 | 影响 | 需要谁处理 |
|---|---|---|---|
| P0 | 学校名称、队伍名称、成员/指导老师是否展示 | 封面和正式提交版不能最终定稿 | 用户 |
| P0 | 正式答辩前公网冷启动和核心流程复测 | 当前部署证据只代表 2026-05-11 的状态 | 我可在答辩前复测 |
| P1 | 中国软件杯官网/报名系统内 A1 页面截图 | 第 3 页可信度可继续增强 | 用户提供 |
| P1 | 最终前端重构后的真实截图 | 第 15 页可替换为最终 UI | 前端重构完成后我截图 |
| P1 | 评测集边界说明/抽样复核签字规则 | 避免 100% 指标被质疑 | 机械队友/用户 |
| P2 | 国产模型配置截图或国产化部署证据 | 国产化主题加分 | 可选 |

## 是否可以标记 goal complete

不能。  
原因：objective 明确包含“在需要用户提供系统截图、真实评测数据或学校/赛事信息时及时反馈”。当前已反馈并生成清单，但学校/队伍/指导老师展示规则仍未收到；正式提交版还无法完全定稿。
