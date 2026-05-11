# 机械专业审核指南

目标：把团队自建案例和评测问答从“演示数据”升级为“机械专业审核数据”，用于答辩说明和量化评测。

## 审核包导出

```powershell
.\.venv\Scripts\python.exe .\scripts\export_review_pack.py
```

生成文件：

```text
data/review/mechanical_cases_review.csv
data/review/eval_questions_review.csv
```

CSV 使用 UTF-8 with BOM，Excel 可直接打开。

## 案例审核标准

每条案例至少检查：

- 故障现象是否符合设备机理。
- 原因分析是否可由现象支撑。
- 处置措施是否包含停机、断电挂牌、泄压/降温、PPE、复测和验收。
- 备件和工具是否合理。
- 风险等级是否偏低。
- 是否需要补充引用手册页码。

建议评分：

```text
mechanical_accuracy_score: 1-5
sop_completeness_score: 1-5
safety_score: 1-5
decision: approve / revise / reject
review_status: approved / needs_revision / rejected
reviewer: 审核人姓名
review_notes: 修改意见
```

## 评测问答审核标准

每条评测题至少检查：

- 问题是否覆盖真实检修场景。
- 期望来源是否能在手册库检索到。
- 期望故障类型是否唯一或可解释。
- 安全关键词是否覆盖 LOTO、PPE、防误启动、泄压/降温、复测验收。
- 难度是否合理，避免全是模板化简单题。

建议字段：

```text
difficulty: easy / medium / hard
expected_reference_ok: yes / no
decision: approve / revise / reject
review_status: approved / needs_revision / rejected
reviewer: 审核人姓名
review_notes: 修改意见
```

## 审核结果回写

审核中或审核后，可先查看进度，不会修改数据库：

```powershell
.\.venv\Scripts\python.exe .\scripts\review_progress.py
```

该脚本会生成：

```text
docs/MECHANICAL_REVIEW_STATUS.md
```

只有当案例和评测题的 `approved` 数量都达到目标时，`ready_for_goal` 才会变为 `true`。

确认 CSV 无误后再回写数据库：

```powershell
.\.venv\Scripts\python.exe .\scripts\import_review_pack.py
```

回写后可以在数据库中统计：

```sql
SELECT review_status, COUNT(*) FROM maintenance_cases GROUP BY review_status;
SELECT review_status, COUNT(*) FROM eval_questions GROUP BY review_status;
```

正式答辩前的最低目标：

- `maintenance_cases.review_status='approved'` 不少于 100 条。
- `eval_questions.review_status='approved'` 不少于 100 条。
- 抽样 20 条案例人工复核，无严重安全漏项。
