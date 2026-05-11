# A1 最终全图像答辩版交付说明

更新时间：2026-05-11

## 主交付文件

- 最终 PPT：`D:\30726\Desktop\竞赛目录\a1-maintenance-assistant\materials\A1-maintenance-assistant-defense-image-only-final.pptx`
- 交付包：`D:\30726\Desktop\竞赛目录\a1-maintenance-assistant\materials\A1-defense-delivery-pack.zip`
- 生成脚本：`scripts/build_defense_image_only_final.py`
- 验证脚本：`scripts/verify_defense_materials.py`

## 交付口径

这版 PPT 按用户后续要求改为“整页图片版”：每一页在 PPTX 内都是一张整页图片，PPT 内没有可编辑文字层，避免出现背景图加文本框的拼贴感。

前 14 页来自 `gpt-image-2` 全图生成页；第 15-18 页用于补足答辩可信证据，基于真实系统截图、评测结果、机械审核摘要和部署验证生成整页图片，再统一合成为 image-only PPT。

## 验证结果

- 页数：18 页
- PPT 图片对象：18 个
- PPT 文本框：0 个
- slide XML 文本节点：0 个
- 最终 PNG 页面：18 张
- 敏感信息扫描：未发现密钥模式

## 仍需人工确认

- 学校、队伍名、成员、指导老师是否允许展示。
- 正式答辩当天重新冷启动公网服务并复测核心链路。
- 如果前端 UI 后续大改，第 15 页真实系统截图需要重新截取。
