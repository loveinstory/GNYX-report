# 更新记录

## V1.1 - 2026-06-11

本版本作为当前开发状态的 GitHub 恢复节点，保留多套餐 OCR、AI 辅助诊断、字段映射和 HTML 报告模板的最新实现。

### 新增与完善

- 新增 P14「安康御癌专项评估健康管理报告」研发接入，包含 11 页 HTML 模板、关键字段配置、规则草案、OCR 策略占位和 AI 提示词；当前已完成第01-04、06-08、11页关键 `data-field` 绑定，并接入基础报告数据骨架与 AI 合并链路。
- 新增并升级 P13「年轻力精准评估健康管理报告」研发接入，包含 10 页 HTML 模板、字段配置、规则、OCR 策略和 AI 提示词；OCR 策略升级至 `P13-ocr-strategy-v0.2-telomere-json-pdf`，支持端粒报告 JSON OCR 结构和同版 PDF 文本层解析，第 07 页已调用 `assets/images/p07-food-pyramid.png` 食物金字塔图片。
- 新增并升级 P16「药物基因组学评估健康管理报告」研发接入，包含 16 页 HTML 模板、字段配置、规则、OCR 策略和 AI 提示词；OCR 策略升级至 `P16-ocr-strategy-v0.2-pgx-multireport-json-pdf`，支持 `reports[]` 多报告聚合 JSON OCR 结构，并在解析 `hebing44831.pdf` 时优先读取同目录 `OCR.txt` 作为结构化 sidecar 输入。
- 新增 P08「心血管代谢风险评估健康管理报告」研发接入，包含模板工程化、字段配置、规则草案、OCR 策略和 AI 提示词。
- 升级 P08 OCR 策略至 `P08-ocr-strategy-v0.2-professional-json-adapter`，适配 `hebing22757.pdf` 同形态完整 OCR JSON，保留 9 个源检验项目并单位换算生成 Ang II/Ang I 比值。
- 调整 P08 首页患者信息：联系电话改为送检单位，样本信息和评估方法改为固定展示，并新增报告编号字段绑定 OCR 条形码。
- 新增 P09「女性激素平衡评估健康管理报告」研发接入，包含 HTML 模板工程化、字段配置、规则草案、OCR 策略和 AI 提示词。
- P09 首版围绕 E2、LH、FSH、孕酮、睾酮、皮质醇、SHBG、AMH、泌乳素和总IgE 建立字段与规则骨架，基础 OCR/AI/渲染链路已接入，等待真实或脱敏样例继续完善专项 OCR。
- 升级 P09 OCR 策略至 `P09-ocr-strategy-v0.2-structured-json-row-adapter`，基于 `hebing93044.pdf` 校准单位前置行解析和 `report_info + pages[].test_items` JSON adapter，修正 E2/FSH/PRL/AMH 等项目单位串行和短别名误命中问题。
- 升级 P09 模板/字段/规则/提示词至 `P09-html-v0.2-data-bound-layout`、`P09-fields-v0.3-ai-binding-layout`、`P09-rules-v0.2-ai-binding-layout`、`P09-prompts-v0.2-a4-bound`，梳理第02-06页真实数据与占位内容，补齐 AI 字段映射并压缩版面文案到 A4 单页。
- 升级 P11 OCR 策略至 `P11-ocr-strategy-v0.4-food-intolerance-42-adapter`，适配食物不耐受完整 42 项 `reportMeta + foodIntoleranceResults` OCR JSON，同时兼容 `reportMeta + sections[].results + foodAppendix` 综合 JSON，归一 IgG1-IgG4、总IgE 和食物不耐受结果，并保留 PDF 文本层回退解析。
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
