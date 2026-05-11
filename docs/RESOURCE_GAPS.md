# 资源缺口与处理方式

当前系统已经具备完整工程入口，且已接入一批公开厂商资料；要达到“国一目标方案”，仍需要补齐正式参赛资源和实机验证。

## 必须补齐

- 真实维修手册授权：9 份公开厂商 PDF 已本地下载并入库，正式提交/开源前仍需确认再分发授权；答辩建议展示来源 URL 和页码，不随作品包发布受限 PDF。
- 真实案例签核：当前已有 125 条团队自建案例并导出审核 CSV，但需要机械专业队友逐条审核通过。
- 评测集签核：当前已有 104 条评测问答并导出审核 CSV，但需要机械专业队友确认期望引用、故障类型和安全关键词。
- 模型 key：放入 `.env.local`，不要发到聊天或提交到仓库。
- LoongArch + 银河麒麟环境：用于最终提交前兼容性验证。

## 可以先用的替代

- `data/raw/manuals` 中的自建样例手册可用于开发和演示，但不能冒充真实厂家资料。
- `scripts/generate_sample_data.py` 可生成 120 条团队自建案例和 100 条团队自建评测问答；`scripts/export_review_pack.py` 可导出给机械队友审核。
- `scripts/build_submission_package.py` 可生成不包含密钥、数据库和原始 PDF 的参赛提交包；公开 PDF 只保留来源 URL 与 sidecar metadata。
- 本地哈希 embedding 可用于无 key 演示；配置 OpenAI-compatible embedding 后可重建真实向量索引。
- 图片理解无 key 时使用规则化 caption；配置视觉模型后自动走 VLM caption。

## 最小验收

- 至少 8 份真实手册入库成功，并在引用中显示来源 URL、许可说明和页码。
- `/api/eval/run` 跑出真实指标，Recall@5 >= 0.85，引用覆盖率 100%。
- LoongArch 环境执行 `scripts/check_deploy.py` 通过。
- `maintenance_cases.review_status='approved'` 不少于 100 条。
- `eval_questions.review_status='approved'` 不少于 100 条。
