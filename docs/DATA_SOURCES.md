# 数据来源建议

系统支持 PDF/TXT/MD 入库。下面是建议的数据类型，不建议直接把受版权保护的厂家完整手册公开提交。

## 维修手册与规范

- 学校实验室自有设备说明书：优先使用，最容易取得授权。
- 厂商公开下载的说明书：记录 URL、下载日期和许可说明。
- 国家/行业安全规范摘要：只提取与检修合规相关的条目，保留来源。
- 自建案例：由机械专业队友按真实故障机理构造，标注“团队自建”。

## 公开手册来源清单

已建立可审计来源清单：

```text
data/sources/public_manual_sources.json
```

当前清单覆盖 ABB、WEG、Grundfos、Xylem、Patterson、Pentair、SKF 等公开厂商资料，设备类型包含电机、泵和轴承。清单中的 PDF 只用于本地参赛研究和引用追踪，不默认具备再分发授权。

验证 URL 可用性：

```powershell
.\.venv\Scripts\python.exe .\scripts\validate_public_sources.py
```

下载到本地原始资料目录：

```powershell
.\.venv\Scripts\python.exe .\scripts\download_public_sources.py --required-only
.\.venv\Scripts\python.exe .\scripts\download_public_sources.py
```

下载脚本会把 PDF 放到 `data/raw/manuals/public`，并为每个文件写入 `*.source.json` sidecar。后端入库会读取 sidecar 中的 `source_url`、`license` 和 `version` 字段，确保查询引用能追溯来源。

## A1-MAKG 外部参考与官方样例

新增资源清单位于：

```text
data/sources/external_reference_resources.json
```

二次验证输出：

```text
data/sources/verified_resources.json
docs/EXTERNAL_RESOURCE_VERIFICATION.md
```

官方《摩托车发动机维修手册.pdf》作为 A1 样例资料纳入 `data/raw/manuals/official/`，设备类型为 `engine`。该文件用于本地比赛研究和演示，不默认随提交包重新分发。

## 公开数据集

- MVTec AD：工业缺陷图像，可用于视觉故障检索演示。
- MIMII：机器异常声音数据，可作为扩展演示，不作为 A1 主链路依赖。
- MyFixit Dataset：维修步骤和工具/部件标注，可参考 SOP 数据结构。

## 数据记录字段

每份资料至少记录：

- 标题
- 来源 URL 或来源说明
- 许可/授权
- 版本或下载日期
- 设备类型
- 设备型号
- 页码或章节
