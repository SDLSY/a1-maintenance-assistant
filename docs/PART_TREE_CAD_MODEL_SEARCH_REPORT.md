# 可拆分 CAD 零件树模型检索报告

更新时间：2026-05-13

## 结论

本轮找到了 8 个可用于后续升级的 CAD 候选，并完成下载与二次验证：

- 3 个 FreeCAD `FCStd` 候选具备较清晰的 FreeCAD 对象/特征树，最适合做对象命名绑定。
- 1 个 FreeCAD 泵类 `FCStd` 候选具备对象树，但不是严格的离心泵教学剖切模型，需要机械队友确认部件语义。
- 4 个 Marathon OS `STEP` 候选是多实体 CAD，可拆分为多个 solid，但没有显式 STEP assembly product tree，需要二次人工命名。
- 本轮没有找到“免登录、授权清晰、已带完整零件名和装配层级”的发动机/离心泵 CAD assembly。发动机主线暂时建议使用多实体 STEP，再人工抽取和命名关键部件。

验证报告：`data/3d/part_tree_candidates/verification_report.json`

资源清单：`data/3d/part_tree_candidates/candidate_manifest.json`

验证脚本：`scripts/verify_part_tree_cad_candidates.py`

## 候选清单

| 设备 | 候选 | 来源 | 本地文件 | 验证结论 | 用法建议 |
| --- | --- | --- | --- | --- | --- |
| 轴承 | 6201-2RS Ball Bearing | FreeCAD-library | `data/3d/authorized_models/freecad_6201_2rs_bearing/6201-2RS_Ball_Bearing.FCStd` | `freecad_feature_tree`，22 个对象，11 个特征 | 可继续作为轴承主线，但需要在 FreeCAD 中把外圈、内圈、滚动体等对象拆得更明确 |
| 轴承 | Parametric Ball Bearing | FreeCAD-library | `data/3d/part_tree_candidates/freecad_parametric_ball_bearing_fcstd/parametric_ball_bearing.FCStd` | `freecad_feature_tree`，32 个对象，16 个特征 | 参数化程度更好，适合作为后续轴承对象树重构候选 |
| 电机 | NEMA 23 Stepper Motor with Connector | FreeCAD-library | `data/3d/authorized_models/freecad_nema23_stepper_motor/NEMA_23_with_connector.FCStd` | `freecad_feature_tree`，332 个对象，166 个特征 | 电机最适合优先升级对象命名，能覆盖输出轴、端盖、机壳、接线端 |
| 电机 | Electric Motor STEP | Marathon OS | `data/3d/part_tree_candidates/marathon_electric_motor_step/electric_motor.step` | `multi_solid_cad`，12 个 B-rep solid | 作为补充多实体电机，不如 FreeCAD NEMA23 适合直接命名 |
| 泵 | Vertical Pump | FreeCAD-library | `data/3d/part_tree_candidates/freecad_vertical_pump_fcstd/vertical_pump.FCStd` | `freecad_feature_tree`，250 个对象，125 个特征 | 有对象树，但是否能映射到离心泵密封区/叶轮/泵轴需要人工确认 |
| 泵 | Centrifugal Motor Pump STEP | Marathon OS | `data/3d/part_tree_candidates/marathon_centrifugal_motor_pump_step/cf_assy.step` | `multi_solid_cad`，7 个 B-rep solid | 场景最接近离心泵，但没有零件名，适合后续做 solid 分组和对象重命名 |
| 发动机 | V6 Engine STEP | Marathon OS | `data/3d/part_tree_candidates/marathon_v6_engine_step/v6_engine.step` | `multi_solid_cad`，21 个 B-rep solid | 轻量发动机候选，可用于火花塞/缸盖/缸体定位实验 |
| 发动机 | Engine ASM STEP | Marathon OS | `data/3d/part_tree_candidates/marathon_engine_asm_step/engine_asm.step` | `multi_solid_cad`，207 个 B-rep solid | 几何最完整但 60MB，建议只抽取关键部件后再进入主演示 |

## 关键判断

`FCStd` 比普通 `STEP` 更适合我们当前目标，因为 FreeCAD 文件天然保留对象、Body、Part、Sketch、Pad、Chamfer 等特征树。对于“检修数字孪生工位”，这比一个单 mesh 或匿名多 solid STEP 更容易做部件命名、爆炸视图和 SOP 绑定。

Marathon OS 的 STEP 模型虽然页面声明是免费下载并在页面 JSON-LD 中标注 CC-BY-4.0，但实际 STEP 文件里只有单一 `PRODUCT`，没有 `NEXT_ASSEMBLY_USAGE_OCCURRENCE` 装配关系。因此它们属于“多实体 CAD”，不是“带原生零件名的完整装配树”。它们仍然有价值，但必须经过 FreeCAD/Blender/OCC 二次处理，把 solid 按部件分组并命名。

FreeCAD-library 的资源许可清楚，仓库 README 明确说明部件使用 CC-BY 3.0。当前最稳妥路线是：电机、轴承优先走 FreeCAD 对象树；泵用 FreeCAD Vertical Pump + Marathon Centrifugal Motor Pump 交叉验证；发动机暂用 Marathon Engine 多实体 STEP，继续寻找更合适的教学发动机装配 CAD。

## 接入建议

1. 优先升级 `freecad_nema23_stepper_existing` 和 `freecad_vertical_pump_fcstd`：用 FreeCAD 导出带对象名的 GLB，替换当前 marker-only 绑定。
2. 发动机不要直接加载 60MB `engine_asm.step` 进前端。先在 FreeCAD/Blender 中抽取火花塞、缸盖、缸体、曲轴箱、起动电机、水泵等关键部件，导出轻量 GLB。
3. 对 Marathon STEP 做二次命名时，必须保留原始 STEP、source page、SHA256、许可证声明和处理日志。
4. 若想做到真正专业级装配树，仍建议从学校机械实验室、指导老师或教材配套资源获取授权的发动机/离心泵教学 CAD。公开互联网上免登录且授权清晰的完整装配树资源较少。

## 验证命令

```powershell
.venv\Scripts\python.exe scripts\verify_part_tree_cad_candidates.py
```

当前结果：

```text
total: 8
passed: 8
failed: 0
assembly_tree: 0
multi_solid_or_feature_tree: 8
```

`assembly_tree: 0` 是刻意保留的风险信号：目前候选能拆，但公开资源没有提供完整、可直接信任的原生装配关系。下一阶段的工作重点不是继续找普通 mesh，而是把这些候选做对象重命名和关键部件抽取。
