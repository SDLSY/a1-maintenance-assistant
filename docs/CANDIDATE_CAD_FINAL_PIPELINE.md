# 候选 CAD 最终版实验链路

## 定位

候选 CAD 功能用于展示“现场照片到结构链资产”的实验闭环，不作为尺寸测量、制造加工或安全放行依据。它的价值是把 OCR/VLM 识别到的设备、部件、孔位、铭牌和相对位置，转成可审核、可追溯、可晋升的 CAD 候选资产。

主线链路：

```text
现场照片
→ OCR/VLM 结构观察
→ CAD spec
→ CadQuery/OpenSCAD 代码
→ STEP/STL/GLB/PNG 产物
→ FreeCAD 校验 + OpenSCAD 导出 + Blender 多视角渲染
→ 人工审核
→ 晋升为 CAD 结构工位资产
```

## 当前实现

- `/api/cad/runtime`：探测 CadQuery、trimesh、Pillow、FreeCAD、OpenSCAD、Blender 可用性，并返回推荐运行模式。
- `/api/cad/candidates/from-visual`：从已上传视觉资产生成候选 CAD。
- `/api/cad/candidates/{id}/spec`：人工修正 CAD spec 的参数和部件 key。
- `/api/cad/candidates/{id}/render`：重新生成 STEP、STL、OpenSCAD STL、GLB 和四视图 PNG。
- `/api/cad/candidates/{id}/review`：机械审核通过或驳回。
- `/api/cad/candidates/{id}/promote`：审核通过后晋升为 CAD 工位标准候选资产。

当前环境验证结果：

```text
CadQuery: 可用，用于参数化 STEP/STL 生成
trimesh: 可用，用于浏览器 GLB 生成
Pillow: 可用，用作兜底多视角 PNG 预览
FreeCAD: 可用，用于 STEP 导入校验、体积/面积/对象数检查
OpenSCAD: 可用，用于校验 OpenSCAD 源码并导出 STL
Blender: 可用，用于高质量正交多视角渲染
推荐模式: real_render
```

## 产物清单

每个候选资产会生成 `artifact_manifest.json`，记录：

- 源文件：`cad_spec.json`、`observation.json`、`candidate_model.py`、`candidate_model.scad`
- CAD 文件：`candidate.step`、`candidate.stl`、`candidate_openscad.stl`、`candidate.glb`
- 渲染图：`render_front.png`、`render_side.png`、`render_top.png`、`render_iso.png`
- 质量报告：`freecad_validation.json`、`openscad_export_report.json`、`blender_render_report.json`
- 运行时报告：`runtime_report.json`
- 对比报告：`comparison_report.json`
- 风险边界：不用于测量、制造、安全放行，必须人工审核

## 前端审核工位

资源与模型页包含“候选 CAD 审核工位”：

- 显示 CAD 运行模式和工具可用性。
- 展示 Blender 多视角渲染图。
- 提供 STEP/STL/OpenSCAD STL/GLB/FreeCAD 校验/Blender 报告/artifact manifest 链接。
- 支持编辑 CAD spec 并重新渲染。
- 支持批准候选和晋升为结构链资产。

## 答辩表述

建议把该功能作为“结构链增强实验”，不要包装成成熟的 photo-to-CAD 工业算法。

推荐说法：

> 系统将现场照片中的部件和结构线索转化为可审核 CAD spec，并生成候选 CAD 产物。候选资产必须经过 FreeCAD 校验、OpenSCAD 导出、Blender 多视角渲染和机械审核，才能晋升为 CAD 结构工位资产；所有候选模型都有产物清单、运行时报告、人工审核记录和风险边界说明。

不建议说法：

> 系统能够从单张照片准确重建可制造 CAD。

## 风险边界

- 复杂设备的主展示仍坚持使用授权 CAD/GLB 或经过验证的标准模型。
- 候选 CAD 是结构理解草稿，适合辅助人工讨论部件、相对位置和结构链绑定。
- 单图生成结果不得作为尺寸测量、加工制造或安全放行依据。
- 如果图像证据不足，系统必须输出待人工复核，不得强行晋升。
