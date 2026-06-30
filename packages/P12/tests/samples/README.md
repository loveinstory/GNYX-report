# P12 样例说明

当前版本已接入 P12 HTML 模板、套餐配置、PDF文本层 OCR、P12 OCR JSON 适配器和 AI 提示词。`hebing80490.pdf` 用于线粒体能量与疲劳评估报告的初始链路验证。

`hebing5001.pdf` 对应的OCR JSON格式包含 `report_overview`、`test_items`、`antioxidant_assessment`、`nad_assessment` 四个顶层字段，P12 OCR策略版本已升级为 `P12-ocr-strategy-v0.2-json-antioxidant-nad`。

后续如补充更多真实或脱敏 PDF 样例，需要继续完善辅酶Q10、NAD+在不同报告版式中的 OCR 别名、单位和参考范围解析规则。
