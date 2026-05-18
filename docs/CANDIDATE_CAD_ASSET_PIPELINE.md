# 现场照片驱动的候选 CAD 资产沉淀链路

## 定位

这条链路是 Tri-MRO 的结构链增强工具，用于把现场照片转化为可审核的候选 CAD 资产。它不用于尺寸测量、制造加工或安全放行。

## 链路

```text
现场照片
-> VLM/OCR 观察结果
-> 结构化 CAD spec
-> CadQuery / OpenSCAD 候选代码
-> SVG 渲染预览
-> VLM 对比报告
-> 人工审核
-> 候选 CAD 资产池
```

## v1 实现

- 后端表：`candidate_cad_assets`
- 生成入口：`POST /api/cad/candidates/from-visual`
- 列表入口：`GET /api/cad/candidates`
- 审核入口：`POST /api/cad/candidates/{id}/review`
- 文件入口：`GET /api/cad/candidates/{id}/files/{preview|spec|cadquery|openscad|observation}`
- 前端入口：资源与模型页的“候选 CAD 资产池”

## 风险边界

每个候选资产都携带 `risk_boundary`：

- `not_for_measurement: true`
- `not_for_manufacturing: true`
- `not_for_safety_release: true`
- 必须经过机械审核后才能作为候选结构链资产使用。

## 后续升级

- 将 SVG 预览替换为真实 CadQuery/FreeCAD 渲染沙箱。
- 增加多视角 PNG 渲染和 VLM 图像相似度评分。
- 增加人工修正 CAD spec 的编辑页。
- 将 `approved_candidate` 资产与 CAD 工位的 `component_key` 绑定。
- 通过许可证和几何审核后，允许晋升为标准 CAD 资产。
