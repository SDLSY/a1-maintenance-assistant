# 维修手册入库目录

把可用于比赛的数据文件放在这里：

- `.pdf`：维修手册、说明书、安全规程。
- `.txt` / `.md`：已整理的故障案例、检修 SOP、培训材料。

入库方式：

```powershell
cd D:\30726\Desktop\竞赛目录\a1-maintenance-assistant
.\.venv\Scripts\python.exe -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8051
```

然后在 Web 的“资源与模型”页点击“入库手册”，或调用：

```powershell
Invoke-RestMethod -Uri http://127.0.0.1:8051/api/admin/ingest-manuals -Method Post
```

注意：

- 不要放入没有授权使用的商业维修手册。
- 文件名建议包含设备类型和型号，例如 `motor-Y2-160M-maintenance.md`。
- 公开来源要记录到参赛材料的数据来源说明里。

