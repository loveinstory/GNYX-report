# P13 样例说明

当前版本已接入 P13《年轻力精准评估健康管理报告》HTML 模板、字段配置、规则、OCR 策略和 AI 提示词。

OCR 策略版本为 `P13-ocr-strategy-v0.2-telomere-json-pdf`，已基于测试 PDF `260601_WTFY_1012_20260601185401505.pdf` 及其 JSON OCR 输出校准，支持：

- JSON OCR：`report_info + patient_info + test_results + recommendations + educational_content + signature`
- PDF 文本层：基础信息、端粒年龄差、端粒相对长度、端粒 Ct 值、内参 Ct 值和同龄人群百分位
- 规则推导：由实际年龄与“端粒年龄比实际年龄大/小 X 岁”推导 `p13.telomere_age`
