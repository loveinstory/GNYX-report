# 更新记录

## V1.1 - 2026-06-11

本版本作为当前开发状态的 GitHub 恢复节点，保留多套餐 OCR、AI 辅助诊断、字段映射和 HTML 报告模板的最新实现。

### 新增与完善

- 新增/完善 P04、P06、P07、P17 套餐配置，包含 `manifest.json`、`fields.json`、`rules.json`、`ocr-strategy.json`、提示词和 HTML 模板资源。
- 扩展后端套餐加载、报告生成、OCR 日志、AI 解读合并和渲染流程，支持更多套餐的真实 OCR 数据接入。
- 完善桌面端报告管理、套餐配置展示和 OCR/AI 相关交互。

### P07 重点更新

- P07 OCR 策略升级到 `P07-ocr-strategy-v0.2-xie-three-page-json`，支持 P07 样例原始报告结构化识别。
- P07 字段配置升级到 `P07-fields-v0.5-symptom-address-cleanup`，保留 54 个字段映射，其中 16 个 AI 接入字段。
- P07 模板版本升级到 `P07-html-v0.4-symptom-address-cleanup`。
- 第 1 页患者信息调整：联系电话改为送检单位，评估方法固定为“化学发光法&比色法&免疫比浊法&测序法”，新增报告编号。
- 第 1 页“相关症状”绑定 OCR 临床诊断；为空或误识别为 `Anweikang/安为康` 时显示 `-`。
- 第 3 页检验结果概览按原始报告对齐：肝功能 15 项、肝纤维化 4 项。
- 第 5 页删除底部温馨提示，并按 A4 页面展示限制优化内容。
- 第 8 页公司地址更新为“安徽省合肥市庐阳区临泉路7266号研发中心楼1、4、5、6层”。

### 恢复说明

- 拉取该版本后运行 `npm install` 和 `.\.venv\Scripts\python -m pip install -r services\api\requirements.txt` 恢复依赖。
- 启动后端：`npm run dev:api`。
- 启动前端：`npm run dev:web`。
- 本次提交不包含 `storage/*.json`、数据库、导入文件、导出报告和渲染结果，避免上传真实检测数据。
