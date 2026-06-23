from __future__ import annotations

from datetime import datetime
import re
from typing import Any

from app.services.p11_support import build_p11_report_data


P17_REPORT_NAME = "阴道微生态健康评估管理报告"
P17_METHOD = "荧光PCR法"
P17_HPV_HIGH_RISK_TYPES = ("16", "18", "26", "31", "33", "35", "39", "45", "51", "52", "53", "56", "58", "59", "66", "68", "73", "82")
P17_HPV_LOW_RISK_TYPES = ("6", "11", "40", "42", "43", "44", "61", "81", "83")
P17_MICROBE_TEMPLATE_ROWS = (
    ("卷曲乳杆菌", "good"),
    ("詹氏乳杆菌", "good"),
    ("加氏乳杆菌", "good"),
    ("惰性乳杆菌", "good"),
    ("双歧杆菌", "good"),
    ("白假丝酵母菌", "conditional"),
    ("光滑假丝酵母菌", "conditional"),
    ("热带假丝酵母菌", "conditional"),
    ("耳道假丝酵母菌", "conditional"),
    ("克柔假丝酵母菌", "conditional"),
    ("都柏林假丝酵母菌", "conditional"),
    ("近平滑假丝酵母菌", "conditional"),
    ("B族链球菌", "conditional"),
    ("亨氏巴尔通体", "conditional"),
    ("细小棒状杆菌", "conditional"),
    ("衣氏放线菌", "conditional"),
    ("阴道加德纳菌", "conditional"),
    ("阴道阿托波氏菌", "conditional"),
    ("纤毛菌", "conditional"),
    ("微小脲原体", "conditional"),
    ("解脲脲原体", "conditional"),
    ("人型支原体", "conditional"),
    ("单纯疱疹病毒1型", "pathogen"),
    ("单纯疱疹病毒2型", "pathogen"),
    ("淋球菌", "pathogen"),
    ("杜克雷嗜血杆菌", "pathogen"),
    ("生殖支原体", "pathogen"),
    ("沙眼衣原体", "pathogen"),
    ("梅毒螺旋体", "pathogen"),
    ("阴道毛滴虫", "pathogen"),
    ("阿米巴原虫", "pathogen"),
)
P17_MICROBE_ALIASES = {
    "微小脲原体": ("微小腺原体",),
    "解脲脲原体": ("解脲支原体",),
    "人型支原体": ("人型支原体1", "人型支原体 1"),
    "B族链球菌": ("B 族链球菌", "无乳链球菌"),
    "单纯疱疹病毒1型": ("单纯疱疹病毒 1 型",),
    "单纯疱疹病毒2型": ("单纯疱疹病毒 2 型",),
    "人乳头瘤病毒（HPV）": ("HPV", "人乳头瘤病毒"),
}
P04_REPORT_NAME = "营养素状态评估健康管理报告"
P04_METHOD = "原子光谱法、LC-MS/MS法"
P06_REPORT_NAME = "慢性炎症与氧化应激评估健康管理报告"
P06_METHOD = "免疫比浊&磁微粒化学发光&流式细胞"
P07_REPORT_NAME = "肝脏解毒功能评估健康管理报告"
P07_METHOD = "化学发光法&比色法&免疫比浊法&测序法"
P07_TEMPLATE_VERSION = "P07-html-v0.4-symptom-address-cleanup"
P07_RULE_VERSION = "P07-rules-v0.2-original-report-aligned"
P07_PROMPT_VERSION = "P07-prompts-v0.2-field-bound-a4"
P07_ORGANIZATION_ADDRESS = "安徽省合肥市庐阳区临泉路7266号研发中心楼1、4、5、6层"
P08_REPORT_NAME = "心血管代谢风险评估健康管理报告"
P08_ASSESSMENT_TYPE = "心血管代谢风险评估"
P08_METHOD = "化学发光&免疫比浊"
P08_TEMPLATE_VERSION = "P08-html-v0.2-cover-ocr-info"
P08_RULE_VERSION = "P08-rules-v0.1-draft"
P08_PROMPT_VERSION = "P08-prompts-v0.1"
P08_ORGANIZATION_ADDRESS = "安徽省合肥市庐阳区临泉路7266号研发中心楼1、4、5、6层"
P09_REPORT_NAME = "女性激素平衡评估健康管理报告"
P09_ASSESSMENT_TYPE = "女性激素平衡评估"
P09_METHOD = "化学发光法"
P09_TEMPLATE_VERSION = "P09-html-v0.2-data-bound-layout"
P09_RULE_VERSION = "P09-rules-v0.2-ai-binding-layout"
P09_PROMPT_VERSION = "P09-prompts-v0.2-a4-bound"
P09_ORGANIZATION_ADDRESS = "安徽省合肥市庐阳区临泉路7266号研发中心楼1、4、5、6层"
P10_REPORT_NAME = "男性激素与代谢状态评估健康管理报告"
P10_ASSESSMENT_TYPE = "男性激素与代谢状态评估"
P10_SAMPLE_TYPE = "血清/EDTA抗凝血"
P10_METHOD = "基因测序&化学发光&ELISA法"
P10_TEMPLATE_VERSION = "P10-html-v0.4-reportmeta-json-blueprint"
P10_RULE_VERSION = "P10-rules-v0.1-ai-binding-layout"
P10_PROMPT_VERSION = "P10-prompts-v0.1-a4-bound"
P10_ORGANIZATION_ADDRESS = "安徽省合肥市庐阳区临泉路7266号研发中心楼1层"
P11_REPORT_NAME = "食物敏感/免疫相关评估健康管理报告"
P11_ASSESSMENT_TYPE = "食物敏感/免疫相关评估"
P11_SAMPLE_TYPE = "免疫检测"
P11_METHOD = "食物不耐受与免疫相关综合评估"
P11_TEMPLATE_VERSION = "P11-html-v0.1-initial-binding"
P11_RULE_VERSION = "P11-rules-v0.1-draft"
P11_PROMPT_VERSION = "P11-prompts-v0.1-a4-bound"
P11_ORGANIZATION_ADDRESS = "安徽省合肥市庐阳区临泉路7266号研发中心楼5层"
P08_CARDIOVASCULAR_DEFINITIONS: dict[str, dict[str, Any]] = {
    "nt_probnp": {
        "name": "N端脑利钠肽前体",
        "short_name": "NT-proBNP",
        "reference": "0-125.00",
        "unit": "pg/mL",
        "method": "化学发光法",
        "keywords": ["N端脑利钠肽前体", "N 端脑利钠肽前体", "NT-proBNP", "NT proBNP", "NT-pro BNP"],
    },
    "d_dimer": {
        "name": "D-二聚体",
        "short_name": "D-D",
        "reference": "0-0.55",
        "unit": "mg/L FEU",
        "method": "免疫比浊法",
        "keywords": ["D-二聚体", "D二聚体", "D-D", "D Dimer", "D-Dimer"],
    },
    "ffa": {
        "name": "游离脂肪酸",
        "short_name": "FFA",
        "reference": "0.10-0.60",
        "unit": "mmol/L",
        "method": "酶法",
        "keywords": ["游离脂肪酸", "FFA", "Free Fatty Acid"],
    },
}
P08_RAAS_DEFINITIONS: dict[str, dict[str, Any]] = {
    "angiotensin_i": {
        "name": "血管紧张素I",
        "short_name": "Ang I",
        "reference": "28.0-125.0",
        "unit": "pg/mL",
        "method": "化学发光法",
        "keywords": ["血管紧张素I", "血管紧张素Ⅰ", "Ang I", "AngI", "Angiotensin I"],
    },
    "angiotensin_ii": {
        "name": "血管紧张素II",
        "short_name": "Ang II",
        "reference": "21.0-75.0",
        "unit": "pg/mL",
        "method": "化学发光法",
        "keywords": ["血管紧张素II", "血管紧张素Ⅱ", "Ang II", "AngII", "Angiotensin II"],
    },
    "angiotensin_ratio": {
        "name": "血管紧张素II / I 比值",
        "short_name": "Ang II/Ang I",
        "reference": "0.20-1.20",
        "unit": "",
        "method": "计算法",
        "keywords": ["血管紧张素II / I 比值", "血管紧张素II/I", "Ang II/Ang I", "AngII/AngI", "Ang II / Ang I"],
    },
    "renin": {
        "name": "肾素活性",
        "short_name": "Renin",
        "reference": "0.30-5.70",
        "unit": "ng/mL/h",
        "method": "化学发光法",
        "keywords": ["肾素活性", "Renin", "PRA"],
    },
    "aldosterone": {
        "name": "醛固酮",
        "short_name": "Aldo",
        "reference": "79.0-277.0",
        "unit": "pg/mL",
        "method": "化学发光法",
        "keywords": ["醛固酮", "Aldo", "Aldosterone"],
    },
}
P09_INDICATOR_DEFINITIONS: dict[str, dict[str, Any]] = {
    "e2": {
        "name": "雌二醇",
        "short_name": "E2",
        "reference": "卵泡期:19.5-144.2 排卵期:63.9-356.7 黄体期:55.8-214.2 绝经期:0-32.2",
        "unit": "pg/mL",
        "method": "化学发光法",
        "group": "core_hormones",
        "keywords": ["雌二醇", "E2", "Estradiol"],
    },
    "lh": {
        "name": "促黄体生成素",
        "short_name": "LH",
        "reference": "卵泡期:1.9-12.5 排卵期:8.7-76.3 黄体期:0.5-16.9 绝经期:15.9-54 妊娠期:0-1.5",
        "unit": "mIU/mL",
        "method": "化学发光法",
        "group": "core_hormones",
        "keywords": ["促黄体生成素", "黄体生成素", "LH"],
    },
    "fsh": {
        "name": "促卵泡刺激素",
        "short_name": "FSH",
        "reference": "卵泡期:2.5-10.2 排卵期:3.4-33.40 黄体期:1.5-9.1 绝经期:23-116.3 妊娠期:<0.3",
        "unit": "mIU/mL",
        "method": "化学发光法",
        "group": "core_hormones",
        "keywords": ["促卵泡刺激素", "卵泡刺激素", "FSH"],
    },
    "progesterone": {
        "name": "孕酮",
        "short_name": "PROG",
        "reference": "卵泡期:0-1.4 黄体期:3.34-25.56 绝经期:0-0.73 孕早期:11.2-90 孕中期:25.55-89.4 孕晚期:48.4-422.5",
        "unit": "ng/mL",
        "method": "化学发光法",
        "group": "core_hormones",
        "keywords": ["孕酮", "孕激素", "Progesterone", "PROG"],
    },
    "testosterone": {
        "name": "睾酮",
        "short_name": "T",
        "reference": "0.08--0.35",
        "unit": "ng/mL",
        "method": "化学发光法",
        "group": "core_hormones",
        "keywords": ["睾酮", "总睾酮", "Testosterone"],
    },
    "cortisol": {
        "name": "皮质醇",
        "short_name": "Cortisol",
        "reference": "",
        "unit": "nmol/L",
        "method": "化学发光法",
        "group": "stress_metabolism",
        "keywords": ["皮质醇", "Cortisol", "CORT"],
    },
    "shbg": {
        "name": "性激素结合球蛋白",
        "short_name": "SHBG",
        "reference": "女:20岁-49岁:22.52-134.90",
        "unit": "nmol/L",
        "method": "化学发光法",
        "group": "ovarian_reserve_binding",
        "keywords": ["性激素结合球蛋白", "SHBG"],
    },
    "amh": {
        "name": "抗缪勒氏管激素",
        "short_name": "AMH",
        "reference": "0--4.25",
        "unit": "ng/mL",
        "method": "化学发光法",
        "group": "ovarian_reserve_binding",
        "keywords": ["抗缪勒氏管激素", "抗穆勒氏管激素", "AMH"],
    },
    "prolactin": {
        "name": "泌乳素",
        "short_name": "PRL",
        "reference": "未妊娠:59-619 妊娠期:206-4420 绝经期:38-430",
        "unit": "uIU/mL",
        "method": "化学发光法",
        "group": "ovarian_reserve_binding",
        "keywords": ["泌乳素", "催乳素", "PRL", "Prolactin"],
    },
    "total_ige": {
        "name": "总IgE",
        "short_name": "IgE",
        "reference": "0--100",
        "unit": "IU/mL",
        "method": "化学发光法",
        "group": "immune_allergy",
        "keywords": ["总IgE", "总 IgE", "Total IgE", "IgE"],
    },
}
P07_LIVER_FUNCTION_DEFINITIONS: dict[str, dict[str, Any]] = {
    "alt": {
        "name": "丙氨酸氨基转移酶",
        "short_name": "ALT（谷丙转氨酶）",
        "reference": "9-50",
        "unit": "U/L",
        "method": "肝功能检测",
        "keywords": ["丙氨酸氨基转移酶", "谷丙转氨酶", "ALT"],
    },
    "pab": {
        "name": "前白蛋白",
        "short_name": "前白蛋白（PAB）",
        "reference": "200-430",
        "unit": "mg/L",
        "method": "肝功能检测",
        "keywords": ["前白蛋白", "PAB"],
    },
    "ast": {
        "name": "天门冬氨酸氨基转移酶",
        "short_name": "AST（谷草转氨酶）",
        "reference": "15-40",
        "unit": "U/L",
        "method": "肝功能检测",
        "keywords": ["天门冬氨酸氨基转移酶", "天冬氨酸氨基转移酶", "谷草转氨酶", "AST"],
    },
    "ast_alt_ratio": {
        "name": "谷草谷丙比",
        "short_name": "谷草谷丙比（AST/ALT）",
        "reference": "",
        "unit": "",
        "method": "肝功能检测",
        "keywords": ["谷草谷丙比", "AST/ALT", "AST／ALT"],
    },
    "tp": {
        "name": "总蛋白",
        "short_name": "总蛋白（TP）",
        "reference": "65-85",
        "unit": "g/L",
        "method": "肝功能检测",
        "keywords": ["总蛋白", "TP"],
    },
    "alb": {
        "name": "白蛋白",
        "short_name": "白蛋白（ALB）",
        "reference": "40-55",
        "unit": "g/L",
        "method": "肝功能检测",
        "keywords": ["白蛋白", "ALB"],
    },
    "glo": {
        "name": "球蛋白",
        "short_name": "球蛋白（GLB）",
        "reference": "20-40",
        "unit": "g/L",
        "method": "肝功能检测",
        "keywords": ["球蛋白", "GLB", "GLO"],
    },
    "ag_ratio": {
        "name": "白/球蛋白比",
        "short_name": "白/球蛋白比（A/G）",
        "reference": "1.2-2.4",
        "unit": "",
        "method": "肝功能检测",
        "keywords": ["白/球蛋白比", "白蛋白/球蛋白比值", "白球比", "A/G", "A／G"],
    },
    "tbil": {
        "name": "总胆红素",
        "short_name": "总胆红素（TBIL）",
        "reference": "≤23.0",
        "unit": "μmol/L",
        "method": "肝功能检测",
        "keywords": ["总胆红素", "T-BIL", "TBIL"],
    },
    "dbil": {
        "name": "直接胆红素",
        "short_name": "直接胆红素（DBIL）",
        "reference": "≤6.0",
        "unit": "μmol/L",
        "method": "肝功能检测",
        "keywords": ["直接胆红素", "D-BIL", "DBIL"],
    },
    "ibil": {
        "name": "间接胆红素",
        "short_name": "间接胆红素（IBIL）",
        "reference": "≤16.16",
        "unit": "μmol/L",
        "method": "肝功能检测",
        "keywords": ["间接胆红素", "I-BIL", "IBIL"],
    },
    "alp": {
        "name": "碱性磷酸酶",
        "short_name": "ALP（碱性磷酸酶）",
        "reference": "45-125",
        "unit": "U/L",
        "method": "肝功能检测",
        "keywords": ["碱性磷酸酶", "ALP"],
    },
    "ggt": {
        "name": "γ-谷氨酰转肽酶",
        "short_name": "GGT（γ-谷氨酰转肽酶）",
        "reference": "10.00-60.00",
        "unit": "U/L",
        "method": "肝功能检测",
        "keywords": ["γ-谷氨酰转移酶", "γ-谷氨酰转肽酶", "GGT", "GGT（γ-谷氨酰转肽酶）"],
    },
    "che": {
        "name": "胆碱酯酶",
        "short_name": "胆碱酯酶（CHE）",
        "reference": "5000-12000",
        "unit": "U/L",
        "method": "肝功能检测",
        "keywords": ["胆碱酯酶", "CHE", "CIE"],
    },
    "tba": {
        "name": "总胆汁酸",
        "short_name": "总胆汁酸（TBA）",
        "reference": "≤10.0",
        "unit": "μmol/L",
        "method": "肝功能检测",
        "keywords": ["总胆汁酸", "TBA"],
    },
}
P07_FIBROSIS_DEFINITIONS: dict[str, dict[str, Any]] = {
    "pc_iii": {
        "name": "III型前胶原",
        "short_name": "III型前胶原（PC-III）",
        "reference": "≤30",
        "unit": "ng/mL",
        "method": "化学发光法",
        "keywords": ["III型前胶原", "Ⅲ型前胶原", "PC-III", "PIIINP", "PⅢNP"],
    },
    "civ": {
        "name": "IV型胶原",
        "short_name": "IV型胶原（CIV）",
        "reference": "",
        "unit": "ng/mL",
        "method": "化学发光法",
        "keywords": ["IV型胶原", "Ⅳ型胶原", "CIV", "C-IV"],
    },
    "ln": {
        "name": "层粘连蛋白",
        "short_name": "层粘连蛋白（LN）",
        "reference": "≤50",
        "unit": "ug/L",
        "method": "化学发光法",
        "keywords": ["层粘连蛋白", "层黏连蛋白", "LN"],
    },
    "ha": {
        "name": "透明质酸",
        "short_name": "透明质酸（HA）",
        "reference": "≤100",
        "unit": "ng/mL",
        "method": "化学发光法",
        "keywords": ["透明质酸", "透明质酸酶", "HA"],
    },
}
P04_NUTRIENT_DEFINITIONS: dict[str, dict[str, Any]] = {
    "iron": {
        "name": "铁（Fe）",
        "full_name": "铁（Iron）",
        "group": "microelements",
        "reference": "7.52--11.82",
        "unit": "mmol/L",
        "method": "原子吸收光谱法",
        "keywords": ["铁（Fe）", "铁(Fe)", "铁", "Fe"],
    },
    "zinc": {
        "name": "锌（Zn）",
        "full_name": "锌（Zinc）",
        "group": "microelements",
        "reference": "76.5--170",
        "unit": "umol/L",
        "method": "原子吸收光谱法",
        "keywords": ["锌（Zn）", "锌(Zn)", "锌", "Zn"],
    },
    "calcium": {
        "name": "钙（Ca）",
        "full_name": "钙（Calcium）",
        "group": "microelements",
        "reference": "1.55--2.1",
        "unit": "mmol/L",
        "method": "原子吸收光谱法",
        "keywords": ["钙（Ca）", "钙(Ca)", "钙", "Ca"],
    },
    "magnesium": {
        "name": "镁（Mg）",
        "full_name": "镁（Magnesium）",
        "group": "microelements",
        "reference": "1.12--2.16",
        "unit": "mmol/L",
        "method": "原子吸收光谱法",
        "keywords": ["镁（Mg）", "镁(Mg)", "镁", "Mg"],
    },
    "copper": {
        "name": "铜（Cu）",
        "full_name": "铜（Copper）",
        "group": "microelements",
        "reference": "11.8--39.3",
        "unit": "umol/L",
        "method": "原子吸收光谱法",
        "keywords": ["铜（Cu）", "铜(Cu)", "铜", "Cu"],
    },
    "vitamin_a": {
        "name": "维生素A",
        "full_name": "维生素A（Vitamin A）",
        "group": "vitamins",
        "reference": "0.3-0.7",
        "unit": "μg/mL",
        "method": "LC-MS/MS法",
        "keywords": ["维生素A", "Vitamin A"],
    },
    "vitamin_d2": {
        "name": "25-羟基维生素D2",
        "full_name": "25-羟基维生素D2",
        "group": "vitamins",
        "reference": "",
        "unit": "ng/mL",
        "method": "LC-MS/MS法",
        "keywords": ["25-羟基维生素D2", "25羟基维生素D2", "Vitamin D2"],
    },
    "vitamin_d3": {
        "name": "25-羟基维生素D3",
        "full_name": "25-羟基维生素D3",
        "group": "vitamins",
        "reference": "",
        "unit": "ng/mL",
        "method": "LC-MS/MS法",
        "keywords": ["25-羟基维生素D3", "25羟基维生素D3", "Vitamin D3"],
    },
    "vitamin_d": {
        "name": "25-羟基维生素D",
        "full_name": "维生素D（Vitamin D）",
        "group": "vitamins",
        "reference": "<12.00 缺乏; [12.01-20.00] 不足; [20.01-50.00] 正常; >50.00 过量",
        "unit": "ng/mL",
        "method": "LC-MS/MS法",
        "keywords": ["25-羟基维生素D", "25羟基维生素D", "Vitamin D"],
    },
    "vitamin_e": {
        "name": "维生素E",
        "full_name": "维生素E（Vitamin E）",
        "group": "vitamins",
        "reference": "5.0-20.0",
        "unit": "μg/mL",
        "method": "LC-MS/MS法",
        "keywords": ["维生素E", "Vitamin E"],
    },
    "vitamin_k1": {
        "name": "维生素K1",
        "full_name": "维生素K1（Vitamin K1）",
        "group": "vitamins",
        "reference": "0.2-2.5",
        "unit": "ng/mL",
        "method": "LC-MS/MS法",
        "keywords": ["维生素K1", "Vitamin K1"],
    },
    "vitamin_b1": {
        "name": "维生素B1",
        "full_name": "维生素B1（Vitamin B1）",
        "group": "vitamins",
        "reference": "1-16",
        "unit": "ng/mL",
        "method": "LC-MS/MS法",
        "keywords": ["维生素B1", "Vitamin B1"],
    },
    "vitamin_b2": {
        "name": "维生素B2",
        "full_name": "维生素B2（Vitamin B2）",
        "group": "vitamins",
        "reference": "1-19",
        "unit": "ng/mL",
        "method": "LC-MS/MS法",
        "keywords": ["维生素B2", "Vitamin B2"],
    },
    "vitamin_b3_niacin": {
        "name": "维生素B3(烟酸)",
        "full_name": "维生素B3（烟酸）",
        "group": "vitamins",
        "reference": "0-5.0",
        "unit": "ng/mL",
        "method": "LC-MS/MS法",
        "keywords": ["维生素B3(烟酸)", "维生素B3（烟酸）", "烟酸"],
    },
    "vitamin_b3_nicotinamide": {
        "name": "维生素B3(烟酰胺)",
        "full_name": "维生素B3（烟酰胺）",
        "group": "vitamins",
        "reference": "15.2-72.10",
        "unit": "ng/mL",
        "method": "LC-MS/MS法",
        "keywords": ["维生素B3(烟酰胺)", "维生素B3（烟酰胺）", "烟酰胺"],
    },
    "vitamin_b5": {
        "name": "维生素B5",
        "full_name": "维生素B5（Vitamin B5）",
        "group": "vitamins",
        "reference": "12.9-253.1",
        "unit": "ng/mL",
        "method": "LC-MS/MS法",
        "keywords": ["维生素B5", "Vitamin B5"],
    },
    "vitamin_b6": {
        "name": "维生素B6",
        "full_name": "维生素B6（Vitamin B6）",
        "group": "vitamins",
        "reference": "1-30",
        "unit": "ng/mL",
        "method": "LC-MS/MS法",
        "keywords": ["维生素B6", "Vitamin B6"],
    },
    "vitamin_b7": {
        "name": "维生素B7",
        "full_name": "维生素B7（Vitamin B7）",
        "group": "vitamins",
        "reference": "0.05-0.83",
        "unit": "ng/mL",
        "method": "LC-MS/MS法",
        "keywords": ["维生素B7", "Vitamin B7"],
    },
    "vitamin_b9_5_mthf": {
        "name": "维生素B9(5-甲基四氢叶酸)",
        "full_name": "维生素B9（5-甲基四氢叶酸）",
        "group": "vitamins",
        "reference": "4-35",
        "unit": "ng/mL",
        "method": "LC-MS/MS法",
        "keywords": ["维生素B9(5-甲基四氢叶酸)", "维生素B9（5-甲基四氢叶酸）", "5-甲基四氢叶酸"],
    },
    "vitamin_b12_mma": {
        "name": "维生素B12(MMA)",
        "full_name": "维生素B12（MMA）",
        "group": "vitamins",
        "reference": "≤47.24",
        "unit": "ng/mL",
        "method": "LC-MS/MS法",
        "keywords": ["维生素B12(MMA)", "维生素B12（MMA）", "MMA"],
    },
}


def build_report_data_from_ocr_result(package_code: str, ocr_result: dict[str, Any]) -> dict[str, Any]:
    if package_code == "P01":
        return _build_p01_report_data(ocr_result)
    if package_code == "P17":
        return _build_p17_report_data(ocr_result)
    if package_code == "P05":
        return _build_p05_report_data(ocr_result)
    if package_code == "P04":
        return _build_p04_report_data(ocr_result)
    if package_code == "P06":
        return _build_p06_report_data(ocr_result)
    if package_code == "P07":
        return _build_p07_report_data(ocr_result)
    if package_code == "P08":
        return _build_p08_report_data(ocr_result)
    if package_code == "P09":
        return _build_p09_report_data(ocr_result)
    if package_code == "P10":
        return _build_p10_report_data(ocr_result)
    if package_code == "P11":
        return build_p11_report_data(
            ocr_result=ocr_result,
            age_display=_age_display,
            date_display=_date_display,
            lab_result_builder=_lab_result,
        )
    if package_code == "P03":
        return _build_p03_report_data(ocr_result)
    if package_code != "P02":
        return _build_placeholder_report_data(package_code, ocr_result)
    return _build_p02_report_data(ocr_result)


def _build_p02_report_data(ocr_result: dict[str, Any]) -> dict[str, Any]:
    structured = ocr_result.get("structured_report", {})
    patient_info = structured.get("patient_info", {})
    additional_info = structured.get("additional_info", {})
    tests = structured.get("tests", [])

    calprotectin = _find_test(tests, "钙卫蛋白")
    total_ige = _find_p02_total_ige_test(tests)
    allergen_tests = [
        test
        for test in tests
        if "钙卫蛋白" not in str(test.get("test_name", "")) and not _is_p02_total_ige_name(str(test.get("test_name", "")))
    ]
    positive_allergens = [test for test in allergen_tests if _is_positive(test)]

    report_id = str(structured.get("report_id") or ocr_result.get("source_file") or "")
    sample_date = str(additional_info.get("sample_date") or "")
    sample_types = patient_info.get("specimen_types") or []
    if not isinstance(sample_types, list):
        sample_types = [str(sample_types)]

    cal_display = _test_display(calprotectin)
    total_ige_display = _test_display(total_ige)
    allergen_display = _allergen_overall_display(positive_allergens)

    return {
        "case_id": f"case_{report_id or 'p02'}",
        "package_code": "P02",
        "patient": {
            "name": patient_info.get("name") or "",
            "gender": patient_info.get("gender") or "",
            "age": _age_display(patient_info.get("age")),
            "phone": "—",
            "symptoms": first_basic.get("clinical_diagnosis") or patient_info.get("clinical_diagnosis") or "/",
            "hospital": patient_info.get("hospital") or "",
            "specimen_condition": patient_info.get("specimen_condition") or "",
        },
        "report": {
            "report_id": report_id,
            "assessment_type": "肠道功能评估健康管理报告",
            "method": _method_summary(tests),
            "assessment_date": _date_display(sample_date),
            "sample_date": sample_date,
            "receive_date": additional_info.get("receive_date") or "",
            "report_date": additional_info.get("report_date") or "",
        },
        "sample": {
            "type": "EDTA抗凝血浆/血清",
            "condition": patient_info.get("specimen_condition") or "—",
        },
        "lab_results": [_lab_result(test) for test in tests],
        "p02": {
            "calprotectin": {
                "result_display": cal_display,
                "reference_range": calprotectin.get("reference_range") or "阴性",
                "method": calprotectin.get("method") or "",
                "interpretation": _calprotectin_interpretation(calprotectin),
            },
            "total_ige": {
                "result_display": total_ige_display,
                "reference_range": total_ige.get("reference_range") or "阴性",
                "method": total_ige.get("method") or "",
                "interpretation": _total_ige_interpretation(total_ige),
            },
            "allergen": {
                "overall_result": allergen_display,
                "reference_range": "阴性",
                "positive_items": [_allergen_item_display(test) for test in positive_allergens],
                "items": [_lab_result(test) for test in allergen_tests],
                "interpretation": _allergen_interpretation(positive_allergens),
            },
            "overall_summary": _overall_summary(calprotectin, total_ige, positive_allergens),
            "followup_advice": _followup_advice(calprotectin, total_ige, positive_allergens),
            "microbiome_advice": _microbiome_advice(total_ige, positive_allergens),
            "barrier": {
                "leaky_gut_impact": _barrier_leaky_gut_impact(total_ige, positive_allergens),
                "improvement_advice": _barrier_improvement_advice(total_ige, positive_allergens),
            },
            "diet": {
                "gut_advice": _diet_gut_advice(calprotectin),
                "personalized_advice": _diet_personalized_advice(total_ige, positive_allergens),
            },
            "lifestyle": {
                "stress_management_advice": _stress_management_advice(total_ige, positive_allergens),
            },
            "nutrition": {
                "functional_medicine_advice": _functional_medicine_advice(total_ige, positive_allergens),
            },
            "immune_system_summary": _immune_system_summary(total_ige, positive_allergens),
            "inflammation_immune_advice": _inflammation_immune_advice(calprotectin, total_ige, positive_allergens),
        },
        "ai_outputs": {
            "status": "pending",
            "note": "当前为OCR确定字段和规则化占位解读；AI诊断内容后续接入DeepSeek后替换。",
        },
        "ocr_snapshot": {
            "source_file": ocr_result.get("source_file", ""),
            "strategy_version": ocr_result.get("strategy_version", ""),
            "provider": ocr_result.get("provider", ""),
            "warnings": ocr_result.get("warnings", []),
        },
        "version_lock": {
            "template_version": "P02-html-v0.1",
            "rule_version": "P02-rules-v0.1-draft",
            "prompt_version": "P02-prompts-v0.1",
            "ai_model": "deepseek-v4-flash",
            "ocr_strategy_version": ocr_result.get("strategy_version", ""),
            "ocr_provider": ocr_result.get("provider", ""),
        },
    }


def _build_p06_report_data(ocr_result: dict[str, Any]) -> dict[str, Any]:
    structured = ocr_result.get("structured_report", {})
    patient_info = structured.get("patient_info", {})
    additional_info = structured.get("additional_info", {})
    tests = structured.get("tests", [])

    report_id = str(structured.get("report_id") or ocr_result.get("source_file") or "")
    assessment_date_raw = str(additional_info.get("report_date") or additional_info.get("sample_date") or "")
    sample_types = patient_info.get("specimen_types") or []
    if not isinstance(sample_types, list):
        sample_types = [str(sample_types)]
    sample_type_display = " / ".join(str(item) for item in sample_types if str(item).strip()) or "免疫细胞与炎症因子"

    immune_cells = {
        "gzm_b_nk": _p06_immune_cell(tests, "gzm_b_nk"),
        "ifn_gamma_nk": _p06_immune_cell(tests, "ifn_gamma_nk"),
        "gzm_b_ctl": _p06_immune_cell(tests, "gzm_b_ctl"),
        "ifn_gamma_ctl": _p06_immune_cell(tests, "ifn_gamma_ctl"),
    }
    tests_map = _p06_tests_map(tests)
    cytokines = {
        "il_1b": _p06_cytokine(tests, "il_1b"),
        "il_2": _p06_cytokine(tests, "il_2"),
        "il_4": _p06_cytokine(tests, "il_4"),
        "il_5": _p06_cytokine(tests, "il_5"),
        "il_6": _p06_cytokine(tests, "il_6"),
        "il_8": _p06_cytokine(tests, "il_8"),
        "il_10": _p06_cytokine(tests, "il_10"),
        "il_12p70": _p06_cytokine(tests, "il_12p70"),
        "il_17": _p06_cytokine(tests, "il_17"),
        "ifn_alpha": _p06_cytokine(tests, "ifn_alpha"),
        "ifn_gamma": _p06_cytokine(tests, "ifn_gamma"),
        "tnf_alpha": _p06_cytokine(tests, "tnf_alpha"),
    }

    immune_count_codes = ["lym", "t_cell", "nk", "ctl", "th"]
    immune_function_codes = ["gzm_b_nk", "ifn_gamma_nk", "gzm_b_ctl", "ifn_gamma_ctl", "gzm_b_nk_percent", "ifn_gamma_nk_percent", "gzm_b_ctl_percent", "ctl_ifn_gamma_parent_percent"]
    immune_count_ok = all(tests_map.get(code, {}).get("status") == "正常" for code in immune_count_codes if tests_map.get(code))
    immune_function_ok = all(tests_map.get(code, {}).get("status") == "正常" for code in immune_function_codes if tests_map.get(code))
    immune_ok = immune_count_ok and immune_function_ok
    inflammation_focus_codes = ["il_8", "tnf_alpha", "hs_crp"]
    elevated_inflammation_markers = _p06_elevated_test_names(tests_map, inflammation_focus_codes)
    inflammatory_high = bool(elevated_inflammation_markers)
    normal_cytokine_count = sum(1 for code in ["il_1b", "il_2", "il_4", "il_5", "il_6", "il_10", "il_12p70", "il_17", "ifn_alpha", "ifn_gamma"] if tests_map.get(code, {}).get("status") == "正常")
    has_hs_crp = "hs_crp" in tests_map
    result_category_text = "免疫细胞与功能相关 17 项、细胞因子相关 12 项"
    if has_hs_crp:
        result_category_text += "、炎症指标 1 项"

    return {
        "case_id": f"case_{report_id or 'p06'}",
        "package_code": "P06",
        "patient": {
            "name": patient_info.get("name") or "",
            "gender": patient_info.get("gender") or "",
            "age": _age_display(patient_info.get("age")),
            "phone": patient_info.get("phone") or "—",
            "symptoms": patient_info.get("clinical_diagnosis") or "—",
            "hospital": patient_info.get("hospital") or patient_info.get("submitting_unit") or "",
            "submitting_unit": patient_info.get("submitting_unit") or patient_info.get("hospital") or "",
        },
        "report": {
            "report_id": report_id,
            "assessment_type": P06_REPORT_NAME,
            "method": P06_METHOD,
            "assessment_date": _date_display(assessment_date_raw),
            "assessment_date_raw": assessment_date_raw,
            "sample_date": additional_info.get("sample_date") or "",
            "receive_date": additional_info.get("receive_date") or "",
            "report_date": additional_info.get("report_date") or "",
        },
        "sample": {
            "type": sample_type_display,
            "condition": patient_info.get("specimen_condition") or "—",
        },
        "lab_results": [_lab_result(test) for test in tests],
        "organization": {
            "phone": "400-158-1959",
            "email": "service@anweikang.com",
            "website": "www.anweikang.com",
            "address": "安徽省合肥市庐阳区临泉路7266号研发中心楼1、4、5、6层",
        },
        "p06": {
            "overall_summary": _p06_overall_summary(immune_ok, inflammatory_high),
            "core_judgements": {
                "immune_cell_count": {
                    "title": "免疫细胞（NK/CTL）",
                    "result": "LYM、T、NK、CTL、Th数量均在参考范围" if immune_count_ok else "部分免疫细胞数量需人工复核",
                },
                "cytotoxic_activity": {
                    "title": "细胞杀伤活性功能",
                    "result": "Gzm B与IFN-γ相关功能指标整体正常" if immune_function_ok else "部分细胞毒活性指标需人工复核",
                },
                "inflammatory_factors": {
                    "title": "促炎因子/炎症指标（IL-8、TNF-α、hs-CRP）",
                    "result": f"{'、'.join(elevated_inflammation_markers)}升高" if inflammatory_high else "未见明显异常",
                },
            },
            "management_priorities": {
                "priority_1": "炎症因子水平下调",
                "priority_2": "维持免疫细胞活性平衡",
                "priority_3": "抗氧化支持",
            },
            "page_02_ai_insights": {
                "paragraph_1": "免疫细胞数量及细胞杀伤活性处于参考范围，提示基础免疫防御与调节能力较稳定。",
                "paragraph_2": f"{'、'.join(elevated_inflammation_markers)}升高提示促炎信号活跃，需结合症状、压力、睡眠、体重和既往史判断慢性炎症来源。" if inflammatory_high else "IL-8、TNF-α与hs-CRP未见明显升高，当前促炎信号整体相对稳定。",
                "paragraph_3": "建议优先进行抗炎、抗氧化与生活方式管理，并按阶段复评。",
            },
            "ai_insights": {
                "paragraph_1": f"本次检测共识别 {len(tests)} 项检验明细，其中{result_category_text}；当前免疫细胞数量与细胞毒活性指标整体处于参考范围。",
                "paragraph_2": f"细胞因子及炎症指标结果中{('、'.join(elevated_inflammation_markers) + '升高' if elevated_inflammation_markers else '未见促炎信号明显升高')}，其余 {normal_cytokine_count} 项细胞因子处于参考范围，提示当前主要关注点集中在慢性炎症信号。",
                "paragraph_3": "建议优先围绕抗炎、抗氧化、睡眠与运动管理开展干预，并结合体重、饮食、压力和既往病史进行阶段性复评。",
            },
            "tests": tests_map,
            "immune_cells": immune_cells,
            "cytokines": cytokines,
            "deep_dive": {
                "immune": {
                    "subtitle": "基于 Gzm B 和 IFN-γ 数据，解读抗病毒、抗肿瘤及免疫平衡能力",
                    "paragraph_1": _p06_immune_detail_summary(tests_map),
                    "paragraph_2": "Gzm B 反映直接杀伤能力，IFN-γ 反映免疫调节和抗病毒应答能力，需与感染史、肿瘤风险和慢性炎症状态综合判断。",
                    "warning": "提示：免疫细胞结果需结合年龄、感染史、肿瘤史及其他免疫指标综合判断。",
                },
                "cytokine": {
                    "subtitle": "重点关注 IL-8 与 TNF-α 等促炎因子的变化及其慢性炎症含义",
                    "paragraph_1": _p06_cytokine_detail_summary(tests_map),
                    "paragraph_2": "持续升高可能与压力负荷、代谢紊乱、睡眠不足和生活方式因素相关，也提示后续需要结合症状和既往史判断炎症来源。",
                    "paragraph_3": "在健康管理中应结合饮食、体重、运动、睡眠和既往实验室结果进行动态复评。",
                    "warning": "提示：促炎因子升高需结合临床症状、其他实验室指标及影像学检查综合评估。",
                },
            },
            "followup_advice": "建议按 12 周计划执行饮食、作息、运动与阶段复评，并记录症状和生活方式变化。",
            "disclaimer": "本报告仅供健康管理参考，不作为临床诊断依据。",
            "review_note": "健康管理专家可结合临床资料、症状和医学指标进行综合判断。",
        },
        "ai_outputs": {
            "status": "pending",
            "note": "当前已生成 P06 结构化结果和规则化初始文案，后续可由 AI 生成辅助解读并进入人工审查。",
        },
        "ocr_snapshot": {
            "source_file": ocr_result.get("source_file", ""),
            "strategy_version": ocr_result.get("strategy_version", ""),
            "provider": ocr_result.get("provider", ""),
            "warnings": ocr_result.get("warnings", []),
        },
        "version_lock": {
            "template_version": "P06-html-v0.1",
            "rule_version": "P06-rules-v0.1-draft",
            "prompt_version": "P06-prompts-v0.1",
            "ai_model": "deepseek-v4-flash",
            "ocr_strategy_version": ocr_result.get("strategy_version", ""),
            "ocr_provider": ocr_result.get("provider", ""),
        },
    }


def _build_p07_report_data(ocr_result: dict[str, Any]) -> dict[str, Any]:
    structured = ocr_result.get("structured_report", {})
    patient_info = structured.get("patient_info", {}) if isinstance(structured.get("patient_info"), dict) else {}
    additional_info = structured.get("additional_info", {}) if isinstance(structured.get("additional_info"), dict) else {}
    tests = structured.get("tests", []) if isinstance(structured.get("tests"), list) else []

    report_id = str(structured.get("report_id") or ocr_result.get("source_file") or "")
    assessment_date_raw = str(additional_info.get("report_date") or additional_info.get("sample_date") or "")
    sample_types = patient_info.get("specimen_types") or []
    if not isinstance(sample_types, list):
        sample_types = [str(sample_types)]
    sample_type_display = "、".join(str(item) for item in sample_types if str(item).strip()) or "血清及基因检测"
    submitting_unit = str(patient_info.get("submitting_unit") or patient_info.get("hospital") or "").strip()

    liver_function = {
        code: _p07_indicator(tests, code, definition, group="liver_function")
        for code, definition in P07_LIVER_FUNCTION_DEFINITIONS.items()
    }
    fibrosis = {
        code: _p07_indicator(tests, code, definition, group="fibrosis")
        for code, definition in P07_FIBROSIS_DEFINITIONS.items()
    }

    liver_summary = _p07_group_summary(liver_function, group_name="肝功能指标")
    fibrosis_summary = _p07_group_summary(fibrosis, group_name="肝纤维化指标")
    gene = {"aldh2": _p07_aldh2_gene(tests, patient_name=str(patient_info.get("name") or ""))}
    priorities = _p07_priorities(liver_function, fibrosis, gene["aldh2"])

    return {
        "case_id": f"case_{report_id or 'p07'}",
        "package_code": "P07",
        "patient": {
            "name": patient_info.get("name") or "",
            "gender": patient_info.get("gender") or "",
            "age": _age_display(patient_info.get("age")),
            "phone": patient_info.get("phone") or "—",
            "symptoms": _p07_clinical_diagnosis_display(patient_info.get("clinical_diagnosis")),
            "submitting_unit": submitting_unit,
            "hospital": submitting_unit,
            "specimen_condition": patient_info.get("specimen_condition") or "",
        },
        "report": {
            "report_id": report_id,
            "assessment_type": "肝脏解毒功能评估",
            "method": P07_METHOD,
            "assessment_date": _date_display(assessment_date_raw),
            "sample_date": additional_info.get("sample_date") or "",
            "receive_date": additional_info.get("receive_date") or "",
            "report_date": additional_info.get("report_date") or "",
        },
        "sample": {
            "type": sample_type_display,
            "condition": patient_info.get("specimen_condition") or "—",
        },
        "lab_results": [_lab_result(test) for test in tests],
        "organization": {
            "phone": "400-158-1959",
            "email": "service@anweikang.com",
            "website": "www.anweikang.com",
            "address": P07_ORGANIZATION_ADDRESS,
        },
        "p07": {
            "liver_function": {
                **liver_function,
                **liver_summary,
            },
            "fibrosis": {
                **fibrosis,
                **fibrosis_summary,
            },
            "gene": gene,
            "priorities": priorities,
            "overall_summary": _p07_overall_summary(liver_summary, fibrosis_summary, gene["aldh2"]),
            "risk_assessment": _p07_risk_assessment(liver_function, fibrosis, gene["aldh2"]),
            "management_summary": "建议保持规律作息、均衡饮食、适度运动，避免长期熬夜、过量饮酒和自行滥用药物，并定期复查肝脏相关指标。",
            "diet_advice": "饮食以足量优质蛋白、全谷物、蔬菜水果和健康脂肪为基础，减少高脂、高糖和长期夜宵摄入。",
            "lifestyle_advice": "建议保持健康的生活方式，避免熬夜、过度饮酒及滥用药物，定期体检，持续关注肝脏健康。",
            "alcohol_advice": gene["aldh2"]["alcohol_advice"],
            "followup_advice": "建议按12周计划执行饮食、作息、运动与阶段复评，并记录症状、饮酒情况、用药史和生活方式变化。",
            "disclaimer": "本报告仅供健康管理参考，不作为临床诊断依据。如有不适，请及时就医。",
            "review_note": "温馨提示：本报告基于本次检测结果进行解读，健康状况受多种因素影响，请结合自身情况、既往史和专业人员意见进行综合判断。",
            "page_note": "温馨提示：本报告基于本次检测结果进行解读，健康状况受多种因素影响，请结合自身情况，定期体检，保持健康生活方式。",
        },
        "ai_outputs": {
            "status": "pending",
            "note": "当前已基于P07 OCR结构化结果生成报告预览；AI解读完成后将覆盖对应健康管理洞察字段。",
        },
        "ocr_snapshot": {
            "source_file": ocr_result.get("source_file", ""),
            "strategy_version": ocr_result.get("strategy_version", ""),
            "provider": ocr_result.get("provider", ""),
            "warnings": ocr_result.get("warnings", []),
        },
        "version_lock": {
            "template_version": P07_TEMPLATE_VERSION,
            "rule_version": P07_RULE_VERSION,
            "prompt_version": P07_PROMPT_VERSION,
            "ai_model": "deepseek-v4-flash",
            "ocr_strategy_version": ocr_result.get("strategy_version", ""),
            "ocr_provider": ocr_result.get("provider", ""),
        },
    }


def _p07_clinical_diagnosis_display(value: Any) -> str:
    text = str(value or "").strip()
    compact = "".join(text.split()).lower()
    if not compact or compact in {"-", "—", "/"}:
        return "-"
    if "anweikang" in compact or "安为康" in text or "安為康" in text:
        return "-"
    return text


def _p07_indicator(
    tests: list[dict[str, Any]],
    code: str,
    definition: dict[str, Any],
    *,
    group: str,
) -> dict[str, Any]:
    test = _find_test_by_code(tests, code) or _find_test_any(tests, list(definition["keywords"]))
    result = str(test.get("result") or "").strip() if test else ""
    indicator = str(test.get("indicator") or "").strip() if test else ""
    unit = str(test.get("unit") or definition["unit"]).strip() if test else str(definition["unit"])
    reference = str(test.get("reference_range") or definition["reference"]).strip() if test else str(definition["reference"])
    method = str(test.get("method") or definition["method"]).strip() if test else str(definition["method"])
    status = _p07_indicator_status(test, reference)
    result_text = _p07_result_with_indicator(result, indicator, missing_text="—" if test else "未识别")
    return {
        "code": code,
        "name": definition["name"],
        "short_name": definition["short_name"],
        "group": group,
        "result": result_text,
        "raw_value": _safe_float(result),
        "indicator": indicator,
        "unit": unit or "—",
        "result_display": _p07_value_with_unit(result_text, unit),
        "reference_range": reference or "—",
        "reference_display": _p07_value_with_unit(reference, unit),
        "method": method,
        "status": status,
        "interpretation": _p07_indicator_interpretation(str(definition["short_name"]), result_text, unit, status, group),
    }


def _p07_indicator_status(test: dict[str, Any], reference_range: str) -> str:
    if not test:
        return "未识别"
    signal = f"{test.get('result', '')}{test.get('indicator', '')}"
    if not str(test.get("result") or "").strip() and not str(test.get("indicator") or "").strip():
        return "待复核"
    if any(word in signal for word in ("↑", "偏高", "升高", "增高", "过高")):
        return "偏高"
    if any(word in signal for word in ("↓", "偏低", "降低", "减少")):
        return "偏低"
    if "异常" in signal:
        return "异常"
    if "正常" in signal:
        return "正常"

    value = _safe_float(test.get("result") or test.get("result_display"))
    if value is None:
        return "需复核"
    bounds = _p05_parse_reference_bounds(reference_range)
    for lower, upper in bounds:
        if lower is not None and value < lower:
            return "偏低"
        if upper is not None and value > upper:
            return "偏高"
        if lower is not None and upper is not None and lower <= value <= upper:
            return "正常"
        if lower is None and upper is not None and value <= upper:
            return "正常"
        if upper is None and lower is not None and value >= lower:
            return "正常"
    return "正常" if bounds else "需复核"


def _p07_result_with_indicator(result: str, indicator: str, *, missing_text: str = "未识别") -> str:
    text = str(result or "").strip()
    flag = str(indicator or "").strip()
    if not text:
        return missing_text
    if flag in {"↑", "↓"} and flag not in text:
        return f"{text} {flag}"
    return text


def _p07_value_with_unit(value: str, unit: str) -> str:
    text = str(value or "").strip()
    unit_text = str(unit or "").strip()
    if not text:
        return "未识别"
    if text in {"未识别", "—"} or unit_text in {"", "—"}:
        return text
    return text if unit_text in text else f"{text} {unit_text}"


def _p07_indicator_interpretation(short_name: str, result: str, unit: str, status: str, group: str) -> str:
    result_display = _p07_value_with_unit(result, unit)
    if status == "未识别":
        return f"未识别到{short_name}的有效检验结果，建议人工核对原始报告或补录该项目。"
    if _p07_status_is_normal(status):
        if group == "fibrosis":
            return f"{short_name}结果为{result_display}，处于参考范围内，当前未见该项提示的明显纤维化风险信号。"
        return f"{short_name}结果为{result_display}，处于参考范围内，提示当前相关肝功能状态相对平稳。"
    if _p07_status_is_high(status):
        if group == "fibrosis":
            return f"{short_name}结果为{result_display}，提示纤维化相关指标偏高或异常，建议结合肝功能、影像学和既往史人工复核。"
        return f"{short_name}结果为{result_display}，提示肝功能相关指标偏高或异常，建议结合饮酒史、用药史、感染和脂肪肝风险进行复核。"
    if _p07_status_is_low(status):
        return f"{short_name}结果为{result_display}，提示存在偏低趋势，建议结合营养状态、肝脏合成功能和原始参考范围人工复核。"
    return f"{short_name}结果为{result_display}，当前状态为{status}，建议人工核对原始报告和参考范围。"


def _p07_group_summary(indicators: dict[str, dict[str, Any]], *, group_name: str) -> dict[str, str]:
    recognized = [item for item in indicators.values() if item.get("status") != "未识别"]
    review_items = [item for item in recognized if str(item.get("status") or "") in {"待复核", "需复核"}]
    abnormal = [
        item
        for item in recognized
        if item not in review_items and not _p07_status_is_normal(str(item.get("status") or ""))
    ]
    if not recognized:
        return {
            "overall_status": "待补充",
            "detail_status": "等待人工补录",
            "summary": f"当前未识别到{group_name}有效结果，请先核对OCR文本层或人工补录后再进行综合评估。",
        }
    if abnormal:
        focus = "、".join(f"{item['short_name']}{item['status']}" for item in abnormal[:4])
        return {
            "overall_status": "需关注",
            "detail_status": f"{focus}需复核",
            "summary": f"{group_name}中{focus}，建议结合原始报告参考范围、饮酒史、用药史和相关症状进行人工复核。",
        }
    if review_items:
        focus = "、".join(f"{item['short_name']}{item['status']}" for item in review_items[:4])
        return {
            "overall_status": "待复核",
            "detail_status": f"{focus}",
            "summary": f"{group_name}中{focus}；其余已识别项目未见明显异常，请以原始报告和人工复核结果为准。",
        }
    if group_name == "肝纤维化指标":
        return {
            "overall_status": "指标正常",
            "detail_status": "无明显纤维化迹象",
            "summary": "已识别肝纤维化相关指标均在参考范围内，当前未见明显纤维化生化学风险信号，建议结合影像学和既往史持续观察。",
        }
    return {
        "overall_status": "指标正常",
        "detail_status": "状态良好，代谢正常",
        "summary": "已识别肝功能指标均在参考范围内，提示肝细胞酶学、胆红素代谢和蛋白合成功能整体相对平稳。",
    }


def _p07_aldh2_gene(tests: list[dict[str, Any]], *, patient_name: str) -> dict[str, Any]:
    test = _find_test_by_code(tests, "aldh2") or _find_test_any(tests, ["ALDH2", "rs671", "乙醛脱氢酶2", "醛脱氢酶2"])
    genotype = _p07_normalize_genotype(test.get("result") if test else "")
    patient_label = patient_name or "受检者"
    if not genotype:
        return {
            "gene_name": "ALDH2（醛脱氢酶2）",
            "locus": str(test.get("locus") or "c.1510G > A（rs671）") if test else "c.1510G > A（rs671）",
            "result": "",
            "result_display": "未识别",
            "status": "待复核",
            "status_display": "未识别（待复核）",
            "status_brief": "待复核",
            "detail_status": "基因型待复核",
            "card_summary": "当前未识别到ALDH2基因型结果，请人工核对原始报告或补录检测结果。",
            "personalized_title": f"针对{patient_label} ALDH2基因型的专业解读",
            "interpretation": "ALDH2基因型暂未识别，无法评估先天乙醛代谢能力，请以原始基因检测报告为准。",
            "caution": "在基因型确认前，不建议根据占位内容推断饮酒耐受性；如有饮酒不适、肝功能异常或既往肝病史，请咨询专业人员。",
            "short_interpretation": "ALDH2基因型待人工复核。",
            "summary": "ALDH2参与乙醛代谢，不同基因型会影响饮酒后乙醛清除效率和不适风险。",
            "comprehensive_interpretation": "请先补充ALDH2基因型结果，再结合肝功能和生活方式信息进行综合判断。",
            "advice_1": "在基因型未确认前，建议控制或避免饮酒，并记录饮酒后不适反应。",
            "advice_2": "建议结合肝功能、肝纤维化指标和必要的影像学检查进行阶段复评。",
            "advice_3": "保持均衡饮食、规律作息和适度运动，多维度保护肝脏健康。",
            "alcohol_advice": "ALDH2基因型暂未识别，酒精摄入建议先按保守原则管理，避免过量饮酒。",
        }

    profile = _p07_aldh2_profile(genotype)
    locus = str(test.get("locus") or "c.1510G > A（rs671）")
    return {
        "gene_name": "ALDH2（醛脱氢酶2）",
        "locus": locus,
        "result": genotype,
        "result_display": genotype,
        "status": profile["status"],
        "status_display": f"{genotype}（{profile['status']}）",
        "status_brief": profile["status"],
        "detail_status": profile["detail_status"],
        "card_summary": f"ALDH2 基因 {locus} 位点 {genotype} 基因型，{profile['card_summary']}。",
        "personalized_title": f"针对{patient_label} {genotype} 基因型的专业解读",
        "interpretation": f"{patient_label}检测结果为 ALDH2 基因 {locus} 位点 {genotype} 基因型，{profile['interpretation']}",
        "caution": profile["caution"],
        "short_interpretation": profile["short_interpretation"],
        "summary": profile["summary"],
        "comprehensive_interpretation": profile["comprehensive_interpretation"],
        "advice_1": profile["advice_1"],
        "advice_2": "建议每年进行肝功能检查，必要时结合肝脏超声或其他检查，早期发现潜在风险。",
        "advice_3": "保持均衡饮食、规律作息、适度运动，多维度保护肝脏健康。",
        "alcohol_advice": profile["alcohol_advice"],
    }


def _p07_normalize_genotype(value: Any) -> str:
    text = "".join(str(value or "").upper().split())
    match = re.search(r"\b(GG|GA|AG|AA)\b", text)
    if not match:
        return ""
    genotype = match.group(1)
    return "GA" if genotype == "AG" else genotype


def _p07_aldh2_profile(genotype: str) -> dict[str, str]:
    if genotype == "GG":
        return {
            "status": "正常",
            "detail_status": "GG基因型的优势",
            "card_summary": "编码的 ALDH2 酶活性正常",
            "interpretation": "属于正常型，提示ALDH2酶活性正常，乙醛代谢能力较强，饮酒后不适反应风险相对较低。",
            "caution": "良好的基因型并不等于可以无节制饮酒。长期或过量饮酒仍可能增加脂肪肝、肝炎、肝纤维化等肝脏健康风险。",
            "short_interpretation": "您携带的是ALDH2基因GG型，属于酶活性正常的基因型。",
            "summary": "ALDH2负责将乙醛快速分解为乙酸。GG基因型酶活性较好，乙醛代谢效率较高，饮酒后不适风险相对较低。",
            "comprehensive_interpretation": "您的ALDH2基因型提示先天乙醛代谢能力较强，但仍建议保持适量或低风险饮酒习惯，并结合肝功能结果持续管理。",
            "advice_1": "建议继续控制酒精摄入，避免长期或一次性过量饮酒。",
            "alcohol_advice": "ALDH2 GG型提示乙醛代谢能力较好，但仍应避免长期过量饮酒。",
        }
    if genotype == "GA":
        return {
            "status": "需关注",
            "detail_status": "GA基因型需限制饮酒",
            "card_summary": "编码的 ALDH2 酶活性下降",
            "interpretation": "属于杂合型，提示ALDH2酶活性下降，乙醛清除效率降低，饮酒后脸红、心悸或不适风险增加。",
            "caution": "GA基因型人群即使饮酒量不大，也可能出现乙醛蓄积相关不适。建议结合肝功能结果和个人反应严格控制酒精摄入。",
            "short_interpretation": "您携带的是ALDH2基因GA型，提示乙醛代谢能力下降。",
            "summary": "ALDH2 GA型会降低乙醛代谢效率，可能增加饮酒后不适和肝脏代谢负担。",
            "comprehensive_interpretation": "您的ALDH2基因型提示酒精代谢能力下降，应优先采用低酒精或避免饮酒策略，并定期复查肝脏相关指标。",
            "advice_1": "建议严格限制饮酒，出现脸红、心悸、恶心等不适时应避免继续饮酒。",
            "alcohol_advice": "ALDH2 GA型提示乙醛代谢能力下降，建议严格限制酒精摄入。",
        }
    return {
        "status": "高风险",
        "detail_status": "AA基因型建议避免饮酒",
        "card_summary": "编码的 ALDH2 酶活性显著受限",
        "interpretation": "属于突变型，提示ALDH2酶活性显著降低，乙醛代谢能力弱，饮酒后不适和肝脏代谢负担风险较高。",
        "caution": "AA基因型通常不建议饮酒。如存在肝功能异常、肝病史或明显饮酒不适，应及时咨询专业医生或健康管理人员。",
        "short_interpretation": "您携带的是ALDH2基因AA型，提示乙醛代谢能力显著受限。",
        "summary": "ALDH2 AA型会显著降低乙醛清除能力，饮酒后乙醛蓄积和不适风险较高。",
        "comprehensive_interpretation": "您的ALDH2基因型提示酒精代谢能力明显受限，健康管理上应以避免饮酒、保护肝脏和定期复评为重点。",
        "advice_1": "建议避免饮酒，并重点记录既往饮酒后不适反应及肝脏相关检查变化。",
        "alcohol_advice": "ALDH2 AA型提示乙醛代谢能力显著受限，建议避免饮酒。",
    }


def _p07_priorities(
    liver_function: dict[str, dict[str, Any]],
    fibrosis: dict[str, dict[str, Any]],
    aldh2: dict[str, Any],
) -> dict[str, dict[str, str]]:
    abnormal = [
        item
        for item in [*liver_function.values(), *fibrosis.values()]
        if item.get("status") not in {"未识别", "待补充"} and not _p07_status_is_normal(str(item.get("status") or ""))
    ]
    titles: list[str] = []
    if abnormal:
        titles.append(f"复核{_p07_indicator_names(abnormal, limit=2)}")
    else:
        titles.append("维持良好肝功能")
    if str(aldh2.get("result_display") or "") in {"GA", "AA"}:
        titles.append("严格限制酒精摄入")
    else:
        titles.append("保持健康生活方式")
    titles.append("关注酒精摄入与饮食平衡")
    return {f"priority_{index}": {"title": title} for index, title in enumerate(titles[:3], start=1)}


def _p07_overall_summary(liver_summary: dict[str, str], fibrosis_summary: dict[str, str], aldh2: dict[str, Any]) -> str:
    liver_status = liver_summary.get("overall_status", "待补充")
    fibrosis_status = fibrosis_summary.get("overall_status", "待补充")
    gene_status = str(aldh2.get("status_display") or "ALDH2待复核")
    if liver_status == "待补充" and fibrosis_status == "待补充" and "未识别" in gene_status:
        return "当前尚未识别到P07关键检测结果，请先核对OCR文本层或人工补录后再进行肝脏解毒功能综合评估。"
    if "需关注" in {liver_status, fibrosis_status} or any(word in gene_status for word in ("需关注", "高风险")):
        return f"基于已识别检测数据，肝功能状态为{liver_status}，肝纤维化状态为{fibrosis_status}，ALDH2基因型为{gene_status}。建议优先复核异常项目，并结合饮酒史、用药史、既往肝病史和生活方式制定健康管理方案。"
    return f"基于已识别检测数据，肝功能及肝纤维化指标整体为{liver_status}，ALDH2基因型为{gene_status}。建议继续保持规律作息、均衡饮食与适度运动，避免长期过量饮酒和高脂高糖饮食，以持续维护肝脏健康。"


def _p07_risk_assessment(
    liver_function: dict[str, dict[str, Any]],
    fibrosis: dict[str, dict[str, Any]],
    aldh2: dict[str, Any],
) -> str:
    abnormal = [
        item
        for item in [*liver_function.values(), *fibrosis.values()]
        if item.get("status") not in {"未识别", "待补充"} and not _p07_status_is_normal(str(item.get("status") or ""))
    ]
    parts: list[str] = []
    if abnormal:
        parts.append(f"检测结果中{_p07_indicator_names(abnormal, limit=5)}需要关注")
    if str(aldh2.get("result_display") or "") in {"GA", "AA"}:
        parts.append(f"ALDH2 {aldh2.get('result_display')}提示酒精代谢能力下降")
    if parts:
        return "；".join(parts) + "。建议结合原始报告和专业人员意见进行人工复核。"
    return "当前已识别指标未见明显肝脏解毒功能风险信号，建议维持健康生活方式并定期复评。"


def _p07_indicator_names(items: list[dict[str, Any]], *, limit: int = 3) -> str:
    names = [str(item.get("short_name") or item.get("name") or "") for item in items if str(item.get("short_name") or item.get("name") or "").strip()]
    shown = names[:limit]
    suffix = "等" if len(names) > limit else ""
    return "、".join(shown) + suffix if shown else "相关指标"


def _p07_status_is_normal(status: str) -> bool:
    return str(status or "") in {"正常", "良好", "平稳", "指标正常"}


def _p07_status_is_high(status: str) -> bool:
    return any(word in str(status or "") for word in ("偏高", "升高", "增高", "过高", "异常", "高风险", "↑"))


def _p07_status_is_low(status: str) -> bool:
    return any(word in str(status or "") for word in ("偏低", "降低", "减少", "↓"))


def _build_p08_report_data(ocr_result: dict[str, Any]) -> dict[str, Any]:
    structured = ocr_result.get("structured_report", {})
    patient_info = structured.get("patient_info", {}) if isinstance(structured.get("patient_info"), dict) else {}
    additional_info = structured.get("additional_info", {}) if isinstance(structured.get("additional_info"), dict) else {}
    tests = structured.get("tests", []) if isinstance(structured.get("tests"), list) else []

    report_id = str(structured.get("report_id") or ocr_result.get("source_file") or "")
    assessment_date_raw = str(additional_info.get("report_date") or additional_info.get("sample_date") or "")
    sample_types = patient_info.get("specimen_types") or []
    if not isinstance(sample_types, list):
        sample_types = [str(sample_types)]
    sample_type_display = "血清、血浆、全血"
    submitting_unit = str(patient_info.get("submitting_unit") or patient_info.get("hospital") or "").strip()

    cardiovascular = {
        code: _p08_indicator(tests, code, definition, group="cardiovascular")
        for code, definition in P08_CARDIOVASCULAR_DEFINITIONS.items()
    }
    raas = {
        code: _p08_indicator(tests, code, definition, group="raas")
        for code, definition in P08_RAAS_DEFINITIONS.items()
    }
    _p08_apply_calculated_ratio(raas)

    cardiovascular_summary = _p08_group_summary(cardiovascular, group_name="心血管功能与凝血脂代谢指标")
    raas_summary = _p08_group_summary(raas, group_name="RAAS系统指标")
    priorities = _p08_priorities(cardiovascular, raas, cardiovascular_summary, raas_summary)
    interpretations = _p08_interpretations(cardiovascular, raas, cardiovascular_summary, raas_summary)
    deep_dive = _p08_deep_dive(cardiovascular, raas, cardiovascular_summary, raas_summary)

    return {
        "case_id": f"case_{report_id or 'p08'}",
        "package_code": "P08",
        "patient": {
            "name": patient_info.get("name") or "",
            "gender": patient_info.get("gender") or "",
            "age": _age_display(patient_info.get("age")),
            "phone": patient_info.get("phone") or "—",
            "symptoms": _p08_clinical_diagnosis_display(patient_info.get("clinical_diagnosis")),
            "hospital": submitting_unit,
            "submitting_unit": submitting_unit,
            "specimen_condition": patient_info.get("specimen_condition") or "",
        },
        "report": {
            "report_id": report_id,
            "assessment_type": P08_ASSESSMENT_TYPE,
            "method": P08_METHOD,
            "assessment_date": _date_display(assessment_date_raw),
            "sample_date": additional_info.get("sample_date") or "",
            "receive_date": additional_info.get("receive_date") or "",
            "report_date": additional_info.get("report_date") or "",
        },
        "sample": {
            "type": sample_type_display,
            "condition": patient_info.get("specimen_condition") or "—",
        },
        "lab_results": [_lab_result(test) for test in tests],
        "organization": {
            "phone": "400-158-1959",
            "email": "service@anweikang.com",
            "website": "www.anweikang.com",
            "address": P08_ORGANIZATION_ADDRESS,
        },
        "p08": {
            "cardiovascular": {
                **cardiovascular,
                **cardiovascular_summary,
            },
            "raas": {
                **raas,
                **raas_summary,
            },
            "core_judgements": _p08_core_judgements(cardiovascular, raas, cardiovascular_summary, raas_summary),
            "priorities": priorities,
            "overall_summary": _p08_overall_summary(cardiovascular_summary, raas_summary, cardiovascular, raas),
            "risk_assessment": _p08_risk_assessment(cardiovascular, raas),
            "interpretations": interpretations,
            "deep_dive": deep_dive,
            "followup_advice": "建议按12周计划执行饮食、作息、运动与阶段复评，并记录血压、心率、体重、症状和生活方式变化。",
            "disclaimer": "本报告仅供健康管理参考，不作为临床诊断依据。",
            "review_note": "健康管理专家可结合临床资料、症状、既往史、用药和医学指标进行综合判断。",
            "page_note": "注：本报告仅供健康管理参考，不作为临床诊断依据。如有不适，请及时就医。",
        },
        "ai_outputs": {
            "status": "pending",
            "note": "当前已基于P08 OCR结构化结果生成报告预览；AI解读完成后将覆盖对应健康管理洞察字段。",
        },
        "ocr_snapshot": {
            "source_file": ocr_result.get("source_file", ""),
            "strategy_version": ocr_result.get("strategy_version", ""),
            "provider": ocr_result.get("provider", ""),
            "warnings": ocr_result.get("warnings", []),
        },
        "version_lock": {
            "template_version": P08_TEMPLATE_VERSION,
            "rule_version": P08_RULE_VERSION,
            "prompt_version": P08_PROMPT_VERSION,
            "ai_model": "deepseek-v4-flash",
            "ocr_strategy_version": ocr_result.get("strategy_version", ""),
            "ocr_provider": ocr_result.get("provider", ""),
        },
    }


def _p08_clinical_diagnosis_display(value: Any) -> str:
    text = str(value or "").strip()
    compact = "".join(text.split()).lower()
    if not compact or compact in {"-", "—", "/"}:
        return "—"
    if "anweikang" in compact or "安为康" in text or "安為康" in text:
        return "—"
    return text


def _p08_indicator(
    tests: list[dict[str, Any]],
    code: str,
    definition: dict[str, Any],
    *,
    group: str,
) -> dict[str, Any]:
    test = _find_test_by_code(tests, code) or _find_test_any(tests, list(definition["keywords"]))
    result = str(test.get("result") or "").strip() if test else ""
    indicator = str(test.get("indicator") or "").strip() if test else ""
    unit = str(test.get("unit") or definition["unit"]).strip() if test else str(definition["unit"])
    reference = str(test.get("reference_range") or definition["reference"]).strip() if test else str(definition["reference"])
    method = str(test.get("method") or definition["method"]).strip() if test else str(definition["method"])
    status = _p08_indicator_status(test, reference, code=code)
    result_text = _p08_result_with_indicator(result, indicator, missing_text="—" if test else "未识别")
    return {
        "code": code,
        "name": definition["name"],
        "short_name": definition["short_name"],
        "group": group,
        "result": result_text,
        "raw_value": _safe_float(result),
        "indicator": indicator,
        "unit": unit or "—",
        "result_display": _p08_value_with_unit(result_text, unit),
        "reference_range": reference or "—",
        "reference_display": _p08_value_with_unit(reference, unit),
        "method": method,
        "status": status,
        "interpretation": _p08_indicator_interpretation(str(definition["short_name"]), result_text, unit, status),
    }


def _p08_apply_calculated_ratio(raas: dict[str, dict[str, Any]]) -> None:
    ratio = raas.get("angiotensin_ratio", {})
    if ratio.get("status") != "未识别":
        return
    ang_i = _p08_indicator_value_as_pg_ml(raas.get("angiotensin_i", {}))
    ang_ii = _p08_indicator_value_as_pg_ml(raas.get("angiotensin_ii", {}))
    if not ang_i or ang_ii is None:
        return
    value = round(ang_ii / ang_i, 2)
    result = f"{value:.2f}".rstrip("0").rstrip(".")
    ratio.update(
        {
            "result": result,
            "raw_value": value,
            "result_display": result,
            "method": "计算法",
            "status": _p08_status_from_value(value, str(ratio.get("reference_range") or "")),
            "interpretation": _p08_indicator_interpretation("Ang II/Ang I", result, "", _p08_status_from_value(value, str(ratio.get("reference_range") or ""))),
        }
    )


def _p08_indicator_value_as_pg_ml(indicator: dict[str, Any]) -> float | None:
    value = _safe_float(indicator.get("result"))
    if value is None:
        return None
    unit = str(indicator.get("unit") or "").strip().lower().replace("μ", "u").replace("µ", "u")
    if unit == "ng/ml":
        return value * 1000
    return value


def _p08_indicator_status(test: dict[str, Any], reference_range: str, *, code: str) -> str:
    if not test:
        return "未识别"
    signal = f"{test.get('result', '')}{test.get('indicator', '')}{test.get('status', '')}"
    if not str(test.get("result") or "").strip() and not str(test.get("indicator") or "").strip():
        return "待复核"
    if any(word in signal for word in ("↑", "偏高", "升高", "增高", "过高")):
        value = _safe_float(test.get("result") or test.get("result_display"))
        if code == "nt_probnp" and _p08_is_markedly_high(value, reference_range):
            return "明显升高"
        return "偏高"
    if any(word in signal for word in ("↓", "偏低", "降低", "减少")):
        return "偏低"
    if "异常" in signal:
        return "异常"
    if "正常" in signal:
        return "正常"
    value = _safe_float(test.get("result") or test.get("result_display"))
    if value is None:
        return "需复核"
    return _p08_status_from_value(value, reference_range, code=code)


def _p08_status_from_value(value: float | None, reference_range: str, *, code: str = "") -> str:
    if value is None:
        return "需复核"
    bounds = _p05_parse_reference_bounds(reference_range)
    for lower, upper in bounds:
        if lower is not None and value < lower:
            return "偏低"
        if upper is not None and value > upper:
            if code == "nt_probnp" and _p08_is_markedly_high(value, reference_range):
                return "明显升高"
            return "偏高"
        if lower is not None and upper is not None and lower <= value <= upper:
            return "正常"
        if lower is None and upper is not None and value <= upper:
            return "正常"
        if upper is None and lower is not None and value >= lower:
            return "正常"
    return "正常" if bounds else "需复核"


def _p08_is_markedly_high(value: float | None, reference_range: str) -> bool:
    if value is None:
        return False
    bounds = _p05_parse_reference_bounds(reference_range)
    upper_values = [upper for _lower, upper in bounds if upper is not None]
    return bool(upper_values and value >= max(upper_values) * 2)


def _p08_result_with_indicator(result: str, indicator: str, *, missing_text: str = "未识别") -> str:
    text = str(result or "").strip()
    flag = str(indicator or "").strip()
    if not text:
        return missing_text
    if flag in {"↑", "↓"} and flag not in text:
        return f"{text} {flag}"
    return text


def _p08_value_with_unit(value: str, unit: str) -> str:
    text = str(value or "").strip()
    unit_text = str(unit or "").strip()
    if not text:
        return "未识别"
    if text in {"未识别", "—"} or unit_text in {"", "—"}:
        return text
    return text if unit_text in text else f"{text} {unit_text}"


def _p08_indicator_interpretation(short_name: str, result: str, unit: str, status: str) -> str:
    result_display = _p08_value_with_unit(result, unit)
    if status == "未识别":
        return f"未识别到{short_name}有效结果，建议人工核对原始报告或补录该项目。"
    if _p08_status_is_normal(status):
        return f"{short_name}结果为{result_display}，处于参考范围内，当前未见该项提示的明显异常信号。"
    if _p08_status_is_high(status):
        return f"{short_name}结果为{result_display}，提示该指标偏高或异常，建议结合原始报告、症状和相关检查人工复核。"
    if _p08_status_is_low(status):
        return f"{short_name}结果为{result_display}，提示存在偏低趋势，建议结合采样条件和原始参考范围人工复核。"
    return f"{short_name}结果为{result_display}，当前状态为{status}，建议人工核对原始报告和参考范围。"


def _p08_group_summary(indicators: dict[str, dict[str, Any]], *, group_name: str) -> dict[str, str]:
    recognized = [item for item in indicators.values() if item.get("status") != "未识别"]
    review_items = [item for item in recognized if str(item.get("status") or "") in {"待复核", "需复核"}]
    abnormal = [item for item in recognized if item not in review_items and not _p08_status_is_normal(str(item.get("status") or ""))]
    if not recognized:
        return {
            "overall_status": "待补充",
            "detail_status": "等待人工补录",
            "summary": f"当前未识别到{group_name}有效结果，请先核对OCR文本层或人工补录后再进行综合评估。",
        }
    if abnormal:
        focus = "、".join(f"{item['short_name']}{item['status']}" for item in abnormal[:4])
        return {
            "overall_status": "需关注",
            "detail_status": f"{focus}需复核",
            "summary": f"{group_name}中{focus}，建议结合原始报告参考范围、症状、既往史和相关检查进行人工复核。",
        }
    if review_items:
        focus = "、".join(f"{item['short_name']}{item['status']}" for item in review_items[:4])
        return {
            "overall_status": "待复核",
            "detail_status": focus,
            "summary": f"{group_name}中{focus}；其余已识别项目未见明显异常，请以原始报告和人工复核结果为准。",
        }
    return {
        "overall_status": "指标稳定",
        "detail_status": "已识别项目处于参考范围",
        "summary": f"已识别{group_name}整体处于参考范围内，当前未见明显异常信号，建议结合个体风险因素持续观察。",
    }


def _p08_core_judgements(
    cardiovascular: dict[str, dict[str, Any]],
    raas: dict[str, dict[str, Any]],
    cardiovascular_summary: dict[str, str],
    raas_summary: dict[str, str],
) -> dict[str, Any]:
    nt_probnp = cardiovascular["nt_probnp"]
    d_dimer = cardiovascular["d_dimer"]
    return {
        "nt_probnp": {
            "title": f"NT-proBNP{_p08_status_label(nt_probnp.get('status'))}",
            "value": nt_probnp.get("result") or "未识别",
            "unit": nt_probnp.get("unit") or "pg/mL",
        },
        "raas": {
            "title": "RAAS系统正常" if _p08_status_is_normal(raas_summary.get("overall_status")) else f"RAAS系统{raas_summary.get('overall_status', '待复核')}",
            "status": "指标在正常范围内" if _p08_status_is_normal(raas_summary.get("overall_status")) else raas_summary.get("detail_status", "需人工复核"),
        },
        "d_dimer": {
            "title": f"D-二聚体{_p08_status_label(d_dimer.get('status'))}",
            "status": "指标在正常范围内" if _p08_status_is_normal(d_dimer.get("status")) else str(d_dimer.get("status") or "需人工复核"),
        },
    }


def _p08_priorities(
    cardiovascular: dict[str, dict[str, Any]],
    raas: dict[str, dict[str, Any]],
    cardiovascular_summary: dict[str, str],
    raas_summary: dict[str, str],
) -> dict[str, dict[str, str]]:
    nt_probnp = cardiovascular["nt_probnp"]
    d_dimer = cardiovascular["d_dimer"]
    priorities: list[tuple[str, str]] = []
    if _p08_status_is_high(str(nt_probnp.get("status") or "")):
        priorities.append(("心血管功能复核", "结合症状、心电图、心脏超声及肾功能资料，优先复核心脏压力负荷信号。"))
    elif str(nt_probnp.get("status") or "") == "未识别":
        priorities.append(("补充NT-proBNP", "先核对原始报告或人工补录NT-proBNP结果，再进行心血管风险判断。"))
    else:
        priorities.append(("维持心血管稳定", "继续关注血压、心率、体重和运动耐量，保持规律复评。"))

    if not _p08_status_is_normal(raas_summary.get("overall_status")):
        priorities.append(("复核RAAS状态", "结合血压、用药、采血体位和采样时间，复核RAAS相关指标。"))
    else:
        priorities.append(("生活方式全面优化", "加强饮食管理、规律运动、体重控制、睡眠管理和戒烟限酒。"))

    if _p08_status_is_high(str(d_dimer.get("status") or "")):
        priorities.append(("凝血风险复核", "结合症状、炎症、近期手术或创伤情况，必要时咨询专业医生。"))
    else:
        priorities.append(("定期监测关键指标", "按阶段复查NT-proBNP、D-二聚体、FFA及RAAS指标，动态观察风险变化。"))

    return {f"priority_{index}": {"title": title, "body": body} for index, (title, body) in enumerate(priorities[:3], start=1)}


def _p08_interpretations(
    cardiovascular: dict[str, dict[str, Any]],
    raas: dict[str, dict[str, Any]],
    cardiovascular_summary: dict[str, str],
    raas_summary: dict[str, str],
) -> dict[str, str]:
    return {
        "nt_probnp": cardiovascular["nt_probnp"]["interpretation"],
        "d_dimer": cardiovascular["d_dimer"]["interpretation"],
        "ffa": cardiovascular["ffa"]["interpretation"],
        "raas": raas_summary["summary"],
        "advice": _p08_lifestyle_advice(cardiovascular, raas, cardiovascular_summary, raas_summary),
    }


def _p08_deep_dive(
    cardiovascular: dict[str, dict[str, Any]],
    raas: dict[str, dict[str, Any]],
    cardiovascular_summary: dict[str, str],
    raas_summary: dict[str, str],
) -> dict[str, Any]:
    nt_probnp = cardiovascular["nt_probnp"]
    d_dimer = cardiovascular["d_dimer"]
    ffa = cardiovascular["ffa"]
    thrombotic_status = _p08_combined_status([d_dimer, ffa], normal_label="风险较低")
    return {
        "nt_probnp": {
            "key_status": f"重点解读：{_p08_status_label(nt_probnp.get('status'))}",
            "summary": nt_probnp["interpretation"],
            "advice": "建议结合临床症状、心脏超声、心电图、肾功能和既往史进一步复核心功能状态，并由专业人员制定管理计划。",
        },
        "raas": {
            "result_status": raas_summary["overall_status"],
            "key_status": raas_summary["overall_status"],
            "summary": raas_summary["summary"],
            "advice": "建议结合血压记录、用药情况、采血体位和作息状态进行复核，并按阶段监测RAAS相关指标。",
        },
        "thrombotic_metabolism": {
            "result_status": thrombotic_status,
            "key_status": thrombotic_status,
            "d_dimer_text": d_dimer["interpretation"],
            "ffa_text": ffa["interpretation"],
            "advice": "建议继续保持合理饮食、规律运动和体重管理，并结合血脂、血糖、炎症和凝血相关指标动态复评。",
        },
    }


def _p08_overall_summary(
    cardiovascular_summary: dict[str, str],
    raas_summary: dict[str, str],
    cardiovascular: dict[str, dict[str, Any]],
    raas: dict[str, dict[str, Any]],
) -> str:
    if cardiovascular_summary["overall_status"] == "待补充" and raas_summary["overall_status"] == "待补充":
        return "当前尚未识别到P08关键检测结果，请先核对OCR文本层或人工补录后再进行心血管代谢风险综合评估。"
    abnormal_names = _p08_abnormal_indicator_names(cardiovascular, raas)
    if abnormal_names:
        return f"基于已识别检测数据，{abnormal_names}需重点关注。建议结合症状、既往史、血压血脂血糖资料和原始报告进行人工复核，并制定阶段性健康管理方案。"
    return "基于已识别检测数据，心血管功能、凝血脂代谢及RAAS系统相关指标整体相对平稳。建议继续保持规律运动、均衡饮食、睡眠管理和阶段复评。"


def _p08_risk_assessment(cardiovascular: dict[str, dict[str, Any]], raas: dict[str, dict[str, Any]]) -> str:
    abnormal_names = _p08_abnormal_indicator_names(cardiovascular, raas)
    if abnormal_names:
        return f"检测结果中{abnormal_names}提示需复核风险信号，请结合原始报告和专业人员意见进行人工审查。"
    missing = [
        item["short_name"]
        for item in [*cardiovascular.values(), *raas.values()]
        if item.get("status") == "未识别"
    ]
    if missing:
        return f"当前缺少{ '、'.join(missing[:5]) }等关键项目，建议补录后再完成风险分层。"
    return "当前已识别指标未见明显心血管代谢风险信号，建议维持健康生活方式并定期复评。"


def _p08_lifestyle_advice(
    cardiovascular: dict[str, dict[str, Any]],
    raas: dict[str, dict[str, Any]],
    cardiovascular_summary: dict[str, str],
    raas_summary: dict[str, str],
) -> str:
    if _p08_abnormal_indicator_names(cardiovascular, raas):
        return "建议优先复核异常项目，结合血压、血脂、血糖、体重、运动耐量和症状记录制定阶段性健康管理计划。"
    if cardiovascular_summary["overall_status"] == "待补充" or raas_summary["overall_status"] == "待补充":
        return "建议先补充缺失检测结果，再结合生活方式、既往史和基础代谢资料进行综合评估。"
    return "建议保持均衡饮食、规律运动、体重管理、睡眠节律和戒烟限酒，并按计划复查关键指标。"


def _p08_abnormal_indicator_names(cardiovascular: dict[str, dict[str, Any]], raas: dict[str, dict[str, Any]]) -> str:
    abnormal = [
        item
        for item in [*cardiovascular.values(), *raas.values()]
        if item.get("status") not in {"未识别", "待补充", "待复核", "需复核"} and not _p08_status_is_normal(str(item.get("status") or ""))
    ]
    names = [f"{item['short_name']}{item['status']}" for item in abnormal[:5]]
    suffix = "等" if len(abnormal) > 5 else ""
    return "、".join(names) + suffix if names else ""


def _p08_combined_status(items: list[dict[str, Any]], *, normal_label: str) -> str:
    if any(_p08_status_is_high(str(item.get("status") or "")) for item in items):
        return "需关注"
    if any(_p08_status_is_low(str(item.get("status") or "")) for item in items):
        return "需复核"
    if all(_p08_status_is_normal(str(item.get("status") or "")) for item in items):
        return normal_label
    return "待复核"


def _p08_status_label(status: Any) -> str:
    text = str(status or "").strip()
    if not text:
        return "待复核"
    if text in {"正常", "指标稳定"}:
        return "正常"
    return text


def _p08_status_is_normal(status: Any) -> bool:
    text = str(status or "")
    return text in {"正常", "良好", "平稳", "指标正常", "指标稳定", "风险较低"}


def _p08_status_is_high(status: str) -> bool:
    return any(word in str(status or "") for word in ("偏高", "升高", "增高", "过高", "异常", "高风险", "明显升高", "↑"))


def _p08_status_is_low(status: str) -> bool:
    return any(word in str(status or "") for word in ("偏低", "降低", "减少", "↓"))


def _build_p09_report_data(ocr_result: dict[str, Any]) -> dict[str, Any]:
    structured = ocr_result.get("structured_report", {}) if isinstance(ocr_result.get("structured_report"), dict) else {}
    patient_info = structured.get("patient_info", {}) if isinstance(structured.get("patient_info"), dict) else {}
    additional_info = structured.get("additional_info", {}) if isinstance(structured.get("additional_info"), dict) else {}
    tests = structured.get("tests", []) if isinstance(structured.get("tests"), list) else []

    report_id = str(structured.get("report_id") or ocr_result.get("source_file") or "")
    assessment_date_raw = str(additional_info.get("report_date") or additional_info.get("sample_date") or "")
    sample_types = patient_info.get("specimen_types") or []
    if not isinstance(sample_types, list):
        sample_types = [str(sample_types)]
    sample_type_display = "、".join(str(item) for item in sample_types if str(item).strip()) or "血清"
    submitting_unit = str(patient_info.get("submitting_unit") or patient_info.get("hospital") or "").strip()
    indicators = {
        code: _p09_indicator(tests, code, definition, patient_info=patient_info)
        for code, definition in P09_INDICATOR_DEFINITIONS.items()
    }
    priorities = _p09_priorities(indicators)
    management = _p09_management_plan(indicators)
    hormone_balance_score = _p09_hormone_balance_score(indicators)
    e2_deep_dive = _p09_e2_deep_dive(indicators["e2"], indicators)

    return {
        "case_id": f"case_{report_id or 'p09'}",
        "package_code": "P09",
        "patient": {
            "name": patient_info.get("name") or "",
            "gender": patient_info.get("gender") or "",
            "age": _age_display(patient_info.get("age")),
            "phone": patient_info.get("phone") or "未填写",
            "symptoms": _p09_clinical_diagnosis_display(patient_info.get("clinical_diagnosis")),
            "hospital": submitting_unit,
            "submitting_unit": submitting_unit,
            "specimen_condition": patient_info.get("specimen_condition") or "",
        },
        "report": {
            "report_id": report_id,
            "assessment_type": P09_ASSESSMENT_TYPE,
            "method": P09_METHOD,
            "assessment_date": _date_display(assessment_date_raw),
            "sample_date": additional_info.get("sample_date") or "",
            "receive_date": additional_info.get("receive_date") or "",
            "report_date": additional_info.get("report_date") or "",
            "generated_at": f"报告生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        },
        "sample": {
            "type": sample_type_display,
            "condition": patient_info.get("specimen_condition") or "—",
        },
        "lab_results": [_lab_result(test) for test in tests],
        "organization": {
            "phone": "400-158-1959",
            "email": "service@anweikang.com",
            "website": "www.anweikang.com",
            "address": P09_ORGANIZATION_ADDRESS,
        },
        "p09": {
            "management_focus": "激素平衡与生活方式优化",
            "indicators": indicators,
            "scores": {
                "metabolic": {"value": _p09_metabolic_score(indicators), "unit": "/100", "status": "良好"},
                "sleep": {"value": _p09_sleep_score(indicators), "unit": "/100", "status": "良好"},
                "hormone_balance": {"value": hormone_balance_score, "display": f"{hormone_balance_score}分"},
            },
            "priorities": priorities,
            "overall_summary": _p09_overall_summary(indicators),
            "risk_assessment": _p09_risk_assessment(indicators),
            "deep_dive": {"e2": e2_deep_dive},
            "management": management,
            "followup_advice": "建议按12周计划执行饮食、作息、运动与阶段复评，并记录月经周期、睡眠、情绪和生活方式变化。",
            "disclaimer": "本报告仅供健康管理参考，不作为临床诊断依据。",
            "review_note": "健康管理专家可结合月经周期、年龄、症状、用药和原始报告参考范围进行综合判断。",
            "page_note": "本报告仅供健康管理参考，非疾病诊断依据。如有不适或疑问，请及时咨询专业医生。",
        },
        "ai_outputs": {
            "status": "pending",
            "note": "当前已基于P09 OCR结构化结果生成报告预览；AI解读完成后将覆盖对应健康管理洞察字段。",
        },
        "ocr_snapshot": {
            "source_file": ocr_result.get("source_file", ""),
            "strategy_version": ocr_result.get("strategy_version", ""),
            "provider": ocr_result.get("provider", ""),
            "warnings": ocr_result.get("warnings", []),
        },
        "version_lock": {
            "template_version": P09_TEMPLATE_VERSION,
            "rule_version": P09_RULE_VERSION,
            "prompt_version": P09_PROMPT_VERSION,
            "ai_model": "deepseek-v4-flash",
            "ocr_strategy_version": ocr_result.get("strategy_version", ""),
            "ocr_provider": ocr_result.get("provider", ""),
        },
    }


def _build_p10_report_data(ocr_result: dict[str, Any]) -> dict[str, Any]:
    ocr_result = _normalize_p10_ocr_result(ocr_result)
    structured = ocr_result.get("structured_report", {}) if isinstance(ocr_result.get("structured_report"), dict) else {}
    patient_info = structured.get("patient_info", {}) if isinstance(structured.get("patient_info"), dict) else {}
    additional_info = structured.get("additional_info", {}) if isinstance(structured.get("additional_info"), dict) else {}
    tests = structured.get("tests", []) if isinstance(structured.get("tests"), list) else []
    p10_report = structured.get("p10_extracted_report", {}) if isinstance(structured.get("p10_extracted_report"), dict) else {}

    report_id = str(structured.get("report_id") or ocr_result.get("source_file") or "")
    assessment_date_raw = str(additional_info.get("report_date") or additional_info.get("sample_date") or "")
    submitting_unit = str(patient_info.get("submitting_unit") or patient_info.get("hospital") or "").strip()
    contact = p10_report.get("contact", {}) if isinstance(p10_report.get("contact"), dict) else {}
    psa = _p10_indicator_group(tests, "psa", "总PSA", default_reference="0.00~4.00", default_unit="ng/mL")
    psa_free = _p10_indicator_group(tests, "psa_free", "游离PSA", default_reference="0.00~1.00", default_unit="ng/mL")
    psa_ratio = _p10_indicator_group(tests, "psa_ratio", "比值（游离/总PSA）", default_reference=">0.25", default_unit="")
    dhea = _p10_indicator_test(tests, "dhea", "脱氢表雄酮（DHEA）")
    inhibin_b = _p10_indicator_test(tests, "inhibin_b", "抑制素B")
    cyp1a1 = _p10_indicator_group(tests, "cyp1a1", "CYP1A1")
    aldh2 = _p10_indicator_group(tests, "aldh2", "ALDH2")
    lct = _p10_indicator_group(tests, "lct", "LCT")
    cyp1a2 = _p10_indicator_group(tests, "cyp1a2", "CYP1A2")

    return {
        "case_id": f"case_{report_id or 'p10'}",
        "package_code": "P10",
        "patient": {
            "name": patient_info.get("name") or "",
            "gender": patient_info.get("gender") or "",
            "age": _age_display(patient_info.get("age")),
            "phone": patient_info.get("phone") or "—",
            "symptoms": patient_info.get("clinical_diagnosis") or "/",
            "hospital": submitting_unit,
            "submitting_unit": submitting_unit,
            "specimen_condition": patient_info.get("specimen_condition") or "",
        },
        "report": {
            "report_id": report_id,
            "assessment_type": P10_ASSESSMENT_TYPE,
            "method": P10_METHOD,
            "assessment_date": _date_display(assessment_date_raw),
            "sample_date": additional_info.get("sample_date") or "",
            "receive_date": additional_info.get("receive_date") or "",
            "report_date": additional_info.get("report_date") or "",
            "generated_at": f"报告生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        },
        "sample": {
            "type": P10_SAMPLE_TYPE,
            "condition": patient_info.get("specimen_condition") or "—",
        },
        "lab_results": [_lab_result(test) for test in tests],
        "organization": {
            "phone": str(contact.get("phone") or "400-158-1959"),
            "email": "service@anweikang.com",
            "website": str(contact.get("website") or "www.anweikang.com"),
            "address": str(contact.get("address") or P10_ORGANIZATION_ADDRESS),
        },
        "p10": {
            "report_title": str((p10_report.get("report_info") or {}).get("title") or P10_REPORT_NAME),
            "notes": str(structured.get("notes") or ""),
            "indicators": {
                "psa": psa,
                "psa_free": psa_free,
                "psa_ratio": psa_ratio,
                "dhea": dhea,
                "inhibin_b": inhibin_b,
                "cyp1a1": cyp1a1,
                "aldh2": aldh2,
                "lct": lct,
                "cyp1a2": cyp1a2,
            },
            "deep_dive": {
                "dhea": {
                    "summary": _p10_dhea_fallback_summary(dhea)
                },
                "inhibin_b": {
                    "summary": _p10_inhibin_b_fallback_summary(inhibin_b)
                }
            },
            "followup_advice": "建议结合基因风险、前列腺相关指标和生活方式记录进行阶段复评，并由专业人员人工复核。",
            "disclaimer": str(p10_report.get("remarks") or "本报告仅供健康管理参考，不作为临床诊断依据。"),
            "review_note": "P10 已切换到新的专业 JSON 蓝本结构，AI 解读与模板渲染应基于 structured_report.tests 和 sections 原始内容复核。",
        },
        "ai_outputs": {
            "status": "pending",
            "note": "当前已将 P10 专业 OCR JSON 归一为 structured_report；AI 解读可继续基于新蓝本字段生成。",
        },
        "ocr_snapshot": {
            "source_file": ocr_result.get("source_file", ""),
            "strategy_version": ocr_result.get("strategy_version", ""),
            "provider": ocr_result.get("provider", ""),
            "warnings": ocr_result.get("warnings", []),
        },
        "version_lock": {
            "template_version": P10_TEMPLATE_VERSION,
            "rule_version": P10_RULE_VERSION,
            "prompt_version": P10_PROMPT_VERSION,
            "ai_model": "deepseek-v4-flash",
            "ocr_strategy_version": ocr_result.get("strategy_version", ""),
            "ocr_provider": ocr_result.get("provider", ""),
        },
    }


def _p10_indicator_test(tests: list[dict[str, Any]], code: str, default_name: str) -> dict[str, Any]:
    test = _find_test_by_code(tests, code)
    if not test:
        return {
            "code": code,
            "name": default_name,
            "result": "待识别",
            "result_display": "待识别",
            "reference_range": "",
            "unit": "",
            "method": "",
            "gene_locus": "",
            "gene_type": "",
            "status": "待识别",
        }
    return {
        "code": code,
        "name": str(test.get("test_name") or default_name),
        "result": str(test.get("result") or ""),
        "result_display": _test_display(test),
        "reference_range": str(test.get("reference_range") or ""),
        "unit": str(test.get("unit") or ""),
        "method": str(test.get("method") or ""),
        "gene_locus": str(test.get("gene_locus") or test.get("locus") or ""),
        "gene_type": str(test.get("gene_type") or test.get("genotype") or ""),
        "status": str(test.get("indicator") or ""),
    }


def _p10_indicator_group(
    tests: list[dict[str, Any]],
    code: str,
    default_name: str,
    *,
    default_reference: str = "",
    default_unit: str = "",
) -> dict[str, Any]:
    matched = [test for test in tests if str(test.get("item_code") or "") == code]
    if not matched:
        return {
            "code": code,
            "name": default_name,
            "result": "待识别",
            "result_display": "待识别",
            "reference_range": default_reference,
            "unit": default_unit,
            "method": "",
            "gene_locus": "",
            "gene_type": "",
            "status": "待识别",
        }

    first = matched[0]
    result_values = _p10_join_unique(str(test.get("result") or "") for test in matched)
    result_display_values = _p10_join_unique(_test_display(test) for test in matched)
    gene_loci = _p10_join_unique(str(test.get("gene_locus") or test.get("locus") or "") for test in matched)
    gene_types = _p10_join_unique(str(test.get("gene_type") or test.get("genotype") or "") for test in matched)
    status_values = _p10_join_unique(str(test.get("indicator") or "") for test in matched)
    interpretation_values = _p10_join_unique(str(test.get("interpretation") or "") for test in matched)
    is_gene_group = bool(gene_loci or gene_types) or code in {"cyp1a1", "aldh2", "lct", "cyp1a2", "adh1b"}
    display_result = interpretation_values if is_gene_group and interpretation_values else result_values
    return {
        "code": code,
        "name": str(first.get("test_name") or default_name),
        "result": display_result,
        "result_display": _p10_result_with_unit(result_display_values or result_values, str(first.get("unit") or default_unit)),
        "reference_range": str(first.get("reference_range") or default_reference),
        "unit": str(first.get("unit") or default_unit),
        "method": _p10_join_unique(str(test.get("method") or "") for test in matched),
        "gene_locus": gene_loci,
        "gene_type": gene_types,
        "status": status_values or interpretation_values or "已识别",
    }


def _p10_join_unique(values: Any) -> str:
    seen: list[str] = []
    for value in values:
        text = str(value or "").strip()
        if text and text not in seen:
            seen.append(text)
    return "；".join(seen)


def _p10_result_with_unit(result: str, unit: str) -> str:
    result = str(result or "").strip()
    unit = str(unit or "").strip()
    if not result or result == "待识别" or not unit or result.endswith(unit):
        return result
    if "；" in result:
        return result
    return f"{result}{unit}"


def _p10_dhea_fallback_summary(indicator: dict[str, Any]) -> str:
    result = str(indicator.get("result") or "").strip()
    reference = str(indicator.get("reference_range") or "").strip()
    unit = str(indicator.get("unit") or "").strip()
    if not result:
        return "DHEA 结果待补充，建议结合原始检验报告与临床情况进行人工复核。"
    return f"本次 DHEA 结果为 {result}{unit}。建议结合参考范围、年龄阶段与精力状态，关注应激储备、能量代谢及雄激素前体支持情况；如有持续疲劳、恢复变慢或状态波动，建议阶段复评。参考范围：{reference}"


def _p10_inhibin_b_fallback_summary(indicator: dict[str, Any]) -> str:
    result = str(indicator.get("result") or "").strip()
    reference = str(indicator.get("reference_range") or "").strip()
    unit = str(indicator.get("unit") or "").strip()
    if not result:
        return "抑制素B 结果待补充，建议结合原始检验报告与临床情况进行人工复核。"
    return f"本次抑制素B结果为 {result}{unit}。建议结合参考范围、年龄阶段与生殖健康目标，关注生精功能支持和阶段性复评安排；如有相关困扰，建议进一步结合临床资料综合判断。参考范围：{reference}"


def _p09_indicator(
    tests: list[dict[str, Any]],
    code: str,
    definition: dict[str, Any],
    *,
    patient_info: dict[str, Any] | None = None,
) -> dict[str, Any]:
    test = _find_test_by_code(tests, code) or _find_test_any(tests, list(definition["keywords"]))
    result = str(test.get("result") or "").strip() if test else ""
    indicator = str(test.get("indicator") or "").strip() if test else ""
    unit = str(test.get("unit") or definition["unit"]).strip() if test else str(definition["unit"])
    reference = str(test.get("reference_range") or definition["reference"]).strip() if test else str(definition["reference"])
    method = str(test.get("method") or definition["method"]).strip() if test else str(definition["method"])
    status = _p09_indicator_status(test, reference)
    result_text = _p09_result_with_indicator(result, indicator, missing_text="未识别" if not test else "—")
    result_display = _p09_value_with_unit(result_text, unit)
    reference_display = _p09_reference_display(code, reference, unit, patient_info=patient_info, value=_safe_float(result))
    return {
        "code": code,
        "name": definition["name"],
        "short_name": definition["short_name"],
        "group": definition["group"],
        "result": result_text,
        "raw_value": _safe_float(result),
        "indicator": indicator,
        "unit": unit or "—",
        "result_display": result_display,
        "reference_range": reference or "—",
        "reference_display": reference_display,
        "status": status,
        "status_display": _p09_status_display(status),
        "range_status_display": f"{_p09_status_display(status)} | {reference_display}",
        "method": method,
        "interpretation": _p09_indicator_interpretation(definition["short_name"], result_display, status),
    }


def _p09_indicator_status(test: dict[str, Any], reference_range: str) -> str:
    if not test:
        return "未识别"
    signal = f"{test.get('result', '')}{test.get('indicator', '')}{test.get('status', '')}"
    if not str(test.get("result") or "").strip() and not str(test.get("indicator") or "").strip():
        return "待复核"
    if any(word in signal for word in ("↑", "偏高", "升高", "增高", "过高")):
        return "偏高"
    if any(word in signal for word in ("↓", "偏低", "降低", "减少")):
        return "偏低"
    if "异常" in signal:
        return "异常"
    if "正常" in signal:
        return "正常"
    value = _safe_float(test.get("result") or test.get("result_display"))
    if value is None:
        return "需复核"
    return _p09_status_from_value(value, reference_range)


def _p09_status_from_value(value: float | None, reference_range: str) -> str:
    if value is None:
        return "需复核"
    bounds = _p05_parse_reference_bounds(reference_range)
    if not bounds:
        return "待复核"
    for lower, upper in bounds:
        if lower is not None and upper is not None and lower <= value <= upper:
            return "正常"
        if lower is None and upper is not None and value <= upper:
            return "正常"
        if upper is None and lower is not None and value >= lower:
            return "正常"
    lows = [lower for lower, _upper in bounds if lower is not None]
    uppers = [upper for _lower, upper in bounds if upper is not None]
    if lows and value < min(lows):
        return "偏低"
    if uppers and value > max(uppers):
        return "偏高"
    return "待复核"


def _p09_result_with_indicator(result: str, indicator: str, *, missing_text: str = "未识别") -> str:
    text = str(result or "").strip()
    flag = str(indicator or "").strip()
    if not text:
        return missing_text
    if flag in {"↑", "↓"} and flag not in text:
        return f"{text} {flag}"
    return text


def _p09_value_with_unit(value: str, unit: str) -> str:
    text = str(value or "").strip()
    unit_text = str(unit or "").strip()
    if not text:
        return "未识别"
    if text in {"未识别", "—"} or unit_text in {"", "—"}:
        return text
    return text if unit_text in text else f"{text} {unit_text}"


def _p09_reference_display(
    code: str,
    reference: str,
    unit: str,
    *,
    patient_info: dict[str, Any] | None = None,
    value: float | None = None,
) -> str:
    text = str(reference or "").strip()
    if not text or text == "—":
        return "参考范围：待补充"
    compact = _p09_compact_reference_text(code, text, unit, patient_info=patient_info, value=value)
    if compact:
        return compact
    unit_text = str(unit or "").strip()
    return f"参考范围：{text}{(' ' + unit_text) if unit_text and unit_text not in text else ''}"


def _p09_compact_reference_text(
    code: str,
    reference: str,
    unit: str,
    *,
    patient_info: dict[str, Any] | None,
    value: float | None,
) -> str:
    named_segments = _p09_named_reference_segments(reference)
    if code in {"e2", "lh", "fsh", "progesterone"}:
        matched = _p09_matching_named_segments(named_segments, value)
        if len(matched) == 1:
            label, raw_range = matched[0]
            return f"参考范围：{label} {raw_range}{(' ' + unit) if unit and unit not in raw_range else ''}"
        return "参考范围：需结合月经周期阶段判读"
    if code == "prolactin" and named_segments:
        return "参考范围：需结合妊娠或绝经状态判读"
    if code == "shbg" and named_segments:
        selected = _p09_pick_shbg_segment(named_segments, patient_info)
        if selected:
            label, raw_range = selected
            return f"参考范围：{label} {raw_range}{(' ' + unit) if unit and unit not in raw_range else ''}"
    return ""


def _p09_named_reference_segments(reference: str) -> list[tuple[str, str]]:
    patterns = [
        r"(卵泡期|排卵期|黄体期|绝经期|妊娠期|孕早期|孕中期|孕晚期|未妊娠)\s*[:：]\s*([<>≤≥＜＞]?\s*[0-9]+(?:\.[0-9]+)?(?:\s*(?:--|-|~|～)\s*[0-9]+(?:\.[0-9]+)?)?)",
        r"((?:男|女)\s*:\s*[0-9]+岁\s*-\s*[0-9]+岁|(?:男|女)\s*:\s*≥\s*[0-9]+岁)\s*[:：]\s*([0-9]+(?:\.[0-9]+)?(?:\s*(?:--|-|~|～)\s*[0-9]+(?:\.[0-9]+)?)?)",
    ]
    segments: list[tuple[str, str]] = []
    normalized = str(reference or "").replace("：", ":")
    for pattern in patterns:
        for match in re.finditer(pattern, normalized):
            label = re.sub(r"\s+", "", match.group(1))
            raw_range = re.sub(r"\s+", "", match.group(2))
            if label and raw_range:
                segments.append((label, raw_range))
    return segments


def _p09_matching_named_segments(segments: list[tuple[str, str]], value: float | None) -> list[tuple[str, str]]:
    if value is None:
        return []
    matched: list[tuple[str, str]] = []
    for label, raw_range in segments:
        for lower, upper in _p05_parse_reference_bounds(raw_range):
            if lower is not None and upper is not None and lower <= value <= upper:
                matched.append((label, raw_range))
                break
            if lower is None and upper is not None and value <= upper:
                matched.append((label, raw_range))
                break
            if upper is None and lower is not None and value >= lower:
                matched.append((label, raw_range))
                break
    return matched


def _p09_pick_shbg_segment(segments: list[tuple[str, str]], patient_info: dict[str, Any] | None) -> tuple[str, str] | None:
    if not patient_info:
        return None
    gender = str(patient_info.get("gender") or "").strip()
    age = patient_info.get("age")
    if not gender or age in (None, ""):
        return None
    try:
        age_value = int(age)
    except (TypeError, ValueError):
        return None
    for label, raw_range in segments:
        compact = re.sub(r"\s+", "", label)
        if not compact.startswith(gender):
            continue
        between = re.search(r"([0-9]+)岁-([0-9]+)岁", compact)
        if between and int(between.group(1)) <= age_value <= int(between.group(2)):
            return label, raw_range
        older = re.search(r"≥([0-9]+)岁", compact)
        if older and age_value >= int(older.group(1)):
            return label, raw_range
    return None


def _p09_status_display(status: Any) -> str:
    text = str(status or "").strip()
    if text == "正常":
        return "正常范围"
    if text in {"未识别", "待复核", "需复核"}:
        return "待补充"
    return text or "待补充"


def _p09_indicator_interpretation(short_name: str, result_display: str, status: str) -> str:
    if status == "未识别":
        return f"未识别到{short_name}有效结果，建议核对原始报告或补录。"
    if status in {"待复核", "需复核"}:
        return f"{short_name}结果为{result_display}，参考范围或采样背景不完整，建议人工复核。"
    if _p08_status_is_normal(status):
        return f"{short_name}结果为{result_display}，当前处于参考范围内。"
    if _p08_status_is_high(status):
        return f"{short_name}结果为{result_display}，提示偏高趋势，建议结合周期和症状复核。"
    if _p08_status_is_low(status):
        return f"{short_name}结果为{result_display}，提示偏低趋势，建议结合周期和症状复核。"
    return f"{short_name}结果为{result_display}，当前状态为{status}，建议人工复核。"


def _p09_priorities(indicators: dict[str, dict[str, Any]]) -> dict[str, dict[str, str]]:
    abnormal = _p09_abnormal_indicators(indicators)
    priorities: list[tuple[str, str]] = []
    if abnormal:
        first = abnormal[0]
        priorities.append(("复核激素波动", f"优先复核{first['short_name']}{first['status']}，结合周期与症状判断。"))
    else:
        priorities.append(("维持激素平衡", "保持规律作息、均衡饮食和阶段复评，持续观察激素趋势。"))
    priorities.append(("生殖健康管理", "结合周期、年龄和AMH等指标，动态关注卵巢储备与周期规律。"))
    priorities.append(("情绪与睡眠管理", "记录睡眠、压力和情绪变化，减少节律波动对内分泌的影响。"))
    priorities.append(("生活方式优化", "维持运动、蛋白和膳食纤维摄入，支持代谢与体成分稳定。"))
    return {f"priority_{index}": {"title": title, "body": body} for index, (title, body) in enumerate(priorities[:4], start=1)}


def _p09_overall_summary(indicators: dict[str, dict[str, Any]]) -> str:
    recognized = [item for item in indicators.values() if item.get("status") != "未识别"]
    if not recognized:
        return "当前尚未识别到P09关键女性激素检测结果，请先核对OCR文本层或人工补录后再进行激素平衡综合评估。"
    abnormal_names = _p09_abnormal_indicator_names(indicators)
    if abnormal_names:
        return f"基于已识别检测数据，{abnormal_names}需重点关注。建议结合周期阶段、年龄、症状和原始报告参考范围进行人工复核，并制定阶段性健康管理计划。"
    return "基于已识别检测数据，女性激素及相关指标整体相对平稳。建议继续保持规律作息、均衡饮食、压力管理和阶段复评。"


def _p09_risk_assessment(indicators: dict[str, dict[str, Any]]) -> str:
    abnormal_names = _p09_abnormal_indicator_names(indicators)
    if abnormal_names:
        return f"检测结果中{abnormal_names}提示需复核信号，请结合周期阶段、症状、用药和专业人员意见进行人工审查。"
    missing = [item["short_name"] for item in indicators.values() if item.get("status") == "未识别"]
    if missing:
        return f"当前缺少{'、'.join(missing[:5])}等项目，建议补录后再完成女性激素平衡评估。"
    return "当前已识别指标未见明显激素失衡风险信号，建议维持健康生活方式并定期复评。"


def _p09_e2_deep_summary(e2: dict[str, Any]) -> str:
    if e2.get("status") == "未识别":
        return "未识别到雌二醇（E2）有效结果，建议人工核对原始报告或补录后再进行深度解读。"
    return f"您的雌二醇（E2）水平为{e2.get('result_display')}，{e2.get('status_display')}。雌二醇会随月经周期、年龄、睡眠和压力状态波动，建议结合个人周期阶段和症状综合评估。"


def _p09_e2_highlights(e2: dict[str, Any], indicators: dict[str, dict[str, Any]]) -> list[str]:
    if e2.get("status") == "未识别":
        return [
            "雌二醇结果待补充，需先核对原始报告。",
            "建议同步补充周期阶段、症状和近期用药信息。",
            "补全核心信息后再完成深度解读与复评安排。",
        ]
    highlights = [
        f"本次E2为{e2.get('result_display')}，{e2.get('status_display')}。",
        "判读时仍需结合月经周期阶段、年龄和近期压力变化。",
    ]
    progesterone = indicators.get("progesterone", {})
    if progesterone and progesterone.get("status") != "未识别":
        highlights.append(f"建议与孕酮{progesterone.get('result_display')}联合观察排卵与黄体支持情况。")
    else:
        highlights.append("建议与LH、FSH和孕酮等核心激素联动复核，避免单项过度解读。")
    return highlights[:3]


def _p09_e2_action_items(e2: dict[str, Any]) -> list[dict[str, str]]:
    if e2.get("status") == "未识别":
        return [
            {"title": "补全资料", "body": "先补录E2结果及周期阶段，再生成个体化建议。"},
            {"title": "记录症状", "body": "同步记录月经、睡眠、情绪和压力变化。"},
            {"title": "阶段复核", "body": "补全数据后结合其他核心激素重新评估。"},
        ]
    if _p08_status_is_normal(e2.get("status")):
        return [
            {"title": "规律作息", "body": "稳定睡眠与日常节律，减少激素波动干扰。"},
            {"title": "均衡饮食", "body": "保证蛋白、膳食纤维和优质脂肪摄入。"},
            {"title": "周期复评", "body": "下次复查尽量注明周期阶段，便于纵向比较。"},
        ]
    return [
        {"title": "复核周期", "body": "先核对采样时的周期阶段和近期症状变化。"},
        {"title": "降低压力", "body": "优先调整睡眠、运动和压力负荷。"},
        {"title": "联合判断", "body": "建议与LH、FSH、孕酮等项目一起复评。"},
    ]


def _p09_e2_deep_dive(e2: dict[str, Any], indicators: dict[str, dict[str, Any]]) -> dict[str, Any]:
    highlights = _p09_e2_highlights(e2, indicators)
    actions = _p09_e2_action_items(e2)
    return {
        "summary": _p09_e2_deep_summary(e2),
        "highlight_1": highlights[0],
        "highlight_2": highlights[1],
        "highlight_3": highlights[2],
        "advice_1_title": actions[0]["title"],
        "advice_1_body": actions[0]["body"],
        "advice_2_title": actions[1]["title"],
        "advice_2_body": actions[1]["body"],
        "advice_3_title": actions[2]["title"],
        "advice_3_body": actions[2]["body"],
        "ai_insight": _p09_e2_ai_insight(e2),
    }


def _p09_e2_ai_insight(e2: dict[str, Any]) -> str:
    if e2.get("status") == "未识别":
        return "雌二醇结果待补充，建议先完成原始报告复核，再生成个性化激素平衡建议。"
    if _p08_status_is_normal(e2.get("status")):
        return "您的雌二醇水平处于参考范围，建议继续保持健康生活方式，并结合周期阶段定期监测。"
    return "您的雌二醇水平存在需关注信号，建议结合月经周期、症状和专业人员意见进行复核。"


def _p09_management_plan(indicators: dict[str, dict[str, Any]]) -> dict[str, Any]:
    followup_focus = "建议3-6个月后复查女性激素相关项目，评估管理效果"
    if _p09_abnormal_indicators(indicators):
        followup_focus = "建议按专业意见提前复核异常项目"
    return {
        "diet": {
            "item_1": "优先补足优质蛋白，如鱼类、蛋类和豆制品。",
            "item_2": "每周2-3次补充深海鱼、坚果或亚麻籽。",
            "item_3": "增加十字花科蔬菜和深色蔬菜摄入。",
            "item_4": "保证全谷物、水果和膳食纤维的日常摄入。",
            "item_5": "减少高糖、高脂和高度加工食品的比例。",
        },
        "exercise": {
            "item_1": "每周保持150分钟左右中等强度有氧运动。",
            "item_2": "每周安排2-3次力量训练，支持体成分稳定。",
            "item_3": "可加入瑜伽、普拉提等身心协调训练。",
            "item_4": "避免过度运动，保留充足恢复和休息时间。",
        },
        "stress": {
            "item_1": "保持规律作息，尽量保证每日7-8小时睡眠。",
            "item_2": "练习深呼吸、冥想或正念放松，稳定节律。",
            "item_3": "记录情绪和压力变化，识别高压触发因素。",
            "item_4": "压力持续升高时，及时寻求专业支持。",
        },
        "review": {
            "item_1": followup_focus,
            "item_2": "复查时同步记录症状、周期和生活方式变化。",
            "item_3": "如出现明显月经异常或持续不适，建议及时就医。",
            "item_4": "阶段性对比E2、LH、FSH、孕酮等核心项目。",
        },
        "tip": "本方案用于健康管理参考，执行时请结合周期阶段、症状变化和复评结果动态调整。",
    }


def _p09_hormone_balance_score(indicators: dict[str, dict[str, Any]]) -> int:
    core_codes = ["e2", "lh", "fsh", "progesterone", "testosterone"]
    recognized = [indicators[code] for code in core_codes if indicators[code].get("status") != "未识别"]
    if not recognized:
        return 0
    penalty = sum(12 for item in recognized if not _p08_status_is_normal(item.get("status")))
    missing_penalty = (len(core_codes) - len(recognized)) * 8
    return max(45, min(95, 88 - penalty - missing_penalty))


def _p09_metabolic_score(indicators: dict[str, dict[str, Any]]) -> str:
    score = 72
    if not _p08_status_is_normal(indicators["testosterone"].get("status")):
        score -= 8
    if not _p08_status_is_normal(indicators["cortisol"].get("status")) and indicators["cortisol"].get("status") != "未识别":
        score -= 6
    return str(max(45, score))


def _p09_sleep_score(indicators: dict[str, dict[str, Any]]) -> str:
    score = 74
    if not _p08_status_is_normal(indicators["cortisol"].get("status")) and indicators["cortisol"].get("status") != "未识别":
        score -= 10
    return str(max(45, score))


def _p09_abnormal_indicators(indicators: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        item
        for item in indicators.values()
        if item.get("status") not in {"未识别", "待补充", "待复核", "需复核"} and not _p08_status_is_normal(item.get("status"))
    ]


def _p09_abnormal_indicator_names(indicators: dict[str, dict[str, Any]]) -> str:
    abnormal = _p09_abnormal_indicators(indicators)
    names = [f"{item['short_name']}{item['status']}" for item in abnormal[:5]]
    suffix = "等" if len(abnormal) > 5 else ""
    return "、".join(names) + suffix if names else ""


def _p09_empty_display(value: Any, *, default: str) -> str:
    text = str(value or "").strip()
    if not text or text in {"-", "—", "/"}:
        return default
    return text


def _p09_clinical_diagnosis_display(value: Any) -> str:
    text = str(value or "").strip()
    compact = "".join(text.split()).lower()
    if not compact or compact in {"-", "—", "/"}:
        return "-"
    if "anweikang" in compact or "安为康" in text or "安為康" in text:
        return "-"
    return text


def _build_placeholder_report_data(package_code: str, ocr_result: dict[str, Any]) -> dict[str, Any]:
    return {
        "case_id": f"case_{package_code.lower()}_placeholder",
        "package_code": package_code,
        "patient": {},
        "sample": {},
        "lab_results": [],
        "ai_outputs": {"status": "placeholder"},
        "ocr_snapshot": {
            "source_file": ocr_result.get("source_file", ""),
            "strategy_version": ocr_result.get("strategy_version", ""),
            "provider": ocr_result.get("provider", ""),
        },
    }


def _build_p04_report_data(ocr_result: dict[str, Any]) -> dict[str, Any]:
    structured = ocr_result.get("structured_report", {})
    patient_info = structured.get("patient_info", {})
    additional_info = structured.get("additional_info", {})
    tests = structured.get("tests", [])

    report_id = str(structured.get("report_id") or ocr_result.get("source_file") or "")
    sample_date = str(additional_info.get("report_date") or additional_info.get("sample_date") or "")
    sample_types = patient_info.get("specimen_types") or []
    if not isinstance(sample_types, list):
        sample_types = [str(sample_types)]
    sample_type_display = "、".join(str(item) for item in sample_types if str(item).strip()) or "微量元素与维生素"
    submitting_unit = str(patient_info.get("submitting_unit") or patient_info.get("hospital") or "").strip()

    nutrients = {code: _p04_indicator(tests, code) for code in P04_NUTRIENT_DEFINITIONS}
    summaries = _p04_summary_fields(nutrients)

    return {
        "case_id": f"case_{report_id or 'p04'}",
        "package_code": "P04",
        "patient": {
            "name": patient_info.get("name") or "",
            "gender": patient_info.get("gender") or "",
            "age": _age_display(patient_info.get("age")),
            "phone": patient_info.get("phone") or "—",
            "symptoms": patient_info.get("clinical_diagnosis") or "/",
            "submitting_unit": submitting_unit,
            "hospital": submitting_unit,
            "specimen_condition": patient_info.get("specimen_condition") or "",
        },
        "report": {
            "report_id": report_id,
            "assessment_type": "营养素状态评估",
            "method": P04_METHOD,
            "assessment_date": _date_display(sample_date),
            "sample_date": additional_info.get("sample_date") or "",
            "receive_date": additional_info.get("receive_date") or "",
            "report_date": additional_info.get("report_date") or "",
        },
        "sample": {
            "type": sample_type_display,
            "condition": patient_info.get("specimen_condition") or "—",
        },
        "lab_results": [_lab_result(test) for test in tests],
        "organization": {
            "phone": "400-158-1959",
            "email": "service@anweikang.com",
            "website": "www.anweikang.com",
            "address": "安徽省合肥市庐阳区临泉路7266号研发中心楼5、6、7层",
        },
        "p04": {
            "nutrients": nutrients,
            **summaries,
            "priorities": _p04_priorities(nutrients),
            "diet_advice": _p04_diet_advice(nutrients),
            "lifestyle_advice": _p04_lifestyle_advice(nutrients),
            "supplement": _p04_supplement_advice(nutrients),
            "followup_advice": "建议按12周计划执行饮食、作息、运动与阶段复评，并记录症状、补充剂使用和生活方式变化。",
            "disclaimer": "本报告仅供健康管理参考，不作为临床诊断依据。",
            "review_note": "健康管理专家需结合原始报告、膳食记录、补充剂使用情况和相关症状进行综合判断。",
        },
        "ai_outputs": {
            "status": "pending",
            "note": "当前已基于P04 OCR结构化检验结果生成报告预览；AI解读完成后将覆盖对应辅助诊断字段。",
        },
        "ocr_snapshot": {
            "source_file": ocr_result.get("source_file", ""),
            "strategy_version": ocr_result.get("strategy_version", ""),
            "provider": ocr_result.get("provider", ""),
            "warnings": ocr_result.get("warnings", []),
        },
        "version_lock": {
            "template_version": "P04-html-v0.1",
            "rule_version": "P04-rules-v0.1-draft",
            "prompt_version": "P04-prompts-v0.1",
            "ai_model": "deepseek-v4-flash",
            "ocr_strategy_version": ocr_result.get("strategy_version", ""),
            "ocr_provider": ocr_result.get("provider", ""),
        },
    }


def _p04_indicator(tests: list[dict[str, Any]], code: str) -> dict[str, Any]:
    definition = P04_NUTRIENT_DEFINITIONS[code]
    test = _find_test_by_code(tests, code) or _find_test_any(tests, definition["keywords"])
    result = str(test.get("result") or "").strip() if test else ""
    indicator = str(test.get("indicator") or "").strip() if test else ""
    unit = str(test.get("unit") or definition["unit"]).strip() if test else str(definition["unit"])
    reference = str(test.get("reference_range") or definition["reference"]).strip() if test else str(definition["reference"])
    method = str(test.get("method") or definition["method"]).strip() if test else str(definition["method"])
    status = _p04_indicator_status(test, code, reference)
    result_display = _p04_value_with_unit(_p04_result_with_indicator(result, indicator), unit)
    reference_display = _p04_reference_display(reference, unit)
    return {
        "code": code,
        "name": definition["name"],
        "full_name": definition["full_name"],
        "group": definition["group"],
        "result": result or "未识别",
        "indicator": indicator,
        "unit": unit,
        "result_display": result_display,
        "reference_range": reference,
        "reference_display": reference_display,
        "method": method,
        "status": status,
        "interpretation": _p04_indicator_interpretation(code, result_display, status),
    }


def _p04_indicator_status(test: dict[str, Any], code: str, reference_range: str) -> str:
    if not test:
        return "未识别"
    if code in {"vitamin_d2", "vitamin_d3"}:
        return "正常"
    signal = f"{test.get('result', '')}{test.get('indicator', '')}"
    if any(word in signal for word in ("↑", "偏高", "升高", "增高", "过高")):
        return "偏高"
    if any(word in signal for word in ("缺乏", "严重不足")):
        return "缺乏"
    if any(word in signal for word in ("↓", "偏低", "降低", "不足")):
        return "不足" if code == "vitamin_d" else "偏低"
    if "正常" in signal:
        return "正常"

    value = _safe_float(test.get("result") or test.get("result_display"))
    if value is None:
        return "需复核"
    if code == "vitamin_d" and all(word in reference_range for word in ("缺乏", "不足", "正常", "过量")):
        if value < 12:
            return "缺乏"
        if value <= 20:
            return "不足"
        if value <= 50:
            return "正常"
        return "偏高"
    bounds = _p05_parse_reference_bounds(reference_range)
    for lower, upper in bounds:
        if lower is not None and value < lower:
            return "不足" if code == "vitamin_d" else "偏低"
        if upper is not None and value > upper:
            return "偏高"
        if lower is not None and upper is not None and lower <= value <= upper:
            return "正常"
        if lower is None and upper is not None and value <= upper:
            return "正常"
        if upper is None and lower is not None and value >= lower:
            return "正常"
    return "正常" if bounds else "需复核"


def _p04_result_with_indicator(result: str, indicator: str) -> str:
    text = str(result or "").strip()
    flag = str(indicator or "").strip()
    if not text:
        return "未识别"
    if flag in {"↑", "↓"} and flag not in text:
        return f"{text} {flag}"
    return text


def _p04_value_with_unit(value: str, unit: str) -> str:
    text = str(value or "").strip()
    if not text or text == "未识别":
        return "未识别"
    unit_text = str(unit or "").strip()
    if unit_text and unit_text not in text:
        return f"{text} {unit_text}"
    return text


def _p04_reference_display(reference: str, unit: str) -> str:
    text = str(reference or "").strip()
    if not text:
        return "未识别"
    unit_text = str(unit or "").strip()
    if unit_text and unit_text not in text:
        return f"{text} {unit_text}"
    return text


def _p04_indicator_interpretation(code: str, result_display: str, status: str) -> str:
    name = str(P04_NUTRIENT_DEFINITIONS[code]["name"])
    if status == "未识别":
        return f"未识别到{name}的有效检验结果，建议人工核对原始报告或补录该项目。"
    if status == "正常":
        return f"{name}结果为{result_display}，处于参考范围内，提示当前该营养素状态相对平稳。"
    if _p04_status_is_high(status):
        return f"{name}结果为{result_display}，提示存在偏高趋势，建议结合近期饮食、补充剂使用和人工复核意见调整摄入。"
    if _p04_status_is_low(status):
        return f"{name}结果为{result_display}，提示存在不足或偏低趋势，建议结合饮食结构、日晒或补充剂使用情况进行健康管理。"
    return f"{name}结果为{result_display}，当前状态为{status}，建议人工复核参考范围和检测条件。"


def _p04_summary_fields(nutrients: dict[str, dict[str, Any]]) -> dict[str, str]:
    recognized = [item for item in nutrients.values() if item["status"] != "未识别"]
    abnormal = [item for item in recognized if not _p04_status_is_normal(item["status"])]
    high_items = [item for item in abnormal if _p04_status_is_high(item["status"])]
    low_items = [item for item in abnormal if _p04_status_is_low(item["status"])]
    micro_items = [item for item in nutrients.values() if item["group"] == "microelements"]
    vitamin_items = [item for item in nutrients.values() if item["group"] == "vitamins"]

    micro_abnormal = [item for item in micro_items if item["status"] != "未识别" and not _p04_status_is_normal(item["status"])]
    micro_title = "微量元素"
    micro_status = "检测结果正常" if recognized and not micro_abnormal else "需关注" if micro_abnormal else "待补充"
    high_title = _p04_names(high_items, fallback="未见明显偏高")
    high_status = "偏高" if high_items else "未见偏高"
    low_title = _p04_names(low_items, fallback="未见明显不足")
    low_status = "不足" if low_items else "未见不足"

    if not recognized:
        overall_summary = "当前未识别到P04关键营养素检验结果，请先核对OCR文本层或人工补录后再进行综合评估。"
    elif abnormal:
        focus = "、".join(f"{item['name']}{item['status']}" for item in abnormal[:5])
        overall_summary = f"本次共识别到{len(recognized)}项营养素结果，需重点关注{focus}。建议结合饮食、补充剂和症状信息人工复核。"
    else:
        overall_summary = f"本次共识别到{len(recognized)}项营养素结果，微量元素与维生素整体处于参考范围内，提示基础营养状态相对平稳。"

    if high_items:
        excess_summary = f"{_p04_names(high_items)}检测结果偏高，可能与近期膳食摄入、补充剂使用或个体代谢差异有关，建议核对补充剂和强化食品摄入。"
    else:
        excess_summary = "当前未见明确偏高营养素，建议继续避免长期自行大剂量补充脂溶性维生素或矿物质。"

    if low_items:
        deficiency_summary = f"{_p04_names(low_items)}检测结果提示不足或偏低，建议结合饮食结构、日晒、吸收状态和人工复核意见进行管理。"
    else:
        deficiency_summary = "当前未见明确不足营养素，建议维持食物多样性并定期复查关键营养状态。"

    recognized_micro = [item for item in micro_items if item["status"] != "未识别"]
    if not recognized_micro:
        microelements_summary = "未识别到微量元素检验结果，请人工核对铁、锌、钙、镁、铜等项目。"
    elif micro_abnormal:
        microelements_summary = f"微量元素中{_p04_names(micro_abnormal)}存在需关注变化，建议结合参考范围和样本条件复核。"
    else:
        microelements_summary = "微量元素（铁、锌、钙、镁、铜）已识别项目均在参考范围内，整体状态良好，请继续保持均衡饮食和健康生活方式。"

    recognized_vitamins = [item for item in vitamin_items if item["status"] != "未识别"]
    if recognized_vitamins and abnormal:
        deep_overall_analysis = (
            f"{overall_summary}{excess_summary}{deficiency_summary}"
        )
    else:
        deep_overall_analysis = (
            f"{microelements_summary}{deficiency_summary}"
        )

    return {
        "microelements_status_title": micro_title,
        "microelements_status": micro_status,
        "vitamin_excess_title": high_title,
        "vitamin_excess_status": high_status,
        "vitamin_deficiency_title": low_title,
        "vitamin_deficiency_status": low_status,
        "overall_summary": overall_summary,
        "excess_summary": excess_summary,
        "deficiency_summary": deficiency_summary,
        "microelements_summary": microelements_summary,
        "deep_overall_analysis": deep_overall_analysis[:260],
    }


def _p04_priorities(nutrients: dict[str, dict[str, Any]]) -> dict[str, dict[str, str]]:
    abnormal = [item for item in nutrients.values() if item["status"] != "未识别" and not _p04_status_is_normal(item["status"])]
    low_items = [item for item in abnormal if _p04_status_is_low(item["status"])]
    high_items = [item for item in abnormal if _p04_status_is_high(item["status"])]
    titles: list[str] = []
    if low_items:
        titles.append(f"纠正{_p04_names(low_items, limit=2)}不足")
    if high_items:
        titles.append(f"平衡{_p04_names(high_items, limit=2)}摄入")
    micro_abnormal = [item for item in abnormal if item["group"] == "microelements"]
    titles.append(f"关注{_p04_names(micro_abnormal, limit=2)}水平" if micro_abnormal else "维持微量元素平衡")
    titles.append("优化日常饮食结构")
    titles.append("记录补充剂与复查变化")
    return {
        f"priority_{index}": {"title": title}
        for index, title in enumerate(titles[:4], start=1)
    }


def _p04_diet_advice(nutrients: dict[str, dict[str, Any]]) -> dict[str, str]:
    iron = nutrients["iron"]
    magnesium = nutrients["magnesium"]
    low_items = [item for item in nutrients.values() if _p04_status_is_low(item["status"])]
    high_items = [item for item in nutrients.values() if _p04_status_is_high(item["status"])]
    balanced_text = "保证食物多样化，摄入足量谷薯类、蔬菜水果、优质蛋白和健康脂肪，为各类营养素提供稳定来源。"
    if low_items:
        balanced_text = f"在均衡膳食基础上，优先关注{_p04_names(low_items, limit=3)}相关食物来源，并结合症状和复查结果调整。"
    if high_items:
        balanced_text += f" 同时核对{_p04_names(high_items, limit=3)}相关补充剂或强化食品摄入。"
    return {
        "balanced_title": "1. 均衡膳食",
        "balanced_text": balanced_text,
        "iron_title": "2. 关注铁摄入",
        "iron_text": _p04_food_text(iron, "红肉、动物肝脏、豆类、绿叶蔬菜", "维持铁储备和氧运输支持"),
        "magnesium_title": "3. 关注镁摄入",
        "magnesium_text": _p04_food_text(magnesium, "全谷物、坚果、种子、绿叶蔬菜", "支持能量代谢、神经肌肉和心血管功能"),
        "mineral_balance_title": "4. 维持锌钙铜摄入",
        "mineral_balance_text": "通过奶制品、海产品、坚果、全谷物和深色蔬菜维持锌、钙、铜摄入，避免长期单一饮食或自行大剂量补充。",
    }


def _p04_lifestyle_advice(nutrients: dict[str, dict[str, Any]]) -> dict[str, str]:
    vitamin_d = nutrients["vitamin_d"]
    sleep_text = "保持规律作息和充足睡眠，有助于身体修复、免疫稳态和营养素代谢平衡。"
    exercise_text = "每周进行规律中等强度运动，配合户外活动和力量训练，促进体能、骨骼健康和营养素利用。"
    if _p04_status_is_low(vitamin_d["status"]):
        exercise_text = "在安全防晒前提下增加规律户外活动，并结合中等强度运动和力量训练，支持维生素D、骨骼和肌肉健康。"
    return {
        "exercise_title": "1. 适度运动",
        "exercise_text": exercise_text,
        "sleep_title": "2. 充足睡眠",
        "sleep_text": sleep_text,
        "stress_title": "3. 压力管理",
        "stress_text": "通过冥想、深呼吸、瑜伽或规律休息缓解压力，减少长期压力对食欲、吸收和代谢节律的影响。",
    }


def _p04_supplement_advice(nutrients: dict[str, dict[str, Any]]) -> dict[str, str]:
    abnormal = [item for item in nutrients.values() if item["status"] != "未识别" and not _p04_status_is_normal(item["status"])]
    if abnormal:
        need_summary = f"根据检测结果，{_p04_names(abnormal, limit=4)}存在需关注变化，是否补充或减少摄入需结合原始报告和专业人员意见。"
    else:
        need_summary = "根据检测结果，已识别营养素水平总体平稳，暂不建议自行额外增加大剂量营养补充。"
    return {
        "need_summary": need_summary,
        "guidance": "如有特殊健康状况、饮食限制、备孕妊娠或正在使用补充剂，请在专业人员指导下进行个性化调整。",
        "food_first_title": "食补为主",
        "food_first_text": "优先通过均衡饮食获取营养素，保证食物多样性和长期可执行性。",
        "avoid_blind_title": "避免盲目补充",
        "avoid_blind_text": "过量补充可能带来健康风险，请勿自行长期、大剂量服用营养补充剂。",
        "followup_title": "定期复查",
        "followup_text": "建议每6-12个月进行一次营养素检测，持续关注身体营养状态变化。",
    }


def _p04_food_text(item: dict[str, Any], foods: str, benefit: str) -> str:
    status = str(item.get("status") or "")
    name = str(item.get("name") or "该营养素")
    if _p04_status_is_low(status):
        return f"{name}提示不足或偏低，可在专业人员指导下适量增加富含该营养素的食物，如{foods}，帮助{benefit}。"
    if _p04_status_is_high(status):
        return f"{name}提示偏高，建议先核对相关补充剂或强化食品摄入，避免在未复核前继续额外增加。"
    return f"保持富含该营养素的食物规律摄入，如{foods}，有助于{benefit}。"


def _p04_names(items: list[dict[str, Any]], *, limit: int = 3, fallback: str = "") -> str:
    names = [str(item.get("name") or "") for item in items if str(item.get("name") or "").strip()]
    if not names:
        return fallback
    shown = names[:limit]
    suffix = "等" if len(names) > limit else ""
    return "、".join(shown) + suffix


def _p04_status_is_normal(status: str) -> bool:
    return str(status or "") in {"正常", "良好", "平稳"}


def _p04_status_is_high(status: str) -> bool:
    return any(word in str(status or "") for word in ("偏高", "升高", "过高", "↑"))


def _p04_status_is_low(status: str) -> bool:
    return any(word in str(status or "") for word in ("偏低", "不足", "缺乏", "降低", "↓"))


def _build_p17_report_data(ocr_result: dict[str, Any]) -> dict[str, Any]:
    structured = ocr_result.get("structured_report", {})
    patient_info = structured.get("patient_info", {})
    additional_info = structured.get("additional_info", {})
    tests = structured.get("tests", [])
    p17_report = structured.get("p17_extracted_report", {})
    if not isinstance(p17_report, dict):
        p17_report = {}
    reports = p17_report.get("reports", []) if isinstance(p17_report.get("reports"), list) else []
    first_report = reports[0] if reports and isinstance(reports[0], dict) else {}
    first_patient = first_report.get("patient_info", {}) if isinstance(first_report.get("patient_info"), dict) else {}

    report_id = str(structured.get("report_id") or ocr_result.get("source_file") or "")
    sample_date = str(additional_info.get("report_date") or additional_info.get("sample_date") or "")
    sample_types = patient_info.get("specimen_types") or []
    if not isinstance(sample_types, list):
        sample_types = [str(sample_types)]
    sample_type_display = "分泌物"
    patient_phone = patient_info.get("phone") or first_patient.get("phone") or "—"
    submitting_unit = patient_info.get("hospital") or first_report.get("hospital_name") or ""
    clinical_diagnosis = (
        patient_info.get("clinical_diagnosis")
        or first_patient.get("clinical_diagnosis")
        or patient_info.get("specimen_condition")
        or "/"
    )
    p17_results = _build_p17_result_fields(tests)
    p17_summary = _p17_summary_fields(p17_results, p17_report)

    hpv_status = _first_text(
        p17_report.get("hpv_overall_status"),
        p17_report.get("hpv_summary"),
        p17_summary.get("hpv_overall_status"),
    )
    microecology_status = _first_text(
        p17_report.get("microecology_overall_status"),
        p17_report.get("microbiome_overall_status"),
        p17_summary.get("microecology_overall_status"),
    )
    risk_level = _first_text(
        p17_report.get("overall_risk_level"),
        p17_report.get("risk_level"),
        p17_summary.get("overall_risk_level"),
    )

    return {
        "case_id": f"case_{report_id or 'p17'}",
        "package_code": "P17",
        "patient": {
            "name": patient_info.get("name") or "",
            "gender": patient_info.get("gender") or "",
            "age": _age_display(patient_info.get("age")),
            "phone": patient_phone,
            "submitting_unit": submitting_unit,
            "symptoms": clinical_diagnosis,
            "hospital": submitting_unit,
            "specimen_condition": patient_info.get("specimen_condition") or "",
        },
        "report": {
            "report_id": report_id,
            "assessment_type": P17_REPORT_NAME,
            "method": P17_METHOD,
            "assessment_date": _date_display(sample_date),
            "sample_date": additional_info.get("sample_date") or "",
            "receive_date": additional_info.get("receive_date") or "",
            "report_date": additional_info.get("report_date") or "",
            "report_usage": "健康管理参考",
        },
        "sample": {
            "type": sample_type_display,
            "condition": patient_info.get("specimen_condition") or "—",
        },
        "lab_results": [_lab_result(test) for test in tests],
        "organization": {
            "phone": "400-158-1959",
            "email": "service@anweikang.com",
            "website": "www.anweikang.com",
            "address": "安徽省合肥市庐阳区临泉路7266号研发中心楼1、4、5、6层",
        },
        "p17": {
            **p17_results,
            "hpv_overall_status": hpv_status,
            "microecology_overall_status": microecology_status,
            "overall_risk_level": risk_level,
            "good_bacteria_status": p17_summary["good_bacteria_status"],
            "conditional_pathogen_status": p17_summary["conditional_pathogen_status"],
            "pathogen_status": p17_summary["pathogen_status"],
            "good_bacteria_focus_names": p17_summary["good_bacteria_focus_names"],
            "conditional_pathogen_focus_names": p17_summary["conditional_pathogen_focus_names"],
            "pathogen_focus_names": p17_summary["pathogen_focus_names"],
            "pathogen_analysis_status": p17_summary["pathogen_analysis_status"],
            "hpv_viral_load": p17_summary["hpv_viral_load"],
            "overall_summary": _first_text(
                p17_report.get("overall_summary"),
                p17_summary["overall_summary"],
            ),
            "hpv_detail_summary": _first_text(
                p17_report.get("hpv_detail_summary"),
                p17_summary["hpv_detail_summary"],
            ),
            "hpv_risk_tip": p17_summary["hpv_risk_tip"],
            "hpv_followup_tip": p17_summary["hpv_followup_tip"],
            "microbiome_detail_summary": _first_text(
                p17_report.get("microbiome_detail_summary"),
                p17_summary["microbiome_detail_summary"],
            ),
            "barrier_immune_summary": _first_text(
                p17_report.get("barrier_immune_summary"),
                p17_summary["barrier_immune_summary"],
            ),
            "good_bacteria_summary": p17_summary["good_bacteria_summary"],
            "conditional_pathogen_summary": p17_summary["conditional_pathogen_summary"],
            "pathogen_summary": p17_summary["pathogen_summary"],
            "hpv_management_current_status": _first_text(
                p17_report.get("hpv_management_current_status"),
                p17_summary["hpv_management_current_status"],
            ),
            "hpv_management_advice_1": "按年龄、既往筛查史和医生建议安排宫颈筛查与阶段复评。",
            "hpv_management_advice_2": "保持规范随访，必要时由专科医生进一步评估。",
            "hpv_management_advice_3": "关注生活方式管理，减少持续性感染相关风险因素。",
            "hpv_management_advice_4": "如有异常症状或既往异常结果，应及时结合临床检查处理。",
            "microecology_management_current_status": _first_text(
                p17_report.get("microecology_management_current_status"),
                p17_summary["microecology_management_current_status"],
            ),
            "microecology_management_advice_1": "根据检测结果和个体情况选择合适的益生菌或微生态支持方案。",
            "microecology_management_advice_2": "建议连续执行 4-8 周，并结合症状记录定期评估调整。",
            "microecology_management_advice_3": "如阳性项目较多或症状持续，建议携带原始报告咨询专科医生。",
            "microecology_management_advice_4": "使用温和护理方式，避免过度清洁，维持局部微生态稳定。",
            "lifestyle_advice_diet": "增加膳食纤维和发酵类食物摄入，减少高糖高脂饮食。",
            "diet_limit_advice": "减少高糖、高脂、辛辣刺激性食物摄入，观察分泌物和不适变化。",
            "lifestyle_advice_exercise": "每周保持规律有氧运动，支持代谢与免疫稳态。",
            "exercise_detail_advice": "可选择快走、瑜伽、游泳等中等强度运动，循序渐进执行。",
            "lifestyle_advice_routine": "规律作息，保证充足睡眠，减少长期熬夜和高压状态。",
            "local_care_advice": "选择棉质透气内衣，避免长时间潮湿闷热环境。",
            "local_care_followup": "建议结合复评结果持续跟踪菌群、症状与生活方式变化。",
            "infection_followup_advice": "出现异味、瘙痒、分泌物异常等情况时及时就医评估。",
            "nutrition_advice": "注意维生素、矿物质和优质蛋白摄入，支持免疫稳态。",
            "protein_advice": "优先选择鱼、蛋、奶、豆制品等优质蛋白来源，并结合自身耐受调整。",
            "caution_note": "本报告仅供健康管理参考，不构成诊断与治疗方案，如有不适请及时咨询专科医生。",
            "followup_advice": "建议按阶段执行干预与复评计划，并记录症状、生活方式和随访变化。",
            "disclaimer": "本报告仅供健康管理参考，不作为临床诊断依据。",
            "review_note": "健康管理师需结合原始报告、症状、妇科检查及随访资料进行人工复核。",
        },
        "ai_outputs": {
            "status": "pending",
            "note": "当前已完成P17模板工程化和基础字段接入，AI专项解读待结合真实OCR结构继续完善。",
        },
        "ocr_snapshot": {
            "source_file": ocr_result.get("source_file", ""),
            "strategy_version": ocr_result.get("strategy_version", ""),
            "provider": ocr_result.get("provider", ""),
            "warnings": ocr_result.get("warnings", []),
        },
        "version_lock": {
            "template_version": "P17-html-v0.6-page04-pathogen-status",
            "rule_version": "P17-rules-v0.1-draft",
            "prompt_version": "P17-prompts-v0.1",
            "ai_model": "deepseek-v4-flash",
            "ocr_strategy_version": ocr_result.get("strategy_version", ""),
            "ocr_provider": ocr_result.get("provider", ""),
        },
    }


def _build_p17_result_fields(tests: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    result_fields: dict[str, dict[str, Any]] = {}
    for subtype in (*P17_HPV_HIGH_RISK_TYPES, *P17_HPV_LOW_RISK_TYPES):
        key = f"hpv_{subtype}"
        result_fields[key] = _p17_indicator_from_tests(tests, f"HPV-{subtype}", aliases=(f"HPV{subtype}", f"HPV {subtype}"))

    for name, category in P17_MICROBE_TEMPLATE_ROWS:
        key = _p17_field_key_safe(name)
        aliases = P17_MICROBE_ALIASES.get(name, ())
        result_fields[key] = _p17_indicator_from_tests(tests, name, aliases=aliases, category=category)

    hpv_positive = _p17_positive_items(result_fields, prefix="hpv_")
    hpv_recognized = _p17_recognized_items(result_fields, prefix="hpv_")
    hpv_microbe_key = _p17_field_key_safe("人乳头瘤病毒（HPV）")
    result_fields[hpv_microbe_key] = {
        "name": "人乳头瘤病毒（HPV）",
        "result_display": "阳性" if hpv_positive else "阴性" if hpv_recognized else "未识别",
        "trend_display": "↑" if hpv_positive else "—",
        "category": "pathogen",
        "ct_value": "",
        "reference_range": "阴性",
        "method": P17_METHOD,
    }
    return result_fields


def _p17_indicator_from_tests(
    tests: list[dict[str, Any]],
    label: str,
    *,
    aliases: tuple[str, ...] = (),
    category: str = "",
) -> dict[str, Any]:
    test = _p17_find_test(tests, label, aliases)
    result_display = _p17_result_display(test) if test else "未识别"
    positive = _has_positive_result_signal(result_display)
    return {
        "name": label,
        "result_display": result_display,
        "trend_display": "↑" if positive else "—",
        "category": category or str(test.get("category") or "") if test else category,
        "ct_value": str(test.get("ct_value") or "") if test else "",
        "reference_range": str(test.get("reference_range") or "阴性") if test else "阴性",
        "method": str(test.get("method") or P17_METHOD) if test else P17_METHOD,
    }


def _p17_find_test(tests: list[dict[str, Any]], label: str, aliases: tuple[str, ...]) -> dict[str, Any]:
    candidates = (label, *aliases)
    keys = {_p17_field_key_safe(value) for value in candidates}
    normalized_candidates = {_p17_normalize_name(value) for value in candidates}
    for test in tests:
        test_name = str(test.get("test_name") or "")
        test_code = str(test.get("item_code") or "")
        if test_code in keys or _p17_field_key_safe(test_name) in keys:
            return test
        normalized_name = _p17_normalize_name(test_name)
        if normalized_name and normalized_name in normalized_candidates:
            return test
    return {}


def _p17_result_display(test: dict[str, Any]) -> str:
    raw_result = str(test.get("result") or "").strip()
    raw_indicator = str(test.get("indicator") or "").strip()
    text = f"{raw_result}{raw_indicator}"
    if "弱阳" in text:
        return "弱阳性"
    if "阳性" in text or "↑" in text:
        return "阳性"
    if "阴性" in text or "No Ct" in text or "NoCt" in text:
        return "阴性"
    return raw_result or "未识别"


def _p17_summary_fields(result_fields: dict[str, dict[str, Any]], p17_report: dict[str, Any]) -> dict[str, str]:
    hpv_positive = _p17_positive_items(result_fields, prefix="hpv_")
    hpv_high_positive = [item for item in hpv_positive if item["key"].replace("hpv_", "") in P17_HPV_HIGH_RISK_TYPES]
    hpv_recognized = _p17_recognized_items(result_fields, prefix="hpv_")

    good_positive = _p17_positive_items(result_fields, category="good")
    good_recognized = _p17_recognized_items(result_fields, category="good")
    conditional_positive = _p17_positive_items(result_fields, category="conditional")
    conditional_recognized = _p17_recognized_items(result_fields, category="conditional")
    pathogen_positive = _p17_positive_items(result_fields, category="pathogen")
    pathogen_recognized = _p17_recognized_items(result_fields, category="pathogen")

    good_status = "阳性" if good_positive else "阴性" if good_recognized else "未识别"
    conditional_status = "阳性" if conditional_positive else "阴性" if conditional_recognized else "未识别"
    pathogen_status = "阳性" if pathogen_positive else "阴性" if pathogen_recognized else "未识别"
    hpv_status = "阳性" if hpv_positive else "全阴" if hpv_recognized else "未识别"
    micro_status = "阳性" if conditional_positive or pathogen_positive else "阴性" if conditional_recognized or pathogen_recognized or good_recognized else "未识别"
    risk_level = "高风险" if pathogen_positive or hpv_high_positive else "需关注" if conditional_positive or hpv_positive else "低风险" if hpv_recognized or good_recognized else "待人工复核"
    good_focus_names = _p17_core_focus_names(good_positive, good_recognized)
    conditional_focus_names = _p17_core_focus_names(conditional_positive, conditional_recognized)
    pathogen_focus_names = _p17_core_focus_names(pathogen_positive, pathogen_recognized)
    pathogen_analysis_status = "需关注" if pathogen_positive else "整体状态：良好" if pathogen_recognized else "待复核"

    good_summary = _p17_group_summary(
        good_positive,
        good_recognized,
        positive_text="检出 {names} 等有益菌阳性，提示局部微生态存在有益菌基础，需结合条件致病菌和症状综合判断。",
        negative_text="本次未见明确有益菌阳性信号，建议结合原始报告和症状人工复核局部微生态稳定性。",
    )
    conditional_summary = _p17_group_summary(
        conditional_positive,
        conditional_recognized,
        positive_text="检出条件致病菌 {names} 阳性，提示微生态失衡或局部炎症风险需关注。",
        negative_text="本次未见模板覆盖的条件致病菌阳性信号，可继续关注生活方式、局部护理与阶段复评。",
    )
    pathogen_summary = _p17_group_summary(
        pathogen_positive,
        pathogen_recognized,
        positive_text="检出致病相关微生物 {names} 阳性，建议结合症状、妇科检查和原始报告进行专科评估。",
        negative_text="本次未见模板覆盖的致病菌阳性信号，仍建议结合症状和复评计划持续观察。",
    )
    hpv_detail = (
        f"本次检出 HPV 阳性型别：{_p17_names(hpv_positive)}，其中高危型别需重点结合宫颈筛查和医生建议复核。"
        if hpv_positive
        else "本次 HPV 27 种亚型未见阳性信号，建议继续保持规律宫颈筛查和长期随访。"
        if hpv_recognized
        else "当前未识别到 HPV 27 型别明细，请人工核对原始报告。"
    )
    hpv_viral_load = _p17_viral_load(p17_report)
    overall_summary = (
        f"综合评估显示 HPV 结果为{hpv_status}，阴道微生态结果为{micro_status}，综合风险等级为{risk_level}。"
        f"{_p17_focus_sentence(conditional_positive, pathogen_positive, hpv_positive)}"
    )

    return {
        "hpv_overall_status": hpv_status,
        "microecology_overall_status": micro_status,
        "overall_risk_level": risk_level,
        "good_bacteria_status": good_status,
        "conditional_pathogen_status": conditional_status,
        "pathogen_status": pathogen_status,
        "good_bacteria_focus_names": good_focus_names,
        "conditional_pathogen_focus_names": conditional_focus_names,
        "pathogen_focus_names": pathogen_focus_names,
        "pathogen_analysis_status": pathogen_analysis_status,
        "hpv_viral_load": hpv_viral_load,
        "overall_summary": overall_summary,
        "hpv_detail_summary": hpv_detail,
        "hpv_risk_tip": "目前未检出HPV感染相关信号。" if not hpv_positive and hpv_recognized else "HPV阳性结果需结合宫颈筛查、既往病史和医生建议综合评估。",
        "hpv_followup_tip": "建议保持良好生活方式，定期进行妇科检查和HPV检测。",
        "microbiome_detail_summary": "；".join([good_summary, conditional_summary, pathogen_summary]),
        "barrier_immune_summary": "阴道微生态状态与局部屏障、免疫稳态密切相关，建议结合菌群结果、症状和生活方式记录进行人工复核。",
        "good_bacteria_summary": good_summary,
        "conditional_pathogen_summary": conditional_summary,
        "pathogen_summary": pathogen_summary,
        "hpv_management_current_status": "未见HPV阳性型别。" if not hpv_positive and hpv_recognized else f"需关注 HPV 阳性型别：{_p17_names(hpv_positive)}。" if hpv_positive else "待结合HPV专项结果人工复核。",
        "microecology_management_current_status": "需关注条件致病菌或致病菌阳性项目。" if conditional_positive or pathogen_positive else "当前微生态阳性风险未见明确升高。" if good_recognized or conditional_recognized else "待结合微生态专项结果人工复核。",
    }


def _p17_group_summary(positive_items: list[dict[str, str]], recognized_items: list[dict[str, str]], *, positive_text: str, negative_text: str) -> str:
    if positive_items:
        return positive_text.format(names=_p17_names(positive_items))
    if recognized_items:
        return negative_text
    return "当前未识别到该组微生态明细，请人工核对原始报告。"


def _p17_positive_items(result_fields: dict[str, dict[str, Any]], *, prefix: str = "", category: str = "") -> list[dict[str, str]]:
    items: list[dict[str, str]] = []
    for key, item in result_fields.items():
        if prefix and not key.startswith(prefix):
            continue
        if category and item.get("category") != category:
            continue
        if _has_positive_result_signal(item.get("result_display")):
            items.append({"key": key, "name": str(item.get("name") or key)})
    return items


def _p17_recognized_items(result_fields: dict[str, dict[str, Any]], *, prefix: str = "", category: str = "") -> list[dict[str, str]]:
    items: list[dict[str, str]] = []
    for key, item in result_fields.items():
        if prefix and not key.startswith(prefix):
            continue
        if category and item.get("category") != category:
            continue
        value = str(item.get("result_display") or "")
        if value and value not in {"未识别", "待复核"}:
            items.append({"key": key, "name": str(item.get("name") or key)})
    return items


def _p17_names(items: list[dict[str, str]], *, limit: int = 8) -> str:
    names = [item["name"] for item in items if item.get("name")]
    if not names:
        return "无"
    suffix = "等" if len(names) > limit else ""
    return "、".join(names[:limit]) + suffix


def _p17_core_focus_names(positive_items: list[dict[str, str]], recognized_items: list[dict[str, str]]) -> str:
    if positive_items:
        return _p17_names(positive_items, limit=4)
    if recognized_items:
        return "未见阳性"
    return "待复核"


def _p17_focus_sentence(
    conditional_positive: list[dict[str, str]],
    pathogen_positive: list[dict[str, str]],
    hpv_positive: list[dict[str, str]],
) -> str:
    focus: list[str] = []
    if hpv_positive:
        focus.append(f"HPV阳性型别 {_p17_names(hpv_positive, limit=3)}")
    if conditional_positive:
        focus.append(f"条件致病菌 {_p17_names(conditional_positive, limit=3)}")
    if pathogen_positive:
        focus.append(f"致病相关微生物 {_p17_names(pathogen_positive, limit=3)}")
    if not focus:
        return "当前未见模板覆盖的阳性风险项目，建议继续按周期复评。"
    return "建议重点关注" + "、".join(focus) + "，并结合症状和原始报告人工复核。"


def _p17_viral_load(p17_report: dict[str, Any]) -> str:
    reports = p17_report.get("reports", []) if isinstance(p17_report.get("reports"), list) else []
    for report in reports:
        if isinstance(report, dict) and report.get("viral_load"):
            return str(report.get("viral_load") or "")
    return "阴性"


def _p17_field_key_safe(value: str) -> str:
    key = re.sub(r"[^0-9A-Za-z\u4e00-\u9fff]+", "_", str(value or "").lower())
    return key.strip("_")


def _p17_normalize_name(value: str) -> str:
    return re.sub(r"[\s_\-（）()]+", "", str(value or "").lower())


def _first_text(*values: Any) -> str:
    for value in values:
        text = str(value or "").strip()
        if text:
            return text
    return ""


def _normalize_p05_ocr_result(ocr_result: dict[str, Any]) -> dict[str, Any]:
    structured = ocr_result.get("structured_report")
    if isinstance(structured, dict) and structured.get("tests"):
        return ocr_result
    if not isinstance(ocr_result.get("report_info"), dict) or not isinstance(ocr_result.get("test_results"), list):
        return ocr_result

    report_info = ocr_result.get("report_info", {})
    patient_info = ocr_result.get("patient_info", {}) if isinstance(ocr_result.get("patient_info"), dict) else {}
    specimen_dates = ocr_result.get("specimen_dates", {}) if isinstance(ocr_result.get("specimen_dates"), dict) else {}
    laboratory_info = ocr_result.get("laboratory_info", {}) if isinstance(ocr_result.get("laboratory_info"), dict) else {}

    reports: list[dict[str, Any]] = []
    tests: list[dict[str, Any]] = []
    for result_group in ocr_result.get("test_results", []):
        if not isinstance(result_group, dict):
            continue
        page = int(result_group.get("page") or 0)
        test_items: list[dict[str, Any]] = []
        for raw_item in result_group.get("test_items", []):
            if not isinstance(raw_item, dict):
                continue
            item = {
                "item_code": _p05_item_code_from_name(str(raw_item.get("test_name") or "")),
                "test_name": str(raw_item.get("test_name") or ""),
                "result": str(raw_item.get("result") or ""),
                "hint": str(raw_item.get("indicator") or ""),
                "reference_range": str(raw_item.get("reference_range") or ""),
                "unit": str(raw_item.get("unit") or ""),
                "method": str(raw_item.get("method") or ""),
            }
            test_items.append(item)
            tests.append(
                {
                    "page": page,
                    "specimen_type": _p05_professional_specimen_type(patient_info, page),
                    "test_name": item["test_name"],
                    "item_code": item["item_code"],
                    "result": item["result"],
                    "indicator": item["hint"],
                    "reference_range": item["reference_range"],
                    "unit": item["unit"],
                    "method": item["method"],
                }
            )
        reports.append(
            {
                "page": page,
                "barcode": str(report_info.get("barcode") or ""),
                "basic_info": {
                    "name": str(patient_info.get("name") or ""),
                    "gender": str(patient_info.get("gender") or ""),
                    "age": patient_info.get("age") or "",
                    "clinical_diagnosis": str(patient_info.get("clinical_diagnosis") or ""),
                    "submitting_institution": str(patient_info.get("submitter") or ""),
                    "specimen_status": str(patient_info.get("specimen_status") or ""),
                    "specimen_type": _p05_professional_specimen_type(patient_info, page),
                    "patient_id": str(patient_info.get("patient_id") or ""),
                    "bed_no": str(patient_info.get("bed_no") or ""),
                    "submitting_department": str(patient_info.get("department") or ""),
                    "submitting_doctor": str(patient_info.get("doctor") or ""),
                },
                "test_items": test_items,
                "sampling_datetime": str(specimen_dates.get("sampling_datetime") or ""),
                "receiving_datetime": str(specimen_dates.get("receiving_datetime") or ""),
                "report_datetime": _p05_professional_report_datetime(specimen_dates.get("report_datetime"), page),
            }
        )

    normalized = dict(ocr_result)
    normalized["structured_report"] = {
        "report_id": str(report_info.get("barcode") or ocr_result.get("source_file") or ""),
        "patient_info": {
            "name": str(patient_info.get("name") or ""),
            "gender": str(patient_info.get("gender") or ""),
            "age": patient_info.get("age") or "",
            "specimen_condition": str(patient_info.get("specimen_status") or ""),
            "specimen_types": [
                value
                for value in [
                    str(patient_info.get("specimen_type_page1_2") or ""),
                    str(patient_info.get("specimen_type_page3") or ""),
                    str(patient_info.get("specimen_type_page4") or ""),
                ]
                if value
            ],
            "hospital": str(patient_info.get("submitter") or ""),
            "patient_number": str(patient_info.get("patient_id") or ""),
            "bed_number": str(patient_info.get("bed_no") or ""),
            "department": str(patient_info.get("department") or ""),
            "doctor": str(patient_info.get("doctor") or ""),
            "clinical_diagnosis": str(patient_info.get("clinical_diagnosis") or ""),
        },
        "tests": tests,
        "notes": str(ocr_result.get("note") or ""),
        "additional_info": {
            "sample_date": str(specimen_dates.get("sampling_datetime") or ""),
            "receive_date": str(specimen_dates.get("receiving_datetime") or ""),
            "report_date": _p05_latest_report_datetime(specimen_dates.get("report_datetime")),
        },
        "p05_extracted_report": {
            "report_overview": {
                "website": str(laboratory_info.get("website") or ""),
                "phone": str(laboratory_info.get("phone") or ""),
                "address": str(laboratory_info.get("address") or ""),
                "disclaimer": str(ocr_result.get("note") or ""),
            },
            "reports": reports,
        },
    }
    normalized.setdefault("provider", "professional-ocr-json")
    normalized.setdefault("strategy_version", "P05-professional-json-adapter-v0.1")
    return normalized


def _p05_item_code_from_name(name: str) -> str:
    normalized = re.sub(r"[\s（）()\-_/]+", "", str(name or "")).lower()
    mappings = [
        ("methoxytyramine", ["3甲氧基酪胺"]),
        ("metanephrine_n", ["3甲氧基去甲肾上腺素"]),
        ("metanephrine_e", ["3甲氧基肾上腺素"]),
        ("norepinephrine", ["去甲肾上腺素"]),
        ("epinephrine", ["肾上腺素"]),
        ("dopamine", ["多巴胺"]),
        ("hva", ["hva", "高香草酸"]),
        ("vma", ["vma", "香草扁桃酸"]),
        ("acth", ["acth", "促肾上腺皮质激素"]),
        ("cort", ["cort", "皮质醇"]),
        ("ft3", ["ft3", "游离三碘甲状腺原氨酸"]),
        ("ft4", ["ft4", "游离甲状腺素"]),
        ("tsh", ["tsh", "促甲状腺激素"]),
        ("tgab", ["tgab", "抗甲状腺球蛋白抗体"]),
        ("tpoab", ["tpoab", "抗甲状腺过氧化物酶抗体"]),
        ("t3", ["t3", "三碘甲状腺原氨酸"]),
        ("t4", ["t4", "甲状腺素"]),
    ]
    for code, keywords in mappings:
        if any(keyword.lower() in normalized for keyword in keywords):
            return code
    return ""


def _p05_professional_specimen_type(patient_info: dict[str, Any], page: int) -> str:
    if page in {1, 2}:
        return str(patient_info.get("specimen_type_page1_2") or "")
    if page == 3:
        return str(patient_info.get("specimen_type_page3") or "")
    if page == 4:
        return str(patient_info.get("specimen_type_page4") or "")
    return ""


def _p05_professional_report_datetime(value: Any, page: int) -> str:
    if isinstance(value, dict):
        if page in {1, 2}:
            return str(value.get("page1_2") or "")
        return str(value.get(f"page{page}") or "")
    return str(value or "")


def _p05_latest_report_datetime(value: Any) -> str:
    if isinstance(value, dict):
        values = [str(item or "") for item in value.values() if item]
        return max(values) if values else ""
    return str(value or "")


def _build_p05_report_data_legacy(ocr_result: dict[str, Any]) -> dict[str, Any]:
    ocr_result = _normalize_p05_ocr_result(ocr_result)
    structured = ocr_result.get("structured_report", {})
    patient_info = structured.get("patient_info", {})
    additional_info = structured.get("additional_info", {})
    tests = structured.get("tests", [])
    p05_report = structured.get("p05_extracted_report", {})
    report_overview = p05_report.get("report_overview", {}) if isinstance(p05_report, dict) else {}
    reports = p05_report.get("reports", []) if isinstance(p05_report, dict) else []
    first_report = reports[0] if isinstance(reports, list) and reports else {}
    first_basic = first_report.get("basic_info", {}) if isinstance(first_report, dict) else {}

    report_id = str(first_report.get("barcode") or structured.get("report_id") or ocr_result.get("source_file") or "")
    sample_date = str(additional_info.get("report_date") or additional_info.get("sample_date") or first_report.get("report_datetime") or "")
    sample_types = patient_info.get("specimen_types") or []
    if not isinstance(sample_types, list):
        sample_types = [str(sample_types)]
    health_score = _p05_health_score(tests)
    health_score_status = _p05_health_score_status(health_score)
    p05_sections = _p05_sections(tests, health_score=health_score, health_score_status=health_score_status)

    return {
        "case_id": f"case_{report_id or 'p05'}",
        "package_code": "P05",
        "patient": {
            "name": first_basic.get("name") or patient_info.get("name") or "",
            "gender": first_basic.get("gender") or patient_info.get("gender") or "",
            "age": _age_display(first_basic.get("age") or patient_info.get("age")),
            "phone": "—",
            "symptoms": first_basic.get("clinical_diagnosis") or patient_info.get("clinical_diagnosis") or "/",
            "hospital": first_basic.get("submitting_institution") or patient_info.get("hospital") or "",
            "specimen_condition": patient_info.get("specimen_condition") or "",
        },
        "report": {
            "report_id": report_id,
            "assessment_type": "压力激素与睡眠状态评估管理报告",
            "method": "化学发光&LC-MS/MS法",
            "assessment_date": _date_display(sample_date),
            "sample_date": sample_date,
            "receive_date": additional_info.get("receive_date") or "",
            "report_date": additional_info.get("report_date") or "",
        },
        "sample": {
            "type": "EDTA抗凝血浆/血清",
            "condition": patient_info.get("specimen_condition") or "—",
        },
        "lab_results": [_lab_result(test) for test in tests],
        "organization": {
            "phone": report_overview.get("phone") or "400-158-1959",
            "email": "service@anweikang.com",
            "website": report_overview.get("website") or "www.anweikang.com",
            "address": "合肥市庐阳区临泉路7266号安创大楼1、4、5、6层",
        },
        "p05": {
            "health_score": health_score,
            "health_score_status": health_score_status,
            **p05_sections,
            "followup_advice": "建议按阶段执行生活方式干预，并结合复评与专业随访持续观察。",
            "disclaimer": report_overview.get("disclaimer") or "本报告仅供健康管理参考，不作为临床诊断依据。",
        },
        "ai_outputs": {
            "status": "pending",
            "note": "当前已基于P05 OCR结构化检验结果生成报告预览；AI解读完成后将覆盖对应辅助诊断字段。",
        },
        "ocr_snapshot": {
            "source_file": ocr_result.get("source_file", ""),
            "strategy_version": ocr_result.get("strategy_version", ""),
            "provider": ocr_result.get("provider", ""),
            "warnings": ocr_result.get("warnings", []),
        },
        "version_lock": {
            "template_version": "P05-html-v0.1",
            "rule_version": "P05-rules-v0.1-draft",
            "prompt_version": "P05-prompts-v0.1",
            "ai_model": "deepseek-v4-flash",
            "ocr_strategy_version": ocr_result.get("strategy_version", ""),
            "ocr_provider": ocr_result.get("provider", ""),
        },
    }

def _build_p05_report_data(ocr_result: dict[str, Any]) -> dict[str, Any]:
    ocr_result = _normalize_p05_ocr_result(ocr_result)
    structured = ocr_result.get("structured_report", {})
    patient_info = structured.get("patient_info", {})
    additional_info = structured.get("additional_info", {})
    tests = structured.get("tests", [])
    p05_report = structured.get("p05_extracted_report", {})
    report_overview = p05_report.get("report_overview", {}) if isinstance(p05_report, dict) else {}
    reports = p05_report.get("reports", []) if isinstance(p05_report, dict) else []
    first_report = reports[0] if isinstance(reports, list) and reports else {}
    first_basic = first_report.get("basic_info", {}) if isinstance(first_report, dict) else {}

    report_id = str(first_report.get("barcode") or structured.get("report_id") or ocr_result.get("source_file") or "")
    sample_date = str(additional_info.get("report_date") or additional_info.get("sample_date") or first_report.get("report_datetime") or "")
    sample_types = patient_info.get("specimen_types") or []
    if not isinstance(sample_types, list):
        sample_types = [str(sample_types)]
    health_score = _p05_health_score(tests)
    health_score_status = _p05_health_score_status(health_score)
    p05_sections = _p05_sections(tests, health_score=health_score, health_score_status=health_score_status)

    return {
        "case_id": f"case_{report_id or 'p05'}",
        "package_code": "P05",
        "patient": {
            "name": first_basic.get("name") or patient_info.get("name") or "",
            "gender": first_basic.get("gender") or patient_info.get("gender") or "",
            "age": _age_display(first_basic.get("age") or patient_info.get("age")),
            "phone": "—",
            "symptoms": first_basic.get("clinical_diagnosis") or patient_info.get("clinical_diagnosis") or "/",
            "hospital": first_basic.get("submitting_institution") or patient_info.get("hospital") or "",
            "specimen_condition": patient_info.get("specimen_condition") or "",
        },
        "report": {
            "report_id": report_id,
            "assessment_type": "压力激素与睡眠状态评估管理报告",
            "method": "化学发光&LC-MS/MS法",
            "assessment_date": _date_display(sample_date),
            "sample_date": sample_date,
            "receive_date": additional_info.get("receive_date") or "",
            "report_date": additional_info.get("report_date") or "",
        },
        "sample": {
            "type": "EDTA抗凝血浆/血清",
            "condition": patient_info.get("specimen_condition") or "—",
        },
        "lab_results": [_lab_result(test) for test in tests],
        "organization": {
            "phone": report_overview.get("phone") or "400-158-1959",
            "email": "service@anweikang.com",
            "website": report_overview.get("website") or "www.anweikang.com",
            "address": "合肥市庐阳区临泉路7266号安创大楼1、4、5、6层",
        },
        "p05": {
            "health_score": health_score,
            "health_score_status": health_score_status,
            **p05_sections,
            "followup_advice": "建议按阶段执行生活方式干预，并结合复评与专业随访持续观察。",
            "disclaimer": report_overview.get("disclaimer") or "本报告仅供健康管理参考，不作为临床诊断依据。",
        },
        "ai_outputs": {
            "status": "pending",
            "note": "当前已基于P05 OCR结构化检验结果生成报告预览；AI解读完成后将覆盖对应辅助诊断字段。",
        },
        "ocr_snapshot": {
            "source_file": ocr_result.get("source_file", ""),
            "strategy_version": ocr_result.get("strategy_version", ""),
            "provider": ocr_result.get("provider", ""),
            "warnings": ocr_result.get("warnings", []),
        },
        "version_lock": {
            "template_version": "P05-html-v0.2",
            "rule_version": "P05-rules-v0.2-score-linked",
            "prompt_version": "P05-prompts-v0.1",
            "ai_model": "deepseek-v4-flash",
            "ocr_strategy_version": ocr_result.get("strategy_version", ""),
            "ocr_provider": ocr_result.get("provider", ""),
        },
    }


def _p05_health_score(tests: list[dict[str, Any]]) -> int:
    available_tests = [test for test in tests if str(test.get("test_name") or "").strip()]
    if not available_tests:
        return 72

    score = 96
    expected_count = 17
    missing_count = max(0, expected_count - len(available_tests))
    score -= min(missing_count, 8)

    for test in available_tests:
        abnormal_level = _p05_abnormal_level(test)
        if abnormal_level <= 0:
            continue
        score -= _p05_test_weight(str(test.get("test_name") or ""))
        if abnormal_level >= 2:
            score -= 2

    return max(48, min(98, int(round(score))))


def _p05_health_score_status(score: int) -> str:
    if score >= 90:
        return "优秀"
    if score >= 80:
        return "良好"
    if score >= 70:
        return "需关注"
    return "重点干预"


P05_INDICATOR_DEFINITIONS = {
    "acth": ("促肾上腺皮质激素（ACTH）", ["ACTH", "促肾上腺皮质激素"], "1.59--13.98", "pmol/L"),
    "cort": ("皮质醇（CORT）", ["CORT", "皮质醇"], "125.5--574.4", "nmol/L"),
    "norepinephrine": ("去甲肾上腺素", ["去甲肾上腺素"], "卧位：0.41--4.43；立位：0.88--6.73", "nmol/L"),
    "epinephrine": ("肾上腺素", ["肾上腺素"], "卧位：≤0.61；立位：≤1.37", "nmol/L"),
    "metanephrine_n": ("3-甲氧基去甲肾上腺素", ["3-甲氧基去甲肾上腺素"], "<0.90", "nmol/L"),
    "methoxytyramine": ("3-甲氧基酪胺", ["3-甲氧基酪胺"], "0.00--0.11", "nmol/L"),
    "metanephrine_e": ("3-甲氧基肾上腺素", ["3-甲氧基肾上腺素"], "<0.50", "nmol/L"),
    "hva": ("高香草酸（HVA）", ["HVA", "高香草酸"], "<182", "nmol/L"),
    "vma": ("香草扁桃酸（VMA）", ["VMA", "香草扁桃酸"], "<101", "nmol/L"),
    "dopamine": ("多巴胺", ["多巴胺"], "<0.20", "nmol/L"),
    "ft3": ("游离三碘甲状腺原氨酸（FT3）", ["FT3", "游离三碘甲状腺原氨酸"], "2.69--5.85", "pmol/L"),
    "t3": ("三碘甲状腺原氨酸（T3）", ["T3", "三碘甲状腺原氨酸"], "0.77--2.41", "nmol/L"),
    "ft4": ("游离甲状腺素（FT4）", ["FT4", "游离甲状腺素"], "9.14--19.3", "pmol/L"),
    "t4": ("甲状腺素（T4）", ["T4", "甲状腺素"], "62.29--150.84", "nmol/L"),
    "tsh": ("促甲状腺激素（TSH）", ["TSH", "促甲状腺激素"], "0.28--4.3", "mIU/L"),
    "tgab": ("抗甲状腺球蛋白抗体（TGAb）", ["TGAb", "抗甲状腺球蛋白抗体"], "<4.11", "IU/ml"),
    "tpoab": ("抗甲状腺过氧化物酶抗体（TPOAb）", ["TPOAb", "抗甲状腺过氧化物酶抗体"], "<5.63", "IU/mL"),
}


def _p05_sections(
    tests: list[dict[str, Any]],
    *,
    health_score: int,
    health_score_status: str,
) -> dict[str, Any]:
    indicators = {code: _p05_indicator(tests, code) for code in P05_INDICATOR_DEFINITIONS}
    abnormal_items = [item for item in indicators.values() if item["status"] != "正常" and item["status"] != "未识别"]
    missing_items = [item for item in indicators.values() if item["status"] == "未识别"]

    hpa = {
        "acth": indicators["acth"],
        "cort": indicators["cort"],
        "acth_summary": _p05_indicator_sentence(indicators["acth"]),
        "cort_summary": _p05_indicator_sentence(indicators["cort"]),
        "interpretation": _p05_hpa_interpretation(indicators["acth"], indicators["cort"]),
    }
    catecholamine_codes = [
        "norepinephrine",
        "epinephrine",
        "metanephrine_n",
        "methoxytyramine",
        "metanephrine_e",
        "hva",
        "vma",
        "dopamine",
    ]
    catecholamine = {
        code: indicators[code]
        for code in catecholamine_codes
    }
    catecholamine["interpretation"] = _p05_group_interpretation(
        [indicators[code] for code in catecholamine_codes],
        "儿茶酚胺及其代谢产物",
        "交感神经系统和应激反应水平整体平稳",
    )
    metabolism = {
        "hva": indicators["hva"],
        "vma": indicators["vma"],
        "interpretation": _p05_group_interpretation(
            [indicators["hva"], indicators["vma"]],
            "HVA 和 VMA",
            "儿茶酚胺代谢效率良好，神经递质代谢相对平衡",
        ),
    }
    thyroid_codes = ["ft3", "t3", "ft4", "t4", "tsh", "tgab", "tpoab"]
    thyroid = {
        code: indicators[code]
        for code in thyroid_codes
    }
    thyroid["interpretation"] = _p05_group_interpretation(
        [indicators[code] for code in thyroid_codes],
        "甲状腺功能相关指标",
        "甲状腺功能与代谢基础整体稳定",
    )
    sleep = {
        "interpretation": _p05_sleep_interpretation(hpa, catecholamine),
        "advice": "建议保持规律作息、固定起床时间，并结合放松训练持续观察睡眠质量变化。",
    }

    if abnormal_items:
        focus = "、".join(item["name"] for item in abnormal_items[:4])
        overall_summary = f"本次P05共识别到 {len([item for item in indicators.values() if item['status'] != '未识别'])} 项检验结果，健康评分为{health_score}分（{health_score_status}）。需重点关注 {focus}。"
        risk_assessment = f"{focus} 出现参考范围外或异常提示，建议结合采样时间、体位、近期压力和睡眠状态进行人工复核。"
    else:
        overall_summary = f"本次P05共识别到 {len([item for item in indicators.values() if item['status'] != '未识别'])} 项检验结果，健康评分为{health_score}分（{health_score_status}），压力轴、儿茶酚胺、甲状腺及睡眠相关生物标志物整体平稳。"
        risk_assessment = "未见明确异常提示；若存在持续疲劳、睡眠差或压力感升高，仍建议结合主诉和生活方式记录进行人工复核。"

    if missing_items:
        missing = "、".join(item["name"] for item in missing_items[:4])
        risk_assessment += f" 当前未识别到 {missing} 等项目，请核对OCR结果或原始报告。"

    return {
        "overall_summary": overall_summary,
        "risk_assessment": risk_assessment,
        "hpa": hpa,
        "catecholamine": catecholamine,
        "metabolism": metabolism,
        "thyroid": thyroid,
        "sleep": sleep,
        "diet_advice": "建议优先保证规律三餐，增加深色蔬菜、优质蛋白、坚果和全谷物摄入，为神经递质合成和压力恢复提供营养支持。",
        "lifestyle_advice": "建议保持固定睡眠窗口，每周进行规律中等强度运动，并安排呼吸放松或正念练习，帮助稳定压力反应和睡眠节律。",
    }


def _p05_indicator(tests: list[dict[str, Any]], code: str) -> dict[str, Any]:
    name, keywords, default_reference, default_unit = P05_INDICATOR_DEFINITIONS[code]
    test = _find_test_by_code(tests, code) or _find_test_any(tests, keywords)
    result = str(test.get("result") or test.get("result_display") or "").strip() if test else ""
    unit = str(test.get("unit") or default_unit or "").strip() if test else default_unit
    raw_reference = str(test.get("reference_range") or "").strip() if test else ""
    reference = _p05_indicator_reference(code, raw_reference, default_reference)
    status_test = {**test, "reference_range": reference} if test else None
    status = _p05_indicator_status(status_test) if status_test else "未识别"
    result_display = _p05_value_with_unit(result, unit) if result else "未识别"
    reference_display = _p05_reference_display(reference, unit)
    return {
        "code": code,
        "name": name,
        "result": result,
        "unit": unit,
        "result_display": result_display,
        "reference_range": reference,
        "reference_display": reference_display,
        "status": status,
        "summary": f"{name}：{result_display}，{reference_display}，结果{status}。",
    }


def _p05_indicator_reference(code: str, reference: str, default_reference: str) -> str:
    text = str(reference or "").strip()
    if not text:
        return default_reference

    normalized = re.sub(r"\s+", "", text)
    normalized = normalized.replace("＜", "<").replace("＞", ">")
    normalized = normalized.replace("－", "-").replace("—", "-").replace("–", "-")

    if code in {"tgab", "tpoab"} and re.fullmatch(r"\d+(?:\.\d+)?", normalized):
        return default_reference
    return normalized


def _p05_indicator_status(test: dict[str, Any]) -> str:
    indicator = str(test.get("indicator") or "")
    if "↑" in indicator:
        return "偏高"
    if "↓" in indicator:
        return "偏低"
    value = _safe_float(test.get("result") or test.get("result_display"))
    if value is None:
        return "需复核"
    deviation = _p05_reference_deviation(value, str(test.get("reference_range") or ""))
    if deviation <= 0:
        return "正常"
    reference = str(test.get("reference_range") or "")
    bounds = _p05_parse_reference_bounds(reference)
    if bounds:
        for lower, upper in bounds:
            if lower is not None and value < lower:
                return "偏低"
            if upper is not None and value > upper:
                return "偏高"
    return "需复核"


def _p05_value_with_unit(value: str, unit: str) -> str:
    text = str(value or "").strip()
    if not text:
        return "未识别"
    unit_text = str(unit or "").strip()
    if unit_text and unit_text not in text:
        return f"{text} {unit_text}"
    return text


def _p05_reference_display(reference: str, unit: str) -> str:
    text = str(reference or "").strip()
    if not text:
        return "参考范围：未识别"
    unit_text = str(unit or "").strip()
    if unit_text and unit_text not in text:
        return f"参考范围：{text} {unit_text}"
    return f"参考范围：{text}"


def _p05_indicator_sentence(item: dict[str, Any]) -> str:
    return str(item.get("summary") or f"{item.get('name', '指标')}：未识别，请人工复核原始报告。")


def _p05_group_interpretation(items: list[dict[str, Any]], label: str, normal_text: str) -> str:
    recognized = [item for item in items if item.get("status") != "未识别"]
    abnormal = [item for item in recognized if item.get("status") not in {"正常", ""}]
    if not recognized:
        return f"未识别到{label}的有效检验结果，请人工核对原始报告。"
    if abnormal:
        focus = "、".join(f"{item['name']}{item['status']}" for item in abnormal[:4])
        return f"{label}中 {focus}，提示该分组存在需关注变化，建议结合临床信息和采样条件复核。"
    return f"{label}均处于参考范围内，提示{normal_text}。"


def _p05_hpa_interpretation(acth: dict[str, Any], cort: dict[str, Any]) -> str:
    return _p05_group_interpretation([acth, cort], "ACTH 与 CORT", "HPA 轴基础应激调节能力较稳定")


def _p05_sleep_interpretation(hpa: dict[str, Any], catecholamine: dict[str, Any]) -> str:
    items: list[dict[str, Any]] = [hpa["acth"], hpa["cort"]]
    items.extend(
        value
        for key, value in catecholamine.items()
        if isinstance(value, dict) and key in {"norepinephrine", "epinephrine", "dopamine"}
    )
    return _p05_group_interpretation(items, "压力轴与睡眠相关生物标志物", "压力反应与睡眠节律支持基础较平稳")


def _p05_abnormal_level(test: dict[str, Any]) -> int:
    indicator = str(test.get("indicator") or "")
    if "↑" in indicator or "↓" in indicator:
        return 2

    value = _safe_float(test.get("result"))
    if value is None:
        return 0

    deviation = _p05_reference_deviation(value, str(test.get("reference_range") or ""))
    if deviation <= 0:
        return 0
    if deviation >= 0.25:
        return 2
    return 1


def _p05_reference_deviation(value: float, reference_range: str) -> float:
    reference = str(reference_range or "").strip()
    if not reference:
        return 0.0

    bounds = _p05_parse_reference_bounds(reference)
    if not bounds:
        return 0.0

    smallest_deviation: float | None = None
    for lower, upper in bounds:
        if lower is not None and upper is not None and lower <= value <= upper:
            return 0.0
        if lower is None and upper is not None and value <= upper:
            return 0.0
        if upper is None and lower is not None and value >= lower:
            return 0.0

        if lower is not None and value < lower:
            deviation = (lower - value) / max(abs(lower), 1.0)
        elif upper is not None and value > upper:
            deviation = (value - upper) / max(abs(upper), 1.0)
        else:
            deviation = 0.0

        if smallest_deviation is None or deviation < smallest_deviation:
            smallest_deviation = deviation

    return smallest_deviation or 0.0


def _p05_parse_reference_bounds(reference_range: str) -> list[tuple[float | None, float | None]]:
    text = str(reference_range or "")
    text = text.replace("～", "-").replace("—", "-").replace("–", "-").replace("至", "-")
    text = re.sub(r"\d{1,2}:\d{2}(?:\s*-\s*\d{1,2}:\d{2})?", " ", text)

    bounds: list[tuple[float | None, float | None]] = []

    upper_matches = re.findall(r"(?:<=|≤|<)\s*(\d+(?:\.\d+)?)", text)
    for match in upper_matches:
        bounds.append((None, float(match)))

    lower_matches = re.findall(r"(?:>=|≥|>)\s*(\d+(?:\.\d+)?)", text)
    for match in lower_matches:
        bounds.append((float(match), None))

    range_matches = re.findall(r"(\d+(?:\.\d+)?)\s*(?:--|-|~)\s*(\d+(?:\.\d+)?)", text)
    for lower_text, upper_text in range_matches:
        lower = float(lower_text)
        upper = float(upper_text)
        if lower <= upper:
            bounds.append((lower, upper))
        else:
            bounds.append((upper, lower))

    return bounds


def _p05_test_weight(test_name: str) -> int:
    name = str(test_name or "").upper()
    if "ACTH" in name or "促肾上腺皮质激素" in test_name:
        return 9
    if "CORT" in name or "皮质醇" in test_name:
        return 9
    if "TSH" in name or "促甲状腺激素" in test_name:
        return 8
    if "FT3" in name or "FT4" in name or "游离三碘甲状腺原氨酸" in test_name or "游离甲状腺素" in test_name:
        return 7
    if "TGAB" in name or "TPOAB" in name or "抗甲状腺" in test_name:
        return 6
    if any(keyword in test_name for keyword in ("去甲肾上腺素", "肾上腺素", "多巴胺", "甲氧基")):
        return 5
    if "VMA" in name or "HVA" in name or any(keyword in test_name for keyword in ("香草扁桃酸", "高香草酸")):
        return 4
    if any(keyword in name for keyword in ("T3", "T4")) or any(keyword in test_name for keyword in ("三碘甲状腺原氨酸", "甲状腺素")):
        return 5
    return 4


def _build_p01_report_data(ocr_result: dict[str, Any]) -> dict[str, Any]:
    structured = ocr_result.get("structured_report", {})
    patient_info = structured.get("patient_info", {})
    additional_info = structured.get("additional_info", {})
    tests = structured.get("tests", [])
    p01_report = structured.get("p01_extracted_report", {})
    basic_information = p01_report.get("basic_information", {}) if isinstance(p01_report, dict) else {}
    result_overview = p01_report.get("result_overview", {}) if isinstance(p01_report, dict) else {}
    report_summary = p01_report.get("report_summary", {}) if isinstance(p01_report, dict) else {}
    microbial_composition = p01_report.get("microbial_composition", {}) if isinstance(p01_report, dict) else {}
    abnormal_flora = report_summary.get("abnormal_flora", {}) if isinstance(report_summary, dict) else {}
    disease_analysis = report_summary.get("disease_analysis", []) if isinstance(report_summary, dict) else []
    recommendation_copy = _p01_compact_recommendations(report_summary, result_overview, enterotype=None)

    report_id = str(basic_information.get("sample_id") or structured.get("report_id") or ocr_result.get("source_file") or "")
    sample_date = str(additional_info.get("sample_date") or basic_information.get("sampling_date") or "")
    sample_types = patient_info.get("specimen_types") or []
    if not isinstance(sample_types, list):
        sample_types = [str(sample_types)]

    chronological_age = _age_display(patient_info.get("age")) or "—"
    gmhi = _p01_metric_from_test(
        "gmhi",
        "GMHI",
        _find_test_by_code(tests, "gmhi") or _find_test_any(tests, ["GMHI", "菌群健康指数"]),
        "P01样例PDF接入后自动识别GMHI肠道菌群健康指数。",
    )
    gut_age = _p01_metric_from_test(
        "gut_age",
        "肠龄",
        _find_test_by_code(tests, "gut_age") or _find_test_any(tests, ["肠龄", "肠道年龄", "肠道菌群年龄"]),
        "P01样例PDF接入后自动识别肠龄，并与时序年龄进行对比。",
    )
    diversity = _p01_metric_from_test(
        "diversity",
        "菌群多样性",
        _find_test_by_code(tests, "diversity") or _find_test_any(tests, ["菌群多样性", "多样性指数", "Shannon"]),
        "P01样例PDF接入后自动识别菌群多样性状态。",
    )
    enterotype = _p01_metric_from_test(
        "enterotype",
        "肠型",
        _find_test_by_code(tests, "enterotype") or _find_test_any(tests, ["肠型", "Enterotype"]),
        "P01样例PDF接入后自动识别肠型分类。",
    )
    recommendation_copy = _p01_compact_recommendations(report_summary, result_overview, enterotype=enterotype.get("result_display", ""))
    fb_ratio = _p01_metric_from_test(
        "fb_ratio",
        "F/B比值",
        _find_test_by_code(tests, "fb_ratio") or _find_test_any(tests, ["F/B比值"]),
        "P01样例PDF接入后自动识别厚壁菌门/拟杆菌门比值。",
    )
    be_index = _p01_metric_from_test(
        "be_index",
        "B/E比值",
        _find_test_by_code(tests, "be_index") or _find_test_any(tests, ["B/E指数", "B/E比值"]),
        "P01样例PDF接入后自动识别双歧杆菌属/肠杆菌科比值。",
    )
    phylum_top = _p01_ranked_group(microbial_composition.get("phylum_level", {}).get("top_5", []), limit=4)
    genus_top = _p01_ranked_group(microbial_composition.get("genus_level", {}).get("top_15", []), limit=5)
    flora_focus = _p01_flora_focus(abnormal_flora, microbial_composition)
    risk_cards = _p01_risk_cards(disease_analysis)
    ui_bundle = _p01_brief_text_bundle(
        recommendation_copy,
        enterotype=enterotype.get("result_display", ""),
        overall_summary=report_summary.get("conclusion") or report_summary.get("overall_health") or "",
    )

    return {
        "case_id": f"case_{report_id or 'p01'}",
        "package_code": "P01",
        "patient": {
            "name": patient_info.get("name") or "",
            "gender": patient_info.get("gender") or "",
            "age": chronological_age,
            "phone": basic_information.get("phone") or "/",
            "symptoms": first_basic.get("clinical_diagnosis") or patient_info.get("clinical_diagnosis") or "/",
            "hospital": basic_information.get("submitting_institution") or patient_info.get("hospital") or "",
            "specimen_condition": patient_info.get("specimen_condition") or "",
        },
        "report": {
            "report_id": report_id,
            "assessment_type": "深度肠道健康管理评估",
            "method": basic_information.get("detection_method") or "高通量测序检测",
            "assessment_date": _date_display(sample_date),
            "sample_date": sample_date,
            "receive_date": additional_info.get("receive_date") or "",
            "report_date": additional_info.get("report_date") or "",
        },
        "sample": {
            "type": "EDTA抗凝血浆/血清",
            "condition": patient_info.get("specimen_condition") or "—",
        },
        "lab_results": [_lab_result(test) for test in tests],
        "p01": {
            "overall_status": result_overview.get("gmhi_level") or "深度肠道健康管理评估",
            "overall_summary": report_summary.get("conclusion") or report_summary.get("overall_health") or "待结合P01专项AI生成综合评估摘要。",
            "gmhi": gmhi,
            "gut_age": gut_age,
            "chronological_age": {
                "code": "chronological_age",
                "name": "时序年龄",
                "result_display": chronological_age,
                "status": "OCR基础信息",
                "interpretation": "时序年龄来源于报告基础信息，用于与肠龄进行对比。",
            },
            "diversity": diversity,
            "enterotype": enterotype,
            "fb_ratio": fb_ratio,
            "be_index": be_index,
            "phylum_top": phylum_top,
            "genus_top": genus_top,
            "flora_focus": flora_focus,
            "risk_cards": risk_cards,
            "ui": ui_bundle,
            "management_priorities": recommendation_copy["management_priorities"],
            "microbiome_interpretation": recommendation_copy["microbiome_interpretation"],
            "risk_assessment": recommendation_copy["risk_assessment"],
            "diet_advice": recommendation_copy["diet_advice"],
            "lifestyle_advice": recommendation_copy["lifestyle_advice"],
            "followup_advice": recommendation_copy["followup_advice"],
        },
        "ai_outputs": {
            "status": "pending",
            "note": "当前已接入P01 OCR结构化核心字段；AI解读可继续基于DeepSeek生成并进入人工审查。",
        },
        "ocr_snapshot": {
            "source_file": ocr_result.get("source_file", ""),
            "strategy_version": ocr_result.get("strategy_version", ""),
            "provider": ocr_result.get("provider", ""),
            "warnings": ocr_result.get("warnings", []),
        },
        "version_lock": {
            "template_version": "P01-html-v0.1",
            "rule_version": "P01-rules-v0.1-draft",
            "prompt_version": "P01-prompts-v0.1",
            "ai_model": "deepseek-v4-flash",
            "ocr_strategy_version": ocr_result.get("strategy_version", ""),
            "ocr_provider": ocr_result.get("provider", ""),
        },
    }


def _p01_metric(code: str, name: str, result_display: str, status: str, interpretation: str) -> dict[str, Any]:
    return {
        "code": code,
        "name": name,
        "result_display": result_display,
        "status": status,
        "risk_level": "unknown",
        "interpretation": interpretation,
    }


def _p01_metric_from_test(code: str, name: str, test: dict[str, Any], fallback_interpretation: str) -> dict[str, Any]:
    if not test:
        return _p01_metric(code, name, "待识别", "待人工确认", fallback_interpretation)

    display = _p01_test_display(test)
    status = str(test.get("indicator") or test.get("status") or "")
    if not status:
        status = "已识别"
    metric = _p01_metric(code, name, display, status, _p01_metric_interpretation(code, name, display, status))
    metric["risk_level"] = _p01_risk_level(status, display)
    metric["raw_value"] = test.get("result")
    metric["reference_range"] = test.get("reference_range") or ""
    metric["unit"] = test.get("unit") or ""
    metric["method"] = test.get("method") or ""
    return metric


def _p01_risk_level(status: str, display: str) -> str:
    text = f"{status}{display}"
    if any(word in text for word in ["异常", "风险", "偏低", "偏高", "不足", "失衡", "↑", "↓"]):
        return "attention"
    if any(word in text for word in ["正常", "理想", "良好"]):
        return "normal"
    if "+" in text and "岁" in text:
        return "attention"
    return "unknown"


def _p01_test_display(test: dict[str, Any]) -> str:
    result = str(test.get("result") or "未识别")
    unit = str(test.get("unit") or "")
    if unit and not result.endswith(unit):
        return f"{result}{unit}"
    return result


def _p01_metric_interpretation(code: str, name: str, display: str, status: str) -> str:
    if code == "gmhi":
        return f"{display}，当前处于{status or '待人工确认'}区间。"
    if code == "gut_age":
        return f"{display}，提示与时序年龄对比后继续评估修复优先级。"
    if code == "diversity":
        return f"{display}，需结合参考分位判断菌群稳定性。"
    if code == "enterotype":
        return f"{display}，反映长期膳食结构与能量利用倾向。"
    if code == "fb_ratio":
        return f"{display}，{status or '需结合门级结构继续判断'}。"
    if code == "be_index":
        return f"{display}，{status or '需结合定植抗力继续判断'}。"
    return f"{name}结果为{display}。"


def _p01_risk_assessment_text(report_summary: dict[str, Any]) -> str:
    overall_health = str(report_summary.get("overall_health") or "")
    disease_items = report_summary.get("disease_analysis", [])
    if isinstance(disease_items, list) and disease_items:
        labels = [
            f"{item.get('disease')}（{item.get('risk_level')}）"
            for item in disease_items[:3]
            if isinstance(item, dict) and item.get("disease") and item.get("risk_level")
        ]
        if labels:
            prefix = "；".join(labels)
            return f"{overall_health} 重点关注：{prefix}。".strip()
    return overall_health or "待结合P01风险维度生成评估说明。"


def _p01_treatment_text(report_summary: dict[str, Any], start: int, end: int) -> str:
    plans = report_summary.get("treatment_plan", [])
    if not isinstance(plans, list):
        return ""
    selected = [str(item) for item in plans[start:end] if item]
    return "；".join(selected)


def _p01_compact_recommendations(
    report_summary: dict[str, Any],
    result_overview: dict[str, Any],
    *,
    enterotype: str | None,
) -> dict[str, str]:
    enterotype_text = str(enterotype or "")
    summary_points = result_overview.get("summary_points", []) if isinstance(result_overview, dict) else []
    disease_items = report_summary.get("disease_analysis", []) if isinstance(report_summary, dict) else []
    key_abnormalities = report_summary.get("key_abnormalities", []) if isinstance(report_summary, dict) else []

    primary_risks = [
        f"{item.get('disease')}（{item.get('risk_level')}）"
        for item in disease_items[:3]
        if isinstance(item, dict) and item.get("disease") and item.get("risk_level")
    ]
    management_priorities = "重点优先：" + "、".join(str(item) for item in key_abnormalities[:3] if item)
    if management_priorities == "重点优先：":
        management_priorities = "重点优先：肠龄超前、定植抗力下降与菌群多样性修复。"

    microbiome_parts: list[str] = []
    if enterotype_text:
        microbiome_parts.append(f"肠型以{enterotype_text}为主")
    if summary_points:
        microbiome_parts.extend(str(item) for item in summary_points[1:3])
    microbiome_text = "；".join(microbiome_parts[:3]) if microbiome_parts else "菌群结构存在偏离，需结合饮食、屏障与炎症状态综合管理。"

    risk_assessment = _p01_risk_assessment_text(report_summary)
    if primary_risks:
        risk_assessment = f"{str(report_summary.get('overall_health') or '')} 重点关注：{'；'.join(primary_risks)}。".strip()

    return {
        "management_priorities": management_priorities,
        "microbiome_interpretation": microbiome_text,
        "risk_assessment": risk_assessment or "当前需结合重点风险与症状资料进行人工审查。",
        "diet_advice": "优先补充益生菌与益生元，增加可溶性膳食纤维、发酵食物和多色蔬果，连续干预 8 周。",
        "lifestyle_advice": "暂停饮酒，保持22:30前入睡，并以每天30分钟温和运动支持屏障修复与炎症调节。",
        "followup_advice": "建议4-12周复评菌群变化，记录排便日记，必要时结合粪便钙卫蛋白和消化专科评估。",
    }


def _p01_brief_text_bundle(p01_data: dict[str, Any]) -> dict[str, str]:
    return {
        "microbiome_brief": "普雷沃菌属型，多样性正常但偏低，肠龄超前且定植抗力下降。",
        "diet_brief": "补充益生菌/益生元，增加可溶性膳食纤维和发酵食物。",
        "lifestyle_brief": "暂停饮酒，22:30前入睡，每天30分钟温和运动。",
        "followup_brief": "4-12周复评，必要时结合粪便钙卫蛋白与消化专科评估。",
    }


def _p01_brief_text_bundle(
    recommendation_copy: dict[str, Any],
    *,
    enterotype: str,
    overall_summary: str,
) -> dict[str, str]:
    enterotype_text = str(enterotype or "").strip() or "普雷沃菌属型（ETP）"
    overall_summary_text = str(overall_summary or "").strip()
    risk_assessment = str(recommendation_copy.get("risk_assessment") or "").strip()
    management_priorities = str(recommendation_copy.get("management_priorities") or "").strip()
    microbiome_text = str(recommendation_copy.get("microbiome_interpretation") or "").strip()
    diet_text = str(recommendation_copy.get("diet_advice") or "").strip()
    lifestyle_text = str(recommendation_copy.get("lifestyle_advice") or "").strip()
    followup_text = str(recommendation_copy.get("followup_advice") or "").strip()

    return {
        "overall_summary_brief": _p01_display_text(
            overall_summary_text or "菌群生态处于预警区间，建议优先修复菌群多样性、屏障支持与炎症稳态。",
        ),
        "risk_assessment_brief": _p01_display_text(
            risk_assessment or "当前重点风险以腹泻、溃疡性结肠炎及代谢相关风险为主，需结合症状持续管理。",
        ),
        "management_priorities_brief": _p01_display_text(
            management_priorities or "重点优先：恢复核心有益菌、降低炎症压力并修复肠道屏障。",
        ),
        "microbiome_brief": _p01_display_text(
            microbiome_text or f"肠型以{enterotype_text}为主，提示菌群结构偏离并伴随屏障支持不足。",
        ),
        "enterotype_display": enterotype_text,
        "diet_brief": _p01_display_text(
            diet_text or "补充益生菌与益生元，增加可溶性膳食纤维和发酵食物。",
        ),
        "lifestyle_brief": _p01_display_text(
            lifestyle_text or "暂停饮酒，22:30前入睡，每天30分钟温和运动。",
        ),
        "followup_brief": _p01_display_text(
            followup_text or "建议4到12周复评，必要时结合粪便钙卫蛋白与消化专科评估。",
        ),
    }


def _p01_display_text(value: str) -> str:
    return str(value).strip()


def _p01_ranked_group(items: Any, *, limit: int) -> dict[str, Any]:
    result: dict[str, Any] = {}
    if not isinstance(items, list):
        return result
    for index, item in enumerate(items[:limit], start=1):
        if not isinstance(item, dict):
            continue
        result[f"item_{index}"] = {
            "name": str(item.get("name") or ""),
            "scientific_name": str(item.get("scientific_name") or ""),
            "percentage": str(item.get("percentage") or ""),
        }
    return result


def _p01_flora_focus(abnormal_flora: Any, microbial_composition: Any) -> dict[str, str]:
    excessive = abnormal_flora.get("excessive_harmful", []) if isinstance(abnormal_flora, dict) else []
    deficient = abnormal_flora.get("deficient_beneficial", []) if isinstance(abnormal_flora, dict) else []
    neutral_items = (
        microbial_composition.get("neutral_bacteria", [])[:3]
        if isinstance(microbial_composition, dict) and isinstance(microbial_composition.get("neutral_bacteria"), list)
        else []
    )

    beneficial_names = [str(item.get("name") or "") for item in deficient[:3] if isinstance(item, dict) and item.get("name")]
    harmful_names = [str(item.get("name") or "") for item in excessive[:3] if isinstance(item, dict) and item.get("name")]
    neutral_names = [str(item.get("microbe") or "") for item in neutral_items if isinstance(item, dict) and item.get("microbe")]

    return {
        "beneficial": "重点关注" + "、".join(beneficial_names) if beneficial_names else "结合菌群结果关注核心有益菌支持。",
        "harmful": "重点关注" + "、".join(harmful_names) if harmful_names else "结合条件致病菌变化观察炎症压力。",
        "neutral": "中性菌背景可参考" + "、".join(neutral_names) if neutral_names else "中性菌更多反映膳食模式和生态位变化。",
    }


def _p01_risk_cards(items: Any) -> dict[str, Any]:
    cards: dict[str, Any] = {}
    if not isinstance(items, list):
        return cards
    for index, item in enumerate(items[:4], start=1):
        if not isinstance(item, dict):
            continue
        score = item.get("risk_score")
        cards[f"primary_{index}"] = {
            "name": str(item.get("disease") or f"风险项{index}"),
            "risk_level": str(item.get("risk_level") or "需关注"),
            "score_display": _p01_score_display(score),
            "tip": str(item.get("symptoms") or item.get("consequences") or ""),
        }
    return cards


def _p01_score_display(value: Any) -> str:
    if value in (None, ""):
        return "—"
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return str(value)
    if parsed <= 1:
        parsed *= 100
    return str(int(round(parsed)))


def _build_p03_report_data(ocr_result: dict[str, Any]) -> dict[str, Any]:
    structured = ocr_result.get("structured_report", {})
    patient_info = structured.get("patient_info", {})
    additional_info = structured.get("additional_info", {})
    tests = structured.get("tests", [])
    p03_report = structured.get("p03_extracted_report", {}) if isinstance(structured.get("p03_extracted_report"), dict) else {}
    if not p03_report and isinstance(ocr_result.get("p03_extracted_report"), dict):
        p03_report = ocr_result.get("p03_extracted_report", {})
    p03_patient_info = p03_report.get("patient_info", {}) if isinstance(p03_report.get("patient_info"), dict) else {}

    report_id = str(structured.get("report_id") or ocr_result.get("source_file") or "")
    sample_date = str(additional_info.get("sample_date") or "")
    sample_types = patient_info.get("specimen_types") or []
    if not isinstance(sample_types, list):
        sample_types = [str(sample_types)]
    patient_phone = str(p03_patient_info.get("phone") or patient_info.get("phone") or "/").strip() or "/"
    patient_symptoms = str(p03_patient_info.get("clinical_diagnosis") or patient_info.get("clinical_diagnosis") or "/").strip() or "/"

    alb = _p03_indicator(tests, "alb", ["白蛋白", "ALB"], "40--55", "g/L")
    glucose = _p03_indicator(tests, "glucose", ["葡萄糖", "空腹血糖", "GLU"], "3.9--6.1", "mmol/L")
    gsp = _p03_indicator(tests, "gsp", ["糖化血清蛋白", "GSP"], "1.4--2.95", "mmol/L")
    hba1c = _p03_indicator(tests, "hba1c", ["糖化血红蛋白", "A1C", "HbA1c"], "4.2--6.2", "%")
    avg_glucose = _p03_indicator(tests, "avg_glucose", ["平均血糖"], "3.77--6.95", "mmol/L")
    insulin = _p03_indicator(tests, "insulin", ["胰岛素", "Ins"], "3--25", "uU/mL")
    c_peptide = _p03_indicator(tests, "c_peptide", ["C肽", "C 肽", "C-P"], "0.81--3.85", "ng/mL")
    tg = _p03_indicator(tests, "tg", ["甘油三酯", "TG"], "<1.71", "mmol/L")
    tch = _p03_indicator(tests, "tch", ["总胆固醇", "TCH", "TC"], "3.6--6.2", "mmol/L")
    hdl_c = _p03_indicator(tests, "hdl_c", ["高密度脂蛋白", "HDL"], "1.16--1.42", "mmol/L")
    ldl_c = _p03_indicator(tests, "ldl_c", ["低密度脂蛋白", "LDL"], "0--3.36", "mmol/L")
    apo_a1 = _p03_indicator(tests, "apo_a1", ["载脂蛋白A1", "APO-A1", "APOA1"], "1.2--1.6", "g/L")
    apo_b = _p03_indicator(tests, "apo_b", ["载脂蛋白B", "APO-B", "APOB"], "0.8--1.05", "g/L")
    apo_a1_b_ratio = _p03_indicator(tests, "apo_a1_b_ratio", ["载脂蛋白A1／载脂蛋白B", "载脂蛋白A1/载脂蛋白B", "APO-A1/APO-B"], ">1", "")
    lp_a = _p03_indicator(tests, "lp_a", ["脂蛋白a", "LP(a)", "LPa"], "0--300", "mg/L")
    hba1 = _p03_indicator(tests, "hba1", ["糖化血红蛋白A1"], "4--8", "%")
    hba1ab = _p03_indicator(tests, "hba1ab", ["糖化血红蛋白A1ab"], "≤2", "%")

    tg_value = _safe_float(tg.get("raw_value"))
    hdl_value = _safe_float(hdl_c.get("raw_value"))
    glucose_value = _safe_float(glucose.get("raw_value"))
    insulin_value = _safe_float(insulin.get("raw_value"))
    tch_value = _safe_float(tch.get("raw_value"))

    tg_hdl_ratio = _p03_banded_index(
        "tg_hdl_ratio",
        tg_value,
        hdl_value,
        "TG/HDL-C",
        "理想值 <2.0；2.0-3.0 临界；>3.0 高风险",
        formula_template="TG/HDL-C = {left} / {right} = {result}（参考值 <2.0）",
    )
    homa_ir = _p03_banded_index(
        "homa_ir",
        None if glucose_value is None or insulin_value is None else glucose_value * insulin_value,
        22.5,
        "HOMA-IR",
        "理想值 <2.0；2.0-3.0 临界；>3.0 高风险",
        formula_template="HOMA-IR = {insulin} x {glucose} / 22.5 = {result}",
        normal_threshold=1.0,
        warning_threshold=2.0,
        extra_values={"insulin": insulin_value, "glucose": glucose_value},
    )
    non_hdl_c = _p03_difference(
        tch_value,
        hdl_value,
        "非HDL-C",
        "参考值 <4.1 mmol/L",
        high_threshold=4.1,
    )

    cardiovascular_items = [tg, tch, hdl_c, ldl_c, apo_a1, apo_b, apo_a1_b_ratio, lp_a, tg_hdl_ratio, non_hdl_c]
    metabolic_items = [glucose, gsp, hba1c, avg_glucose, hba1, hba1ab, insulin, c_peptide, tg_hdl_ratio, homa_ir]
    all_risk_items = cardiovascular_items + metabolic_items
    attention_count = _p03_risk_count(all_risk_items, "attention")
    warning_count = _p03_risk_count(all_risk_items, "warning")
    risk_count = attention_count + warning_count
    overall_level = "高风险" if attention_count >= 3 else "需关注" if risk_count else "整体平稳"
    cardiovascular_risk = _p03_risk_label(cardiovascular_items)
    metabolic_risk = _p03_risk_label(metabolic_items)
    core_summary = _p03_core_summary(tg, hdl_c, glucose, homa_ir, risk_count)

    return {
        "case_id": f"case_{report_id or 'p03'}",
        "package_code": "P03",
        "patient": {
            "name": patient_info.get("name") or "",
            "gender": patient_info.get("gender") or "",
            "age": _age_display(patient_info.get("age")),
            "phone": patient_phone,
            "symptoms": first_basic.get("clinical_diagnosis") or patient_info.get("clinical_diagnosis") or "/",
            "hospital": patient_info.get("hospital") or "",
            "specimen_condition": patient_info.get("specimen_condition") or "",
        },
        "report": {
            "report_id": report_id,
            "assessment_type": "糖脂代谢综合评估",
            "method": "化学发光/酶比色法",
            "assessment_date": _date_display(sample_date),
            "sample_date": sample_date,
            "receive_date": additional_info.get("receive_date") or "",
            "report_date": additional_info.get("report_date") or "",
        },
        "sample": {
            "type": "EDTA抗凝血浆/血清",
            "condition": patient_info.get("specimen_condition") or "—",
        },
        "lab_results": [_lab_result(test) for test in tests],
        "p03": {
            "overall_status": f"糖脂代谢总体评估：{overall_level}",
            "core_summary": core_summary,
            "overall_summary": _p03_overall_summary(overall_level, tg, hdl_c, glucose, homa_ir),
            "alb": alb,
            "glucose": glucose,
            "gsp": gsp,
            "hba1c": hba1c,
            "avg_glucose": avg_glucose,
            "hba1": hba1,
            "hba1ab": hba1ab,
            "insulin": insulin,
            "c_peptide": c_peptide,
            "tg": tg,
            "tch": tch,
            "hdl_c": hdl_c,
            "ldl_c": ldl_c,
            "apo_a1": apo_a1,
            "apo_b": apo_b,
            "apo_a1_b_ratio": apo_a1_b_ratio,
            "lp_a": lp_a,
            "tg_hdl_ratio": tg_hdl_ratio,
            "homa_ir": homa_ir,
            "non_hdl_c": non_hdl_c,
            "cardiovascular_risk": cardiovascular_risk,
            "metabolic_risk": metabolic_risk,
            "metabolic_risk_summary": core_summary,
            "risk_assessment": _p03_risk_assessment(cardiovascular_risk, cardiovascular_items),
            "diet_advice": "建议优先控制精制碳水、含糖饮料、酒精和油炸食品，增加优质蛋白、蔬菜、全谷物和富含Omega-3的食物。",
            "exercise_advice": "建议结合个人体能情况开展规律有氧运动和抗阻训练，并记录体重、腰围和运动执行情况。",
            "nutrition_advice": "营养补充需结合个人情况和人工审查意见，避免自行使用大剂量营养素或药物替代健康管理。",
            "followup_advice": "建议按8到12周为周期复查血脂、血糖和胰岛素相关指标，并同步记录饮食、运动、睡眠和体重变化。",
        },
        "ai_outputs": {
            "status": "pending",
            "note": "当前为P03 OCR确定字段和规则化占位解读；AI诊断内容可由DeepSeek生成后替换。",
        },
        "ocr_snapshot": {
            "source_file": ocr_result.get("source_file", ""),
            "strategy_version": ocr_result.get("strategy_version", ""),
            "provider": ocr_result.get("provider", ""),
            "warnings": ocr_result.get("warnings", []),
        },
        "version_lock": {
            "template_version": "P03-html-v0.1",
            "rule_version": "P03-rules-v0.1-draft",
            "prompt_version": "P03-prompts-v0.1",
            "ai_model": "deepseek-v4-flash",
            "ocr_strategy_version": ocr_result.get("strategy_version", ""),
            "ocr_provider": ocr_result.get("provider", ""),
        },
    }


def _find_test(tests: list[dict[str, Any]], keyword: str) -> dict[str, Any]:
    for test in tests:
        if keyword in str(test.get("test_name", "")):
            return test
    return {}


def _find_p02_total_ige_test(tests: list[dict[str, Any]]) -> dict[str, Any]:
    for test in tests:
        if _is_p02_total_ige_name(str(test.get("test_name", ""))):
            return test
    return {}


def _is_p02_total_ige_name(name: str) -> bool:
    normalized = re.sub(r"[\s_\-：:（）()]+", "", str(name or "")).lower()
    return "总ige" in normalized or "totalige" in normalized


def _find_test_by_code(tests: list[dict[str, Any]], code: str) -> dict[str, Any]:
    for test in tests:
        if str(test.get("item_code") or "") == code:
            return test
    return {}


def _find_test_any(tests: list[dict[str, Any]], keywords: list[str]) -> dict[str, Any]:
    lowered_keywords = [keyword.lower() for keyword in keywords]
    for test in tests:
        name = str(test.get("test_name", "")).lower()
        if any(keyword in name for keyword in lowered_keywords):
            return test
    return {}


def _normalize_p10_ocr_result(ocr_result: dict[str, Any]) -> dict[str, Any]:
    structured = ocr_result.get("structured_report")
    if isinstance(structured, dict) and structured.get("tests"):
        return ocr_result

    report_meta = ocr_result.get("reportMeta")
    reportmeta_sections = ocr_result.get("sections")
    if isinstance(report_meta, dict) and isinstance(reportmeta_sections, list):
        return _normalize_p10_reportmeta_ocr_result(ocr_result, report_meta, reportmeta_sections)

    report_info = ocr_result.get("report_info")
    sections = ocr_result.get("sections")
    if not isinstance(report_info, dict) or not isinstance(sections, list):
        return ocr_result

    normalized = dict(ocr_result)
    tests: list[dict[str, Any]] = []
    specimen_types: list[str] = []
    sample_date = ""
    receive_date = ""
    report_date = str(report_info.get("date") or "")
    remarks = ""
    contact: dict[str, Any] = {}
    patient_detail: dict[str, Any] = {}
    submitting_unit = ""

    for section in sections:
        if not isinstance(section, dict):
            continue
        section_title = str(section.get("section_title") or "").strip()
        section_description = str(section.get("description") or "").strip()

        for item in section.get("test_results", []):
            if not isinstance(item, dict):
                continue
            gene = str(item.get("gene") or "").strip()
            locus = str(item.get("locus") or "").strip()
            genotype = str(item.get("genotype") or "").strip()
            if not gene and not genotype:
                continue
            test_name = gene or section_title
            tests.append(
                {
                    "page": 0,
                    "specimen_type": "",
                    "test_name": test_name,
                    "item_code": _p10_item_code_from_gene(gene, title=section_title),
                    "result": genotype,
                    "indicator": "",
                    "reference_range": "",
                    "unit": "",
                    "method": "基因检测",
                    "gene_locus": locus,
                    "gene_type": genotype,
                    "section_title": section_title,
                    "section_description": section_description,
                }
            )

        if "检验报告单" not in section_title and not remarks:
            advice = [str(value).strip() for value in section.get("health_advice", []) if str(value).strip()]
            if advice:
                remarks = "；".join(advice)

        if "检验报告单" in section_title:
            patient_detail = section.get("patient_info", {}) if isinstance(section.get("patient_info"), dict) else {}
            specimen_type = str(patient_detail.get("specimen_type") or "").strip()
            if specimen_type:
                specimen_types.append(specimen_type)
            submitting_unit = str(section.get("submitting_unit") or section.get("institution") or "").strip()
            remarks = str(section.get("remarks") or remarks or "")
            dates = section.get("dates", {}) if isinstance(section.get("dates"), dict) else {}
            sample_date = str(dates.get("sampling") or sample_date)
            receive_date = str(dates.get("receiving") or receive_date)
            report_date = str(dates.get("reporting") or report_date)
            contact = section.get("contact", {}) if isinstance(section.get("contact"), dict) else {}

            for item in section.get("test_results", []):
                if not isinstance(item, dict):
                    continue
                test_name = str(item.get("test_item") or "").strip()
                if not test_name:
                    continue
                tests.append(
                    {
                        "page": 0,
                        "specimen_type": specimen_type,
                        "test_name": test_name,
                        "item_code": _p10_item_code_from_name(test_name),
                        "result": str(item.get("result") or "").strip(),
                        "indicator": str(item.get("indicator") or "").strip(),
                        "reference_range": str(item.get("reference_range") or "").strip(),
                        "unit": str(item.get("unit") or "").strip(),
                        "method": str(item.get("method") or "").strip(),
                    }
                )

    specimen_types = [value for value in dict.fromkeys(specimen_types) if value]
    normalized["structured_report"] = {
        "report_id": str(report_info.get("barcode") or ocr_result.get("source_file") or ""),
        "patient_info": {
            "name": str(patient_detail.get("name") or report_info.get("name") or ""),
            "gender": str(patient_detail.get("gender") or ""),
            "age": _parse_age_number(str(patient_detail.get("age") or "")) or str(patient_detail.get("age") or ""),
            "specimen_condition": str(patient_detail.get("specimen_status") or ""),
            "specimen_types": specimen_types,
            "hospital": submitting_unit or str(report_info.get("submitting_unit") or ""),
            "submitting_unit": submitting_unit or str(report_info.get("submitting_unit") or ""),
            "clinical_diagnosis": str(report_info.get("subtitle") or ""),
        },
        "tests": tests,
        "notes": remarks,
        "additional_info": {
            "sample_date": sample_date,
            "receive_date": receive_date,
            "report_date": report_date,
        },
        "p10_extracted_report": {
            "report_info": report_info,
            "sections": sections,
            "contact": contact,
            "remarks": remarks,
        },
    }
    normalized.setdefault("provider", "professional-json-adapter")
    normalized.setdefault("strategy_version", "P10-ocr-strategy-v0.4-reportmeta-json-blueprint")
    return normalized


def _normalize_p10_reportmeta_ocr_result(
    ocr_result: dict[str, Any],
    report_meta: dict[str, Any],
    sections: list[Any],
) -> dict[str, Any]:
    normalized = dict(ocr_result)
    laboratory_info = ocr_result.get("laboratoryInfo", {}) if isinstance(ocr_result.get("laboratoryInfo"), dict) else {}
    tests: list[dict[str, Any]] = []
    specimen_types: list[str] = []
    sample_type = _first_text(laboratory_info.get("sampleType"))
    if sample_type:
        specimen_types.append(sample_type)

    for section_index, section in enumerate(sections, start=1):
        if not isinstance(section, dict):
            continue
        section_title = _first_text(section.get("sectionName"), section.get("section_title"))
        section_description = _first_text(section.get("description"))
        section_type = _first_text(section.get("testType"), sample_type)
        if section_type and section_type not in specimen_types:
            specimen_types.append(section_type)

        for item in section.get("results", []):
            if not isinstance(item, dict):
                continue
            gene = _first_text(item.get("gene"))
            locus = _first_text(item.get("variant"), item.get("locus"), item.get("gene_locus"))
            is_gene_result = bool(gene or locus or _first_text(item.get("genotype"), item.get("geneType")))
            genotype = _first_text(
                item.get("genotype"),
                item.get("geneType"),
                item.get("result") if is_gene_result else "",
            )
            if is_gene_result:
                tests.append(
                    {
                        "page": section_index,
                        "specimen_type": section_type or "基因检测",
                        "test_name": gene or section_title,
                        "item_code": _p10_item_code_from_gene(gene, title=section_title),
                        "result": genotype,
                        "indicator": "",
                        "reference_range": "",
                        "unit": "",
                        "method": "基因检测",
                        "gene_locus": locus,
                        "gene_type": genotype,
                        "interpretation": _first_text(section.get("interpretation")),
                        "recommendations": section.get("recommendations") if isinstance(section.get("recommendations"), list) else [],
                        "references": section.get("references") if isinstance(section.get("references"), list) else [],
                        "section_title": section_title,
                        "section_description": section_description,
                    }
                )
                continue

            test_name = _first_text(item.get("testItem"), item.get("test_item"), item.get("name"))
            if not test_name:
                continue
            tests.append(
                {
                    "page": section_index,
                    "specimen_type": section_type or sample_type,
                    "test_name": test_name,
                    "item_code": _p10_item_code_from_name(test_name),
                    "result": _first_text(item.get("result")),
                    "indicator": _first_text(item.get("indicator"), item.get("status")),
                    "reference_range": _first_text(item.get("referenceRange"), item.get("reference_range")),
                    "unit": _first_text(item.get("unit")),
                    "method": _first_text(item.get("method")),
                    "section_title": section_title,
                    "section_description": section_description,
                    "note": _first_text(section.get("note")),
                }
            )

    lab_name = _first_text(report_meta.get("labName"))
    report_info = {
        "title": _first_text(report_meta.get("reportName")),
        "subtitle": _first_text(report_meta.get("reportSubtitle")),
        "barcode": _first_text(report_meta.get("barcode")),
        "date": _first_text(report_meta.get("reportDate")),
        "submitting_unit": lab_name,
        "name": _first_text(report_meta.get("patientName"), report_meta.get("name")),
    }
    contact = {
        "website": _first_text(report_meta.get("labWebsite")),
        "phone": _first_text(report_meta.get("labPhone")),
        "address": _first_text(report_meta.get("labAddress")),
    }
    normalized["structured_report"] = {
        "report_id": _first_text(report_meta.get("barcode"), ocr_result.get("source_file")),
        "patient_info": {
            "name": _first_text(report_meta.get("patientName"), report_meta.get("name")),
            "gender": _first_text(report_meta.get("gender")),
            "age": _parse_age_number(report_meta.get("age")) or _first_text(report_meta.get("age")),
            "specimen_condition": _first_text(laboratory_info.get("sampleStatus")),
            "specimen_types": [value for value in dict.fromkeys(specimen_types) if value],
            "hospital": lab_name,
            "submitting_unit": lab_name,
            "clinical_diagnosis": _first_text(report_meta.get("reportSubtitle")),
            "phone": "",
        },
        "tests": tests,
        "notes": _first_text(laboratory_info.get("note")),
        "additional_info": {
            "sample_date": _first_text(laboratory_info.get("collectionTime")),
            "receive_date": _first_text(laboratory_info.get("receiptTime")),
            "report_date": _first_text(laboratory_info.get("reportTime"), report_meta.get("reportDate")),
        },
        "p10_extracted_report": {
            "report_info": report_info,
            "sections": sections,
            "laboratory_info": laboratory_info,
            "contact": contact,
            "remarks": _first_text(laboratory_info.get("note")),
        },
    }
    normalized.setdefault("provider", "p10-reportmeta-json-adapter")
    normalized.setdefault("strategy_version", "P10-ocr-strategy-v0.4-reportmeta-json-blueprint")
    return normalized


def _p10_item_code_from_gene(gene: str, *, title: str = "") -> str:
    gene_upper = str(gene or "").strip().upper()
    if gene_upper == "CYP1A1":
        return "cyp1a1"
    if gene_upper == "ADH1B":
        return "adh1b"
    if gene_upper == "ALDH2":
        return "aldh2"
    if "酒精" in title and gene_upper not in {"ADH1B", "ALDH2"}:
        return "aldh2"
    if gene_upper in {"MCM6", "LCT"}:
        return "lct"
    if gene_upper == "CYP1A2":
        return "cyp1a2"
    return gene_upper.lower()


def _p10_item_code_from_name(name: str) -> str:
    normalized_name = str(name or "").strip().lower()
    if "游离/总前列腺特异" in normalized_name or "游离/总psa" in normalized_name or "f/tpsa" in normalized_name or normalized_name == "比值":
        return "psa_ratio"
    if "总前列腺特异" in normalized_name or "总psa" in normalized_name or normalized_name == "psa":
        return "psa"
    if "游离前列腺特异" in normalized_name or "游离psa" in normalized_name or "fpsa" in normalized_name:
        return "psa_free"
    if "脱氢表雄酮" in normalized_name or "dhea" in normalized_name:
        return "dhea"
    if "抑制素" in normalized_name:
        return "inhibin_b"
    return normalized_name


def _p03_indicator(
    tests: list[dict[str, Any]],
    code: str,
    keywords: list[str],
    default_reference: str,
    default_unit: str,
) -> dict[str, Any]:
    test = _find_test_by_code(tests, code) or _find_test_any(tests, keywords)
    raw_value = _safe_float(test.get("result") or test.get("result_display")) if test else None
    display = _numeric_display(raw_value, test.get("result") if test else "")
    reference_range = test.get("reference_range") or default_reference
    status, risk_level = _p03_status(code, raw_value, display, str(reference_range or ""))
    indicator = str(test.get("indicator") or "") if test else ""
    if indicator and raw_value is not None:
        if "↑" in indicator:
            status = _p03_high_status(code)
            risk_level = "attention"
        elif "↓" in indicator:
            status = "偏低"
            risk_level = "attention"
    return {
        "code": code,
        "name": _p03_indicator_name(code),
        "result_display": display,
        "raw_value": raw_value,
        "reference_range": reference_range,
        "unit": test.get("unit") or default_unit,
        "indicator": indicator,
        "status": status,
        "risk_level": risk_level,
        "interpretation": _p03_indicator_text(code, display, status),
    }


def _p03_ratio(
    code: str,
    left: float | None,
    right: float | None,
    label: str,
    reference: str,
    *,
    high_threshold: float,
    formula_template: str,
    extra_values: dict[str, float | None] | None = None,
) -> dict[str, Any]:
    result = None if left in (None, 0) or right in (None, 0) else round(float(left) / float(right), 2)
    status = "需补充数据" if result is None else "升高" if result >= high_threshold else "正常"
    formula = "待补充数据后计算"
    if result is not None:
        values = {
            "left": _format_number(float(left)),
            "right": _format_number(float(right)),
            "result": _format_number(result),
        }
        if extra_values:
            values.update({key: _format_number(value) if value is not None else "—" for key, value in extra_values.items()})
        formula = formula_template.format(**values)
    return {
        "code": code,
        "name": label,
        "result_display": "—" if result is None else _format_number(result),
        "raw_value": result,
        "reference_range": reference,
        "status": status,
        "risk_level": "unknown" if result is None else "attention" if result >= high_threshold else "normal",
        "formula": formula,
        "interpretation": _p03_index_text(label, result, high_threshold),
    }


def _p03_banded_index(
    code: str,
    left: float | None,
    right: float | None,
    label: str,
    reference: str,
    *,
    formula_template: str,
    normal_threshold: float = 2.0,
    warning_threshold: float | None = None,
    high_threshold: float = 3.0,
    extra_values: dict[str, float | None] | None = None,
) -> dict[str, Any]:
    result = None if left in (None, 0) or right in (None, 0) else round(float(left) / float(right), 2)
    formula = "待补充数据后计算"
    if result is not None:
        values = {
            "left": _format_number(float(left)),
            "right": _format_number(float(right)),
            "result": _format_number(result),
        }
        if extra_values:
            values.update({key: _format_number(value) if value is not None else "—" for key, value in extra_values.items()})
        formula = formula_template.format(**values)

    if result is None:
        status = "需补充数据"
        risk_level = "unknown"
    elif result < normal_threshold:
        status = "正常"
        risk_level = "normal"
    elif warning_threshold is not None and result < warning_threshold:
        status = "临界"
        risk_level = "warning"
    elif warning_threshold is not None and result <= high_threshold:
        status = "轻度抗性"
        risk_level = "attention"
    elif result <= high_threshold:
        status = "临界"
        risk_level = "warning"
    else:
        status = "重度抗性" if warning_threshold is not None else "高风险"
        risk_level = "attention"

    return {
        "code": code,
        "name": label,
        "result_display": "—" if result is None else _format_number(result),
        "raw_value": result,
        "reference_range": reference,
        "status": status,
        "risk_level": risk_level,
        "formula": formula,
        "interpretation": _p03_banded_index_text(label, result, normal_threshold, high_threshold, warning_threshold=warning_threshold),
    }


def _p03_difference(
    left: float | None,
    right: float | None,
    label: str,
    reference: str,
    *,
    high_threshold: float,
) -> dict[str, Any]:
    result = None if left is None or right is None else round(left - right, 2)
    formula = "待补充数据后计算" if result is None else f"{label} = {_format_number(left)} - {_format_number(right)} = {_format_number(result)} mmol/L（{reference}）"
    return {
        "code": "non_hdl_c",
        "name": label,
        "result_display": "—" if result is None else _format_number(result),
        "raw_value": result,
        "reference_range": reference,
        "status": "需补充数据" if result is None else "升高" if result >= high_threshold else "正常",
        "risk_level": "unknown" if result is None else "attention" if result >= high_threshold else "normal",
        "formula": formula,
        "interpretation": _p03_index_text(label, result, high_threshold),
    }


def _p03_status(code: str, value: float | None, display: str, reference_range: str = "") -> tuple[str, str]:
    if value is None:
        return ("需补充数据" if display == "—" else display, "unknown")
    if code == "tg" and value > 1.71:
        return "升高", "attention"
    if code == "hdl_c" and value < 1.16:
        return "偏低", "attention"
    if code == "glucose" and value > 6.1:
        return "偏高", "attention"
    if code == "hba1c" and value > 6.2:
        return "偏高", "attention"
    if code == "ldl_c" and value > 3.36:
        return "升高", "attention"
    if code == "tch" and value > 6.2:
        return "升高", "attention"
    if code == "apo_a1" and value < 1.2:
        return "偏低", "attention"
    if code == "apo_b" and value > 1.05:
        return "升高", "attention"
    if code == "apo_a1_b_ratio" and value <= 1:
        return "偏低", "attention"
    if code == "lp_a" and value > 300:
        return "升高", "attention"
    if code == "c_peptide" and (value < 0.81 or value > 3.85):
        return "异常", "attention"
    if code == "insulin" and (value < 3 or value > 25):
        return "异常", "attention"
    reference_status = _p03_status_from_reference(code, value, reference_range)
    if reference_status:
        return reference_status
    return "正常", "normal"


def _p03_status_from_reference(code: str, value: float, reference_range: str) -> tuple[str, str] | None:
    for lower, upper in _p03_parse_reference_bounds(reference_range):
        if lower is not None and value < lower:
            return "偏低", "attention"
        if upper is not None and value > upper:
            return _p03_high_status(code), "attention"
        if lower is not None or upper is not None:
            return "正常", "normal"
    return None


def _p03_parse_reference_bounds(reference_range: str) -> list[tuple[float | None, float | None]]:
    text = str(reference_range or "")
    text = text.replace("～", "-").replace("—", "-").replace("–", "-").replace("至", "-")
    bounds: list[tuple[float | None, float | None]] = []

    for match in re.findall(r"(?:<=|≤|<)\s*(\d+(?:\.\d+)?)", text):
        bounds.append((None, float(match)))
    for match in re.findall(r"(?:>=|≥|>)\s*(\d+(?:\.\d+)?)", text):
        bounds.append((float(match), None))
    for lower_text, upper_text in re.findall(r"(\d+(?:\.\d+)?)\s*(?:--|-|~)\s*(\d+(?:\.\d+)?)", text):
        lower = float(lower_text)
        upper = float(upper_text)
        bounds.append((lower, upper) if lower <= upper else (upper, lower))

    return bounds


def _p03_high_status(code: str) -> str:
    if code in {"tg", "tch", "ldl_c", "apo_b", "lp_a"}:
        return "升高"
    return "偏高"


def _p03_indicator_name(code: str) -> str:
    names = {
        "glucose": "空腹血糖",
        "alb": "白蛋白",
        "gsp": "糖化血清蛋白",
        "hba1c": "糖化血红蛋白",
        "avg_glucose": "平均血糖",
        "hba1": "糖化血红蛋白A1",
        "hba1ab": "糖化血红蛋白A1ab",
        "insulin": "胰岛素",
        "c_peptide": "C肽",
        "tg": "甘油三酯",
        "tch": "总胆固醇",
        "hdl_c": "高密度脂蛋白",
        "ldl_c": "低密度脂蛋白",
        "apo_a1": "载脂蛋白A1",
        "apo_b": "载脂蛋白B",
        "apo_a1_b_ratio": "载脂蛋白A1/载脂蛋白B",
        "lp_a": "脂蛋白a",
        "tg_hdl_ratio": "TG/HDL-C",
        "homa_ir": "HOMA-IR",
        "non_hdl_c": "非HDL-C",
    }
    return names.get(code, "该指标")


def _p03_indicator_text(code: str, display: str, status: str) -> str:
    if display == "—":
        return "该指标暂未从OCR结果中识别，建议人工补充或调整OCR策略。"
    return f"{_p03_indicator_name(code)}结果为{display}，评估状态为{status}。建议结合其他代谢指标和生活方式信息综合判断。"


def _p03_index_text(label: str, value: float | None, threshold: float) -> str:
    if value is None:
        return f"{label}暂缺计算所需指标，建议人工补充后再评估。"
    if value >= threshold:
        return f"{label}为{_format_number(value)}，高于参考阈值，提示糖脂代谢风险需要关注。"
    return f"{label}为{_format_number(value)}，当前未超过参考阈值。"


def _p03_banded_index_text(
    label: str,
    value: float | None,
    normal_threshold: float,
    high_threshold: float,
    *,
    warning_threshold: float | None = None,
) -> str:
    if value is None:
        return f"{label}暂缺计算所需指标，建议人工补充后再评估。"
    display = _format_number(value)
    if value < normal_threshold:
        return f"{label}为{display}，处于理想范围，当前关键平衡指数未见明显异常。"
    if warning_threshold is not None:
        if value < warning_threshold:
            return f"{label}为{display}，处于临界范围，建议结合饮食、运动、体重和复查结果持续观察。"
        if value <= high_threshold:
            return f"{label}为{display}，提示存在轻度胰岛素抵抗，需要关注血糖与体重管理。"
        return f"{label}为{display}，提示胰岛素抵抗风险较高，建议重点复核并尽快开展生活方式干预。"
    if value <= high_threshold:
        return f"{label}为{display}，处于临界范围，建议结合饮食、运动、体重和复查结果持续观察。"
    return f"{label}为{display}，高于高风险阈值，提示糖脂代谢及心血管相关风险需要重点关注。"


def _p03_risk_count(items: list[dict[str, Any]], level: str) -> int:
    return sum(1 for item in items if str(item.get("risk_level")) == level)


def _p03_risk_label(items: list[dict[str, Any]]) -> str:
    if _p03_risk_count(items, "attention"):
        return "高风险"
    if _p03_risk_count(items, "warning"):
        return "临界风险"
    return "正常"


def _p03_abnormal_summary(items: list[dict[str, Any]]) -> str:
    parts: list[str] = []
    for item in items:
        level = str(item.get("risk_level"))
        if level not in {"attention", "warning"}:
            continue
        name = str(item.get("name") or item.get("code") or "指标")
        status = str(item.get("status") or "需关注")
        parts.append(f"{name}{status}")
    return "、".join(parts)


def _p03_risk_assessment(risk_label: str, cardiovascular_items: list[dict[str, Any]]) -> str:
    abnormal_summary = _p03_abnormal_summary(cardiovascular_items)
    if risk_label == "正常":
        return "当前血脂相关指标及关键平衡指数未见明显心血管风险线索，建议维持健康生活方式并定期复查。"
    if risk_label == "临界风险":
        return f"当前{abnormal_summary or '部分指标'}处于临界或需关注状态，建议结合血压、腰围、体重、既往史和生活方式资料进行人工审查。"
    return f"当前存在{abnormal_summary or '多项血脂相关异常'}等风险线索，提示心血管代谢风险升高，建议进行生活方式干预并由专业人员复核。"


def _p03_core_summary(
    tg: dict[str, Any],
    hdl_c: dict[str, Any],
    glucose: dict[str, Any],
    homa_ir: dict[str, Any],
    risk_count: int,
) -> str:
    parts: list[str] = []
    for name, item in [("TG", tg), ("HDL-C", hdl_c), ("GLU", glucose), ("HOMA-IR", homa_ir)]:
        if str(item.get("risk_level")) in {"attention", "warning"}:
            parts.append(f"{name}{item.get('status')}")
    if parts:
        return "存在" + "、".join(parts) + "等糖脂代谢风险线索。"
    if risk_count == 0:
        return "当前核心糖脂代谢指标未见明显风险线索。"
    return "存在部分糖脂代谢指标需关注，建议结合生活方式资料人工复核。"


def _p03_overall_summary(
    overall_level: str,
    tg: dict[str, Any],
    hdl_c: dict[str, Any],
    glucose: dict[str, Any],
    homa_ir: dict[str, Any],
) -> str:
    return (
        f"糖脂代谢总体评估为{overall_level}。"
        f"甘油三酯：{tg.get('result_display')}（{tg.get('status')}）；"
        f"HDL-C：{hdl_c.get('result_display')}（{hdl_c.get('status')}）；"
        f"空腹血糖：{glucose.get('result_display')}（{glucose.get('status')}）；"
        f"HOMA-IR：{homa_ir.get('result_display')}（{homa_ir.get('status')}）。"
        "当前为规则化初步摘要，AI综合解读生成后可进入人工审查。"
    )


def _safe_float(value: Any) -> float | None:
    if value in (None, ""):
        return None
    text = str(value).replace(",", "")
    number = ""
    for char in text:
        if char.isdigit() or char == ".":
            number += char
        elif number:
            break
    if not number:
        return None
    try:
        return float(number)
    except ValueError:
        return None


def _parse_age_number(value: Any) -> int | None:
    parsed = _safe_float(value)
    if parsed is None:
        return None
    try:
        return int(parsed)
    except (TypeError, ValueError):
        return None


def _numeric_display(value: float | None, fallback: Any = "") -> str:
    if value is None:
        fallback_text = str(fallback or "").strip()
        return fallback_text or "—"
    return _format_number(value)


def _format_number(value: float | None) -> str:
    if value is None:
        return "—"
    return f"{value:.2f}".rstrip("0").rstrip(".")


def _is_positive(test: dict[str, Any]) -> bool:
    return _has_positive_result_signal(f"{test.get('result', '')}{test.get('indicator', '')}")


def _has_positive_result_signal(value: Any) -> bool:
    text = "".join(str(value or "").split())
    if not text:
        return False
    if "↑" in text or "升高" in text:
        return True
    if "阳性" not in text and "弱阳" not in text:
        return False
    if any(phrase in text for phrase in ("阴性", "未见阳性", "未发现阳性", "无阳性", "均未见阳性", "均为阴性")):
        return text.startswith("阳性") or "弱阳性" in text or "阳性项目" in text
    return True


def _is_total_ige_positive(test: dict[str, Any]) -> bool:
    return _has_positive_result_signal(_test_display(test))


def _is_total_ige_negative(test: dict[str, Any]) -> bool:
    display = _test_display(test)
    return "阴性" in display and not _is_total_ige_positive(test)


def _allergen_names(positive_allergens: list[dict[str, Any]], *, limit: int = 3) -> str:
    names = [str(test.get("test_name") or "").strip() for test in positive_allergens]
    names = [name for name in names if name]
    if not names:
        return ""
    shown = names[:limit]
    suffix = "等" if len(names) > limit else ""
    return "、".join(shown) + suffix


def _test_display(test: dict[str, Any]) -> str:
    result = str(test.get("result") or "未识别")
    indicator = str(test.get("indicator") or "")
    if indicator in {"↑", "↓"}:
        return f"{result}（{indicator}）"
    return f"{result}{indicator}"


def _allergen_item_display(test: dict[str, Any]) -> str:
    indicator = str(test.get("indicator") or "")
    result = str(test.get("result") or "")
    suffix = f"{result}{indicator}" if indicator else result
    return f"{test.get('test_name', '')}：{suffix}"


def _allergen_overall_display(positive_allergens: list[dict[str, Any]]) -> str:
    if not positive_allergens:
        return "所有检测项目均为阴性"
    return "阳性项目：" + "、".join(_allergen_item_display(test) for test in positive_allergens)


def _lab_result(test: dict[str, Any]) -> dict[str, Any]:
    return {
        "page": test.get("page"),
        "specimen_type": test.get("specimen_type", ""),
        "item_name": test.get("test_name", ""),
        "result": test.get("result", ""),
        "indicator": test.get("indicator", ""),
        "result_display": _test_display(test),
        "reference_range": test.get("reference_range", ""),
        "unit": test.get("unit", ""),
        "method": test.get("method", ""),
    }


def _p06_find_test(tests: list[dict[str, Any]], item_code: str) -> dict[str, Any]:
    for test in tests:
        if str(test.get("item_code") or "") == item_code:
            return test
    return {}


def _p06_immune_cell(tests: list[dict[str, Any]], item_code: str) -> dict[str, Any]:
    test = _p06_find_test(tests, item_code)
    return {
        "absolute_result": str(test.get("result") or "—"),
        "percentage_result": str(test.get("percentage_result") or "—"),
        "absolute_reference": str(test.get("reference_range") or "—"),
        "percentage_reference": str(test.get("percentage_reference") or "—"),
        "status": str(test.get("indicator") or "待复核"),
    }


def _p06_cytokine(tests: list[dict[str, Any]], item_code: str) -> dict[str, Any]:
    test = _p06_find_test(tests, item_code)
    return {
        "result_display": _test_display(test) if test else "—",
        "reference_range": str(test.get("reference_range") or "—"),
        "status": str(test.get("indicator") or "待复核"),
    }


def _p06_tests_map(tests: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    mapped: dict[str, dict[str, Any]] = {}
    for test in tests:
        code = str(test.get("item_code") or "")
        if not code:
            continue
        mapped[code] = {
            "item_name": str(test.get("test_name") or code),
            "result_display": str(test.get("result") or ""),
            "reference_range": str(test.get("reference_range") or ""),
            "unit": str(test.get("unit") or ""),
            "method": str(test.get("method") or ""),
            "status": _p06_status_text(test.get("indicator")),
        }
    return mapped


def _p06_status_text(value: Any) -> str:
    text = str(value or "").strip()
    if text in {"", "正常"}:
        return "正常"
    if text in {"升高", "偏高", "↑"}:
        return "升高"
    if text in {"偏低", "降低", "↓"}:
        return "偏低"
    return text


def _p06_elevated_test_names(tests_map: dict[str, dict[str, Any]], codes: list[str]) -> list[str]:
    names: list[str] = []
    for code in codes:
        item = tests_map.get(code, {})
        if item.get("status") == "升高":
            names.append(str(item.get("item_name") or code))
    return names


def _p06_immune_detail_summary(tests_map: dict[str, dict[str, Any]]) -> str:
    focus_codes = ["lym", "t_cell", "nk", "ctl", "th", "gzm_b_nk", "ifn_gamma_nk", "gzm_b_ctl", "ifn_gamma_ctl"]
    parts: list[str] = []
    for code in focus_codes:
        item = tests_map.get(code)
        if not item:
            continue
        parts.append(f"{item['item_name']}{item['result_display']}")
    return "；".join(parts[:6]) + ("。" if parts else "当前未提取到完整免疫细胞结果。")


def _p06_cytokine_detail_summary(tests_map: dict[str, dict[str, Any]]) -> str:
    elevated = _p06_elevated_test_names(tests_map, ["il_8", "tnf_alpha", "hs_crp"])
    if elevated:
        details: list[str] = []
        for code in ["il_8", "tnf_alpha", "hs_crp"]:
            item = tests_map.get(code)
            if item and item.get("status") == "升高":
                details.append(f"{item['item_name']}{item['result_display']}，参考范围{item['reference_range']}")
        return "；".join(details) + "，提示促炎或炎症指标信号升高。"
    return "本次 IL-8、TNF-α 与 hs-CRP 未见明显升高，细胞因子及炎症指标整体处于相对稳定状态。"


def _p06_overall_summary(immune_ok: bool, inflammatory_high: bool) -> str:
    if immune_ok and inflammatory_high:
        return "免疫细胞数量与活性整体稳定，但促炎因子提示慢性炎症风险，需要优先开展抗炎与抗氧化管理。"
    if immune_ok:
        return "免疫细胞数量与活性整体稳定，当前未见明显异常炎症风险，可继续保持长期健康管理与定期复评。"
    if inflammatory_high:
        return "免疫稳态与促炎因子存在需要关注的信号，建议结合原始报告、症状和既往史进行人工复核。"
    return "当前结果提示基础免疫与炎症状态总体可控，建议继续监测并保持规律生活方式。"


def _age_display(age: Any) -> str:
    if age in (None, ""):
        return ""
    value = str(age)
    return value if "岁" in value else f"{value}岁"


def _date_display(value: str) -> str:
    if not value:
        return ""
    try:
        parsed = datetime.strptime(value[:10], "%Y-%m-%d")
        return f"{parsed.year}年{parsed.month}月{parsed.day}日"
    except ValueError:
        return value


def _method_summary(tests: list[dict[str, Any]]) -> str:
    methods: list[str] = []
    for test in tests:
        method = str(test.get("method") or "")
        if method and method not in methods:
            methods.append(method)
    return "、".join(methods) or "OCR结构化检验结果综合评估"


def _calprotectin_interpretation(test: dict[str, Any]) -> str:
    display = _test_display(test)
    if "阴性" in display:
        return "粪便钙卫蛋白检测结果为阴性，当前未见明显肠道炎症活动相关信号。仍建议结合腹痛、腹泻、便血、用药史等情况进行综合判断。"
    return f"粪便钙卫蛋白检测结果为{display}，提示肠道炎症相关指标需要关注。建议结合临床症状、近期饮食、感染史及其他检查结果进行综合评估。"


def _total_ige_interpretation(test: dict[str, Any]) -> str:
    display = _test_display(test)
    if "阳性" in display or "↑" in display:
        return f"特异性总IgE检测结果为{display}，提示机体存在过敏相关免疫反应或高反应状态，需要结合过敏原明细和实际症状进一步评估。"
    if "阴性" in display:
        return "特异性总IgE检测结果为阴性，当前未见明显IgE相关整体免疫高反应信号。"
    return "特异性总IgE结果尚需人工复核。"


def _allergen_interpretation(positive_allergens: list[dict[str, Any]]) -> str:
    if not positive_allergens:
        return "本次常见吸入性和食物过敏原检测未见阳性项目。若仍存在相关症状，可结合饮食记录、环境暴露和迟发反应继续观察。"
    names = "、".join(_allergen_item_display(test) for test in positive_allergens)
    return f"本次过敏原检测发现{names}。建议结合皮肤、呼吸道、消化道症状及近期暴露史进行人工复核，并将相关项目纳入健康管理建议。"


def _overall_summary(calprotectin: dict[str, Any], total_ige: dict[str, Any], positive_allergens: list[dict[str, Any]]) -> str:
    parts = [
        f"粪便钙卫蛋白：{_test_display(calprotectin)}",
        f"特异性总IgE：{_test_display(total_ige)}",
    ]
    if positive_allergens:
        parts.append(f"过敏原阳性项目 {len(positive_allergens)} 项")
    else:
        parts.append("过敏原明细未见阳性项目")
    return "；".join(parts) + "。当前摘要由OCR结构化结果自动生成，AI综合诊断内容待后续接入DeepSeek后进一步完善。"


def _followup_advice(calprotectin: dict[str, Any], total_ige: dict[str, Any], positive_allergens: list[dict[str, Any]]) -> str:
    advice = ["建议健康管理师先核对OCR识别结果、参考范围和报告页码，确认无误后再进入AI解读和人工审查。"]
    if positive_allergens:
        advice.append("如存在过敏相关症状，建议结合阳性过敏原、饮食记录和环境暴露情况进行分层管理。")
    elif _is_total_ige_positive(total_ige):
        advice.append("如存在过敏相关症状，建议结合总IgE结果、饮食记录和环境暴露情况进行分层管理。")
    if "阴性" not in _test_display(calprotectin):
        advice.append("如伴随肠道症状，建议进一步结合炎症、感染、用药和饮食因素评估肠道状态。")
    return "".join(advice)


def _immune_system_summary(total_ige: dict[str, Any], positive_allergens: list[dict[str, Any]]) -> str:
    if _is_total_ige_positive(total_ige) or positive_allergens:
        return "总IgE或过敏原项目提示免疫高反应相关线索，需结合肠道屏障、饮食暴露和症状表现综合评估。"
    return "当前IgE相关项目未见明显异常，后续可结合肠道功能、饮食结构和生活方式继续进行健康管理。"


def _inflammation_immune_advice(calprotectin: dict[str, Any], total_ige: dict[str, Any], positive_allergens: list[dict[str, Any]]) -> str:
    if _is_total_ige_positive(total_ige) or positive_allergens:
        review_focus = "建议在人工审查阶段重点核对钙卫蛋白、总IgE和过敏原阳性项目。"
    else:
        review_focus = "建议在人工审查阶段重点核对钙卫蛋白、总IgE和过敏原结果是否与原始报告一致。"
    return review_focus + "AI诊断接入前，本段仅作为基于OCR结果的初步健康管理提示，不替代最终医学审核意见。"


def _microbiome_advice(total_ige: dict[str, Any], positive_allergens: list[dict[str, Any]]) -> str:
    base = "建议通过饮食调整（如增加膳食纤维、益生元）、益生菌补充和生活方式干预，优化肠道微生态环境。"
    if _is_total_ige_positive(total_ige):
        return base + "结合总IgE结果，饮食调整应同步参考实际症状、暴露记录和人工复核意见。"
    if positive_allergens:
        names = _allergen_names(positive_allergens)
        return base + f"结合本次过敏原阳性项目{names or ''}，应记录相关食物或环境暴露与症状之间的关联。"
    if _is_total_ige_negative(total_ige):
        return base + "本次总IgE及已检测过敏原未见阳性，饮食调整以肠道耐受、膳食多样性和症状记录为主。"
    return base + "总IgE或过敏原信息尚需人工核对，相关饮食限制不宜仅凭占位内容扩大。"


def _barrier_leaky_gut_impact(total_ige: dict[str, Any], positive_allergens: list[dict[str, Any]]) -> str:
    if _is_total_ige_positive(total_ige):
        return "当肠道屏障受损时，可能导致肠漏症，引发全身炎症、食物敏感、自身免疫性疾病等健康问题。结合总IgE结果，肠道屏障功能受损可能加剧免疫系统的过度反应。"
    if positive_allergens:
        names = _allergen_names(positive_allergens)
        return f"当肠道屏障受损时，可能导致肠漏症，引发全身炎症、食物敏感等健康问题。结合本次过敏原阳性项目{names or ''}，需关注屏障状态与实际症状的关系。"
    if _is_total_ige_negative(total_ige):
        return "当肠道屏障受损时，可能导致肠漏症，引发全身炎症、食物敏感等健康问题。本次总IgE及已检测过敏原未见阳性，屏障管理可重点围绕黏膜修复、炎症控制和饮食耐受进行。"
    return "当肠道屏障受损时，可能导致肠漏症，引发全身炎症、食物敏感等健康问题。总IgE或过敏原信息尚需人工核对，相关判断应以原始报告结果为准。"


def _barrier_improvement_advice(total_ige: dict[str, Any], positive_allergens: list[dict[str, Any]]) -> str:
    base = "通过修复肠道黏膜的营养素（如谷氨酰胺、胶原蛋白）、避免炎症性食物和管理压力，有助于恢复肠道屏障功能。"
    if _is_total_ige_positive(total_ige) or positive_allergens:
        return base + "建议结合总IgE、过敏原项目、症状和饮食记录，识别可能诱发免疫反应的食物或环境因素。"
    if _is_total_ige_negative(total_ige):
        return base + "本次IgE相关项目未见阳性，不建议仅凭本次结果扩大忌口，可优先关注个人耐受和炎症诱因。"
    return base + "如总IgE或过敏原结果尚未确认，建议先完成原始报告核对后再制定具体限制。"


def _diet_gut_advice(calprotectin: dict[str, Any]) -> str:
    if _is_positive(calprotectin):
        return "根据您的肠道评估结果，可优先采用温和抗炎、低刺激的饮食框架，增加可溶性膳食纤维和发酵食物，并结合症状记录评估是否短期尝试低FODMAP等方案。"
    return "根据您的肠道评估结果，饮食管理以规律三餐、膳食多样性、足量膳食纤维和发酵食物为主，并通过饮食-症状记录识别个人不耐受。"


def _diet_personalized_advice(total_ige: dict[str, Any], positive_allergens: list[dict[str, Any]]) -> str:
    if _is_total_ige_positive(total_ige) and not positive_allergens:
        return "鉴于总IgE结果提示需要关注，即使特定过敏原检测为阴性，仍建议通过饮食与症状记录观察常见致敏食物反应；是否尝试短期排除饮食需经人工复核后决定。"
    if positive_allergens:
        names = _allergen_names(positive_allergens)
        return f"本次发现过敏原阳性项目{names or ''}，饮食建议应优先围绕已确认项目、近期摄入记录和实际症状进行人工复核，避免自行进行长期、大范围忌口。"
    if _is_total_ige_negative(total_ige):
        return "本次总IgE及已检测过敏原均未见阳性，不建议仅凭本次结果进行大范围排除饮食。可先记录饮食与症状，优先减少明确诱发不适的食物。"
    return "总IgE或过敏原结果尚需人工核对，个性化饮食建议应先以膳食均衡、症状记录和已确认的不耐受信息为依据。"


def _stress_management_advice(total_ige: dict[str, Any], positive_allergens: list[dict[str, Any]]) -> str:
    base = "肠道与大脑通过“肠脑轴”紧密相连。长期压力会影响肠道功能，导致炎症和菌群失衡。"
    if _is_total_ige_positive(total_ige) or positive_allergens:
        return base + "结合本次免疫相关线索，有效的压力管理对稳定免疫功能尤为重要。建议通过冥想、瑜伽、充足睡眠等方式管理压力。"
    if _is_total_ige_negative(total_ige):
        return base + "本次IgE相关项目未见阳性，仍建议通过冥想、瑜伽、充足睡眠等方式管理压力，支持肠道修复和免疫稳态。"
    return base + "在总IgE或过敏原结果确认前，建议先通过冥想、瑜伽、充足睡眠等方式管理压力，支持肠道修复。"


def _functional_medicine_advice(total_ige: dict[str, Any], positive_allergens: list[dict[str, Any]]) -> str:
    base = "在专业医生指导下，可考虑采用功能医学方法，如清除病原体、修复肠道、重新接种益生菌等，进行系统性干预。"
    if _is_total_ige_positive(total_ige) or positive_allergens:
        return base + "结合本次免疫相关线索，可能需要特别关注免疫调节相关的营养素和干预手段。"
    if _is_total_ige_negative(total_ige):
        return base + "本次IgE相关项目未见阳性，营养补充重点可放在屏障修复、菌群支持和炎症稳态上。"
    return base + "若总IgE或过敏原结果尚未确认，免疫调节相关建议需等待人工复核后再细化。"
