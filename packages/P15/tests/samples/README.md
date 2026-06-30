# P15 样例说明

当前版本已接入 P15《环境荷尔蒙评估健康管理报告》HTML 模板、基础字段配置、规则草案、OCR 策略和 AI 提示词。

本轮目标：

- 打通套餐注册、模板渲染、AI 字段合并与报告管理链路。
- 接入 P15 JSON OCR 结构：`report_info + patient_info + test_details + results + report_notes + contact_info`。
- 将第 01-06、10 页的关键数据位工程化为 `data-field`。
- 保留第 07-09 页固定图片页，不做动态字段绑定。

当前 OCR 策略版本：

- `P15-ocr-strategy-v0.2-environment-hormone-json-pdf`

已校准样例：

- 测试 PDF：`D:\AWK-OCR\功能医学检测报告模板（2026.4.3）\P15\260625_TAP_5103_20260626093335602 (1).pdf`
- 对应 JSON OCR 结构：`report_info + patient_info + test_details + results + report_notes + contact_info`

待下一轮继续：

- 基于上述 PDF 和更多真实样例继续校准 PDF 文本层识别。
- 升级环境荷尔蒙项目 OCR 文本层别名、参考范围与状态判定。
- 基于真实结构化结果细化综合暴露指数与 AI 输出边界。
