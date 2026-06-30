# P14 测试样例说明

当前版本已接入 P14《安康御癌专项评估健康管理报告》HTML 模板、关键字段配置、规则草案、OCR 策略和 AI 提示词。

当前已完成：

- 模板工程化复制入仓：`D:\AWK-OCR\figma-plugin-figma-openai-curated-1\outputs\html-report\P14`
- 第01-04、06-08、11页关键字段 `data-field` 绑定
- 后端基础报告数据骨架与 AI 合并链路接入
- 基于 `D:\AWK-OCR\功能医学检测报告模板（2026.4.3）\P14\hebing10788.pdf` 对应的 `reports[]` 聚合 JSON OCR 结构升级 `P14-ocr-strategy-v0.2-cancer-multireport-json-pdf`
- 支持疾病风险评估、五癌甲基化和 CTC 计数分型三类子报告统一归一，并输出 CDA/PTF/CTF、五癌甲基化、CTC 总数与历史趋势

当前待补：

- CDA、PTF、CTF、五癌甲基化、CTC 的专项 OCR 校准
- 更多 P14 样例对风险分层、连续复测趋势和字段边界的回归测试
