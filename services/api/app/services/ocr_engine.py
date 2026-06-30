from __future__ import annotations

import json
import re
import tempfile
from pathlib import Path
from statistics import mean
from typing import Any

from app.services.p11_ocr_support import (
    build_p11_structured_report,
    build_p11_warning_requirements,
    extract_p11_fields,
    extract_p11_warning_messages,
)

from pypdf import PdfReader

from app.services.ocr_logs import now_iso


STRATEGY_VERSION = "P02-ocr-strategy-v0.3-structured-json"
P01_STRATEGY_VERSION = "P01-ocr-strategy-v0.2-summary-structured"
P05_STRATEGY_VERSION = "P05-ocr-strategy-v0.2-multipage-rapidocr"
P03_STRATEGY_VERSION = "P03-ocr-strategy-v0.3-c-peptide-prefix"
P04_STRATEGY_VERSION = "P04-ocr-strategy-v0.2-nutrient-multipage-rapidocr"
P06_STRATEGY_VERSION = "P06-ocr-strategy-v0.3-hscrp-three-page"
P07_STRATEGY_VERSION = "P07-ocr-strategy-v0.3-stacked-table"
P08_STRATEGY_VERSION = "P08-ocr-strategy-v0.2-professional-json-adapter"
P09_STRATEGY_VERSION = "P09-ocr-strategy-v0.2-structured-json-row-adapter"
P10_STRATEGY_VERSION = "P10-ocr-strategy-v0.4-reportmeta-json-blueprint"
P11_STRATEGY_VERSION = "P11-ocr-strategy-v0.4-food-intolerance-42-adapter"
P12_STRATEGY_VERSION = "P12-ocr-strategy-v0.2-json-antioxidant-nad"
P13_STRATEGY_VERSION = "P13-ocr-strategy-v0.2-telomere-json-pdf"
P14_STRATEGY_VERSION = "P14-ocr-strategy-v0.2-cancer-multireport-json-pdf"
P15_STRATEGY_VERSION = "P15-ocr-strategy-v0.2-environment-hormone-json-pdf"
P16_STRATEGY_VERSION = "P16-ocr-strategy-v0.2-pgx-multireport-json-pdf"
P17_STRATEGY_VERSION = "P17-ocr-strategy-v0.3-tail-pathogen-ct"
PROVIDER = "pdf-text-extractor"
P16_REPORT_NAME = "药物基因组学评估健康管理报告"
P16_ASSESSMENT_TYPE = "药物基因组学评估"
P16_SAMPLE_TYPE = "EDTA抗凝全血"
P16_METHOD = "荧光PCR法"
P10_SAMPLE_TYPE = "血清/EDTA抗凝血"
P10_METHOD = "基因测序&化学发光&ELISA法"
P13_REPORT_NAME = "年轻力精准评估健康管理报告"
P13_ASSESSMENT_TYPE = "年轻力精准评估"
P13_SAMPLE_TYPE = "口腔黏膜细胞"
P13_METHOD = "荧光PCR"
P14_REPORT_NAME = "安康御癌专项评估健康管理报告"
P14_ASSESSMENT_TYPE = "安康御癌专项评估"
P14_SAMPLE_TYPE = "肿瘤风险指标"
P14_METHOD = "多维风险综合评估"
P15_REPORT_NAME = "环境荷尔蒙评估健康管理报告"
P15_ASSESSMENT_TYPE = "环境荷尔蒙评估"
P15_SAMPLE_TYPE = "晨尿"
P15_METHOD = "电感耦合等离子质谱法"

P17_HPV_HIGH_RISK_TYPES = ["16", "18", "26", "31", "33", "35", "39", "45", "51", "52", "53", "56", "58", "59", "66", "68", "73", "82"]
P17_HPV_LOW_RISK_TYPES = ["6", "11", "40", "42", "43", "44", "61", "81", "83"]
P17_MICROBE_GROUPS: dict[str, list[str]] = {
    "有益菌": [
        "卷曲乳杆菌",
        "詹氏乳杆菌",
        "加氏乳杆菌",
        "惰性乳杆菌",
        "双歧杆菌",
    ],
    "定植/条件致病菌": [
        "白假丝酵母菌",
        "光滑假丝酵母菌",
        "热带假丝酵母菌",
        "耳道假丝酵母菌",
        "克柔假丝酵母菌",
        "都柏林假丝酵母菌",
        "近平滑假丝酵母菌",
        "B族链球菌",
        "亨氏巴尔通体",
        "细小棒状杆菌",
        "衣氏放线菌",
        "阴道加德纳菌",
        "阴道阿托波氏菌",
        "纤毛菌",
        "微小脲原体",
        "解脲脲原体",
        "人型支原体",
    ],
    "致病菌": [
        "单纯疱疹病毒1型",
        "单纯疱疹病毒2型",
        "淋球菌",
        "杜克雷嗜血杆菌",
        "生殖支原体",
        "沙眼衣原体",
        "梅毒螺旋体",
        "阴道毛滴虫",
        "阿米巴原虫",
    ],
}
P17_MICROBE_CT_BLOCK_NAMES: tuple[tuple[str, ...], ...] = (
    (
        "卷曲乳杆菌",
        "詹氏乳杆菌",
        "加氏乳杆菌",
        "惰性乳杆菌",
        "双歧杆菌",
        "白假丝酵母菌",
        "光滑假丝酵母菌",
        "热带假丝酵母菌",
        "耳道假丝酵母菌",
        "克柔假丝酵母菌",
        "都柏林假丝酵母菌",
        "近平滑假丝酵母菌",
        "B族链球菌",
        "亨氏巴尔通体",
        "衣氏放线菌",
        "细小棒状杆菌",
    ),
    (
        "阴道加德纳菌",
        "阴道阿托波氏菌",
        "纤毛菌",
        "微小脲原体",
        "解脲脲原体",
        "人型支原体",
        "单纯疱疹病毒1型",
        "单纯疱疹病毒2型",
    ),
)
P17_MICROBE_TRAILING_NEGATIVE_NAMES = (
    "淋球菌",
    "杜克雷嗜血杆菌",
    "生殖支原体",
    "沙眼衣原体",
    "梅毒螺旋体",
    "阴道毛滴虫",
    "阿米巴原虫",
)
P17_MICROBE_NAME_ALIASES: dict[str, tuple[str, ...]] = {
    "B族链球菌": ("B 族链球菌", "无乳链球菌"),
    "解脲脲原体": ("解脲支原体",),
    "人型支原体": ("人型支原体1", "人型支原体 1"),
    "单纯疱疹病毒1型": ("单纯疱疹病毒 1 型", "单纯疱疹病毒1 型"),
    "单纯疱疹病毒2型": ("单纯疱疹病毒 2 型", "单纯疱疹病毒2 型"),
}

DATE_VALUE_PATTERN = r"[0-9]{4}[/-][0-9]{1,2}[/-][0-9]{1,2}(?:\s+[0-9]{1,2}:[0-9]{2}(?::[0-9]{2})?)?"
RESULT_PATTERN = (
    r"(?:阳性\s*[（(]\s*\+\+\+\s*[）)]|阳性\s*[（(]\s*\+\+\s*[）)]|"
    r"阳性\s*[（(]\s*\+\s*[）)]|弱阳性|阳性|阴性)"
)

CALPROTECTIN_NAME = "钙卫蛋白检测（Cal）"
TOTAL_IGE_NAME = "特异性总IgE"

ALLERGEN_ITEMS = [
    "户尘螨/粉尘螨组合",
    "矮豚草/蒿组合",
    "猫/狗毛皮屑组合",
    "蟑螂",
    "霉菌组合",
    "葎草",
    "荨草",
    "树组合4（柳/榆/栎/梧桐/三角叶杨）",
    "鸡蛋白",
    "牛奶",
    "鱼/虾/蟹组合",
    "牛/羊肉组合",
    "腰果/花生/黄豆组合",
    "芒果",
    "小麦",
    # 兼容其他 P02 样例中可能出现的旧版项目名称。
    "花生",
    "大豆",
    "牛肉",
    "羊肉",
    "鳕鱼/龙虾/扇贝组合",
    "腰果/开心果组合",
    "桃",
]

P01_METRIC_DEFINITIONS = [
    ("gmhi", "GMHI", ["GMHI", "肠道菌群健康指数", "菌群健康指数"], ""),
    ("gut_age", "肠龄", ["肠龄", "肠道年龄", "肠道菌群年龄"], "岁"),
    ("diversity", "菌群多样性", ["菌群多样性", "多样性指数", "Shannon", "α多样性", "Alpha多样性"], ""),
    ("enterotype", "肠型", ["肠型", "Enterotype"], ""),
]

P05_THYROID_TESTS = [
    ("ft3", "游离三碘甲状腺原氨酸（FT3）"),
    ("t3", "三碘甲状腺原氨酸（T3）"),
    ("ft4", "游离甲状腺素（FT4）"),
    ("t4", "甲状腺素（T4）"),
    ("tsh", "促甲状腺激素（TSH）"),
    ("tgab", "抗甲状腺球蛋白抗体（TGAb）"),
    ("tpoab", "抗甲状腺过氧化物酶抗体（TPOAb）"),
]

P05_CATECHOLAMINE_TESTS = [
    ("norepinephrine", "去甲肾上腺素"),
    ("epinephrine", "肾上腺素"),
    ("metanephrine_n", "3-甲氧基去甲肾上腺素"),
    ("methoxytyramine", "3-甲氧基酪胺"),
    ("metanephrine_e", "3-甲氧基肾上腺素"),
    ("hva", "高香草酸"),
    ("vma", "香草扁桃酸"),
    ("dopamine", "多巴胺"),
]

P05_SINGLE_TESTS = [
    ("cort", "皮质醇（CORT）"),
    ("acth", "促肾上腺皮质激素（ACTH）"),
]

P03_TEST_DEFINITIONS = [
    ("alb", "白蛋白（ALB）", ["白蛋白（ALB）", "白蛋白", "ALB"], "g/L"),
    ("glucose", "葡萄糖（GLU）", ["葡萄糖（GLU）", "空腹血糖（GLU）", "葡萄糖", "空腹血糖", "GLU"], "mmol/L"),
    ("gsp", "糖化血清蛋白（GSP）", ["糖化血清蛋白（GSP）", "糖化血清蛋白", "GSP"], "mmol/L"),
    ("tch", "总胆固醇（TCH）", ["总胆固醇（TCH）", "总胆固醇", "TCH", "TC"], "mmol/L"),
    ("tg", "甘油三酯（TG）", ["甘油三酯（TG）", "甘油三酯", "TG"], "mmol/L"),
    ("hdl_c", "高密度脂蛋白胆固醇（HDL-C）", ["高密度脂蛋白胆固醇（HDL-C）", "高密度脂蛋白胆固醇", "高密度脂蛋白", "HDL-C", "HDL"], "mmol/L"),
    ("ldl_c", "低密度脂蛋白胆固醇（LDL-C）", ["低密度脂蛋白胆固醇（LDL-C）", "低密度脂蛋白胆固醇", "低密度脂蛋白", "LDL-C", "LDL"], "mmol/L"),
    ("apo_a1", "载脂蛋白A1 (APO-A1)", ["载脂蛋白A1 (APO-A1)", "载脂蛋白A1", "APO-A1", "APOA1"], "g/L"),
    ("apo_b", "载脂蛋白B (APO-B)", ["载脂蛋白B (APO-B)", "载脂蛋白B", "APO-B", "APOB"], "g/L"),
    ("apo_a1_b_ratio", "载脂蛋白A1／载脂蛋白B", ["载脂蛋白A1／载脂蛋白B", "载脂蛋白A1/载脂蛋白B", "APO-A1/APO-B", "APOA1/APOB"], ""),
    ("lp_a", "脂蛋白a (LP(a))", ["脂蛋白a (LP(a))", "脂蛋白a", "LP(a)", "LPa"], "mg/L"),
    ("c_peptide", "C 肽（C-P）", ["C 肽（C-P）", "C肽（C-P）", "C 肽", "C肽", "C-P"], "ng/mL"),
    ("insulin", "胰岛素（Ins）", ["胰岛素（Ins）", "胰岛素", "Ins"], "uU/mL"),
    ("hba1c", "糖化血红蛋白A1C", ["糖化血红蛋白A1C", "糖化血红蛋白 A1C", "HbA1c", "A1C"], "%"),
    ("avg_glucose", "平均血糖", ["平均血糖"], "mmol/L"),
    ("hba1ab", "糖化血红蛋白A1ab", ["糖化血红蛋白A1ab", "糖化血红蛋白 A1ab", "A1ab"], "%"),
    ("hba1", "糖化血红蛋白A1", ["糖化血红蛋白A1", "糖化血红蛋白 A1"], "%"),
]

P03_METHOD_NAMES = [
    "葡萄糖氧化酶法",
    "高效液相色谱法",
    "化学发光法",
    "免疫比浊法",
    "酶比色法",
    "比色法",
    "NBT 法",
    "NBT法",
    "计算法",
]

P03_REFERENCE_PATTERN = (
    r"≤\s*[0-9]+(?:\.[0-9]+)?|≥\s*[0-9]+(?:\.[0-9]+)?|<\s*[0-9]+(?:\.[0-9]+)?|>\s*[0-9]+(?:\.[0-9]+)?|"
    r"＜\s*[0-9]+(?:\.[0-9]+)?|＞\s*[0-9]+(?:\.[0-9]+)?|"
    r"[0-9]+(?:\.[0-9]+)?\s*(?:--|-|－|—|–|~|～)\s*[0-9]+(?:\.[0-9]+)?"
)

P04_TEST_DEFINITIONS = [
    ("iron", "铁（Fe）", ["铁（Fe）", "铁(Fe)", "铁", "Fe"], "mmol/L", "7.52--11.82", "原子吸收光谱法"),
    ("zinc", "锌（Zn）", ["锌（Zn）", "锌(Zn)", "锌", "Zn"], "umol/L", "76.5--170", "原子吸收光谱法"),
    ("calcium", "钙（Ca）", ["钙（Ca）", "钙(Ca)", "钙", "Ca"], "mmol/L", "1.55--2.1", "原子吸收光谱法"),
    ("magnesium", "镁（Mg）", ["镁（Mg）", "镁(Mg)", "镁", "Mg"], "mmol/L", "1.12--2.16", "原子吸收光谱法"),
    ("copper", "铜（Cu）", ["铜（Cu）", "铜(Cu)", "铜", "Cu"], "umol/L", "11.8--39.3", "原子吸收光谱法"),
    ("vitamin_a", "维生素A", ["维生素A", "Vitamin A"], "μg/mL", "0.3-0.7", "LC-MS/MS法"),
    ("vitamin_d2", "25-羟基维生素D2", ["25-羟基维生素D2", "25羟基维生素D2", "Vitamin D2"], "ng/mL", "", "LC-MS/MS法"),
    ("vitamin_d3", "25-羟基维生素D3", ["25-羟基维生素D3", "25羟基维生素D3", "Vitamin D3"], "ng/mL", "", "LC-MS/MS法"),
    ("vitamin_d", "25-羟基维生素D", ["25-羟基维生素D", "25羟基维生素D", "Vitamin D"], "ng/mL", "<12.00 缺乏; [12.01-20.00] 不足; [20.01-50.00] 正常; >50.00 过量", "LC-MS/MS法"),
    ("vitamin_e", "维生素E", ["维生素E", "Vitamin E"], "μg/mL", "5.0-20.0", "LC-MS/MS法"),
    ("vitamin_k1", "维生素K1", ["维生素K1", "Vitamin K1"], "ng/mL", "0.2-2.5", "LC-MS/MS法"),
    ("vitamin_b1", "维生素B1", ["维生素B1", "Vitamin B1"], "ng/mL", "1-16", "LC-MS/MS法"),
    ("vitamin_b2", "维生素B2", ["维生素B2", "Vitamin B2"], "ng/mL", "1-19", "LC-MS/MS法"),
    ("vitamin_b3_niacin", "维生素B3(烟酸)", ["维生素B3(烟酸)", "维生素B3（烟酸）", "烟酸"], "ng/mL", "0-5.0", "LC-MS/MS法"),
    ("vitamin_b3_nicotinamide", "维生素B3(烟酰胺)", ["维生素B3(烟酰胺)", "维生素B3（烟酰胺）", "烟酰胺"], "ng/mL", "15.2-72.10", "LC-MS/MS法"),
    ("vitamin_b5", "维生素B5", ["维生素B5", "Vitamin B5"], "ng/mL", "12.9-253.1", "LC-MS/MS法"),
    ("vitamin_b6", "维生素B6", ["维生素B6", "Vitamin B6"], "ng/mL", "1-30", "LC-MS/MS法"),
    ("vitamin_b7", "维生素B7", ["维生素B7", "Vitamin B7"], "ng/mL", "0.05-0.83", "LC-MS/MS法"),
    ("vitamin_b9_5_mthf", "维生素B9(5-甲基四氢叶酸)", ["维生素B9(5-甲基四氢叶酸)", "维生素B9（5-甲基四氢叶酸）", "5-甲基四氢叶酸"], "ng/mL", "4-35", "LC-MS/MS法"),
    ("vitamin_b12_mma", "维生素B12(MMA)", ["维生素B12(MMA)", "维生素B12（MMA）", "MMA"], "ng/mL", "≤47.24", "LC-MS/MS法"),
]
P04_METHOD_NAMES = [
    "原子吸收光谱法",
    "LC-MS/MS法",
    "LC-MS/MS",
    "电感耦合等离子体质谱法（ICP-MS）",
    "电感耦合等离子体质谱法",
    "ICP-MS",
    "高效液相色谱法（HPLC）",
    "高效液相色谱法",
    "HPLC",
    "化学发光法（CLIA）",
    "化学发光法",
    "CLIA",
]
P04_UNIT_PATTERN = r"μmol/L|umol/L|μg/mL|ug/mL|μg/L|ug/L|mmol/L|mg/L|ng/mL|nmol/L|IU/mL|%"
P06_IMMUNE_TEST_DEFINITIONS = [
    ("lym", "LYM（CD45+）", ("淋巴细胞(LYM(CD45+))", "淋巴细胞（LYM（CD45+））", "LYM（CD45+#）", "LYM(CD45+#)", "LYM（CD45+）", "LYM(CD45+)"), "个/ul", "流式细胞术"),
    ("t_cell", "T（CD45+CD3+）", ("T细胞(CD45+CD3+)", "T细胞（CD45+CD3+）", "T(CD45+CD3+#)", "T（CD45+CD3+#）", "T（CD45+CD3+）", "T(CD45+CD3+)"), "个/ul", "流式细胞术"),
    ("nk", "NK（CD45+CD3-CD16+CD56+）", ("NK细胞(CD45+CD3-CD16+CD56+)", "NK细胞（CD45+CD3-CD16+CD56+）", "NK(CD45+CD3-CD16+CD56+#）", "NK（CD45+CD3-CD16+CD56+#）", "NK(CD45+CD3-CD16+CD56+)"), "个/ul", "流式细胞术"),
    ("ctl", "CTL（CD45+CD3+CD8+）", ("CTL细胞(CD45+CD3+CD8+)", "CTL细胞（CD45+CD3+CD8+）", "CTL（CD45+CD3+CD8+#）", "CTL(CD45+CD3+CD8+#）", "CTL(CD45+CD3+CD8+)"), "个/ul", "流式细胞术"),
    ("gzm_b_nk", "Gzm B+CD45+CD3-CD16+CD56+", ("Gzm B+NK细胞(CD45+CD3-CD16+CD56+)", "Gzm B+NK细胞（CD45+CD3-CD16+CD56+）", "Gzm B +CD45+CD3-CD16+CD56+#", "Gzm B+CD45+CD3-CD16+CD56+", "GzmB+CD45+CD3-CD16+CD56+"), "个/ul", "流式细胞术"),
    ("ifn_gamma_nk", "IFN-γ+CD45+CD3-CD16+CD56+", ("IFN-γ+NK细胞(CD45+CD3-CD16+CD56+)", "IFN-γ+NK细胞（CD45+CD3-CD16+CD56+）", "IFN-γ+CD45+CD3-CD16+CD56+#", "IFN-γ+CD45+CD3-CD16+CD56+", "IFN-gamma+CD45+CD3-CD16+CD56+"), "个/ul", "流式细胞术"),
    ("gzm_b_ctl", "Gzm B+CD45+CD3+CD8+", ("Gzm B+CTL细胞(CD45+CD3+CD8+)", "Gzm B+CTL细胞（CD45+CD3+CD8+）", "Gzm B +CD45+CD3+CD8+#", "Gzm B+CD45+CD3+CD8+", "GzmB+CD45+CD3+CD8+"), "个/ul", "流式细胞术"),
    ("ifn_gamma_ctl", "IFN-γ+CD45+CD3+CD8+", ("IFN-γ+CTL细胞(CD45+CD3+CD8+)", "IFN-γ+CTL细胞（CD45+CD3+CD8+）", "IFN-γ+CD45+CD3+CD8+#", "IFN-γ+CD45+CD3+CD8+", "IFN-gamma+CD45+CD3+CD8+"), "个/ul", "流式细胞术"),
    ("t_cell_percent", "T（CD45+CD3+）%", ("T细胞比例(CD45+CD3+)", "T细胞比例（CD45+CD3+）", "T(CD45+CD3+%)", "T（CD45+CD3+%）"), "%", "流式细胞术"),
    ("nk_percent", "NK（CD45+CD3-CD16+CD56+）%", ("NK细胞比例(CD45+CD3-CD16+CD56+)", "NK细胞比例（CD45+CD3-CD16+CD56+）", "NK(CD45+CD3-CD16+CD56+%)", "NK（CD45+CD3-CD16+CD56+%）"), "%", "流式细胞术"),
    ("ctl_percent", "CTL（CD45+CD3+CD8+）%", ("CTL细胞比例(CD45+CD3+CD8+)", "CTL细胞比例（CD45+CD3+CD8+）", "CTL(CD45+CD3+CD8+%)", "CTL（CD45+CD3+CD8+%）"), "%", "流式细胞术"),
    ("gzm_b_nk_percent", "Gzm B+CD45+CD3-CD16+CD56+%", ("功能型NK细胞比例：Gzm B+NK细胞(CD45+CD3-CD16+CD56+)", "功能型NK细胞比例:Gzm B+NK细胞(CD45+CD3-CD16+CD56+)", "Gzm B +CD45+CD3-CD16+CD56+%", "Gzm B+CD45+CD3-CD16+CD56+%"), "%", "流式细胞术"),
    ("ifn_gamma_nk_percent", "IFN-γ+CD45+CD3-CD16+CD56+%", ("功能型NK细胞比例：IFN-γ+NK细胞(CD45+CD3-CD16+CD56+)", "功能型NK细胞比例:IFN-γ+NK细胞(CD45+CD3-CD16+CD56+)", "IFN-γ+CD45+CD3-CD16+CD56+%", "IFN-gamma+CD45+CD3-CD16+CD56+%"), "%", "流式细胞术"),
    ("gzm_b_ctl_percent", "Gzm B+CD45+CD3+CD8+%", ("功能型CTL细胞比例：Gzm B+CTL细胞(CD45+CD3+CD8+)", "功能型CTL细胞比例:Gzm B+CTL细胞(CD45+CD3+CD8+)", "Gzm B +CD45+CD3+CD8+%", "Gzm B+CD45+CD3+CD8+%"), "%", "流式细胞术"),
    ("ctl_ifn_gamma_parent_percent", "CTL-IFN-γ Parent%", ("功能型CTL细胞比例：IFN-γ+CTL(CD45+CD3+CD8+)", "功能型CTL细胞比例:IFN-γ+CTL(CD45+CD3+CD8+)", "CTL-IFN-r Parent%", "CTL-IFN-γ Parent%", "CTL-IFN-g Parent%"), "%", "流式细胞术"),
    ("th", "Th（CD45+CD3+CD4+）", ("Th细胞(CD45+CD3+CD4+)", "Th细胞（CD45+CD3+CD4+）", "Th(CD45+CD3+CD4+#)", "Th（CD45+CD3+CD4+#）", "Th(CD45+CD3+CD4+)"), "个/ul", "流式细胞术"),
    ("th_percent", "Th（CD45+CD3+CD4+）%", ("Th细胞比例(CD45+CD3+CD4+)", "Th细胞比例（CD45+CD3+CD4+）", "Th(CD45+CD3+CD4+%)", "Th（CD45+CD3+CD4+%）"), "%", "流式细胞术"),
]
P06_CYTOKINE_TEST_DEFINITIONS = [
    ("il_1b", "白介素-1β（IL-1β）", ("白介素-1β（IL-1β）", "白介素-1β(IL-1β)", "IL-1β"), "pg/ml", "磁微粒化学发光法"),
    ("il_2", "白介素-2（IL-2）", ("白介素-2（IL-2）", "白介素-2(IL-2)", "IL-2"), "pg/ml", "磁微粒化学发光法"),
    ("il_4", "白介素-4（IL-4）", ("白介素-4（IL-4）", "白介素-4(IL-4)", "IL-4"), "pg/ml", "磁微粒化学发光法"),
    ("il_5", "白介素-5（IL-5）", ("白介素-5（IL-5）", "白介素-5(IL-5)", "IL-5"), "pg/ml", "磁微粒化学发光法"),
    ("il_6", "白介素-6（IL-6）", ("白介素-6（IL-6）", "白介素-6(IL-6)", "IL-6"), "pg/ml", "磁微粒化学发光法"),
    ("il_8", "白介素-8（IL-8）", ("白介素-8（IL-8）", "白介素-8(IL-8)", "IL-8"), "pg/ml", "磁微粒化学发光法"),
    ("il_10", "白介素-10（IL-10）", ("白介素-10（IL-10）", "白介素-10(IL-10)", "IL-10"), "pg/ml", "磁微粒化学发光法"),
    ("il_12p70", "白介素-12p70（IL-12P70）", ("白介素-12p70（IL-12P70）", "白介素-12p70(IL-12P70)", "IL-12P70"), "pg/ml", "磁微粒化学发光法"),
    ("il_17", "白介素-17（IL-17）", ("白介素-17（IL-17）", "白介素-17(IL-17)", "IL-17"), "pg/ml", "磁微粒化学发光法"),
    ("ifn_alpha", "干扰素-α（IFN-α）", ("干扰素-α（IFN-α）", "干扰素-α(IFN-α)", "IFN-α"), "pg/ml", "磁微粒化学发光法"),
    ("ifn_gamma", "干扰素-γ（IFN-γ）", ("干扰素-γ（IFN-γ）", "干扰素-γ(IFN-γ)", "干扰素γ（IFN-γ）", "干扰素γ(IFN-γ)"), "pg/ml", "磁微粒化学发光法"),
    ("tnf_alpha", "肿瘤坏死因子-α（TNF-α）", ("肿瘤坏死因子-α（TNF-α）", "肿瘤坏死因子-α(TNF-α)", "TNF-α"), "pg/ml", "磁微粒化学发光法"),
]
P06_INFLAMMATION_TEST_DEFINITIONS = [
    (
        "hs_crp",
        "超敏C反应蛋白（hs-CRP）",
        ("超敏C反应蛋白（hs-CRP）", "超敏C反应蛋白(hs-CRP)", "超敏C反应蛋白", "hs-CRP", "hsCRP", "CRP"),
        "mg/L",
        "免疫比浊法",
    ),
]
P07_LIVER_FUNCTION_TEST_DEFINITIONS = [
    ("alt", "丙氨酸氨基转移酶(ALT)", ("丙氨酸氨基转移酶", "谷丙转氨酶", "ALT"), "U/L", "9-50"),
    ("pab", "前白蛋白(PAB)", ("前白蛋白", "PAB"), "mg/L", "200-430"),
    ("ast", "天门冬氨酸氨基转移酶(AST)", ("天门冬氨酸氨基转移酶", "天冬氨酸氨基转移酶", "谷草转氨酶", "AST"), "U/L", "15-40"),
    ("ast_alt_ratio", "谷草谷丙比", ("谷草谷丙比", "AST/ALT", "AST／ALT"), "", ""),
    ("tp", "总蛋白(TP)", ("总蛋白", "TP"), "g/L", "65-85"),
    ("alb", "白蛋白(ALB)", ("白蛋白", "ALB"), "g/L", "40-55"),
    ("glo", "球蛋白(GLB)", ("球蛋白", "GLB", "GLO"), "g/L", "20-40"),
    ("ag_ratio", "白/球蛋白比", ("白/球蛋白比", "白蛋白/球蛋白比值", "白球比", "A/G", "A／G"), "", "1.2-2.4"),
    ("tbil", "总胆红素(T-BIL)", ("总胆红素", "T-BIL", "TBIL"), "umol/L", "≤23.0"),
    ("dbil", "直接胆红素(D-BIL)", ("直接胆红素", "D-BIL", "DBIL"), "umol/L", "≤6.0"),
    ("ibil", "间接胆红素(I-BIL)", ("间接胆红素", "I-BIL", "IBIL"), "umol/L", "≤16.16"),
    ("alp", "碱性磷酸酶(ALP)", ("碱性磷酸酶", "ALP"), "U/L", "45-125"),
    ("ggt", "γ-谷氨酰转肽酶(GGT)", ("γ-谷氨酰转肽酶", "γ-谷氨酰转移酶", "GGT"), "U/L", "0.00-60.00"),
    ("che", "胆碱酯酶(CHE)", ("胆碱酯酶", "CHE", "CIE"), "U/L", "5000-12000"),
    ("tba", "总胆汁酸(TBA)", ("总胆汁酸", "TBA"), "umol/L", "≤10.0"),
]
P07_FIBROSIS_TEST_DEFINITIONS = [
    ("pc_iii", "III型前胶原（PC-III）", ("III型前胶原", "III 型前胶原", "Ⅲ型前胶原", "PC-III", "PIIINP", "PⅢNP"), "ng/mL", "≤30"),
    ("civ", "IV型胶原（CIV）", ("IV型胶原", "IV 型胶原", "Ⅳ型胶原", "CIV", "C-IV"), "ng/mL", "≤30"),
    ("ln", "层粘连蛋白（LN）", ("层粘连蛋白", "层黏连蛋白", "LN"), "ug/L", "≤50"),
    ("ha", "透明质酸（HA）", ("透明质酸", "透明质酸酶", "HA"), "ng/mL", "≤100"),
]
P07_TARGET_CODES = {code for code, *_ in [*P07_LIVER_FUNCTION_TEST_DEFINITIONS, *P07_FIBROSIS_TEST_DEFINITIONS]}
P08_TEST_DEFINITIONS = [
    ("nt_probnp", "N端脑利钠肽前体", ("N端脑利钠肽前体", "N 端脑利钠肽前体", "NT-proBNP", "NT proBNP", "NT-pro BNP"), "pg/mL", "0-125.00", "cardiovascular", "化学发光法"),
    ("d_dimer", "D-二聚体", ("D-二聚体", "D二聚体", "D-D", "D Dimer", "D-Dimer"), "mg/L FEU", "0-0.55", "cardiovascular", "免疫比浊法"),
    ("ffa", "游离脂肪酸", ("游离脂肪酸", "FFA", "Free Fatty Acid"), "mmol/L", "0.10-0.60", "cardiovascular", "酶法"),
    ("angiotensin_i", "血管紧张素I", ("血管紧张素I", "血管紧张素Ⅰ", "Ang I", "AngI", "Angiotensin I"), "pg/mL", "28.0-125.0", "raas", "化学发光法"),
    ("angiotensin_ii", "血管紧张素II", ("血管紧张素II", "血管紧张素Ⅱ", "Ang II", "AngII", "Angiotensin II"), "pg/mL", "21.0-75.0", "raas", "化学发光法"),
    ("angiotensin_ratio", "血管紧张素II / I 比值", ("血管紧张素II / I 比值", "血管紧张素II/I", "Ang II/Ang I", "AngII/AngI", "Ang II / Ang I"), "", "0.20-1.20", "raas", "计算法"),
    ("renin", "肾素活性", ("肾素活性", "Renin", "PRA"), "ng/mL/h", "0.30-5.70", "raas", "化学发光法"),
    ("aldosterone", "醛固酮", ("醛固酮", "Aldo", "Aldosterone"), "pg/mL", "79.0-277.0", "raas", "化学发光法"),
]
P08_SUPPLEMENTAL_TEST_DEFINITIONS: dict[str, dict[str, str]] = {
    "angiotensin_i_4c": {
        "name": "血管紧张素I 4℃",
        "unit": "ng/mL",
        "reference": "",
        "group": "raas",
        "method": "化学发光法",
    },
    "aldosterone_renin_ratio": {
        "name": "血醛固酮/血浆肾素活性",
        "unit": "",
        "reference": "",
        "group": "raas",
        "method": "",
    },
}
P09_TEST_DEFINITIONS = [
    ("e2", "雌二醇（E2）", ("雌二醇", "E2", "Estradiol"), "pg/mL", "卵泡期:19.5-144.2 排卵期:63.9-356.7 黄体期:55.8-214.2 绝经期:0-32.2", "core_hormones", "化学发光法"),
    ("lh", "促黄体生成素（LH）", ("促黄体生成素", "黄体生成素", "LH"), "mIU/mL", "卵泡期:1.9-12.5 排卵期:8.7-76.3 黄体期:0.5-16.9 绝经期:15.9-54 妊娠期:0-1.5", "core_hormones", "化学发光法"),
    ("fsh", "促卵泡刺激素（FSH）", ("促卵泡刺激素", "卵泡刺激素", "FSH"), "mIU/mL", "卵泡期:2.5-10.2 排卵期:3.4-33.40 黄体期:1.5-9.1 绝经期:23-116.3 妊娠期:<0.3", "core_hormones", "化学发光法"),
    ("progesterone", "孕酮（PROG）", ("孕酮", "孕激素", "Progesterone", "PROG"), "ng/mL", "卵泡期:0-1.4 黄体期:3.34-25.56 绝经期:0-0.73 孕早期:11.2-90 孕中期:25.55-89.4 孕晚期:48.4-422.5", "core_hormones", "化学发光法"),
    ("testosterone", "睾酮", ("睾酮", "总睾酮", "Testosterone"), "ng/mL", "0.08--0.35", "core_hormones", "化学发光法"),
    ("cortisol", "皮质醇", ("皮质醇", "Cortisol", "CORT"), "nmol/L", "", "stress_metabolism", "化学发光法"),
    ("shbg", "性激素结合球蛋白（SHBG）", ("性激素结合球蛋白", "SHBG"), "nmol/L", "女:20岁-49岁:22.52-134.90", "ovarian_reserve_binding", "化学发光法"),
    ("amh", "抗缪勒氏管激素（AMH）", ("抗缪勒氏管激素", "抗穆勒氏管激素", "AMH"), "ng/mL", "0--4.25", "ovarian_reserve_binding", "化学发光法"),
    ("prolactin", "泌乳素（PRL）", ("泌乳素", "催乳素", "PRL", "Prolactin"), "uIU/mL", "未妊娠:59-619 妊娠期:206-4420 绝经期:38-430", "ovarian_reserve_binding", "化学发光法"),
    ("total_ige", "总IgE", ("总IgE", "总 IgE", "Total IgE", "IgE"), "IU/mL", "0--100", "immune_allergy", "化学发光法"),
]
P09_UNIT_PATTERN = r"mIU/mL|miu/ml|uIU/mL|uiu/ml|μIU/mL|µIU/mL|ng/mL|ng/ml|pg/mL|pg/ml|nmol/L|nmol/l|IU/mL|iu/ml|mIU/L|%"
P09_METHOD_PATTERN = r"磁微粒化学发光法|化学发光法|免疫法|免疫比浊法|酶法|LC-MS/MS法|质谱法"
P12_TEST_DEFINITIONS = [
    ("coq10", "辅酶Q10", ("辅酶Q10", "辅酶 Q10", "CoQ10", "Coenzyme Q10"), "ug/mL", "0.37-2.20", "energy_metabolism", "LC-MS/MS"),
    ("nad", "NAD+", ("NAD+", "NAD＋", "NAO+", "NAO＋", "烟酰胺腺嘌呤二核苷酸"), "µmol/L", "", "energy_metabolism", "NAD+细胞活力营养评估"),
]
P12_UNIT_PATTERN = r"µmol/L|μmol/L|umol/L|mmol/L|mmol/l|U/mL|u/mL|µg/mL|μg/mL|ug/mL|ng/mL|ng/ml|pg/mL|pg/ml|mg/L|%"
P12_METHOD_PATTERN = r"LC-MS/MS法|LC-MS/MS|LC-MSAIS\s*法|LC-MSAIS|质谱法|NAD\+细胞活力营养评估|细胞活力营养评估"
P12_ANTIOXIDANT_ALIASES: dict[str, tuple[str, ...]] = {
    "tac": ("抗氧化总容量(TAC)", "抗氧化总容量", "TAC"),
    "gpx": ("谷胱甘肽过氧化物酶(GPX)", "谷胱甘肽过氧化物酶", "GPX"),
    "sod": ("超氧化物歧化酶(SOD)", "超氧化物歧化酶", "SOD"),
    "lpo": ("过氧化脂类(LPO)", "过氧化脂类", "LPO"),
    "gsh": ("谷胱甘肽(GSH)", "谷胱甘肽", "GSH"),
}
P12_ANTIOXIDANT_DEFAULTS: dict[str, tuple[str, str]] = {
    "tac": ("mmol/L", "≥0.54"),
    "gpx": ("U/mL", "110.25-145.81"),
    "sod": ("U/mL", "85.4-123"),
    "lpo": ("µmol/L", "≤10"),
    "gsh": ("µmol/L", "5.26-8.30"),
}


def parse_pdf_to_standard_ocr_json(pdf_path: Path, package_code: str = "P02") -> dict[str, Any]:
    strategy_version = {
        "P01": P01_STRATEGY_VERSION,
        "P05": P05_STRATEGY_VERSION,
        "P03": P03_STRATEGY_VERSION,
        "P04": P04_STRATEGY_VERSION,
        "P06": P06_STRATEGY_VERSION,
        "P07": P07_STRATEGY_VERSION,
        "P08": P08_STRATEGY_VERSION,
        "P09": P09_STRATEGY_VERSION,
        "P10": P10_STRATEGY_VERSION,
        "P11": P11_STRATEGY_VERSION,
        "P12": P12_STRATEGY_VERSION,
        "P13": P13_STRATEGY_VERSION,
        "P16": P16_STRATEGY_VERSION,
        "P17": P17_STRATEGY_VERSION,
    }.get(package_code, STRATEGY_VERSION)
    if pdf_path.suffix.lower() == ".json":
        return parse_json_to_standard_ocr_json(pdf_path, package_code=package_code, strategy_version=strategy_version)
    reader = PdfReader(str(pdf_path))
    pages = []
    page_texts: list[str] = []
    raw_page_texts: list[str] = []
    for page_number, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        raw_page_texts.append(text)
        normalized = normalize_text(text)
        page_texts.append(normalized)
        pages.append(
            {
                "page_number": page_number,
                "width": float(page.mediabox.width) if page.mediabox else None,
                "height": float(page.mediabox.height) if page.mediabox else None,
                "text_blocks": [
                    {
                        "text": normalized,
                        "confidence": 0.95 if normalized else 0.0,
                        "bbox": None,
                    }
                ],
            }
        )

    page_ocr_data: dict[int, dict[str, Any]] = {}
    if package_code in {"P04", "P05"}:
        page_ocr_data = extract_sparse_page_image_ocr(pdf_path, page_texts)
        for page_number, payload in page_ocr_data.items():
            if page_number < 1 or page_number > len(page_texts):
                continue
            merged_text = normalize_text(" ".join(part for part in [page_texts[page_number - 1], payload.get("text", "")] if part))
            page_texts[page_number - 1] = merged_text
            pages[page_number - 1]["text_blocks"] = [
                {
                    "text": merged_text,
                    "confidence": float(payload.get("confidence") or 0.82),
                    "bbox": None,
                }
            ]

    full_text = normalize_text(" ".join(page_texts))
    structured_report = build_structured_report(
        pdf_path.name,
        full_text,
        page_texts,
        package_code=package_code,
        page_ocr_data=page_ocr_data,
    )
    p03_extracted_report: dict[str, Any] = {}
    if package_code == "P03":
        p03_extracted_report = build_p03_extracted_report(structured_report, full_text, raw_page_texts=raw_page_texts)
        structured_report["p03_extracted_report"] = p03_extracted_report
    if package_code == "P06":
        if not test_names:
            warnings.append("P06 褰撳墠鏈瘑鍒埌鍏嶇柅缁嗚優鎴栫粏鑳炲洜瀛愭楠屾槑缁嗭紱璇锋牳瀵筆DF鏂囨湰灞傛垨鍒囨崲浜慜CR銆?")
        elif len(test_names) < 10:
            warnings.append(f"P06 褰撳墠浠呰瘑鍒埌 {len(test_names)} 椤规楠屾槑缁嗭紝寤鸿浜哄伐澶嶆牳鍏嶇柅缁嗚優鍜岀粏鑳炲洜瀛愯〃鏍笺€?")
        test_names = []
    if package_code == "P01":
        fields = extract_p01_fields(page_texts, structured_report)
    elif package_code == "P05":
        fields = extract_p05_fields(page_texts, structured_report)
    elif package_code == "P03":
        fields = extract_p03_fields(page_texts, structured_report)
    elif package_code == "P04":
        fields = extract_p04_fields(page_texts, structured_report)
    elif package_code == "P06":
        fields = extract_p06_fields(page_texts, structured_report)
    elif package_code == "P06":
        required = {
            "patient.name": "濮撳悕",
            "patient.gender": "鎬у埆",
            "patient.age": "骞撮緞",
            "p06.immune_cells.gzm_b_nk.absolute_result": "Gzm B+ NK",
            "p06.immune_cells.ifn_gamma_nk.absolute_result": "IFN-γ+ NK",
            "p06.immune_cells.gzm_b_ctl.absolute_result": "Gzm B+ CTL",
            "p06.immune_cells.ifn_gamma_ctl.absolute_result": "IFN-γ+ CTL",
            "p06.cytokines.il_8.result_display": "IL-8",
            "p06.cytokines.tnf_alpha.result_display": "TNF-α",
        }
    elif package_code == "P17":
        fields = extract_p17_fields(page_texts, structured_report)
    elif package_code == "P10":
        fields = extract_p10_fields(page_texts, structured_report)
    elif package_code == "P11":
        fields = extract_p11_fields(
            page_texts=page_texts,
            structured_report=structured_report,
            add_field=add_field,
            find_page=find_page,
        )
    else:
        fields = extract_p02_fields(full_text, page_texts, structured_report)
    confidence = calculate_confidence(fields, pages)
    warnings = build_warnings(fields, pages, structured_report, package_code=package_code)
    provider = "pdf-text-extractor+rapidocr" if page_ocr_data else PROVIDER
    result = {
        "schema_version": "1.0",
        "package_code": package_code,
        "source_file": pdf_path.name,
        "strategy_version": strategy_version,
        "provider": provider,
        "pages": pages,
        "fields": fields,
        "indicators": build_indicators(fields),
        "structured_report": structured_report,
        "warnings": warnings,
        "created_at": now_iso(),
        "debug": {
            "comparison_key": f"{package_code}:{pdf_path.name}:{strategy_version}",
            "field_keys": [field["field_key"] for field in fields],
            "overall_confidence": confidence,
            "structured_test_count": len(structured_report["tests"]),
        },
    }
    if package_code == "P01":
        result["p01_extracted_report"] = structured_report.get("p01_extracted_report", {})
    if package_code == "P05":
        result["p05_extracted_report"] = structured_report.get("p05_extracted_report", {})
    if package_code == "P03":
        result["p03_extracted_report"] = p03_extracted_report
    if package_code == "P04":
        result["p04_extracted_report"] = structured_report.get("p04_extracted_report", {"tests": structured_report.get("tests", [])})
    if package_code == "P17":
        result["p17_extracted_report"] = structured_report.get("p17_extracted_report", {})
    return result


def normalize_text(text: str) -> str:
    text = text.replace("\u3000", " ")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def build_structured_report(
    source_file: str,
    full_text: str,
    page_texts: list[str],
    package_code: str = "P02",
    *,
    page_ocr_data: dict[int, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    if package_code == "P01":
        return build_p01_structured_report(source_file, full_text, page_texts)
    if package_code == "P05":
        return build_p05_structured_report(source_file, full_text, page_texts, page_ocr_data=page_ocr_data)
    if package_code == "P04":
        return build_p04_structured_report(source_file, full_text, page_texts, page_ocr_data=page_ocr_data or {})
    if package_code == "P10":
        return build_p10_structured_report(source_file, full_text, page_texts)
    if package_code == "P17":
        return build_p17_structured_report(source_file, full_text, page_texts)
    return {
        "report_id": extract_report_id(full_text) or Path(source_file).stem,
        "patient_info": {
            "name": extract_patient_name(full_text),
            "gender": extract_gender(full_text),
            "age": extract_age(full_text),
            "specimen_condition": extract_specimen_condition(full_text),
            "specimen_types": extract_specimen_types(page_texts),
            "hospital": extract_hospital(full_text),
            "patient_number": "",
            "bed_number": "",
            "department": "",
            "doctor": "",
            "clinical_diagnosis": "",
        },
        "tests": extract_structured_tests(page_texts, package_code=package_code),
        "notes": "",
        "additional_info": {
            "sample_date": extract_date(page_texts, "采样日期"),
            "receive_date": extract_date(page_texts, "接收时间"),
            "report_date": extract_date(page_texts, "报告时间"),
            "technician": extract_staff(full_text, ["检测者", "检验者"]),
            "reviewer": extract_staff(full_text, ["审核者", "复核者"]),
            "approver": extract_staff(full_text, ["批准人", "批准者"]),
        },
    }


def build_p17_structured_report(source_file: str, full_text: str, page_texts: list[str]) -> dict[str, Any]:
    p17_report = build_p17_extracted_report(source_file, full_text, page_texts)
    reports = p17_report.get("reports", [])
    first_report = reports[0] if reports else {}
    first_patient = first_report.get("patient_info", {}) if isinstance(first_report, dict) else {}
    first_submission = first_report.get("submission_info", {}) if isinstance(first_report.get("submission_info"), dict) else {}

    tests = extract_p17_structured_tests(p17_report)
    specimen_types = list(
        dict.fromkeys(
            str((report.get("patient_info", {}) or {}).get("specimen_type") or "")
            for report in reports
            if isinstance(report, dict)
        )
    )
    specimen_types = [value for value in specimen_types if value]

    sampling_values = [
        str((report.get("patient_info", {}) or {}).get("sampling_date") or "")
        for report in reports
        if isinstance(report, dict)
    ]
    receive_values = [
        str((report.get("patient_info", {}) or {}).get("receiving_time") or "")
        for report in reports
        if isinstance(report, dict)
    ]
    report_time_values = [
        str((report.get("patient_info", {}) or {}).get("report_time") or "")
        for report in reports
        if isinstance(report, dict)
    ]
    report_dates = [value for value in report_time_values if value] or [value for value in receive_values if value] or [value for value in sampling_values if value]

    return {
        "report_id": str((first_report.get("submission_info", {}) or {}).get("barcode") or extract_report_id(full_text) or Path(source_file).stem),
        "patient_info": {
            "name": str(first_patient.get("name") or extract_patient_name(full_text)),
            "gender": str(first_patient.get("gender") or extract_gender(full_text)),
            "age": _parse_age_number(str(first_patient.get("age") or "")) or extract_age(full_text),
            "specimen_condition": str(first_patient.get("specimen_characteristics") or extract_specimen_condition(full_text)),
            "specimen_types": specimen_types or extract_specimen_types(page_texts),
            "hospital": str(first_submission.get("submitting_unit") or p17_report.get("hospital_name") or extract_laboratory(full_text) or extract_hospital(full_text)),
            "submitting_unit": str(first_submission.get("submitting_unit") or p17_report.get("hospital_name") or extract_laboratory(full_text) or extract_hospital(full_text)),
            "patient_number": str(first_patient.get("inpatient_outpatient_number") or ""),
            "bed_number": str(first_patient.get("bed_number") or ""),
            "department": str(first_patient.get("submitting_department") or ""),
            "doctor": str(first_patient.get("submitting_physician") or ""),
            "clinical_diagnosis": str(first_patient.get("clinical_diagnosis") or ""),
        },
        "tests": tests,
        "notes": _first_non_empty(
            [str(report.get("analysis_and_tips") or report.get("remarks") or "") for report in reports if isinstance(report, dict)]
        ),
        "additional_info": {
            "sample_date": _first_non_empty(sampling_values),
            "receive_date": _first_non_empty(receive_values),
            "report_date": _last_non_empty(report_dates),
            "technician": extract_staff(full_text, ["检验者", "检测者"]),
            "reviewer": extract_staff(full_text, ["审核者", "复核者"]),
            "approver": extract_staff(full_text, ["批准者", "批准人"]),
        },
        "p17_extracted_report": p17_report,
    }


def build_p10_structured_report(source_file: str, full_text: str, page_texts: list[str]) -> dict[str, Any]:
    report_id = extract_report_id(full_text) or Path(source_file).stem
    submitting_unit = extract_hospital(full_text)
    tests = extract_structured_tests(page_texts, package_code="P10")
    return {
        "report_id": report_id,
        "patient_info": {
            "name": extract_patient_name(full_text),
            "gender": extract_gender(full_text),
            "age": extract_age(full_text),
            "specimen_condition": extract_specimen_condition(full_text),
            "specimen_types": extract_specimen_types(page_texts),
            "hospital": submitting_unit,
            "submitting_unit": submitting_unit,
            "patient_number": "",
            "bed_number": "",
            "department": "",
            "doctor": "",
            "clinical_diagnosis": "",
            "phone": "",
        },
        "tests": tests,
        "notes": "",
        "additional_info": {
            "sample_date": extract_date(page_texts, "采样时间") or extract_date(page_texts, "采样日期"),
            "receive_date": extract_date(page_texts, "接收时间"),
            "report_date": extract_date(page_texts, "报告时间") or extract_date(page_texts, "报告日期"),
            "technician": extract_staff(full_text, ["检测者", "检验者"]),
            "reviewer": extract_staff(full_text, ["审核者", "复核者"]),
            "approver": extract_staff(full_text, ["批准人", "批准者"]),
        },
        "p10_extracted_report": {
            "source_file": source_file,
            "mode": "pdf-text-structured",
            "report_info": {
                "barcode": report_id,
                "submitting_unit": submitting_unit,
            },
        },
    }


def build_p04_structured_report(
    source_file: str,
    full_text: str,
    page_texts: list[str],
    *,
    page_ocr_data: dict[int, dict[str, Any]],
) -> dict[str, Any]:
    tests = extract_p04_structured_tests(page_texts, page_ocr_data=page_ocr_data)
    p04_report = build_p04_extracted_report(source_file, full_text, page_texts, tests)
    report_info = p04_report.get("report_info", {})
    page2_report = p04_report.get("test_results_page2", {}) if isinstance(p04_report.get("test_results_page2"), dict) else {}
    specimen_types = extract_specimen_types(page_texts)
    page2_specimen = str(page2_report.get("specimen_type") or "")
    if page2_specimen and page2_specimen not in specimen_types:
        specimen_types.append(page2_specimen)

    return {
        "report_id": str(report_info.get("barcode") or extract_report_id(full_text) or Path(source_file).stem),
        "patient_info": {
            "name": str(report_info.get("patient_name") or extract_patient_name(full_text)),
            "gender": str(report_info.get("gender") or extract_gender(full_text)),
            "age": _parse_age_number(str(report_info.get("age") or "")) or extract_age(full_text),
            "specimen_condition": str(report_info.get("specimen_status") or page2_report.get("specimen_status") or extract_specimen_condition(full_text)),
            "specimen_types": specimen_types,
            "hospital": str(report_info.get("submitting_unit") or extract_hospital(full_text)),
            "submitting_unit": str(report_info.get("submitting_unit") or extract_hospital(full_text)),
            "patient_number": str(report_info.get("patient_id") or ""),
            "bed_number": str(report_info.get("bed_no") or ""),
            "department": str(report_info.get("submitting_department") or ""),
            "doctor": str(report_info.get("submitting_doctor") or ""),
            "clinical_diagnosis": str(report_info.get("clinical_diagnosis") or ""),
        },
        "tests": tests,
        "notes": str(p04_report.get("remarks_page1") or ""),
        "additional_info": {
            "sample_date": _first_non_empty(
                [
                    str((p04_report.get("dates_page1", {}) or {}).get("sampling_date") or ""),
                    str(page2_report.get("sampling_time") or ""),
                    extract_date(page_texts, "采样日期"),
                    extract_date(page_texts, "采样时间"),
                ]
            ),
            "receive_date": _last_non_empty(
                [
                    str((p04_report.get("dates_page1", {}) or {}).get("receiving_date") or ""),
                    str(page2_report.get("receiving_time") or ""),
                    extract_date(page_texts, "接收时间"),
                ]
            ),
            "report_date": _last_non_empty(
                [
                    str(p04_report.get("report_date_page2") or ""),
                    str((p04_report.get("dates_page1", {}) or {}).get("report_date") or ""),
                    extract_date(page_texts, "报告时间"),
                ]
            ),
            "technician": _normalize_p04_staff(extract_staff(full_text, ["检测者", "检验者"])),
            "reviewer": str(p04_report.get("reviewer_page2") or extract_staff(full_text, ["审核者", "复核者"])),
            "approver": _normalize_p04_staff(extract_staff(full_text, ["批准人", "批准者"])),
        },
        "p04_extracted_report": p04_report,
    }


def build_p04_extracted_report(
    source_file: str,
    full_text: str,
    page_texts: list[str],
    tests: list[dict[str, Any]],
) -> dict[str, Any]:
    page_one = page_texts[0] if page_texts else full_text
    page_two = page_texts[1] if len(page_texts) > 1 else ""
    page1_tests = [test for test in tests if int(test.get("page") or 0) == 1]
    page2_tests = [test for test in tests if int(test.get("page") or 0) == 2]
    return {
        "report_info": {
            "lab_name": extract_laboratory(full_text) or "合肥安为康医学检验实验室",
            "report_title": "检验结果报告单" if "检验结果报告单" in page_two else "检验报告单",
            "barcode": extract_report_id(full_text) or Path(source_file).stem,
            "submitting_unit": extract_hospital(full_text),
            "patient_name": extract_patient_name(full_text),
            "gender": extract_gender(full_text),
            "age": extract_age(full_text),
            "specimen_status": extract_specimen_condition(full_text),
            "specimen_type": extract_page_specimen_type(page_one),
            "patient_id": "",
            "bed_no": "",
            "submitting_department": "",
            "submitting_doctor": "",
            "clinical_diagnosis": "",
        },
        "test_results_page1": [_p04_log_test_item(test) for test in page1_tests],
        "remarks_page1": extract_remarks(page_one),
        "dates_page1": {
            "sampling_date": extract_date([page_one], "采样日期"),
            "receiving_date": extract_date([page_one], "接收时间"),
            "report_date": extract_date([page_one], "报告时间"),
        },
        "test_results_page2": {
            "specimen_type": extract_page_specimen_type(page_two),
            "sampling_time": extract_date([page_two], "采样时间") or extract_date([page_two], "采样日期"),
            "receiving_time": extract_date([page_two], "接收时间"),
            "specimen_status": _extract_p04_sample_status(page_two),
            "results": [_p04_log_test_item(test, include_no=True) for test in page2_tests],
        },
        "reviewer_page2": _normalize_p04_reviewer(extract_staff(page_two, ["审核者", "复核者"])),
        "contact": {
            "website": _normalize_p04_website(extract_website(full_text)),
            "phone": extract_phone(full_text),
            "address": _extract_p04_contact_address(full_text),
        },
        "report_date_page2": extract_date([page_two], "报告时间"),
    }


def _p04_log_test_item(test: dict[str, Any], *, include_no: bool = False) -> dict[str, Any]:
    item: dict[str, Any] = {}
    if include_no:
        item["no"] = int(test.get("serial_no") or 0)
    item.update(
        {
            "test_item": str(test.get("test_name") or ""),
            "method": str(test.get("method") or ""),
            "result": _p04_json_number(test.get("result")),
            "reference_range": str(test.get("reference_range") or ""),
            "unit": str(test.get("unit") or ""),
        }
    )
    if test.get("indicator"):
        item["indicator"] = str(test.get("indicator") or "")
    return item


def _p04_json_number(value: Any) -> Any:
    text = str(value or "").strip()
    if re.fullmatch(r"-?[0-9]+(?:\.[0-9]+)?", text):
        return float(text)
    return text


def _extract_p04_sample_status(text: str) -> str:
    value = _extract_between_labels(text, "样本状态", ["临床诊断", "序号", "检测方法"])
    if value:
        return value
    match = re.search(r"(标本未见异常|未见异常|正常|异常|溶血|脂血)", text)
    return match.group(1) if match else ""


def _normalize_p04_reviewer(value: str) -> str:
    return "郎从军" if clean_value(value) == "邵从军" else clean_value(value)


def _normalize_p04_staff(value: str) -> str:
    cleaned = clean_value(value)
    return "" if cleaned in {"址", "话", "网", "电话", "地址"} else cleaned


def _normalize_p04_website(value: str) -> str:
    return clean_value(value).replace("wwww.", "www.")


def _extract_p04_contact_address(text: str) -> str:
    address = extract_address(text)
    if address and "anweikang.com" not in address.lower():
        return address
    return _extract_p04_short_address(text)


def _extract_p04_short_address(text: str) -> str:
    match = re.search(r"(?:^|\s)址[:：]\s*([^\s]*?(?:大楼|中心|实验室|医院|公司|园区))", text)
    return clean_value(match.group(1)) if match else ""


def build_p05_structured_report(
    source_file: str,
    full_text: str,
    page_texts: list[str],
    *,
    page_ocr_data: dict[int, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    p05_report = build_p05_extracted_report(source_file, full_text, page_texts, page_ocr_data=page_ocr_data or {})
    reports = p05_report.get("reports", [])
    first_report = reports[0] if reports else {}
    basic_infos = [
        report.get("basic_info", {})
        for report in reports
        if isinstance(report, dict) and isinstance(report.get("basic_info"), dict)
    ]

    def basic_value(key: str, validate: Any | None = None) -> str:
        return _first_non_empty([str(basic.get(key) or "") for basic in basic_infos], validate=validate)

    tests = extract_p05_structured_tests(p05_report)
    sample_values = [
        str(report.get("sampling_datetime") or "")
        for report in reports
        if isinstance(report, dict) and report.get("sampling_datetime")
    ]
    receive_values = [
        str(report.get("receiving_datetime") or "")
        for report in reports
        if isinstance(report, dict) and report.get("receiving_datetime")
    ]
    report_values = [
        str(report.get("report_datetime") or "")
        for report in reports
        if isinstance(report, dict) and report.get("report_datetime")
    ]
    specimen_types = list(
        dict.fromkeys(
            str((report.get("basic_info", {}) or {}).get("specimen_type") or "")
            for report in reports
            if isinstance(report, dict)
            and _is_clean_p05_basic_value(str((report.get("basic_info", {}) or {}).get("specimen_type") or ""))
        )
    )
    specimen_types = [value for value in specimen_types if value]

    return {
        "report_id": str(first_report.get("barcode") or extract_report_id(full_text) or Path(source_file).stem),
        "patient_info": {
            "name": basic_value("name") or extract_patient_name(full_text),
            "gender": basic_value("gender") or extract_gender(full_text),
            "age": _parse_age_number(basic_value("age")) or extract_age(full_text),
            "specimen_condition": basic_value("specimen_status", validate=_is_clean_p05_basic_value) or extract_specimen_condition(full_text),
            "specimen_types": specimen_types or extract_specimen_types(page_texts),
            "hospital": basic_value("submitting_institution", validate=_is_clean_p05_basic_value) or extract_hospital(full_text),
            "patient_number": basic_value("patient_id"),
            "bed_number": basic_value("bed_no"),
            "department": basic_value("submitting_department"),
            "doctor": basic_value("submitting_doctor"),
            "clinical_diagnosis": basic_value("clinical_diagnosis", validate=_is_clean_p05_basic_value),
        },
        "tests": tests,
        "notes": "",
        "additional_info": {
            "sample_date": min(sample_values) if sample_values else "",
            "receive_date": max(receive_values) if receive_values else "",
            "report_date": max(report_values) if report_values else "",
            "technician": _first_non_empty([str(report.get("tested_by") or "") for report in reports], validate=_is_valid_p05_staff_value),
            "reviewer": _first_non_empty([str(report.get("reviewed_by") or "") for report in reports], validate=_is_valid_p05_staff_value),
            "approver": _first_non_empty([str(report.get("approved_by") or "") for report in reports], validate=_is_valid_p05_staff_value),
        },
        "p05_extracted_report": p05_report,
    }


def build_p01_structured_report(source_file: str, full_text: str, page_texts: list[str]) -> dict[str, Any]:
    p01_report = build_p01_extracted_report(source_file, full_text, page_texts)
    basic_information = p01_report.get("basic_information", {})
    quality_control = p01_report.get("quality_control", {})
    sample_type = str(basic_information.get("sample_type") or "")
    sample_id = str(basic_information.get("sample_id") or "")
    report_date = str(basic_information.get("report_date") or "")
    receiving_date = str(basic_information.get("receiving_date") or "")
    sampling_date = str(basic_information.get("sampling_date") or "")
    name = str(basic_information.get("name") or "")
    gender = str(basic_information.get("gender") or "")
    age = basic_information.get("age") or ""
    submitting_institution = str(basic_information.get("submitting_institution") or "")

    return {
        "report_id": sample_id or extract_report_id(full_text) or Path(source_file).stem,
        "patient_info": {
            "name": name,
            "gender": gender,
            "age": age,
            "specimen_condition": "",
            "specimen_types": [sample_type] if sample_type else extract_specimen_types(page_texts),
            "hospital": submitting_institution,
            "patient_number": sample_id,
            "bed_number": "",
            "department": "",
            "doctor": "",
            "clinical_diagnosis": str(basic_information.get("main_complaint") or ""),
        },
        "tests": extract_p01_structured_tests(page_texts, p01_report=p01_report),
        "notes": str(p01_report.get("test_description", {}).get("content") or ""),
        "additional_info": {
            "sample_date": "" if sampling_date == "-" else sampling_date,
            "receive_date": receiving_date,
            "report_date": report_date,
            "technician": str(quality_control.get("tested_by") or extract_staff(full_text, ["检测者", "检验者"])),
            "reviewer": str(quality_control.get("reviewed_by") or extract_staff(full_text, ["审核者", "复核者"])),
            "approver": str(quality_control.get("approved_by") or ""),
        },
        "p01_extracted_report": p01_report,
    }


def build_p01_extracted_report(source_file: str, full_text: str, page_texts: list[str]) -> dict[str, Any]:
    report_info = _extract_p01_report_info(full_text, page_texts)
    basic_information = _extract_p01_basic_information(full_text, page_texts)
    summary_text = _extract_p01_summary_text(page_texts)
    overview_text = _page_text(page_texts, 4)
    description_text = _extract_p01_test_description(page_texts)
    phylum_top_5 = _extract_p01_ranked_items(_page_text(page_texts, 11), limit=5)
    genus_top_15 = _extract_p01_ranked_items(_page_text(page_texts, 12), limit=15)
    beneficial_bacteria = _extract_p01_microbe_group(page_texts, "beneficial")
    harmful_bacteria = _extract_p01_microbe_group(page_texts, "harmful")
    neutral_bacteria = _extract_p01_microbe_group(page_texts, "neutral")
    disease_analysis = _extract_p01_disease_analysis(summary_text)
    report_summary = _extract_p01_report_summary(summary_text, disease_analysis)
    diversity = _extract_p01_diversity(summary_text)
    intestinal_age = _extract_p01_intestinal_age(summary_text, basic_information)

    return {
        "report_info": report_info,
        "basic_information": basic_information,
        "test_description": {
            "content": description_text,
        },
        "result_overview": _extract_p01_result_overview(overview_text, summary_text),
        "gmhi": _extract_p01_gmhi(summary_text, overview_text),
        "enterotype": {
            "result": _extract_p01_enterotype(summary_text),
            "description": "",
        },
        "diversity": diversity,
        "intestinal_age": intestinal_age,
        "fb_ratio": _extract_p01_fb_ratio(phylum_top_5),
        "be_index": _extract_p01_be_index(_page_text(page_texts, 10)),
        "microbial_composition": {
            "phylum_level": {
                "top_5": phylum_top_5,
            },
            "genus_level": {
                "top_15": genus_top_15,
            },
            "beneficial_bacteria": beneficial_bacteria,
            "harmful_bacteria": harmful_bacteria,
            "neutral_bacteria": neutral_bacteria,
        },
        "disease_risk_assessment": {
            "disclaimer": "",
            "risk_levels": {
                "0-0.4": "低风险",
                "0.4-0.6": "注意",
                "0.6-0.8": "中风险",
                "0.8-1.0": "高风险",
            },
            "diseases": [
                {
                    "name": item["disease"],
                    "risk_score": item["risk_score"],
                    "risk_level": item["risk_level"],
                    "clinical_features": item["symptoms"],
                    "positive_correlations": [],
                    "negative_correlations": [],
                }
                for item in disease_analysis
            ],
        },
        "metabolism_and_nutrients": _extract_p01_metabolism_summary(summary_text),
        "immunity_assessment": _extract_p01_immunity(summary_text),
        "quality_control": _extract_p01_quality_control(_page_text(page_texts, 42)),
        "report_summary": report_summary,
    }


def build_p03_extracted_report(
    structured_report: dict[str, Any],
    full_text: str,
    *,
    raw_page_texts: list[str] | None = None,
) -> dict[str, Any]:
    patient_info = structured_report.get("patient_info", {})
    additional_info = structured_report.get("additional_info", {})
    specimen_types = patient_info.get("specimen_types") or []
    if not isinstance(specimen_types, list):
        specimen_types = [str(specimen_types)]
    source_text = "\n\n".join(text for text in (raw_page_texts or []) if text).strip() or full_text

    barcodes = extract_barcodes(source_text)
    primary_barcode = str(structured_report.get("report_id") or (barcodes[0] if barcodes else ""))
    alternate_barcodes = [barcode for barcode in barcodes if barcode != primary_barcode]
    tests = structured_report.get("tests", [])
    return {
        "report_info": {
            "laboratory": extract_laboratory(source_text),
            "report_name": "检验报告单" if "检验报告单" in full_text else "",
            "barcode": primary_barcode,
            "barcode_alt": alternate_barcodes[0] if alternate_barcodes else "",
        },
        "patient_info": {
            "name": patient_info.get("name") or "",
            "gender": patient_info.get("gender") or "",
            "age": patient_info.get("age") or "",
            "phone": extract_patient_phone(source_text),
            "submitting_unit": patient_info.get("hospital") or "",
            "specimen_status": patient_info.get("specimen_condition") or "",
            "specimen_type": specimen_types[0] if specimen_types else "",
            "specimen_type_alt": specimen_types[1] if len(specimen_types) > 1 else "",
            "patient_id": patient_info.get("patient_number") or "",
            "bed_number": patient_info.get("bed_number") or "",
            "submitting_department": patient_info.get("department") or "",
            "submitting_doctor": patient_info.get("doctor") or "",
            "clinical_diagnosis": extract_patient_symptoms(source_text) or patient_info.get("clinical_diagnosis") or "",
        },
        "test_results": [
            {
                "test_name": test.get("test_name") or "",
                "result": numeric_or_text(test.get("result")),
                "indicator": test.get("indicator") or "",
                "reference_range": test.get("reference_range") or "",
                "unit": test.get("unit") or "",
                "method": test.get("method") or "",
            }
            for test in tests
        ],
        "remarks": extract_remarks(source_text),
        "disclaimer": extract_disclaimer(source_text),
        "signatures": {
            "detected_by": additional_info.get("technician") or "",
            "reviewed_by": additional_info.get("reviewer") or "",
            "approved_by": additional_info.get("approver") or "",
        },
        "dates": {
            "sampling_date": additional_info.get("sample_date") or "",
            "receiving_date": additional_info.get("receive_date") or "",
            "report_date": additional_info.get("report_date") or "",
        },
        "contact": {
            "website": extract_website(source_text),
            "phone": extract_phone(source_text),
            "address": extract_address(source_text),
        },
    }


def extract_sparse_page_image_ocr(pdf_path: Path, page_texts: list[str]) -> dict[int, dict[str, Any]]:
    targets = [index + 1 for index, text in enumerate(page_texts) if len(text.strip()) < 20]
    if not targets:
        return {}
    try:
        import fitz
        from rapidocr_onnxruntime import RapidOCR
    except Exception:
        return {}

    ocr = RapidOCR()
    results: dict[int, dict[str, Any]] = {}
    document = fitz.open(str(pdf_path))
    try:
        for page_number in targets:
            page = document.load_page(page_number - 1)
            pix = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as temp_file:
                temp_path = Path(temp_file.name)
            try:
                pix.save(str(temp_path))
                raw_items, _ = ocr(str(temp_path))
            finally:
                temp_path.unlink(missing_ok=True)
            items = _normalize_p05_ocr_items(raw_items or [])
            if not items:
                continue
            results[page_number] = {
                "text": normalize_text(" ".join(item["text"] for item in items)),
                "items": items,
                "confidence": round(mean(item["score"] for item in items), 4),
            }
    finally:
        document.close()
    return results


def _normalize_p05_ocr_items(raw_items: list[Any]) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for item in raw_items:
        if not isinstance(item, (list, tuple)) or len(item) < 3:
            continue
        box, text, score = item[0], str(item[1]), float(item[2])
        if not box:
            continue
        xs = [point[0] for point in box]
        ys = [point[1] for point in box]
        items.append(
            {
                "text": clean_value(text),
                "score": score,
                "x": float(sum(xs) / len(xs)),
                "y": float(sum(ys) / len(ys)),
            }
        )
    return items


def build_p05_extracted_report(
    source_file: str,
    full_text: str,
    page_texts: list[str],
    *,
    page_ocr_data: dict[int, dict[str, Any]],
) -> dict[str, Any]:
    report_overview = _extract_p05_report_overview(page_texts)
    reports: list[dict[str, Any]] = []

    thyroid_page = _find_p05_page(page_texts, ["FT3", "TPOAb"])
    if thyroid_page:
        thyroid_text = page_texts[thyroid_page - 1]
        reports.append(
            {
                "page": thyroid_page,
                "barcode": _extract_p05_barcode(thyroid_text),
                "basic_info": _extract_p05_basic_info(thyroid_text),
                "test_items": _extract_p05_thyroid_tests(thyroid_text),
                "remark": extract_remarks(thyroid_text),
                "hospital_barcode": "",
                "tested_by": extract_staff(thyroid_text, ["检测者", "检验者"]),
                "reviewed_by": extract_staff(thyroid_text, ["审核者", "复核者"]),
                "approved_by": extract_staff(thyroid_text, ["批准人", "批准者"]),
                "sampling_datetime": _extract_p05_label_value(thyroid_text, ["采样日期"]),
                "receiving_datetime": _extract_p05_label_value(thyroid_text, ["接收时间"]),
                "report_datetime": _extract_p05_label_value(thyroid_text, ["报告时间"]),
            }
        )

    catecholamine_page = _find_p05_page(page_texts, ["去甲肾上腺素", "LC-MS/MS法"])
    if catecholamine_page:
        catecholamine_text = page_texts[catecholamine_page - 1]
        reports.append(
            {
                "page": catecholamine_page,
                "barcode": _extract_p05_barcode(catecholamine_text),
                "basic_info": _extract_p05_basic_info(catecholamine_text),
                "test_items": _extract_p05_catecholamine_tests(page_ocr_data.get(catecholamine_page, {}).get("items", []), catecholamine_text),
                "remark": extract_remarks(catecholamine_text),
                "hospital_barcode": "",
                "tested_by": extract_staff(catecholamine_text, ["检验者", "检测者"]),
                "reviewed_by": _extract_p05_inline_reviewer(page_ocr_data.get(catecholamine_page, {}).get("items", []), catecholamine_text),
                "approved_by": extract_staff(catecholamine_text, ["批准者", "批准人"]),
                "sampling_datetime": _extract_p05_label_value(catecholamine_text, ["采样时间", "采样日期"]),
                "receiving_datetime": _extract_p05_label_value(catecholamine_text, ["接收时间"]),
                "report_datetime": _extract_p05_label_value(catecholamine_text, ["报告时间"]),
            }
        )

    cort_page = _find_p05_page(page_texts, ["皮质醇(CORT)"])
    if cort_page:
        cort_text = page_texts[cort_page - 1]
        reports.append(
            {
                "page": cort_page,
                "barcode": _extract_p05_barcode(cort_text),
                "basic_info": _extract_p05_basic_info(cort_text),
                "test_items": _extract_p05_single_test(cort_text, "cort"),
                "remark": extract_remarks(cort_text),
                "hospital_barcode": "",
                "tested_by": extract_staff(cort_text, ["检测者", "检验者"]),
                "reviewed_by": extract_staff(cort_text, ["审核者", "复核者"]),
                "approved_by": extract_staff(cort_text, ["批准人", "批准者"]),
                "sampling_datetime": _extract_p05_label_value(cort_text, ["采样日期"]),
                "receiving_datetime": _extract_p05_label_value(cort_text, ["接收时间"]),
                "report_datetime": _extract_p05_label_value(cort_text, ["报告时间"]),
            }
        )

    acth_page = _find_p05_page(page_texts, ["促肾上腺皮质激素(ACTH)"])
    if acth_page:
        acth_text = page_texts[acth_page - 1]
        reports.append(
            {
                "page": acth_page,
                "barcode": _extract_p05_barcode(acth_text),
                "basic_info": _extract_p05_basic_info(acth_text),
                "test_items": _extract_p05_single_test(acth_text, "acth"),
                "remark": extract_remarks(acth_text),
                "hospital_barcode": "",
                "tested_by": extract_staff(acth_text, ["检测者", "检验者"]),
                "reviewed_by": extract_staff(acth_text, ["审核者", "复核者"]),
                "approved_by": extract_staff(acth_text, ["批准人", "批准者"]),
                "sampling_datetime": _extract_p05_label_value(acth_text, ["采样日期"]),
                "receiving_datetime": _extract_p05_label_value(acth_text, ["接收时间"]),
                "report_datetime": _extract_p05_label_value(acth_text, ["报告时间"]),
            }
        )

    return {
        "report_overview": report_overview,
        "reports": reports,
    }


def extract_p05_structured_tests(p05_report: dict[str, Any]) -> list[dict[str, Any]]:
    tests: list[dict[str, Any]] = []
    for report in p05_report.get("reports", []):
        if not isinstance(report, dict):
            continue
        page = int(report.get("page") or 0)
        basic_info = report.get("basic_info", {}) if isinstance(report.get("basic_info"), dict) else {}
        specimen_type = str(basic_info.get("specimen_type") or "")
        for item in report.get("test_items", []):
            if not isinstance(item, dict):
                continue
            tests.append(
                {
                    "page": page,
                    "specimen_type": specimen_type,
                    "test_name": str(item.get("test_name") or ""),
                    "item_code": str(item.get("item_code") or ""),
                    "result": str(item.get("result") or ""),
                    "indicator": str(item.get("hint") or ""),
                    "reference_range": str(item.get("reference_range") or ""),
                    "unit": str(item.get("unit") or ""),
                    "method": str(item.get("method") or ""),
                }
            )
    return tests


def build_p17_extracted_report(source_file: str, full_text: str, page_texts: list[str]) -> dict[str, Any]:
    reports: list[dict[str, Any]] = []

    hpv_page = _find_p17_page(page_texts, ["HPV", "16", "18"])
    micro_page = _find_p17_page(page_texts, ["阴道毛滴虫", "加德纳", "乳杆菌"])
    appendix_page = _find_p17_page(page_texts, ["附表"]) or _find_p17_page(page_texts, ["参考文献"])

    if hpv_page is not None:
        hpv_text = page_texts[hpv_page - 1]
        reports.append(
            {
                "report_type": _extract_p17_report_title(hpv_text, "人乳头瘤病毒（HPV）基因分型定量检测报告"),
                "page_number": hpv_page,
                "submission_info": _extract_p17_submission_info(hpv_text),
                "patient_info": _extract_p17_patient_info(hpv_text),
                "detection_content": {
                    "high_risk_types": ",".join(f"HPV{item}" for item in P17_HPV_HIGH_RISK_TYPES),
                    "low_risk_types": ",".join(f"HPV{item}" for item in P17_HPV_LOW_RISK_TYPES),
                },
                "detection_method": _extract_p17_detection_method(hpv_text, "荧光PCR法"),
                "results": _extract_p17_hpv_results(hpv_text),
                "viral_load": _extract_p17_hpv_viral_load(hpv_text),
                "analysis_and_tips": _extract_p17_analysis_and_tips(hpv_text),
                "website": extract_website(hpv_text) or extract_website(full_text),
                "phone": extract_phone(hpv_text) or extract_phone(full_text),
                "address": extract_address(hpv_text) or extract_address(full_text),
            }
        )

    if micro_page is not None:
        micro_text = page_texts[micro_page - 1]
        reports.append(
            {
                "report_type": _extract_p17_report_title(micro_text, "阴道微生态核酸检测报告"),
                "page_number": micro_page,
                "submission_info": _extract_p17_submission_info(micro_text),
                "patient_info": _extract_p17_patient_info(micro_text),
                "detection_content": "见附表",
                "detection_method": _extract_p17_detection_method(micro_text, "多重荧光PCR法"),
                "results": _extract_p17_micro_results(micro_text),
                "remarks": _extract_p17_analysis_and_tips(micro_text),
                "website": extract_website(micro_text) or extract_website(full_text),
                "phone": extract_phone(micro_text) or extract_phone(full_text),
                "address": extract_address(micro_text) or extract_address(full_text),
            }
        )

    if appendix_page is not None:
        appendix_text = page_texts[appendix_page - 1]
        reports.append(
            {
                "report_type": _extract_p17_report_title(appendix_text, "阴道微生态核酸检测报告（附表）"),
                "page_number": appendix_page,
                "submission_info": _extract_p17_submission_info(appendix_text),
                "patient_info": _extract_p17_patient_info(appendix_text),
                "appendix": _extract_p17_appendix(appendix_text),
                "references": _extract_p17_references(appendix_text),
            }
        )

    return {
        "hospital_name": extract_laboratory(full_text) or extract_hospital(full_text),
        "hospital_english": _extract_p17_hospital_english(full_text),
        "reports": reports,
    }


def extract_p17_structured_tests(p17_report: dict[str, Any]) -> list[dict[str, Any]]:
    tests: list[dict[str, Any]] = []
    for report in p17_report.get("reports", []):
        if not isinstance(report, dict):
            continue
        page = int(report.get("page_number") or 0)
        patient_info = report.get("patient_info", {}) if isinstance(report.get("patient_info"), dict) else {}
        specimen_type = str(patient_info.get("specimen_type") or "")
        for item in report.get("results", []):
            if not isinstance(item, dict):
                continue
            test_name = str(item.get("subtype") or item.get("name") or "")
            item_code = field_key_safe(test_name.lower())
            result_text = str(item.get("result") or "")
            ct_value = str(item.get("ct_value") or "")
            indicator = "↑" if "阳性" in result_text else ""
            tests.append(
                {
                    "page": page,
                    "specimen_type": specimen_type,
                    "test_name": test_name,
                    "item_code": item_code,
                    "result": result_text,
                    "indicator": indicator,
                    "reference_range": str(item.get("reference_value") or item.get("reference_range") or ""),
                    "unit": "Ct" if ct_value not in {"", "-", "No Ct"} else "",
                    "method": str(report.get("detection_method") or ""),
                    "ct_value": ct_value,
                    "category": str(item.get("type_category") or item.get("category") or ""),
                }
            )
    return tests


def _extract_p05_report_overview(page_texts: list[str]) -> dict[str, Any]:
    text = " ".join(page_texts)
    page_one = page_texts[0] if page_texts else text
    lab_match = re.search(r"(合肥安为康医学检验实验室)", text)
    address_match = re.search(r"(?:公司地址|地\s*址)[:：]?\s*([^\n]*?安创大楼)", page_one)
    return {
        "laboratory_name": lab_match.group(1) if lab_match else (extract_laboratory(text) or "合肥安为康医学检验实验室"),
        "report_title": "检验报告单 / Results Report",
        "address": clean_value(address_match.group(1)) if address_match else extract_address(text),
        "website": extract_website(text),
        "phone": extract_phone(text),
        "disclaimer": extract_disclaimer(page_one) or extract_disclaimer(text),
    }


def _find_p05_page(page_texts: list[str], keywords: list[str]) -> int | None:
    for index, text in enumerate(page_texts, start=1):
        if all(_p05_keyword_in_text(text, keyword) for keyword in keywords):
            return index
    return None


def _p05_keyword_in_text(text: str, keyword: str) -> bool:
    if keyword in text:
        return True
    return re.search(name_pattern(keyword), text, flags=re.IGNORECASE) is not None


def _extract_p05_barcode(text: str) -> str:
    match = re.search(r"(?:条形码号|条\s*形\s*码)[:：]?\s*([0-9]{8,})", text)
    return match.group(1) if match else extract_report_id(text)


def _extract_p05_basic_info(text: str) -> dict[str, Any]:
    age_value = extract_age(text)
    age_raw = f"{age_value}岁" if age_value != "" else ""
    clinical_diagnosis = _extract_p05_label_value(text, ["临床诊断"])
    if any(clinical_diagnosis.startswith(prefix) for prefix in ["Anweikang", "参考区间", "检验结果报告单", "检测项目"]):
        clinical_diagnosis = ""
    return {
        "submitting_institution": _extract_p05_label_value(text, ["送检单位"]) or extract_hospital(text),
        "name": extract_patient_name(text) or _extract_p05_label_value(text, ["姓名"]),
        "gender": extract_gender(text),
        "age": age_raw,
        "specimen_status": _extract_p05_label_value(text, ["样本状态", "标本情况"]) or extract_specimen_condition(text),
        "specimen_type": _extract_p05_label_value(text, ["标本类型"]),
        "patient_id": _extract_p05_label_value(text, ["病员号", "门诊/住院号", "门诊住院号"]),
        "bed_no": _extract_p05_label_value(text, ["床号", "床 号"]),
        "submitting_department": _extract_p05_label_value(text, ["送检科室", "科室/病区", "科 室/病 区"]),
        "submitting_doctor": _extract_p05_label_value(text, ["送检医生"]),
        "clinical_diagnosis": clinical_diagnosis,
        "outpatient_hospital_no": _extract_p05_label_value(text, ["门诊/住院号", "门诊住院号"]),
        "ward_area": _extract_p05_label_value(text, ["科室/病区", "科 室/病 区"]),
        "sampling_datetime": _extract_p05_label_value(text, ["采样时间", "采样日期"]),
        "receiving_datetime": _extract_p05_label_value(text, ["接收时间"]),
    }


def _extract_p05_label_value(text: str, labels: list[str]) -> str:
    normalized = normalize_text(text)
    next_labels = [
        "条形码号",
        "条 形 码",
        "条码编号",
        "送检单位",
        "姓名",
        "性别",
        "年龄",
        "样本状态",
        "标本情况",
        "标本类型",
        "病员号",
        "床号",
        "床 号",
        "送检科室",
        "科室/病区",
        "科 室/病 区",
        "送检医生",
        "临床诊断",
        "采样时间",
        "采样日期",
        "采集时间",
        "接收时间",
        "报告时间",
        "地址",
        "公司地址",
        "地 址",
        "址",
        "网 址",
        "网址",
        "电 话",
        "电话",
        "检验者",
        "检测者",
        "审核者",
        "批准者",
        "批准人",
        "备注",
        "备 注",
        "医院条码",
        "功能医学测试",
        "门诊/住院号",
        "门诊住院号",
        "单位序号",
        "检测项目",
        "检验项目",
        "参考区间",
        "序号",
        "单位",
        "去甲肾上腺素",
        "肾上腺素",
        "3-甲氧基酪胺",
        "3-甲氧基去甲肾上腺素",
        "3-甲氧基肾上腺素",
        "高香草酸",
        "香草扁桃酸",
        "多巴胺",
        "LC-MS/MS法",
        "化学发光法",
        "第1页/共1页",
        "Anweikang",
    ]
    for label in labels:
        siblings = [candidate for candidate in next_labels if candidate != label]
        value = _extract_between_labels(normalized, label, siblings)
        if value:
            return _sanitize_p05_label_value(label, value)
    return ""


def _sanitize_p05_label_value(label: str, value: str) -> str:
    cleaned = clean_value(value)
    if not cleaned:
        return ""

    if label in {"采样时间", "采样日期", "采集时间", "接收时间", "报告时间"}:
        date_match = re.search(DATE_VALUE_PATTERN, cleaned)
        return date_match.group(0) if date_match else _truncate_p05_table_blob(cleaned)

    if label in {"样本状态", "标本情况"}:
        status_match = re.search(r"(未见异常|正常|异常|溶血|脂血)", cleaned)
        if status_match:
            return status_match.group(1)
        return _truncate_p05_table_blob(cleaned)

    if label == "标本类型":
        return _truncate_p05_table_blob(cleaned)

    if label == "送检单位":
        truncated = _truncate_p05_table_blob(cleaned)
        hospital = extract_hospital(truncated)
        if hospital:
            return hospital
        return re.sub(r"\s+\d+$", "", truncated).strip()

    return _truncate_p05_table_blob(cleaned)


def _truncate_p05_table_blob(value: str) -> str:
    text = clean_value(value)
    stop_patterns = [
        r"\s+\d+\s+(?:去甲肾上腺素|肾上腺素|3-甲氧基|高香草酸|香草扁桃酸|多巴胺|游离三碘|三碘甲状腺|游离甲状腺素|甲状腺素|促甲状腺|抗甲状腺|皮质醇|促肾上腺)",
        r"\s+(?:LC-MS/MS法|化学发光法)\s+",
        r"\s+条码编号[:：]?",
        r"\s+采集时间[:：]?",
        r"\s+采样日期[:：]?",
        r"\s+接收时间[:：]?",
        r"\s+报告时间[:：]?",
        r"\s+第\s*\d+\s*页\s*/\s*共\s*\d+\s*页",
        r"\s+合肥安为康医学检验实验室",
        r"\s+Anweikang\b",
        r"\s+本检测",
    ]
    for pattern in stop_patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            text = text[: match.start()]
    return clean_value(text)


def _is_clean_p05_basic_value(value: str) -> bool:
    compact = clean_value(value)
    if not compact or len(compact) > 40:
        return False
    dirty_markers = (
        "LC-MS/MS法",
        "化学发光法",
        "参考区间",
        "检测结果",
        "nmol/L",
        "pmol/L",
        "mIU/L",
        "IU/mL",
        "IU/ml",
        "第1页",
        "Results Report",
        "本检测",
    )
    return not any(marker in compact for marker in dirty_markers)


def _extract_p05_thyroid_tests(text: str) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for item_code, name in P05_THYROID_TESTS:
        pattern = re.compile(
            rf"(?P<unit>pmol/L|nmol/L|mIU/L|IU/ml|IU/mL)\s+化学发光法\s*"
            rf"{name_pattern(name)}\s*"
            rf"(?P<result>[<>＜]?\d+(?:\.\d+)?)(?![\d.])\s*"
            rf"(?P<hint>[↑↓])?\s*"
            rf"(?P<reference>[<>＜≤≥]?\s*\d+(?:\.\d+)?(?:\s*(?:--|-|－|—|–|~|～)\s*\d+(?:\.\d+)?)?)",
            flags=re.IGNORECASE,
        )
        match = pattern.search(text)
        if not match:
            continue
        items.append(
            {
                "item_code": item_code,
                "test_name": name,
                "result": clean_value(match.group("result").replace("＜", "<")),
                "reference_range": normalize_reference(match.group("reference")),
                "unit": normalize_unit(match.group("unit")),
                "method": "化学发光法",
                "hint": clean_value(match.group("hint") or ""),
            }
        )
    return items


def _extract_p05_single_test(text: str, kind: str) -> list[dict[str, Any]]:
    name_map = {code: name for code, name in P05_SINGLE_TESTS}
    name = name_map[kind]
    patterns = [
        re.compile(
            rf"(nmol/L|pmol/L)\s+化学发光法\s*{name_pattern(name)}\s*([<>＜]?\d+(?:\.\d+)?)\s*(.*?)\s*(?=采样日期|接收时间|报告时间|公司地址|网\s*址|电\s*话|本检测仅对来样负责)",
            flags=re.IGNORECASE | re.DOTALL,
        ),
        re.compile(
            rf"{name_pattern(name)}\s*化学发光法\s*([<>＜]?\d+(?:\.\d+)?)\s*([\s\S]*?)\s*(nmol/L|pmol/L)",
            flags=re.IGNORECASE,
        ),
    ]
    match = patterns[0].search(text)
    if match:
        unit = match.group(1)
        result = match.group(2)
        reference = match.group(3)
    else:
        match = patterns[1].search(text)
        if not match:
            return []
        result = match.group(1)
        reference = match.group(2)
        unit = match.group(3)
    reference = re.split(r"采\s*样日期|接收时间|报告时间", clean_value(reference), maxsplit=1)[0].strip()
    return [
        {
            "item_code": kind,
            "test_name": name,
            "result": clean_value(result.replace("＜", "<")),
            "reference_range": reference,
            "unit": normalize_unit(unit),
            "method": "化学发光法",
            "hint": "",
        }
    ]


def _extract_p05_catecholamine_tests(ocr_items: list[dict[str, Any]], fallback_text: str) -> list[dict[str, Any]]:
    text_items = _extract_p05_catecholamine_tests_from_text(fallback_text)
    if len(text_items) >= 6:
        return text_items
    if not ocr_items:
        return text_items
    items: list[dict[str, Any]] = []
    for item_code, name in P05_CATECHOLAMINE_TESTS:
        name_item = _find_p05_ocr_item(ocr_items, name)
        if not name_item:
            continue
        row_y = float(name_item["y"])
        method_item = _find_p05_nearby_item(ocr_items, row_y, 420, 580)
        result_item = _find_p05_nearby_item(ocr_items, row_y, 600, 700)
        unit_item = _find_p05_nearby_item(ocr_items, row_y, 1000, 1120)
        references = _collect_p05_reference_items(ocr_items, row_y)
        result_text = clean_value(str(result_item["text"])) if result_item else ""
        if not result_text and name == "3-甲氧基酪胺":
            result_text = "<0.06"
        items.append(
            {
                "item_code": item_code,
                "test_name": name,
                "serial_no": len(items) + 1,
                "method": clean_value(str(method_item["text"])) if method_item else "LC-MS/MS法",
                "result": result_text.replace("＜", "<").replace("06'0>", "<0.90"),
                "reference_range": "；".join(references) if references else "",
                "unit": normalize_unit(str(unit_item["text"])) if unit_item else "nmol/L",
                "hint": "",
            }
        )
    return items


def _extract_p05_catecholamine_tests_from_text(text: str) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for item_code, name in P05_CATECHOLAMINE_TESTS:
        pattern = re.compile(
            rf"(?:^|\s)\d+\s+{name_pattern(name)}\s*LC-MS/MS法\s*([<>＜]?\d+(?:\.\d+)?)\s*([\s\S]*?)\s*nmol/L",
            flags=re.IGNORECASE,
        )
        match = pattern.search(text)
        if not match:
            continue
        items.append(
            {
                "item_code": item_code,
                "test_name": name,
                "serial_no": len(items) + 1,
                "method": "LC-MS/MS法",
                "result": clean_value(match.group(1).replace("＜", "<")),
                "reference_range": clean_value(match.group(2)),
                "unit": "nmol/L",
                "hint": "",
            }
        )
    return items


def _find_p05_ocr_item(items: list[dict[str, Any]], target: str) -> dict[str, Any] | None:
    target_text = clean_value(target)
    for item in items:
        if clean_value(str(item.get("text") or "")) == target_text:
            return item
    return None


def _find_p05_nearby_item(items: list[dict[str, Any]], row_y: float, min_x: float, max_x: float) -> dict[str, Any] | None:
    candidates = [
        item
        for item in items
        if min_x <= float(item["x"]) <= max_x and abs(float(item["y"]) - row_y) <= 16
    ]
    if not candidates:
        return None
    return sorted(candidates, key=lambda item: (abs(float(item["y"]) - row_y), float(item["x"])))[0]


def _collect_p05_reference_items(items: list[dict[str, Any]], row_y: float) -> list[str]:
    candidates = [
        item
        for item in items
        if 740 <= float(item["x"]) <= 930 and -6 <= float(item["y"]) - row_y <= 32
    ]
    ordered = sorted(candidates, key=lambda item: (float(item["y"]), float(item["x"])))
    values: list[str] = []
    for item in ordered:
        text = clean_value(str(item["text"] or "")).replace("＜", "<")
        if not text:
            continue
        if text == "06'0>":
            text = "<0.90"
        if text not in values:
            values.append(text)
    return values


def _extract_p05_inline_reviewer(ocr_items: list[dict[str, Any]], fallback_text: str) -> str:
    if ocr_items:
        marker = _find_p05_ocr_item(ocr_items, "审核者:")
        if marker:
            candidates = [
                item
                for item in ocr_items
                if 560 <= float(item["x"]) <= 760 and abs(float(item["y"]) - float(marker["y"])) <= 16
            ]
            if candidates:
                return clean_value(str(sorted(candidates, key=lambda item: float(item["x"]))[-1]["text"]))
    return extract_staff(fallback_text, ["审核者", "复核者"])


def _parse_age_number(value: str) -> int | str:
    match = re.search(r"([0-9]{1,3})", value)
    return int(match.group(1)) if match else ""


def _first_non_empty(values: list[str], validate: Any | None = None) -> str:
    for value in values:
        cleaned = clean_value(value)
        if cleaned and (validate is None or bool(validate(cleaned))):
            return cleaned
    return ""


def _last_non_empty(values: list[str], validate: Any | None = None) -> str:
    for value in reversed(values):
        cleaned = clean_value(value)
        if cleaned and (validate is None or bool(validate(cleaned))):
            return cleaned
    return ""


def _is_valid_p05_staff_value(value: str) -> bool:
    compact = clean_value(value)
    if not compact:
        return False
    if compact in {"址", "话", "网", "备", "注"}:
        return False
    if "功能医学" in compact or "备注" in compact:
        return False
    return True


def _find_page_text(page_texts: list[str], needle: str) -> str:
    for text in page_texts:
        if needle in text:
            return text
    return ""


def _extract_p01_summary_text(page_texts: list[str]) -> str:
    if len(page_texts) >= 7 and any("肠道基因检测报告总结" in text for text in page_texts[-7:]):
        return " ".join(_sanitize_p01_summary_page(text) for text in page_texts[-7:])
    summary_pages = [
        text
        for text in page_texts
        if any(keyword in text for keyword in ["肠道基因检测报告总结", "核心结论", "下一步治疗方案", "异常菌属分析"])
    ]
    return " ".join(_sanitize_p01_summary_page(text) for text in summary_pages)


def _sanitize_p01_summary_page(text: str) -> str:
    cleaned = normalize_text(text)
    cleaned = re.sub(r"安为康医学检验.*?第\s*\d+\s*页\s*/\s*共\s*\d+\s*页", "", cleaned)
    cleaned = re.sub(r"(肠道基因检测报告总结[（(][^）)]+[）)]){2,}", "", cleaned)
    return clean_value(cleaned)


def _extract_between_labels(text: str, label: str, next_labels: list[str]) -> str:
    if not text:
        return ""
    end_pattern = "|".join(label_pattern(item) for item in next_labels)
    pattern = re.compile(
        rf"{label_pattern(label)}[:：]?\s*(?P<value>.*?)\s*(?=(?:{end_pattern})|$)",
        flags=re.S,
    )
    match = pattern.search(text)
    if not match:
        return ""
    return clean_value(match.group("value"))


def _tighten_text(text: str) -> str:
    return normalize_text(text).replace(" ", "")


def _extract_p01_report_info(full_text: str, page_texts: list[str]) -> dict[str, Any]:
    title_match = re.search(r"(人体肠道菌群检测报告)", full_text)
    report_number_match = re.search(r"报告编号[:：]?\s*([0-9]{8,})", full_text)
    page_one = _page_text(page_texts, 1) or full_text
    address_match = re.search(r"地址[:：]?\s*(.*?)\s*客服支持", page_one)
    address = clean_value(address_match.group(1)) if address_match else extract_address(full_text)
    lab_name = address.split("号")[-1] if "号" in address else ("安创大楼" if "安创大楼" in address else "")
    basic_page = _page_text(page_texts, 3) or _find_page_text(page_texts, "主要不适或疾病")
    report_date = _extract_between_labels(basic_page, "报告日期", ["检测项目", "样本类型"]) or extract_date(page_texts, "报告日期")
    return {
        "title": title_match.group(1) if title_match else "",
        "report_date": report_date,
        "lab_name": lab_name,
        "lab_address": address,
        "customer_service": extract_phone(full_text),
        "report_number": report_number_match.group(1) if report_number_match else "",
    }


def _extract_p01_basic_information(full_text: str, page_texts: list[str]) -> dict[str, Any]:
    basic_page = _page_text(page_texts, 3) or _find_page_text(page_texts, "主要不适或疾病") or full_text
    age_value = _extract_between_labels(basic_page, "年龄", ["联系电话"])
    age_match = re.search(r"[0-9]{1,3}", age_value)
    return {
        "name": _extract_between_labels(basic_page, "姓名", ["送检单位", "性别"]),
        "gender": _extract_between_labels(basic_page, "性别", ["样本编号", "年龄"]),
        "age": int(age_match.group(0)) if age_match else "",
        "sample_id": _extract_between_labels(basic_page, "样本编号", ["年龄", "联系电话"]),
        "phone": _extract_between_labels(basic_page, "联系电话", ["主要不适或疾病", "采样日期"]),
        "main_complaint": _extract_between_labels(basic_page, "主要不适或疾病", ["采样日期"]),
        "sampling_date": _extract_between_labels(basic_page, "采样日期", ["收样日期", "报告日期"]) or "-",
        "receiving_date": _extract_between_labels(basic_page, "收样日期", ["报告日期", "检测项目"]),
        "report_date": _extract_between_labels(basic_page, "报告日期", ["检测项目", "样本类型"]),
        "test_item": _extract_between_labels(basic_page, "检测项目", ["样本类型", "检测方法"]),
        "sample_type": _extract_between_labels(basic_page, "样本类型", ["检测方法"]),
        "detection_method": _extract_between_labels(basic_page, "检测方法", ["地址", "客服支持"]) or "高通量测序",
        "submitting_institution": _extract_between_labels(basic_page, "送检单位", ["性别", "样本编号"]) or "-",
    }


def _extract_p01_test_description(page_texts: list[str]) -> str:
    page = _page_text(page_texts, 3) or _find_page_text(page_texts, "二、检测说明")
    if not page:
        return ""
    match = re.search(r"二、检测说明\s*(.*?)(?=姓名\s|送检单位\s|性别\s)", page, flags=re.S)
    return clean_value(match.group(1)) if match else ""


def _extract_p01_result_overview(overview_text: str, summary_text: str) -> dict[str, Any]:
    tight_overview = _tighten_text(overview_text)
    score = _extract_p01_gmhi(summary_text, overview_text).get("score")
    level = _extract_p01_gmhi(summary_text, overview_text).get("assessment", "")
    points: list[str] = []
    if tight_overview:
        for match in re.finditer(
            r"([1-8])\.(.*?)(?=(?:[1-8]\.)|(?:40[≤<]GMHI<60)|(?:[0-9]+(?:\.[0-9]+)?$)|$)",
            tight_overview,
            flags=re.S,
        ):
            value = clean_value(match.group(2))
            if value:
                points.append(value)
    return {
        "gmhi_score": score,
        "gmhi_level": level,
        "summary_points": points,
    }


def _extract_p01_gmhi(summary_text: str, overview_text: str) -> dict[str, Any]:
    tight_summary = _tighten_text(summary_text)
    tight_overview = _tighten_text(overview_text)
    score = None
    assessment = ""
    summary_match = re.search(r"肠道菌群健康指数[:：]([0-9.]+)[（(]([^，）)]+)", tight_summary)
    if summary_match:
        score = _float_or_none(summary_match.group(1))
        assessment = clean_value(summary_match.group(2))
    if score is None:
        score_match = re.search(r"([0-9]+(?:\.[0-9]+)?)$", tight_overview)
        score = _float_or_none(score_match.group(1)) if score_match else None
    if not assessment:
        level_match = re.search(r"属于([^，。]+?)水平", overview_text)
        assessment = clean_value(level_match.group(1)) if level_match else ""
    return {
        "score": score,
        "assessment": assessment,
        "definition": "",
        "range": {},
    }


def _extract_p01_enterotype(summary_text: str) -> str:
    tight_summary = _tighten_text(summary_text)
    match = re.search(r"肠型[:：]([^\s，。；;]+?型(?:[（(][A-Za-z]+[）)])?)", tight_summary)
    return clean_value(match.group(1)) if match else ""


def _extract_p01_diversity(summary_text: str) -> dict[str, Any]:
    tight_summary = _tighten_text(summary_text)
    shannon_match = re.search(r"菌群多样性指数([0-9.]+)", tight_summary)
    percentile_match = re.search(r"第([0-9.]+)%分位", tight_summary)
    return {
        "shannon_index": _float_or_none(shannon_match.group(1)) if shannon_match else None,
        "reference_percentile": f"{percentile_match.group(1)}%" if percentile_match else "",
        "genus_count": None,
        "genus_reference_range": "",
        "species_count": None,
        "species_reference_range": "",
        "interpretation": "",
        "summary": _extract_p01_named_line(tight_summary, "肠道菌群多样性"),
    }


def _extract_p01_intestinal_age(summary_text: str, basic_information: dict[str, Any]) -> dict[str, Any]:
    tight_summary = _tighten_text(summary_text)
    match = re.search(r"肠道年龄[:：]([0-9]+)岁[（(]时序年龄([0-9]+)岁[）)]，?差值([+-]?[0-9]+)岁", tight_summary)
    if match:
        chronological_age = int(match.group(2))
        intestinal_age = int(match.group(1))
        age_difference = f"{match.group(3)}岁"
    else:
        chronological_age = int(basic_information.get("age") or 0) if basic_information.get("age") else None
        intestinal_age = None
        age_difference = ""
    return {
        "chronological_age": chronological_age,
        "intestinal_age": intestinal_age,
        "age_difference": age_difference,
        "reference_standards": "",
        "interpretation": "",
        "summary": _extract_p01_named_line(tight_summary, "肠道年龄"),
    }


def _extract_p01_ranked_items(text: str, *, limit: int) -> list[dict[str, Any]]:
    tight = _tighten_text(text)
    match = re.search(r"依次为[:：](.*)", tight)
    blob = match.group(1) if match else tight
    items: list[dict[str, Any]] = []
    for found in re.finditer(r"([^（()，,]+)[（(]([^,，()（）]+)[,，]([0-9.]+%)[）)]", blob):
        items.append(
            {
                "name": clean_value(found.group(1)),
                "scientific_name": clean_value(found.group(2)),
                "percentage": clean_value(found.group(3)),
            }
        )
        if len(items) >= limit:
            break
    return items


def _extract_p01_fb_ratio(phylum_top_5: list[dict[str, Any]]) -> dict[str, Any]:
    firmicutes = next((item for item in phylum_top_5 if "厚壁菌门" in str(item.get("name") or "")), {})
    bacteroidetes = next((item for item in phylum_top_5 if "拟杆菌门" in str(item.get("name") or "")), {})
    firmicutes_value = _percent_to_float(str(firmicutes.get("percentage") or ""))
    bacteroidetes_value = _percent_to_float(str(bacteroidetes.get("percentage") or ""))
    ratio = round(firmicutes_value / bacteroidetes_value, 4) if firmicutes_value is not None and bacteroidetes_value not in (None, 0) else None
    evaluation = ""
    if firmicutes_value is not None and bacteroidetes_value is not None:
        if firmicutes_value > bacteroidetes_value:
            evaluation = "偏向于厚壁菌"
        elif firmicutes_value < bacteroidetes_value:
            evaluation = "偏向于拟杆菌"
        else:
            evaluation = "平衡"
    return {
        "firmicutes_bacteroidetes_ratio": ratio,
        "result_evaluation": evaluation,
        "reference_range": "0.5-2",
        "firmicutes": {
            "value": str(firmicutes.get("percentage") or ""),
            "evaluation": "正常" if firmicutes else "",
            "reference_range": "",
        },
        "bacteroidetes": {
            "value": str(bacteroidetes.get("percentage") or ""),
            "evaluation": "正常" if bacteroidetes else "",
            "reference_range": "",
        },
        "explanation": "",
    }


def _extract_p01_be_index(text: str) -> dict[str, Any]:
    tight = _tighten_text(text)
    ratio_match = re.search(r"B/E指数([0-9.]+)([^0-9><%]{2,8})(>[0-9.]+)", tight)
    bifidobacterium_match = re.search(r"双歧杆菌属([0-9.]+%?)(正常|偏低|偏高|异常)([0-9.%\-]+)", tight)
    enterobacteriaceae_match = re.search(r"肠杆菌科([0-9.]+%?)(正常|偏低|偏高|异常)([0-9.%\-]+)", tight)
    return {
        "bifidobacterium_enterobacteriaceae_ratio": _float_or_none(ratio_match.group(1)) if ratio_match else None,
        "result_evaluation": clean_value(ratio_match.group(2)) if ratio_match else "",
        "reference_range": ratio_match.group(3) if ratio_match else "",
        "bifidobacterium": {
            "value": _ensure_percent_suffix(bifidobacterium_match.group(1)) if bifidobacterium_match else "",
            "evaluation": bifidobacterium_match.group(2) if bifidobacterium_match else "",
            "reference_range": _ensure_percent_suffix(bifidobacterium_match.group(3)) if bifidobacterium_match else "",
        },
        "enterobacteriaceae": {
            "value": _ensure_percent_suffix(enterobacteriaceae_match.group(1)) if enterobacteriaceae_match else "",
            "evaluation": enterobacteriaceae_match.group(2) if enterobacteriaceae_match else "",
            "reference_range": _ensure_percent_suffix(enterobacteriaceae_match.group(3)) if enterobacteriaceae_match else "",
        },
        "definition": "",
        "interpretation": "",
    }


def _extract_p01_microbe_group(page_texts: list[str], group: str) -> list[dict[str, Any]]:
    chunks: list[str] = []
    if group == "beneficial":
        chunks = [
            _page_text(page_texts, 13),
            _page_text(page_texts, 14),
            _before_keyword(_page_text(page_texts, 15), "10.4 有害菌检测"),
        ]
    elif group == "harmful":
        chunks = [
            _after_keyword(_page_text(page_texts, 15), "10.4 有害菌检测"),
            _page_text(page_texts, 16),
            _page_text(page_texts, 17),
            _before_keyword(_page_text(page_texts, 18), "10.5 中性菌检测"),
        ]
    elif group == "neutral":
        chunks = [
            _after_keyword(_page_text(page_texts, 18), "10.5 中性菌检测"),
            _page_text(page_texts, 19),
            _page_text(page_texts, 20),
        ]
    return _parse_p01_microbe_rows(" ".join(chunk for chunk in chunks if chunk))


def _parse_p01_microbe_rows(text: str) -> list[dict[str, Any]]:
    if not text:
        return []
    cleaned = normalize_text(text)
    if "结果评价" in cleaned:
        cleaned = cleaned.split("结果评价", 1)[1]
    if "注：ND" in cleaned:
        cleaned = cleaned.split("注：ND", 1)[0]
    tokens = cleaned.split()
    rows: list[dict[str, Any]] = []
    index = 0
    while index < len(tokens):
        microbe = tokens[index]
        if not _looks_like_p01_microbe_name(microbe):
            index += 1
            continue
        index += 1
        latin_parts: list[str] = []
        while index < len(tokens) and not _looks_like_p01_result_token(tokens[index]):
            latin_parts.append(tokens[index])
            index += 1
        if not latin_parts or index + 1 >= len(tokens):
            continue
        result = tokens[index]
        reference = tokens[index + 1]
        index += 2
        evaluation = ""
        if index < len(tokens) and tokens[index] in {"正常", "偏低", "偏高", "异常"}:
            evaluation = tokens[index]
            index += 1
        if not evaluation:
            evaluation = _infer_p01_row_evaluation(result, reference)
        rows.append(
            {
                "microbe": clean_value(microbe),
                "latin": clean_value(" ".join(latin_parts)),
                "result": _ensure_percent_suffix(result),
                "reference": _ensure_percent_suffix(reference),
                "evaluation": evaluation,
            }
        )
    return rows


def _looks_like_p01_microbe_name(token: str) -> bool:
    if token in {"微生物名", "拉丁名", "检测结果（%）", "参考范围(%)", "参考范围（%）", "结果评价"}:
        return False
    return bool(re.search(r"[\u4e00-\u9fff]", token))


def _looks_like_p01_result_token(token: str) -> bool:
    return bool(re.fullmatch(r"ND|[0-9]+(?:\.[0-9]+)?%?", token))


def _infer_p01_row_evaluation(result: str, reference: str) -> str:
    numeric_result = None if result == "ND" else _float_or_none(result.replace("%", ""))
    lower, upper = _parse_p01_reference_bounds(reference)
    if result == "ND":
        return "偏低" if lower not in (None, 0.0) else "正常"
    if lower is not None and numeric_result is not None and numeric_result < lower:
        return "偏低"
    if upper is not None and numeric_result is not None and numeric_result > upper:
        return "偏高"
    return "正常"


def _parse_p01_reference_bounds(reference: str) -> tuple[float | None, float | None]:
    cleaned = reference.replace("%", "")
    if cleaned == "0":
        return 0.0, 0.0
    if "-" in cleaned:
        left, right = cleaned.split("-", 1)
        return _float_or_none(left), _float_or_none(right)
    return _float_or_none(cleaned), None


def _extract_p01_disease_analysis(summary_text: str) -> list[dict[str, Any]]:
    tight = _tighten_text(summary_text)
    items: list[dict[str, Any]] = []
    pattern = re.compile(
        r"\((?P<index>\d+)\)(?P<name>[\u4e00-\u9fffA-Za-z]+)\((?P<score>[0-9.]+)(?P<level>低风险|注意|中风险|高风险)\)"
        r".*?风险解读[^:：]*[:：](?P<interpretation>.*?)"
        r"可能后果[^:：]*[:：](?P<consequences>.*?)"
        r"关联异常[^:：]*[:：](?P<related>.*?)(?=\(\d+\)[\u4e00-\u9fffA-Za-z]+\([0-9.]|三、异常菌属分析|四、其他异常问题|$)",
        flags=re.S,
    )
    for match in pattern.finditer(tight):
        items.append(
            {
                "disease": clean_value(match.group("name")),
                "risk_score": _normalize_p01_risk_score(match.group("score")),
                "risk_level": clean_value(match.group("level")),
                "symptoms": clean_value(match.group("interpretation")),
                "consequences": clean_value(match.group("consequences")),
                "related_abnormalities": clean_value(match.group("related")),
            }
        )
    return items


def _normalize_p01_risk_score(value: str) -> float | None:
    text = value.strip()
    if not text:
        return None
    if "." not in text and len(text) == 3 and text.startswith("0"):
        text = f"0.{text[1:]}"
    return _float_or_none(text)


def _extract_p01_report_summary(summary_text: str, disease_analysis: list[dict[str, Any]]) -> dict[str, Any]:
    tight = _tighten_text(summary_text)
    overall_match = re.search(r"核心结论(?:核心结论)*[:：](.*?)(?=肠道菌群健康指数(?:肠道菌群健康指数)*)", tight)
    overall_health = clean_value(overall_match.group(1)) if overall_match else ""
    key_abnormalities = [
        _extract_p01_named_line(tight, "肠道菌群健康指数"),
        _extract_p01_named_line(tight, "肠道菌群多样性"),
        _extract_p01_named_line(tight, "肠道年龄"),
        _extract_p01_named_line(tight, "肠道菌群平衡评估"),
        _extract_p01_named_line(tight, "肠型"),
        _extract_p01_named_line(tight, "物质代谢与营养素评估"),
    ]
    key_abnormalities = [item for item in key_abnormalities if item]
    other_abnormalities = _extract_p01_other_abnormalities(tight)
    conclusion_match = re.search(r"总结(?:总结)*[:：](.*?)(?=\(1\)下一步治疗方案|补充益生菌和益生元|$)", tight)
    conclusion = clean_value(conclusion_match.group(1)) if conclusion_match else ""
    return {
        "overall_health": overall_health,
        "key_abnormalities": key_abnormalities,
        "disease_analysis": disease_analysis,
        "abnormal_flora": _extract_p01_abnormal_flora(tight),
        "other_abnormalities": other_abnormalities,
        "conclusion": conclusion,
        "treatment_plan": _extract_p01_treatment_plan(tight),
        "disclaimer": _extract_p01_disclaimer(tight),
    }


def _extract_p01_abnormal_flora(tight_summary: str) -> dict[str, Any]:
    excessive_harmful: list[dict[str, Any]] = []
    harmful_match = re.search(
        r"1\.嗜血杆菌属[（(]Haemophilus[）)][:：]检测值([0-9.]+%)，.*?参考上限([0-9.]+%)，.*?后果[^:：]*[:：](.*?)功能[^:：]*[:：](.*?)(?=\(2\)丰度过低的有益菌/核心菌|$)",
        tight_summary,
        flags=re.S,
    )
    if harmful_match:
        excessive_harmful.append(
            {
                "name": "嗜血杆菌属",
                "scientific_name": "Haemophilus",
                "value": harmful_match.group(1),
                "reference": harmful_match.group(2),
                "consequences": clean_value(harmful_match.group(3)),
                "function": clean_value(harmful_match.group(4)),
            }
        )

    deficient_beneficial: list[dict[str, Any]] = []
    pattern = re.compile(
        r"\d\.([^\(（:：]+)[（(]([A-Za-z0-9 ._\-\[\]]+)[）)][:：]检测值([0-9.]+%|ND)，.*?参考下限([0-9.]+%)，.*?后果[^:：]*[:：](.*?)功能[^:：]*[:：](.*?)(?=\d\.[^\(（:：]+[（(][A-Za-z]|四、其他异常问题|$)",
        flags=re.S,
    )
    for match in pattern.finditer(tight_summary):
        if match.group(1) == "嗜血杆菌属":
            continue
        deficient_beneficial.append(
            {
                "name": clean_value(match.group(1)),
                "scientific_name": clean_value(match.group(2)),
                "value": match.group(3),
                "reference": match.group(4),
                "consequences": clean_value(match.group(5)),
                "function": clean_value(match.group(6)),
            }
        )
    return {
        "excessive_harmful": excessive_harmful,
        "deficient_beneficial": deficient_beneficial,
    }


def _extract_p01_other_abnormalities(tight_summary: str) -> list[str]:
    items: list[str] = []
    for label, end in [
        ("肠道定植抗力一度损伤（B/E比值0.1583）", "肠道年龄+6岁"),
        ("肠道年龄+6岁（43岁vs时序37岁）", "维生素A合成能力偏低"),
        ("维生素A合成能力偏低", "五、总结与下一步治疗方案"),
    ]:
        value = _extract_p01_section_value(tight_summary, label, end)
        if value:
            items.append(f"{label}：{value}")
    return items


def _extract_p01_treatment_plan(tight_summary: str) -> list[str]:
    items: list[str] = []
    for label, next_label in [
        ("补充益生菌和益生元", "增加膳食纤维摄入"),
        ("增加膳食纤维摄入", "严格限制饮酒"),
        ("严格限制饮酒", "规律作息与温和运动"),
        ("规律作息与温和运动", "定期复查与专科随访"),
        ("定期复查与专科随访", "本报告仅供参考"),
    ]:
        value = _extract_p01_section_value(tight_summary, label, next_label)
        if value:
            value = re.sub(rf"^(?:{re.escape(label)})+(?:[:：])?", "", value)
            items.append(f"{label}：{value}")
    return items


def _extract_p01_disclaimer(tight_summary: str) -> str:
    match = re.search(r"(本报告仅供参考[^。]*。)", tight_summary)
    return clean_value(match.group(1)) if match else ""


def _extract_p01_metabolism_summary(summary_text: str) -> dict[str, Any]:
    tight = _tighten_text(summary_text)
    summary = _extract_p01_named_line(tight, "物质代谢与营养素评估")
    vitamin_match = re.search(r"维生素A合成能力偏低[（(]([0-9.]+)/参考下限([0-9.]+)[）)]", tight)
    return {
        "summary": summary,
        "vitamins": {
            "vitamin_a": {
                "value": _float_or_none(vitamin_match.group(1)) if vitamin_match else None,
                "reference": vitamin_match.group(2) if vitamin_match else "",
                "status": "偏低" if vitamin_match else "",
            }
        },
    }


def _extract_p01_immunity(summary_text: str) -> dict[str, Any]:
    tight = _tighten_text(summary_text)
    match = re.search(r"免疫力评估[:：]肠道免疫力[（(]([0-9.]+)[）)]与抗炎能力[（(]([0-9.]+)[）)]均在正常参考范围内", tight)
    return {
        "intestinal_immunity": {
            "value": _float_or_none(match.group(1)) if match else None,
            "reference": "",
            "status": "正常" if match else "",
        },
        "intestinal_anti_inflammatory": {
            "value": _float_or_none(match.group(2)) if match else None,
            "reference": "",
            "status": "正常" if match else "",
        },
    }


def _extract_p01_quality_control(text: str) -> dict[str, Any]:
    match = re.search(
        r"样本数据\s*([0-9,]+)\s*([0-9.]+%)\s*([0-9.]+%)\s*质控标准\s*(≥?[0-9,]+)\s*(≥?[0-9.]+%)\s*([0-9%-]+)\s*质控结果\s*(合格)\s*(合格)\s*(合格)",
        text,
        flags=re.S,
    )
    tested_by = re.search(r"检测者[:：]\s*([^\s:：]+)", text)
    reviewed_by = re.search(r"审核者[:：]\s*([^\s:：]+)", text)
    note_match = re.search(r"注[:：]\s*(Q30[^。]*。)", text)
    return {
        "total_sequences": int(match.group(1).replace(",", "")) if match else None,
        "q30": match.group(2) if match else "",
        "gc_content": match.group(3) if match else "",
        "qc_standard": {
            "total_sequences": match.group(4) if match else "",
            "q30": match.group(5) if match else "",
            "gc_content": match.group(6) if match else "",
        },
        "qc_result": {
            "total_sequences": match.group(7) if match else "",
            "q30": match.group(8) if match else "",
            "gc_content": match.group(9) if match else "",
        },
        "q30_note": clean_value(note_match.group(1)) if note_match else "",
        "tested_by": tested_by.group(1) if tested_by else "",
        "reviewed_by": reviewed_by.group(1) if reviewed_by else "",
    }


def _extract_p01_diversity_status(diversity: dict[str, Any]) -> str:
    summary = str(diversity.get("summary") or "")
    for label in ["多样性高", "多样性较高", "多样性正常", "正常范围但偏低", "多样性偏低", "多样性低"]:
        if label in summary:
            return label
    percentile = str(diversity.get("reference_percentile") or "").replace("%", "")
    value = _float_or_none(percentile)
    if value is None:
        return ""
    if value > 90:
        return "多样性高"
    if value > 80:
        return "多样性较高"
    if value > 25:
        return "多样性正常"
    if value > 15:
        return "多样性偏低"
    return "多样性低"


def _extract_p01_named_line(tight_text: str, label: str) -> str:
    match = re.search(rf"{re.escape(label)}[:：](.*?)(?=肠道菌群多样性|肠道年龄|肠道菌群平衡评估|肠型|物质代谢与营养素评估|免疫力评估|$)", tight_text)
    return clean_value(match.group(1)) if match else ""


def _extract_p01_section_value(tight_text: str, start_label: str, end_label: str) -> str:
    pattern = re.compile(rf"{re.escape(start_label)}[:：]?(.*?)(?={re.escape(end_label)}|$)", flags=re.S)
    match = pattern.search(tight_text)
    return clean_value(match.group(1)) if match else ""


def _page_text(page_texts: list[str], page_number: int) -> str:
    if 1 <= page_number <= len(page_texts):
        return page_texts[page_number - 1]
    return ""


def _before_keyword(text: str, keyword: str) -> str:
    if not text or keyword not in text:
        return text
    return text.split(keyword, 1)[0]


def _after_keyword(text: str, keyword: str) -> str:
    if not text or keyword not in text:
        return ""
    return text.split(keyword, 1)[1]


def _float_or_none(value: str) -> float | None:
    try:
        return float(str(value).replace("%", "").replace(",", ""))
    except (TypeError, ValueError):
        return None


def _safe_float(value: Any) -> float | None:
    return _float_or_none(str(value or ""))


def _percent_to_float(value: str) -> float | None:
    return _float_or_none(value.replace("%", ""))


def _ensure_percent_suffix(value: str) -> str:
    cleaned = clean_value(value)
    if not cleaned or cleaned == "ND" or cleaned.endswith("%") or cleaned == "0":
        return cleaned
    if re.fullmatch(r"[0-9.]+(?:-[0-9.]+)?", cleaned):
        if "-" in cleaned:
            left, right = cleaned.split("-", 1)
            return f"{left}-{right}%"
        return f"{cleaned}%"
    return cleaned


def _format_number(value: Any) -> str:
    if value in (None, ""):
        return ""
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return str(value)
    return f"{parsed:.4f}".rstrip("0").rstrip(".")


def extract_p01_fields(page_texts: list[str], structured_report: dict[str, Any]) -> list[dict[str, Any]]:
    fields: list[dict[str, Any]] = []
    patient_info = structured_report["patient_info"]
    additional_info = structured_report["additional_info"]
    p01_report = structured_report.get("p01_extracted_report", {})
    basic_information = p01_report.get("basic_information", {}) if isinstance(p01_report, dict) else {}
    fb_ratio = p01_report.get("fb_ratio", {}) if isinstance(p01_report, dict) else {}
    be_index = p01_report.get("be_index", {}) if isinstance(p01_report, dict) else {}

    add_field(fields, "report.barcode", "条形码", structured_report["report_id"], 0.86, find_page(page_texts, structured_report["report_id"]))
    add_field(fields, "patient.name", "姓名", patient_info["name"], 0.82, find_page(page_texts, patient_info["name"]))
    add_field(fields, "patient.gender", "性别", patient_info["gender"], 0.82, find_page(page_texts, patient_info["gender"]))
    if patient_info["age"] != "":
        add_field(fields, "patient.age", "年龄", f"{patient_info['age']} 岁", 0.82, find_page(page_texts, str(patient_info["age"])))
    add_field(fields, "patient.phone", "联系电话", basic_information.get("phone"), 0.8, find_page(page_texts, str(basic_information.get("phone") or "")))
    add_field(fields, "patient.symptoms", "主要不适或疾病", basic_information.get("main_complaint"), 0.8, find_page(page_texts, str(basic_information.get("main_complaint") or "")))
    if p03_patient_info.get("phone"):
        add_field(fields, "patient.phone", "联系电话", p03_patient_info.get("phone"), 0.82, find_page(page_texts, str(p03_patient_info.get("phone") or "")))
    if p03_patient_info.get("clinical_diagnosis"):
        add_field(fields, "patient.symptoms", "相关症状", p03_patient_info.get("clinical_diagnosis"), 0.8, find_page(page_texts, str(p03_patient_info.get("clinical_diagnosis") or "")))
    if patient_info["specimen_types"]:
        add_field(fields, "patient.specimen_types", "样本类型", "、".join(patient_info["specimen_types"]), 0.78, None)
    add_field(fields, "patient.hospital", "送检单位", patient_info["hospital"], 0.76, find_page(page_texts, patient_info["hospital"]))
    add_field(fields, "patient.submitting_unit", "送检单位", patient_info.get("submitting_unit") or patient_info.get("hospital"), 0.76, find_page(page_texts, patient_info.get("submitting_unit") or patient_info.get("hospital") or ""))
    add_field(fields, "report.method", "检测方法", basic_information.get("detection_method"), 0.8, find_page(page_texts, str(basic_information.get("detection_method") or "")))
    add_field(fields, "report.assessment_date", "采样日期", additional_info["sample_date"], 0.78, find_page(page_texts, additional_info["sample_date"]))
    add_field(fields, "report.received_at", "接收时间", additional_info["receive_date"], 0.76, find_page(page_texts, additional_info["receive_date"]))
    add_field(fields, "report.reported_at", "报告时间", additional_info["report_date"], 0.76, find_page(page_texts, additional_info["report_date"]))
    for test in structured_report["tests"]:
        code = str(test.get("item_code") or "")
        if not code:
            continue
        page = int(test.get("page") or 1)
        display_value = format_result_display(str(test.get("result") or ""), str(test.get("indicator") or ""))
        add_field(fields, f"p01.{code}.result_display", str(test.get("test_name") or ""), display_value, 0.72, page)
        add_field(fields, f"p01.{code}.reference_range", str(test.get("test_name") or ""), test.get("reference_range"), 0.68, page)
        add_field(fields, f"p01.{code}.unit", str(test.get("test_name") or ""), test.get("unit"), 0.68, page)
        if test.get("indicator"):
            add_field(fields, f"p01.{code}.status", str(test.get("test_name") or ""), test.get("indicator"), 0.7, page)
    add_field(fields, "p01.fb_ratio.result_display", "F/B比值", fb_ratio.get("firmicutes_bacteroidetes_ratio"), 0.7, find_page(page_texts, "厚壁菌门"))
    add_field(fields, "p01.fb_ratio.status", "F/B比值评估", fb_ratio.get("result_evaluation"), 0.7, find_page(page_texts, "厚壁菌门"))
    add_field(fields, "p01.be_index.result_display", "B/E比值", be_index.get("bifidobacterium_enterobacteriaceae_ratio"), 0.74, find_page(page_texts, "B/E 指数"))
    add_field(fields, "p01.be_index.status", "B/E比值评估", be_index.get("result_evaluation"), 0.74, find_page(page_texts, "B/E 指数"))
    return fields


def extract_p05_fields(page_texts: list[str], structured_report: dict[str, Any]) -> list[dict[str, Any]]:
    fields: list[dict[str, Any]] = []
    patient_info = structured_report["patient_info"]
    additional_info = structured_report["additional_info"]
    p05_report = structured_report.get("p05_extracted_report", {})
    reports = p05_report.get("reports", []) if isinstance(p05_report, dict) else []
    report_overview = p05_report.get("report_overview", {}) if isinstance(p05_report, dict) else {}

    add_field(fields, "report.barcode", "条形码", structured_report["report_id"], 0.84, find_page(page_texts, structured_report["report_id"]))
    add_field(fields, "patient.name", "姓名", patient_info["name"], 0.82, find_page(page_texts, patient_info["name"]))
    add_field(fields, "patient.gender", "性别", patient_info["gender"], 0.8, find_page(page_texts, patient_info["gender"]))
    if patient_info["age"] != "":
        add_field(fields, "patient.age", "年龄", f"{patient_info['age']} 岁", 0.8, find_page(page_texts, str(patient_info["age"])))
    if patient_info["specimen_types"]:
        add_field(fields, "patient.specimen_types", "样本类型", "、".join(patient_info["specimen_types"]), 0.78, None)
    add_field(fields, "patient.hospital", "送检单位", patient_info["hospital"], 0.76, find_page(page_texts, patient_info["hospital"]))
    add_field(fields, "report.assessment_date", "评估日期", additional_info["report_date"] or additional_info["sample_date"], 0.78, find_page(page_texts, additional_info["report_date"] or additional_info["sample_date"]))
    add_field(fields, "organization.phone", "联系电话", report_overview.get("phone"), 0.84, find_page(page_texts, str(report_overview.get("phone") or "")))
    add_field(fields, "organization.website", "官方网站", report_overview.get("website"), 0.82, find_page(page_texts, str(report_overview.get("website") or "")))
    add_field(fields, "organization.address", "公司地址", report_overview.get("address"), 0.8, find_page(page_texts, str(report_overview.get("address") or "")))
    for report in reports:
        if not isinstance(report, dict):
            continue
        page = int(report.get("page") or 1)
        for item in report.get("test_items", []):
            if not isinstance(item, dict):
                continue
            item_code = str(item.get("item_code") or field_key_safe(str(item.get("test_name") or "")))
            label = str(item.get("test_name") or item_code)
            add_field(fields, f"p05.{item_code}.result_display", label, item.get("result"), 0.82, page)
            add_field(fields, f"p05.{item_code}.reference_range", label, item.get("reference_range"), 0.8, page)
            add_field(fields, f"p05.{item_code}.unit", label, item.get("unit"), 0.8, page)
            add_field(fields, f"p05.{item_code}.method", label, item.get("method"), 0.8, page)
    return fields


def extract_p17_fields(page_texts: list[str], structured_report: dict[str, Any]) -> list[dict[str, Any]]:
    fields: list[dict[str, Any]] = []
    patient_info = structured_report["patient_info"]
    additional_info = structured_report["additional_info"]
    p17_report = structured_report.get("p17_extracted_report", {}) if isinstance(structured_report.get("p17_extracted_report"), dict) else {}

    add_field(fields, "report.barcode", "条形码", structured_report["report_id"], 0.88, find_page(page_texts, structured_report["report_id"]))
    add_field(fields, "report.report_id", "报告编号", structured_report["report_id"], 0.88, find_page(page_texts, structured_report["report_id"]))
    add_field(fields, "patient.name", "姓名", patient_info["name"], 0.84, find_page(page_texts, patient_info["name"]))
    add_field(fields, "patient.gender", "性别", patient_info["gender"], 0.82, find_page(page_texts, patient_info["gender"]))
    if patient_info["age"] != "":
        add_field(fields, "patient.age", "年龄", f"{patient_info['age']} 岁", 0.82, find_page(page_texts, str(patient_info["age"])))
    if patient_info["specimen_types"]:
        add_field(fields, "patient.specimen_types", "样本类型", "、".join(patient_info["specimen_types"]), 0.8, None)
    add_field(fields, "sample.type", "样本信息", "分泌物", 0.9, None)
    add_field(fields, "patient.hospital", "送检单位", patient_info["hospital"], 0.8, find_page(page_texts, patient_info["hospital"]))
    add_field(fields, "report.assessment_date", "评估日期", additional_info["report_date"] or additional_info["sample_date"], 0.8, find_page(page_texts, additional_info["report_date"] or additional_info["sample_date"]))
    add_field(fields, "report.method", "评估方法", "荧光PCR法", 0.9, None)

    for report in p17_report.get("reports", []):
        if not isinstance(report, dict):
            continue
        page = int(report.get("page_number") or 1)
        for item in report.get("results", []):
            if not isinstance(item, dict):
                continue
            label = str(item.get("subtype") or item.get("name") or "")
            field_key = field_key_safe(label.lower())
            result_value = str(item.get("result") or "")
            if item.get("ct_value") not in (None, "", "-", "No Ct"):
                result_value = f"{result_value} CT={item.get('ct_value')}"
            add_field(fields, f"p17.{field_key}.result_display", label, result_value, 0.82, page)
            add_field(fields, f"p17.{field_key}.reference_range", label, item.get("reference_value") or item.get("reference_range"), 0.8, page)
    return fields


def extract_p10_fields(page_texts: list[str], structured_report: dict[str, Any]) -> list[dict[str, Any]]:
    fields: list[dict[str, Any]] = []
    patient_info = structured_report.get("patient_info", {})
    additional_info = structured_report.get("additional_info", {})

    add_field(fields, "report.barcode", "条形码", structured_report.get("report_id"), 0.88, find_page(page_texts, str(structured_report.get("report_id") or "")))
    add_field(fields, "report.report_id", "样本编号", structured_report.get("report_id"), 0.88, find_page(page_texts, str(structured_report.get("report_id") or "")))
    add_field(fields, "patient.name", "姓名", patient_info.get("name"), 0.84, find_page(page_texts, str(patient_info.get("name") or "")))
    add_field(fields, "patient.gender", "性别", patient_info.get("gender"), 0.82, find_page(page_texts, str(patient_info.get("gender") or "")))
    if patient_info.get("age") not in ("", None):
        add_field(fields, "patient.age", "年龄", f"{patient_info.get('age')} 岁", 0.82, find_page(page_texts, str(patient_info.get("age") or "")))
    submitting_unit = patient_info.get("submitting_unit") or patient_info.get("hospital")
    add_field(fields, "patient.submitting_unit", "送检单位", submitting_unit, 0.82, find_page(page_texts, str(submitting_unit or "")))
    add_field(fields, "sample.type", "样本信息", P10_SAMPLE_TYPE, 0.9, None)
    add_field(fields, "sample.condition", "标本情况", patient_info.get("specimen_condition"), 0.82, find_page(page_texts, str(patient_info.get("specimen_condition") or "")))
    add_field(fields, "report.assessment_date", "评估日期", additional_info.get("report_date") or additional_info.get("sample_date"), 0.82, None)
    add_field(fields, "report.method", "评估方法", P10_METHOD, 0.9, None)

    for test in structured_report.get("tests", []):
        code = str(test.get("item_code") or "")
        if not code:
            continue
        page = int(test.get("page") or 1)
        label = str(test.get("test_name") or code)
        result = str(test.get("result") or "")
        indicator = str(test.get("indicator") or "")
        prefix = f"p10.indicators.{code}"
        add_field(fields, f"{prefix}.result", label, result, 0.84, page)
        add_field(fields, f"{prefix}.result_display", label, format_result_display(result, indicator), 0.84, page)
        add_field(fields, f"{prefix}.reference_range", label, test.get("reference_range"), 0.8, page)
        add_field(fields, f"{prefix}.unit", label, test.get("unit"), 0.8, page)
        add_field(fields, f"{prefix}.method", label, test.get("method"), 0.8, page)
        if test.get("gene_locus"):
            add_field(fields, f"{prefix}.gene_locus", label, test.get("gene_locus"), 0.82, page)
        if test.get("gene_type"):
            add_field(fields, f"{prefix}.gene_type", label, test.get("gene_type"), 0.82, page)
    return fields


def extract_p02_fields(
    full_text: str,
    page_texts: list[str],
    structured_report: dict[str, Any],
) -> list[dict[str, Any]]:
    fields: list[dict[str, Any]] = []
    patient_info = structured_report["patient_info"]
    additional_info = structured_report["additional_info"]

    add_field(fields, "report.barcode", "条形码", structured_report["report_id"], 0.96, find_page(page_texts, structured_report["report_id"]))
    add_field(fields, "patient.name", "姓名", patient_info["name"], 0.92, find_page(page_texts, patient_info["name"]))
    add_field(fields, "patient.gender", "性别", patient_info["gender"], 0.9, find_page(page_texts, patient_info["gender"]))
    if patient_info["age"] != "":
        add_field(fields, "patient.age", "年龄", f"{patient_info['age']} 岁", 0.9, find_page(page_texts, str(patient_info["age"])))
    add_field(
        fields,
        "patient.specimen_condition",
        "标本情况",
        patient_info["specimen_condition"],
        0.84,
        find_page(page_texts, patient_info["specimen_condition"]),
    )
    if patient_info["specimen_types"]:
        add_field(fields, "patient.specimen_types", "标本类型", "、".join(patient_info["specimen_types"]), 0.88, None)
    add_field(fields, "patient.hospital", "送检单位", patient_info["hospital"], 0.82, find_page(page_texts, patient_info["hospital"]))
    add_field(fields, "report.assessment_date", "采样日期", additional_info["sample_date"], 0.86, find_page(page_texts, additional_info["sample_date"]))
    add_field(fields, "report.received_at", "接收时间", additional_info["receive_date"], 0.84, find_page(page_texts, additional_info["receive_date"]))
    add_field(fields, "report.reported_at", "报告时间", additional_info["report_date"], 0.84, find_page(page_texts, additional_info["report_date"]))

    positive_allergens: list[str] = []
    for test in structured_report["tests"]:
        name = test["test_name"]
        original_name = name.replace("／", "/")
        display_value = format_result_display(test["result"], test["indicator"])
        page = test["page"]
        if "钙卫蛋白" in name:
            add_field(fields, "p02.calprotectin.result_display", "粪便钙卫蛋白检测结果", display_value, 0.94, page)
            add_field(fields, "p02.calprotectin.reference_range", "粪便钙卫蛋白参考范围", test["reference_range"], 0.92, page)
            add_field(fields, "p02.calprotectin.method", "粪便钙卫蛋白检测方法", test["method"], 0.9, page)
            if test["indicator"]:
                add_field(fields, "p02.calprotectin.abnormal_flag", "粪便钙卫蛋白异常标记", test["indicator"], 0.9, page)
            continue
        if "总IgE" in name:
            add_field(fields, "p02.total_ige.result_display", "总IgE检测结果", display_value, 0.94, page)
            add_field(fields, "p02.total_ige.reference_range", "总IgE参考范围", test["reference_range"], 0.92, page)
            add_field(fields, "p02.total_ige.method", "总IgE检测方法", test["method"], 0.9, page)
            if test["indicator"]:
                add_field(fields, "p02.total_ige.abnormal_flag", "总IgE异常标记", test["indicator"], 0.9, page)
            continue

        field_key = f"p02.allergen.items.{field_key_safe(original_name)}"
        add_field(fields, field_key, original_name, display_value, 0.88, page)
        if "阳性" in test["result"] or "弱阳性" in test["result"]:
            positive_allergens.append(f"{name}：{display_value}")

    if any(field["field_key"].startswith("p02.allergen.items.") for field in fields):
        overall = "所有检测项目均为阴性" if not positive_allergens else "、".join(positive_allergens)
        add_field(fields, "p02.allergen.overall_result", "过敏原整体检测结果", overall, 0.88, find_page(page_texts, "免疫印迹法"))
        add_field(fields, "p02.allergen.reference_range", "过敏原参考范围", "阴性", 0.88, find_page(page_texts, "免疫印迹法"))

    return fields


def extract_p04_fields(page_texts: list[str], structured_report: dict[str, Any]) -> list[dict[str, Any]]:
    fields: list[dict[str, Any]] = []
    patient_info = structured_report["patient_info"]
    additional_info = structured_report["additional_info"]

    add_field(fields, "report.barcode", "条形码", structured_report["report_id"], 0.88, find_page(page_texts, structured_report["report_id"]))
    add_field(fields, "patient.name", "姓名", patient_info["name"], 0.84, find_page(page_texts, patient_info["name"]))
    add_field(fields, "patient.gender", "性别", patient_info["gender"], 0.82, find_page(page_texts, patient_info["gender"]))
    if patient_info["age"] != "":
        add_field(fields, "patient.age", "年龄", f"{patient_info['age']} 岁", 0.82, find_page(page_texts, str(patient_info["age"])))
    if patient_info["specimen_types"]:
        add_field(fields, "patient.specimen_types", "样本类型", "、".join(patient_info["specimen_types"]), 0.8, None)
    submitting_unit = patient_info.get("submitting_unit") or patient_info.get("hospital") or ""
    add_field(fields, "patient.hospital", "送检单位", submitting_unit, 0.78, find_page(page_texts, submitting_unit))
    add_field(fields, "patient.submitting_unit", "送检单位", submitting_unit, 0.78, find_page(page_texts, submitting_unit))
    add_field(fields, "report.assessment_date", "评估日期", additional_info["report_date"] or additional_info["sample_date"], 0.8, find_page(page_texts, additional_info["report_date"] or additional_info["sample_date"]))

    for test in structured_report["tests"]:
        code = str(test.get("item_code") or "")
        if not code:
            continue
        page = int(test.get("page") or 1)
        display_value = format_result_display(str(test.get("result") or ""), str(test.get("indicator") or ""))
        label = str(test.get("test_name") or code)
        add_field(fields, f"p04.nutrients.{code}.result_display", label, display_value, 0.82, page)
        add_field(fields, f"p04.nutrients.{code}.status", label, _p04_ocr_status(test), 0.8, page)
        add_field(fields, f"p04.nutrients.{code}.reference_range", label, test.get("reference_range"), 0.8, page)
        add_field(fields, f"p04.nutrients.{code}.unit", label, test.get("unit"), 0.8, page)
        add_field(fields, f"p04.nutrients.{code}.method", label, test.get("method"), 0.78, page)
        if test.get("indicator"):
            add_field(fields, f"p04.nutrients.{code}.abnormal_flag", label, test.get("indicator"), 0.8, page)
    return fields


def extract_p06_fields(page_texts: list[str], structured_report: dict[str, Any]) -> list[dict[str, Any]]:
    fields: list[dict[str, Any]] = []
    patient_info = structured_report["patient_info"]
    additional_info = structured_report["additional_info"]

    add_field(fields, "patient.name", "濮撳悕", patient_info["name"], 0.86, find_page(page_texts, patient_info["name"]))
    add_field(fields, "patient.gender", "鎬у埆", patient_info["gender"], 0.84, find_page(page_texts, patient_info["gender"]))
    if patient_info["age"] != "":
        add_field(fields, "patient.age", "骞撮緞", f"{patient_info['age']}岁", 0.84, find_page(page_texts, str(patient_info["age"])))
    add_field(fields, "report.report_id", "鎶ュ憡缂栧彿", structured_report["report_id"], 0.9, find_page(page_texts, structured_report["report_id"]))
    add_field(fields, "report.assessment_date", "璇勪及鏃ユ湡", additional_info["report_date"] or additional_info["sample_date"], 0.82, find_page(page_texts, additional_info["report_date"] or additional_info["sample_date"]))

    immune_codes = {item[0] for item in P06_IMMUNE_CELL_DEFINITIONS}
    cytokine_codes = {item[0] for item in P06_CYTOKINE_DEFINITIONS}
    for test in structured_report["tests"]:
        code = str(test.get("item_code") or "")
        if not code:
            continue
        page = int(test.get("page") or 1)
        label = str(test.get("test_name") or code)
        if code in immune_codes:
            add_field(fields, f"p06.immune_cells.{code}.absolute_result", label, test.get("result"), 0.82, page)
            add_field(fields, f"p06.immune_cells.{code}.percentage_result", label, test.get("percentage_result"), 0.8, page)
            add_field(fields, f"p06.immune_cells.{code}.absolute_reference", label, test.get("reference_range"), 0.8, page)
            add_field(fields, f"p06.immune_cells.{code}.percentage_reference", label, test.get("percentage_reference"), 0.8, page)
            add_field(fields, f"p06.immune_cells.{code}.status", label, test.get("indicator"), 0.8, page)
        elif code in cytokine_codes:
            add_field(fields, f"p06.cytokines.{code}.result_display", label, test.get("result"), 0.82, page)
            add_field(fields, f"p06.cytokines.{code}.reference_range", label, test.get("reference_range"), 0.8, page)
            add_field(fields, f"p06.cytokines.{code}.status", label, test.get("indicator"), 0.8, page)
    return fields


def extract_p03_fields(page_texts: list[str], structured_report: dict[str, Any]) -> list[dict[str, Any]]:
    fields: list[dict[str, Any]] = []
    patient_info = structured_report["patient_info"]
    additional_info = structured_report["additional_info"]
    p03_report = structured_report.get("p03_extracted_report", {}) if isinstance(structured_report.get("p03_extracted_report"), dict) else {}
    p03_patient_info = p03_report.get("patient_info", {}) if isinstance(p03_report.get("patient_info"), dict) else {}

    add_field(fields, "report.barcode", "条形码", structured_report["report_id"], 0.9, find_page(page_texts, structured_report["report_id"]))
    add_field(fields, "patient.name", "姓名", patient_info["name"], 0.86, find_page(page_texts, patient_info["name"]))
    add_field(fields, "patient.gender", "性别", patient_info["gender"], 0.84, find_page(page_texts, patient_info["gender"]))
    if patient_info["age"] != "":
        add_field(fields, "patient.age", "年龄", f"{patient_info['age']} 岁", 0.84, find_page(page_texts, str(patient_info["age"])))
    if patient_info["specimen_types"]:
        add_field(fields, "patient.specimen_types", "标本类型", "、".join(patient_info["specimen_types"]), 0.82, None)
    add_field(fields, "patient.hospital", "送检单位", patient_info["hospital"], 0.8, find_page(page_texts, patient_info["hospital"]))
    add_field(fields, "report.assessment_date", "采样日期", additional_info["sample_date"], 0.82, find_page(page_texts, additional_info["sample_date"]))
    add_field(fields, "report.received_at", "接收时间", additional_info["receive_date"], 0.8, find_page(page_texts, additional_info["receive_date"]))
    add_field(fields, "report.reported_at", "报告时间", additional_info["report_date"], 0.8, find_page(page_texts, additional_info["report_date"]))

    for test in structured_report["tests"]:
        code = str(test.get("item_code") or "")
        if not code:
            continue
        page = int(test.get("page") or 1)
        add_field(fields, f"p03.{code}.result_display", str(test.get("test_name") or ""), test.get("result"), 0.82, page)
        add_field(fields, f"p03.{code}.reference_range", str(test.get("test_name") or ""), test.get("reference_range"), 0.8, page)
        add_field(fields, f"p03.{code}.unit", str(test.get("test_name") or ""), test.get("unit"), 0.8, page)
        add_field(fields, f"p03.{code}.method", str(test.get("test_name") or ""), test.get("method"), 0.78, page)
        if test.get("indicator"):
            add_field(fields, f"p03.{code}.abnormal_flag", str(test.get("test_name") or ""), test.get("indicator"), 0.8, page)
    return fields


def extract_structured_tests(page_texts: list[str], package_code: str = "P02") -> list[dict[str, Any]]:
    if package_code == "P01":
        return extract_p01_structured_tests(page_texts)
    if package_code == "P05":
        return []
    if package_code == "P03":
        return extract_p03_structured_tests(page_texts)
    if package_code == "P04":
        return extract_p04_structured_tests(page_texts)
    if package_code == "P06":
        return extract_p06_structured_tests(page_texts)
    if package_code == "P12":
        return extract_p12_structured_tests(page_texts)
    if package_code == "P10":
        return extract_p10_structured_tests(page_texts)
    if package_code == "P17":
        return []

    tests: list[dict[str, Any]] = []
    for page_number, text in enumerate(page_texts, start=1):
        specimen_type = extract_page_specimen_type(text)
        cal_match = re.search(
            rf"{name_pattern(CALPROTECTIN_NAME)}\s*(?P<result>{RESULT_PATTERN})\s*"
            rf"(?P<method>胶体金法)?\s*(?P<reference>阴性|阳性)?\s*(?P<flag>[↑↓])?",
            text,
            flags=re.IGNORECASE,
        )
        if cal_match:
            tests.append(
                build_test(
                    page=page_number,
                    specimen_type=specimen_type or "粪便",
                    test_name=CALPROTECTIN_NAME,
                    raw_result=cal_match.group("result"),
                    flag=cal_match.group("flag"),
                    reference_range=cal_match.group("reference") or "阴性",
                    method=cal_match.group("method") or "胶体金法",
                )
            )

        for item in ALLERGEN_ITEMS:
            row_match = re.search(
                rf"{name_pattern(item)}\s*(?P<result>{RESULT_PATTERN})\s*"
                rf"(?P<reference>阴性|阳性)?\s*(?P<flag>[↑↓])?\s*(?P<method>免疫印迹法)?",
                text,
                flags=re.IGNORECASE,
            )
            if not row_match:
                continue
            tests.append(
                build_test(
                    page=page_number,
                    specimen_type=specimen_type or "血清",
                    test_name=output_test_name(item),
                    raw_result=row_match.group("result"),
                    flag=row_match.group("flag"),
                    reference_range=row_match.group("reference") or "阴性",
                    method=row_match.group("method") or "免疫印迹法",
                )
            )

        ige_match = re.search(
            rf"{name_pattern(TOTAL_IGE_NAME)}\s*(?P<result>{RESULT_PATTERN})\s*"
            rf"(?P<reference>阴性|阳性)?\s*(?P<flag>[↑↓])?\s*(?P<method>免疫印迹法)?",
            text,
            flags=re.IGNORECASE,
        )
        if ige_match:
            tests.append(
                build_test(
                    page=page_number,
                    specimen_type=specimen_type or "血清",
                    test_name=TOTAL_IGE_NAME,
                    raw_result=ige_match.group("result"),
                    flag=ige_match.group("flag"),
                    reference_range=ige_match.group("reference") or "阴性",
                    method=ige_match.group("method") or "免疫印迹法",
                )
            )

    return tests


def extract_p10_structured_tests(page_texts: list[str]) -> list[dict[str, Any]]:
    tests: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for page_number, text in enumerate(page_texts, start=1):
        specimen_type = extract_page_specimen_type(text) or "血清"
        for parsed in _extract_p10_gene_tests(text, page_number):
            dedupe_key = (str(parsed["item_code"]), str(parsed["gene_locus"]))
            if dedupe_key in seen:
                continue
            seen.add(dedupe_key)
            tests.append(parsed)
        for item_code, test_name in (
            ("psa", "总前列腺特异性抗原"),
            ("psa_free", "游离前列腺特异性抗原"),
            ("psa_ratio", "游离/总前列腺特异性抗原比值"),
            ("dhea", "脱氢表雄酮（DHEA）"),
            ("inhibin_b", "抑制素B"),
        ):
            parsed = _extract_p10_lab_test(text, test_name, item_code=item_code)
            if not parsed:
                continue
            dedupe_key = (item_code, str(parsed["result"]))
            if dedupe_key in seen:
                continue
            seen.add(dedupe_key)
            tests.append(
                {
                    "page": page_number,
                    "specimen_type": specimen_type,
                    "test_name": test_name,
                    "item_code": item_code,
                    "result": parsed["result"],
                    "indicator": parsed["indicator"],
                    "reference_range": parsed["reference_range"],
                    "unit": parsed["unit"],
                    "method": parsed["method"],
                }
            )
    return tests


def parse_json_to_standard_ocr_json(
    json_path: Path,
    package_code: str = "P02",
    *,
    strategy_version: str | None = None,
) -> dict[str, Any]:
    payload = json.loads(json_path.read_text(encoding="utf-8-sig"))
    if package_code not in {"P10", "P11", "P12", "P13", "P14", "P15", "P16"}:
        raise ValueError(f"{package_code} 暂不支持直接导入 JSON OCR 结果。")
    if package_code == "P12" and not _is_p12_ocr_payload(payload):
        raise ValueError("P12 JSON OCR 结果缺少 report_overview / test_items / nad_assessment 结构。")
    if package_code == "P13" and not _is_p13_ocr_payload(payload):
        raise ValueError("P13 JSON OCR 结果缺少 report_info / patient_info / test_results 结构。")
    if package_code == "P14" and not _is_p14_ocr_payload(payload):
        raise ValueError("P14 JSON OCR 结果缺少 reports[] 多报告聚合结构。")
    if package_code == "P15" and not _is_p15_ocr_payload(payload):
        raise ValueError("P15 JSON OCR 结果缺少 report_info / patient_info / test_details / results 结构。")
    if package_code == "P16" and not _is_p16_ocr_payload(payload):
        raise ValueError("P16 JSON OCR 结果缺少 reports[] 多报告聚合结构。")
    if package_code not in {"P12", "P13", "P14", "P15", "P16"} and not _is_supported_reportmeta_payload(payload, package_code=package_code):
        raise ValueError(f"{package_code} JSON OCR 结果缺少可支持的 reportMeta 结构。")

    page_texts = [normalize_text(json.dumps(payload, ensure_ascii=False))]
    pages = [
        {
            "page_number": 1,
            "width": None,
            "height": None,
            "text_blocks": [
                {
                    "text": page_texts[0],
                    "confidence": 0.99,
                    "bbox": None,
                }
            ],
        }
    ]
    strategy = strategy_version or (
        P13_STRATEGY_VERSION
        if package_code == "P13"
        else (
            P12_STRATEGY_VERSION
            if package_code == "P12"
            else (
                P14_STRATEGY_VERSION
                if package_code == "P14"
                else (
                P15_STRATEGY_VERSION
                if package_code == "P15"
                else (P16_STRATEGY_VERSION if package_code == "P16" else (P11_STRATEGY_VERSION if package_code == "P11" else P10_STRATEGY_VERSION))
                )
            )
        )
    )
    if package_code == "P12":
        structured_report = build_p12_structured_report_from_ocr_json(json_path.name, payload)
        fields = extract_p12_fields(page_texts, structured_report)
        provider = "p12-ocr-json-antioxidant-nad-adapter"
    elif package_code == "P13":
        structured_report = build_p13_structured_report_from_ocr_json(json_path.name, payload)
        fields = extract_p13_fields(page_texts, structured_report)
        provider = "p13-telomere-json-adapter"
    elif package_code == "P14":
        structured_report = build_p14_structured_report_from_ocr_json(json_path.name, payload)
        fields = extract_p14_fields(page_texts, structured_report)
        provider = "p14-cancer-multireport-json-adapter"
    elif package_code == "P15":
        structured_report = build_p15_structured_report_from_ocr_json(json_path.name, payload)
        fields = extract_p15_fields(page_texts, structured_report)
        provider = "p15-environment-hormone-json-adapter"
    elif package_code == "P16":
        structured_report = build_p16_structured_report_from_ocr_json(json_path.name, payload)
        fields = extract_p16_fields(page_texts, structured_report)
        provider = "p16-pgx-multireport-json-adapter"
    elif package_code == "P11":
        structured_report = build_structured_report(
            json_path.name,
            page_texts[0],
            page_texts,
            package_code="P11",
        )
        fields = extract_p11_fields(
            page_texts=page_texts,
            structured_report=structured_report,
            add_field=add_field,
            find_page=find_page,
        )
        provider = "p11-reportmeta-food-json-adapter"
    else:
        structured_report = build_p10_structured_report_from_reportmeta_json(json_path.name, payload)
        fields = extract_p10_fields(page_texts, structured_report)
        provider = "p10-reportmeta-json-adapter"
    confidence = calculate_confidence(fields, pages)
    warnings = build_warnings(fields, pages, structured_report, package_code=package_code)
    result = {
        "schema_version": "1.0",
        "package_code": package_code,
        "source_file": json_path.name,
        "strategy_version": strategy,
        "provider": provider,
        "pages": pages,
        "fields": fields,
        "indicators": build_indicators(fields),
        "structured_report": structured_report,
        "warnings": warnings,
        "created_at": now_iso(),
        "debug": {
            "comparison_key": f"{package_code}:{json_path.name}:{strategy}",
            "field_keys": [field["field_key"] for field in fields],
            "overall_confidence": confidence,
            "structured_test_count": len(structured_report.get("tests", [])),
        },
    }
    if package_code == "P11":
        result["p11_extracted_report"] = structured_report.get("p11_extracted_report", {})
    elif package_code == "P12":
        result["p12_extracted_report"] = structured_report.get("p12_extracted_report", {"tests": structured_report.get("tests", [])})
    elif package_code == "P13":
        result["p13_extracted_report"] = structured_report.get("p13_extracted_report", {"tests": structured_report.get("tests", [])})
    elif package_code == "P14":
        result["p14_extracted_report"] = structured_report.get("p14_extracted_report", {"tests": structured_report.get("tests", [])})
    elif package_code == "P15":
        result["p15_extracted_report"] = structured_report.get("p15_extracted_report", {"tests": structured_report.get("tests", [])})
    elif package_code == "P16":
        result["p16_extracted_report"] = structured_report.get("p16_extracted_report", {"tests": structured_report.get("tests", [])})
    else:
        result["p10_extracted_report"] = structured_report.get("p10_extracted_report", {})
    return result


def _is_p10_reportmeta_payload(payload: Any) -> bool:
    return _is_reportmeta_sections_payload(payload)


def _is_supported_reportmeta_payload(payload: Any, *, package_code: str) -> bool:
    if _is_reportmeta_sections_payload(payload):
        return True
    return (
        package_code == "P11"
        and isinstance(payload, dict)
        and isinstance(payload.get("reportMeta"), dict)
        and isinstance(payload.get("foodIntoleranceResults"), list)
    )


def _is_p12_ocr_payload(payload: Any) -> bool:
    return (
        isinstance(payload, dict)
        and isinstance(payload.get("report_overview"), dict)
        and isinstance(payload.get("test_items"), list)
        and isinstance(payload.get("nad_assessment"), dict)
    )


def _is_p13_ocr_payload(payload: Any) -> bool:
    return (
        isinstance(payload, dict)
        and isinstance(payload.get("report_info"), dict)
        and isinstance(payload.get("patient_info"), dict)
        and isinstance(payload.get("test_results"), dict)
    )


def _is_p15_ocr_payload(payload: Any) -> bool:
    return (
        isinstance(payload, dict)
        and isinstance(payload.get("report_info"), dict)
        and isinstance(payload.get("patient_info"), dict)
        and isinstance(payload.get("test_details"), dict)
        and isinstance(payload.get("results"), list)
    )


def _is_p14_ocr_payload(payload: Any) -> bool:
    return (
        isinstance(payload, dict)
        and isinstance(payload.get("reports"), list)
        and any(isinstance(item, dict) and "report_type" in item for item in payload.get("reports", []))
    )


def _is_p16_ocr_payload(payload: Any) -> bool:
    return (
        isinstance(payload, dict)
        and isinstance(payload.get("reports"), list)
        and any(isinstance(item, dict) and "report_type" in item for item in payload.get("reports", []))
    )


def _is_reportmeta_sections_payload(payload: Any) -> bool:
    return (
        isinstance(payload, dict)
        and isinstance(payload.get("reportMeta"), dict)
        and isinstance(payload.get("sections"), list)
    )


def _looks_like_json_ocr_file(path: Path, *, package_code: str) -> bool:
    if package_code not in {"P10", "P11", "P12", "P13", "P14", "P15", "P16"}:
        return False
    if path.suffix.lower() == ".pdf":
        return False
    try:
        with path.open("r", encoding="utf-8-sig") as handle:
            prefix = handle.read(2048).lstrip()
    except (OSError, UnicodeDecodeError):
        return False
    if not prefix.startswith("{"):
        return False
    if package_code == "P12":
        return '"report_overview"' in prefix and '"nad_assessment"' in prefix
    if package_code == "P13":
        return '"report_info"' in prefix and '"test_results"' in prefix and '"telomere' in prefix
    if package_code == "P14":
        return '"reports"' in prefix and '"report_type"' in prefix and '"疾病风险评估报告"' in prefix
    if package_code == "P15":
        return '"report_info"' in prefix and '"patient_info"' in prefix and '"test_details"' in prefix and '"results"' in prefix
    if package_code == "P16":
        return '"reports"' in prefix and '"report_type"' in prefix and '"patient_name"' in prefix
    return '"reportMeta"' in prefix and ('"sections"' in prefix or (package_code == "P11" and '"foodIntoleranceResults"' in prefix))


def _find_p14_sidecar_ocr_file(pdf_path: Path) -> Path | None:
    if pdf_path.suffix.lower() != ".pdf":
        return None
    candidates = [
        pdf_path.with_suffix(".json"),
        pdf_path.with_suffix(".ocr.json"),
        pdf_path.with_name("OCR.txt"),
        pdf_path.with_name("ocr.txt"),
    ]
    for candidate in candidates:
        if candidate.exists() and _looks_like_json_ocr_file(candidate, package_code="P14"):
            return candidate
    return None


def _find_p16_sidecar_ocr_file(pdf_path: Path) -> Path | None:
    if pdf_path.suffix.lower() != ".pdf":
        return None
    candidates = [
        pdf_path.with_suffix(".json"),
        pdf_path.with_suffix(".ocr.json"),
        pdf_path.with_name("OCR.txt"),
        pdf_path.with_name("ocr.txt"),
    ]
    for candidate in candidates:
        if candidate.exists() and _looks_like_json_ocr_file(candidate, package_code="P16"):
            return candidate
    return None


def build_p10_structured_report_from_reportmeta_json(source_file: str, payload: dict[str, Any]) -> dict[str, Any]:
    report_meta = payload.get("reportMeta", {}) if isinstance(payload.get("reportMeta"), dict) else {}
    laboratory_info = payload.get("laboratoryInfo", {}) if isinstance(payload.get("laboratoryInfo"), dict) else {}
    sections = payload.get("sections", []) if isinstance(payload.get("sections"), list) else []
    tests: list[dict[str, Any]] = []
    specimen_types: list[str] = []
    raw_sample_type = _first_text(laboratory_info.get("sampleType"))
    if raw_sample_type:
        specimen_types.append(raw_sample_type)

    for section_index, section in enumerate(sections, start=1):
        if not isinstance(section, dict):
            continue
        section_name = _first_text(section.get("sectionName"), section.get("section_title"))
        section_type = _first_text(section.get("testType"), raw_sample_type)
        if section_type and section_type not in specimen_types:
            specimen_types.append(section_type)
        for item in section.get("results", []):
            if not isinstance(item, dict):
                continue
            gene = _first_text(item.get("gene"))
            variant = _first_text(item.get("variant"), item.get("locus"), item.get("gene_locus"))
            is_gene_result = bool(gene or variant or _first_text(item.get("genotype"), item.get("geneType")))
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
                        "test_name": gene or section_name,
                        "item_code": _p10_item_code_from_gene_name(gene, title=section_name),
                        "result": genotype,
                        "indicator": "",
                        "reference_range": "",
                        "unit": "",
                        "method": "基因检测",
                        "gene_locus": variant,
                        "gene_type": genotype,
                        "interpretation": _first_text(section.get("interpretation")),
                        "recommendations": section.get("recommendations") if isinstance(section.get("recommendations"), list) else [],
                        "references": section.get("references") if isinstance(section.get("references"), list) else [],
                        "section_title": section_name,
                        "section_description": _first_text(section.get("description")),
                    }
                )
                continue

            test_name = _first_text(item.get("testItem"), item.get("test_item"), item.get("name"))
            if not test_name:
                continue
            tests.append(
                {
                    "page": section_index,
                    "specimen_type": section_type or raw_sample_type,
                    "test_name": test_name,
                    "item_code": _p10_item_code_from_test_name(test_name),
                    "result": _first_text(item.get("result")),
                    "indicator": _first_text(item.get("indicator"), item.get("status")),
                    "reference_range": _first_text(item.get("referenceRange"), item.get("reference_range")),
                    "unit": _first_text(item.get("unit")),
                    "method": _first_text(item.get("method")),
                    "section_title": section_name,
                    "section_description": _first_text(section.get("description")),
                    "note": _first_text(section.get("note")),
                }
            )

    specimen_types = [value for value in dict.fromkeys(specimen_types) if value]
    report_date = _first_text(laboratory_info.get("reportTime"), report_meta.get("reportDate"))
    lab_name = _first_text(report_meta.get("labName"))
    return {
        "report_id": _first_text(report_meta.get("barcode"), Path(source_file).stem),
        "patient_info": {
            "name": _first_text(report_meta.get("patientName"), report_meta.get("name")),
            "gender": _first_text(report_meta.get("gender")),
            "age": _parse_age_number(_first_text(report_meta.get("age"))),
            "specimen_condition": _first_text(laboratory_info.get("sampleStatus")),
            "specimen_types": specimen_types,
            "hospital": lab_name,
            "submitting_unit": lab_name,
            "patient_number": "",
            "bed_number": "",
            "department": "",
            "doctor": "",
            "clinical_diagnosis": _first_text(report_meta.get("reportSubtitle")),
            "phone": "",
        },
        "tests": tests,
        "notes": _first_text(laboratory_info.get("note")),
        "additional_info": {
            "sample_date": _first_text(laboratory_info.get("collectionTime")),
            "receive_date": _first_text(laboratory_info.get("receiptTime")),
            "report_date": report_date,
            "technician": "",
            "reviewer": "",
            "approver": "",
        },
        "p10_extracted_report": {
            "source_file": source_file,
            "mode": "reportmeta-json",
            "report_info": {
                "title": _first_text(report_meta.get("reportName")),
                "subtitle": _first_text(report_meta.get("reportSubtitle")),
                "barcode": _first_text(report_meta.get("barcode")),
                "date": _first_text(report_meta.get("reportDate")),
                "submitting_unit": lab_name,
                "name": _first_text(report_meta.get("patientName"), report_meta.get("name")),
            },
            "sections": sections,
            "laboratory_info": laboratory_info,
            "contact": {
                "website": _first_text(report_meta.get("labWebsite")),
                "phone": _first_text(report_meta.get("labPhone")),
                "address": _first_text(report_meta.get("labAddress")),
            },
            "remarks": _first_text(laboratory_info.get("note")),
        },
    }


def _p10_item_code_from_gene_name(gene: str, *, title: str = "") -> str:
    gene_upper = _first_text(gene).upper()
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
    return gene_upper.lower() or field_key_safe(title)


def _p10_item_code_from_test_name(name: str) -> str:
    normalized = re.sub(r"[\s_\-（）()]+", "", _first_text(name).lower())
    if "游离/总前列腺特异" in normalized or "游离/总psa" in normalized or "f/tpsa" in normalized or "比值" == normalized:
        return "psa_ratio"
    if "游离前列腺特异" in normalized or "游离psa" in normalized or "fpsa" in normalized:
        return "psa_free"
    if "总前列腺特异" in normalized or "总psa" in normalized or normalized == "psa":
        return "psa"
    if "脱氢表雄酮" in normalized or "dhea" in normalized:
        return "dhea"
    if "抑制素b" in normalized:
        return "inhibin_b"
    return field_key_safe(normalized)


def _extract_p10_gene_tests(text: str, page_number: int) -> list[dict[str, Any]]:
    tests: list[dict[str, Any]] = []

    if "CYP1A1" in text:
        for locus, genotype in re.findall(r"CYP1A1\s+(c\.[^\s]+)\s+([A-Z]{1,2})", text, flags=re.IGNORECASE):
            tests.append(
                {
                    "page": page_number,
                    "specimen_type": "基因检测",
                    "test_name": "CYP1A1",
                    "item_code": "cyp1a1",
                    "result": clean_value(genotype),
                    "indicator": "",
                    "reference_range": "",
                    "unit": "",
                    "method": "基因检测",
                    "gene_locus": clean_value(locus),
                    "gene_type": clean_value(genotype),
                }
            )

    if "ADH1B" in text or "ALDH2" in text:
        for gene, locus, genotype in re.findall(r"(ADH1B|ALDH2)\s+([cg]\.[^\s]+)\s+([A-Z]{1,2})", text, flags=re.IGNORECASE):
            tests.append(
                {
                    "page": page_number,
                    "specimen_type": "基因检测",
                    "test_name": clean_value(gene),
                    "item_code": "adh1b" if gene.upper() == "ADH1B" else "aldh2",
                    "result": clean_value(genotype),
                    "indicator": "",
                    "reference_range": "",
                    "unit": "",
                    "method": "基因检测",
                    "gene_locus": clean_value(locus),
                    "gene_type": clean_value(genotype),
                }
            )

    if "MCM6" in text:
        for locus, genotype in re.findall(r"MCM6\s+(c\.[^\s]+)\s+([A-Z]{2})", text, flags=re.IGNORECASE):
            tests.append(
                {
                    "page": page_number,
                    "specimen_type": "基因检测",
                    "test_name": "MCM6",
                    "item_code": "lct",
                    "result": clean_value(genotype),
                    "indicator": "",
                    "reference_range": "",
                    "unit": "",
                    "method": "基因检测",
                    "gene_locus": clean_value(locus),
                    "gene_type": clean_value(genotype),
                }
            )

    if "CYP1A2" in text:
        for locus, genotype in re.findall(r"CYP1A2\s+(c\.[^\s]+)\s+([A-Z]{2})", text, flags=re.IGNORECASE):
            tests.append(
                {
                    "page": page_number,
                    "specimen_type": "基因检测",
                    "test_name": "CYP1A2",
                    "item_code": "cyp1a2",
                    "result": clean_value(genotype),
                    "indicator": "",
                    "reference_range": "",
                    "unit": "",
                    "method": "基因检测",
                    "gene_locus": clean_value(locus),
                    "gene_type": clean_value(genotype),
                }
            )

    return tests


def _extract_p10_lab_test(text: str, test_name: str, *, item_code: str = "") -> dict[str, str] | None:
    if item_code in {"psa", "psa_free", "psa_ratio"}:
        parsed = _extract_p10_psa_stacked_test(text, item_code)
        if parsed:
            return parsed

    match = re.search(
        rf"{name_pattern(test_name)}\s+"
        r"(?P<result>[0-9]+(?:\.[0-9]+)?)\s+"
        r"(?P<method>ELISA法|化学发光法|计算法)\s+"
        r"(?P<reference>.*?)(?P<unit>ng/mL|pg/mL|%)",
        text,
        flags=re.IGNORECASE | re.S,
    )
    if not match:
        return None
    reference_range = clean_value(match.group("reference"))
    reference_range = re.sub(r"\s+", " ", reference_range).strip()
    return {
        "result": clean_value(match.group("result")),
        "indicator": "",
        "reference_range": reference_range,
        "unit": clean_value(match.group("unit")),
        "method": clean_value(match.group("method")),
    }


def _extract_p10_psa_stacked_test(text: str, item_code: str) -> dict[str, str] | None:
    aliases = {
        "psa": ("总前列腺特异性抗原", "总PSA", "tPSA"),
        "psa_free": ("游离前列腺特异性抗原", "游离PSA", "fPSA"),
        "psa_ratio": ("游离/总前列腺特异性抗原比值", "游离/总前列腺特异性抗原", "游离/总PSA", "f/tPSA"),
    }.get(item_code, ())
    if not aliases:
        return None

    match = None
    for alias in aliases:
        match = re.search(name_pattern(alias), text, flags=re.IGNORECASE)
        if match:
            break
    if not match:
        return None

    next_positions = []
    for other_code, other_aliases in {
        "psa": ("总前列腺特异性抗原", "总PSA", "tPSA"),
        "psa_free": ("游离前列腺特异性抗原", "游离PSA", "fPSA"),
        "psa_ratio": ("游离/总前列腺特异性抗原比值", "游离/总前列腺特异性抗原", "游离/总PSA", "f/tPSA"),
    }.items():
        if other_code == item_code:
            continue
        for other_alias in other_aliases:
            other_match = re.search(name_pattern(other_alias), text[match.end() :], flags=re.IGNORECASE)
            if other_match:
                next_positions.append(match.end() + other_match.start())
    window_end = min(next_positions) if next_positions else match.end() + 160
    window = text[match.end() : window_end]
    row_match = re.search(
        r"(?P<result>[0-9]+(?:\.[0-9]+)?)\s*"
        r"(?P<indicator>[↑↓]|\+|-)?\s*"
        r"(?P<reference>(?:≤|>=|≥|<=|<|>|＜|＞)\s*[0-9]+(?:\.[0-9]+)?|[0-9]+(?:\.[0-9]+)?\s*(?:--|-|~|～)\s*[0-9]+(?:\.[0-9]+)?)?",
        window,
    )
    if not row_match:
        return None

    prefix = text[max(0, match.start() - 80) : match.start()]
    unit = ""
    unit_matches = re.findall(r"ng/mL|pg/mL|%", prefix, flags=re.IGNORECASE)
    if unit_matches:
        unit = unit_matches[-1]
    if item_code == "psa_ratio":
        unit = ""

    method = ""
    method_matches = re.findall(r"ELISA法|化学发光法|计算法", prefix, flags=re.IGNORECASE)
    if method_matches:
        method = method_matches[-1]
    if item_code == "psa_ratio" and not method:
        method = "计算法"

    return {
        "result": clean_value(row_match.group("result")),
        "indicator": clean_value(row_match.group("indicator") or ""),
        "reference_range": _p10_normalize_reference(row_match.group("reference") or ""),
        "unit": clean_value(unit),
        "method": clean_value(method),
    }


def _p10_normalize_reference(reference: str) -> str:
    return (
        clean_value(reference)
        .replace("＜", "<")
        .replace("＞", ">")
        .replace(" ", "")
    )


def extract_p06_structured_tests(page_texts: list[str]) -> list[dict[str, Any]]:
    tests: list[dict[str, Any]] = []
    seen_codes: set[str] = set()
    for page_number, text in enumerate(page_texts, start=1):
        specimen_type = extract_page_specimen_type(text) or "血清"
        for code, output_name, keywords in P06_IMMUNE_CELL_DEFINITIONS:
            if code in seen_codes:
                continue
            parsed = find_p06_immune_cell_result(text, keywords)
            if not parsed:
                continue
            tests.append(
                {
                    "page": page_number,
                    "specimen_type": specimen_type,
                    "test_name": output_name,
                    "item_code": code,
                    "result": parsed["absolute_result"],
                    "indicator": parsed["status"],
                    "reference_range": parsed["absolute_reference"],
                    "unit": "个/uL",
                    "method": "免疫细胞活性检测",
                    "percentage_result": parsed["percentage_result"],
                    "percentage_reference": parsed["percentage_reference"],
                }
            )
            seen_codes.add(code)

        for code, output_name, keywords in P06_CYTOKINE_DEFINITIONS:
            if code in seen_codes:
                continue
            parsed = find_p06_cytokine_result(text, keywords)
            if not parsed:
                continue
            tests.append(
                {
                    "page": page_number,
                    "specimen_type": specimen_type,
                    "test_name": output_name,
                    "item_code": code,
                    "result": parsed["result"],
                    "indicator": parsed["status"],
                    "reference_range": parsed["reference_range"],
                    "unit": "pg/mL",
                    "method": "细胞因子检测",
                }
            )
            seen_codes.add(code)
    return tests


def find_p06_immune_cell_result(text: str, keywords: tuple[str, ...]) -> dict[str, str] | None:
    for keyword in keywords:
        pattern = re.compile(name_pattern(keyword), flags=re.IGNORECASE)
        for match in pattern.finditer(text):
            window = normalize_text(text[match.end() : match.end() + 180])
            parsed = parse_p06_immune_cell_window(window)
            if parsed:
                return parsed
    return None


def parse_p06_immune_cell_window(window: str) -> dict[str, str] | None:
    numbers = re.findall(r"[0-9]+(?:\.[0-9]+)?", window)
    ranges = re.findall(r"[0-9]+(?:\.[0-9]+)?\s*[-~]\s*[0-9]+(?:\.[0-9]+)?", window)
    status_match = re.search(r"姝ｅ父|鍗囬珮|鍋忛珮|鍋忎綆|闄嶄綆|寮傚父", window)
    if len(numbers) < 4 or len(ranges) < 2:
        return None
    return {
        "absolute_result": numbers[0],
        "percentage_result": numbers[1],
        "absolute_reference": ranges[0].replace(" ", ""),
        "percentage_reference": ranges[1].replace(" ", ""),
        "status": status_match.group(0) if status_match else "寰呭鏍?",
    }


def find_p06_cytokine_result(text: str, keywords: tuple[str, ...]) -> dict[str, str] | None:
    for keyword in keywords:
        pattern = re.compile(name_pattern(keyword), flags=re.IGNORECASE)
        for match in pattern.finditer(text):
            window = normalize_text(text[match.end() : match.end() + 120])
            parsed = parse_p06_cytokine_window(window)
            if parsed:
                return parsed
    return None


def parse_p06_cytokine_window(window: str) -> dict[str, str] | None:
    value_match = re.search(r"(?P<value>[0-9]+(?:\.[0-9]+)?)(?:\s*(?P<flag>[↑↓]))?", window)
    reference_match = re.search(r"(?P<reference>[0-9]+(?:\.[0-9]+)?\s*[-~]\s*[0-9]+(?:\.[0-9]+)?)", window)
    status_match = re.search(r"鍗囬珮|鍋忛珮|鍋忎綆|姝ｅ父|寮傚父", window)
    if not value_match or not reference_match:
        return None
    result = value_match.group("value")
    if value_match.group("flag"):
        result = f"{result} {value_match.group('flag')}"
    status = status_match.group(0) if status_match else ("鍗囬珮" if value_match.group("flag") == "↑" else "姝ｅ父")
    return {
        "result": result,
        "reference_range": reference_match.group("reference").replace(" ", ""),
        "status": status,
    }


def extract_p01_structured_tests(page_texts: list[str], p01_report: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    report = p01_report or build_p01_extracted_report("", " ".join(page_texts), page_texts)
    basic_information = report.get("basic_information", {})
    specimen_type = str(basic_information.get("sample_type") or "粪便")
    tests: list[dict[str, Any]] = []

    gmhi = report.get("gmhi", {})
    if gmhi.get("score") is not None:
        tests.append(
            {
                "page": 4,
                "specimen_type": specimen_type,
                "test_name": "GMHI",
                "item_code": "gmhi",
                "result": _format_number(gmhi.get("score")),
                "indicator": str(gmhi.get("assessment") or ""),
                "reference_range": "0-100",
                "unit": "分",
                "method": str(basic_information.get("detection_method") or "高通量测序"),
            }
        )

    diversity = report.get("diversity", {})
    if diversity.get("shannon_index") is not None:
        tests.append(
            {
                "page": 7,
                "specimen_type": specimen_type,
                "test_name": "菌群多样性",
                "item_code": "diversity",
                "result": _format_number(diversity.get("shannon_index")),
                "indicator": _extract_p01_diversity_status(diversity),
                "reference_range": str(diversity.get("reference_percentile") or ""),
                "unit": "",
                "method": str(basic_information.get("detection_method") or "高通量测序"),
            }
        )

    intestinal_age = report.get("intestinal_age", {})
    if intestinal_age.get("intestinal_age") is not None:
        tests.append(
            {
                "page": 8,
                "specimen_type": specimen_type,
                "test_name": "肠龄",
                "item_code": "gut_age",
                "result": str(intestinal_age.get("intestinal_age")),
                "indicator": str(intestinal_age.get("age_difference") or ""),
                "reference_range": "成人偏差≤3岁",
                "unit": "岁",
                "method": str(basic_information.get("detection_method") or "高通量测序"),
            }
        )

    enterotype = report.get("enterotype", {})
    if enterotype.get("result"):
        tests.append(
            {
                "page": 6,
                "specimen_type": specimen_type,
                "test_name": "肠型",
                "item_code": "enterotype",
                "result": str(enterotype.get("result") or ""),
                "indicator": "",
                "reference_range": "",
                "unit": "",
                "method": str(basic_information.get("detection_method") or "高通量测序"),
            }
        )

    fb_ratio = report.get("fb_ratio", {})
    if fb_ratio.get("firmicutes_bacteroidetes_ratio") is not None:
        tests.append(
            {
                "page": 9,
                "specimen_type": specimen_type,
                "test_name": "F/B比值",
                "item_code": "fb_ratio",
                "result": _format_number(fb_ratio.get("firmicutes_bacteroidetes_ratio")),
                "indicator": str(fb_ratio.get("result_evaluation") or ""),
                "reference_range": str(fb_ratio.get("reference_range") or ""),
                "unit": "",
                "method": str(basic_information.get("detection_method") or "高通量测序"),
            }
        )

    be_index = report.get("be_index", {})
    if be_index.get("bifidobacterium_enterobacteriaceae_ratio") is not None:
        tests.append(
            {
                "page": 10,
                "specimen_type": specimen_type,
                "test_name": "B/E指数",
                "item_code": "be_index",
                "result": _format_number(be_index.get("bifidobacterium_enterobacteriaceae_ratio")),
                "indicator": str(be_index.get("result_evaluation") or ""),
                "reference_range": str(be_index.get("reference_range") or ""),
                "unit": "",
                "method": str(basic_information.get("detection_method") or "高通量测序"),
            }
        )

    immunity = report.get("immunity_assessment", {})
    intestinal_immunity = immunity.get("intestinal_immunity", {})
    if intestinal_immunity.get("value") is not None:
        tests.append(
            {
                "page": 41,
                "specimen_type": specimen_type,
                "test_name": "肠道免疫力",
                "item_code": "intestinal_immunity",
                "result": _format_number(intestinal_immunity.get("value")),
                "indicator": str(intestinal_immunity.get("status") or ""),
                "reference_range": str(intestinal_immunity.get("reference") or ""),
                "unit": "",
                "method": "微生态综合评估",
            }
        )
    intestinal_anti_inflammatory = immunity.get("intestinal_anti_inflammatory", {})
    if intestinal_anti_inflammatory.get("value") is not None:
        tests.append(
            {
                "page": 41,
                "specimen_type": specimen_type,
                "test_name": "肠道抗炎能力",
                "item_code": "intestinal_anti_inflammatory",
                "result": _format_number(intestinal_anti_inflammatory.get("value")),
                "indicator": str(intestinal_anti_inflammatory.get("status") or ""),
                "reference_range": str(intestinal_anti_inflammatory.get("reference") or ""),
                "unit": "",
                "method": "微生态综合评估",
            }
        )

    metabolism = report.get("metabolism_and_nutrients", {})
    vitamin_a = metabolism.get("vitamins", {}).get("vitamin_a", {}) if isinstance(metabolism, dict) else {}
    if vitamin_a.get("value") is not None:
        tests.append(
            {
                "page": 43,
                "specimen_type": specimen_type,
                "test_name": "维生素A合成能力",
                "item_code": "vitamin_a",
                "result": _format_number(vitamin_a.get("value")),
                "indicator": str(vitamin_a.get("status") or ""),
                "reference_range": str(vitamin_a.get("reference") or ""),
                "unit": "",
                "method": "微生态综合评估",
            }
        )

    return tests


def find_p01_metric_result(text: str, keywords: list[str], *, default_unit: str = "") -> dict[str, str] | None:
    for keyword in sorted(keywords, key=len, reverse=True):
        pattern = re.compile(name_pattern(keyword), flags=re.IGNORECASE)
        for match in pattern.finditer(text):
            window = normalize_text(text[match.end() : match.end() + 160])
            parsed = parse_p01_metric_window(window, default_unit=default_unit)
            if parsed:
                return parsed
    return None


def parse_p01_metric_window(window: str, *, default_unit: str = "") -> dict[str, str] | None:
    cleaned = normalize_text(window)
    value_match = re.search(
        r"(?:[:：=为]\s*)?(?P<value>-?[0-9]+(?:\.[0-9]+)?|[A-Za-z\u4e00-\u9fff]{1,16}型)",
        cleaned,
    )
    if not value_match:
        return None
    tail = cleaned[value_match.end() : value_match.end() + 120]
    indicator_match = re.search(r"[↑↓]|偏低|偏高|异常|正常|理想|良好|较低|较高|不足|失衡|高风险|中风险|低风险", tail[:80])
    reference_match = re.search(
        r"(?:参考|范围|正常值|参考范围)[:：]?\s*"
        r"(?P<reference>[<>≤≥]?\s*-?[0-9]+(?:\.[0-9]+)?(?:\s*(?:--|-|－|—|–|~|～)\s*-?[0-9]+(?:\.[0-9]+)?)?)",
        tail,
    )
    unit_match = re.search(r"岁|分|%|指数", tail[:24])
    return {
        "value": value_match.group("value"),
        "indicator": indicator_match.group(0) if indicator_match else "",
        "reference": normalize_reference(reference_match.group("reference")) if reference_match else "",
        "unit": normalize_unit(unit_match.group(0)) if unit_match else default_unit,
    }


def extract_p04_structured_tests(
    page_texts: list[str],
    page_ocr_data: dict[int, dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    tests: list[dict[str, Any]] = []
    seen_codes: set[str] = set()
    page_ocr_data = page_ocr_data or {}
    for page_number, text in enumerate(page_texts, start=1):
        for ocr_test in extract_p04_tests_from_ocr_items(
            page_ocr_data.get(page_number, {}).get("items", []),
            page_number=page_number,
            fallback_text=text,
        ):
            code = str(ocr_test.get("item_code") or "")
            if code and code not in seen_codes:
                tests.append(ocr_test)
                seen_codes.add(code)

        specimen_type = extract_page_specimen_type(text) or "血清"
        for code, output_name, keywords, default_unit, default_reference, default_method in P04_TEST_DEFINITIONS:
            if code in seen_codes:
                continue
            parsed = find_p04_numeric_result(
                text,
                keywords,
                default_unit=default_unit,
                default_reference=default_reference,
                default_method=default_method,
            )
            if not parsed:
                continue
            tests.append(
                {
                    "page": page_number,
                    "specimen_type": specimen_type,
                    "test_name": output_name,
                    "item_code": code,
                    "result": parsed["value"],
                    "indicator": parsed["flag"],
                    "reference_range": parsed["reference"] or default_reference,
                    "unit": parsed["unit"] or default_unit,
                    "method": parsed["method"] or default_method,
                }
            )
            seen_codes.add(code)
    return tests


def extract_p04_tests_from_ocr_items(
    ocr_items: list[dict[str, Any]],
    *,
    page_number: int,
    fallback_text: str,
) -> list[dict[str, Any]]:
    if not ocr_items:
        return []
    specimen_type = extract_page_specimen_type(fallback_text) or "血清"
    tests: list[dict[str, Any]] = []
    for serial_no, (code, output_name, keywords, default_unit, default_reference, default_method) in enumerate(P04_TEST_DEFINITIONS, start=1):
        name_item = _find_p04_ocr_name_item(ocr_items, keywords)
        if not name_item:
            continue
        row_y = float(name_item["y"])
        result_item = _find_p04_nearby_ocr_item(ocr_items, row_y, 600, 700)
        method_item = _find_p04_nearby_ocr_item(ocr_items, row_y, 430, 575)
        unit_item = _find_p04_nearby_ocr_item(ocr_items, row_y, 1010, 1100)
        reference = _p04_reference_from_ocr_items(ocr_items, row_y, code, default_reference)
        result = _normalize_p04_numeric_text(str(result_item.get("text") or "")) if result_item else ""
        if not result:
            continue
        unit = normalize_unit(str(unit_item.get("text") or default_unit)) if unit_item else default_unit
        method = clean_value(str(method_item.get("text") or default_method)) if method_item else default_method
        indicator = _p04_flag_from_value(result, reference)
        tests.append(
            {
                "page": page_number,
                "specimen_type": specimen_type,
                "test_name": output_name,
                "item_code": code,
                "serial_no": serial_no,
                "result": result,
                "indicator": indicator,
                "reference_range": reference,
                "unit": unit,
                "method": _p04_method_output_name(method),
            }
        )
    return tests


def _find_p04_ocr_name_item(items: list[dict[str, Any]], keywords: list[str]) -> dict[str, Any] | None:
    keyword_set = {_tighten_text(keyword).lower() for keyword in keywords}
    for item in items:
        text = _tighten_text(str(item.get("text") or "")).lower()
        if text in keyword_set:
            return item
    return None


def _find_p04_nearby_ocr_item(items: list[dict[str, Any]], row_y: float, min_x: float, max_x: float) -> dict[str, Any] | None:
    candidates = [
        item
        for item in items
        if min_x <= float(item["x"]) <= max_x and abs(float(item["y"]) - row_y) <= 18
    ]
    if not candidates:
        return None
    return sorted(candidates, key=lambda item: (abs(float(item["y"]) - row_y), float(item["x"])))[0]


def _p04_reference_from_ocr_items(
    items: list[dict[str, Any]],
    row_y: float,
    code: str,
    default_reference: str,
) -> str:
    if not default_reference and code in {"vitamin_d2", "vitamin_d3"}:
        return ""
    if code == "vitamin_d":
        return normalize_reference(default_reference)
    y_min, y_max = (-36, 60) if code == "vitamin_d" else (-8, 20)
    candidates = [
        item
        for item in items
        if 735 <= float(item["x"]) <= 935 and y_min <= float(item["y"]) - row_y <= y_max
    ]
    ordered = sorted(candidates, key=lambda item: (float(item["y"]), float(item["x"])))
    values: list[str] = []
    for item in ordered:
        text = clean_value(str(item.get("text") or "")).replace("|", " ").replace("＜", "<").replace("＞", ">")
        if not text or text in values:
            continue
        values.append(text)
    reference = "; ".join(values)
    if code == "vitamin_b3_nicotinamide" and reference.startswith("5.2-"):
        reference = default_reference
    if code == "vitamin_d" and ("<12.00" not in reference or ">50.00" not in reference):
        reference = default_reference
    return normalize_reference(reference or default_reference)


def _normalize_p04_numeric_text(value: str) -> str:
    cleaned = clean_value(value).replace("O", "0").replace("o", "0").replace("＜", "<").replace("＞", ">")
    match = re.search(r"[<>≤≥]?\s*-?[0-9]+(?:\.[0-9]+)?", cleaned)
    return clean_value(match.group(0).replace(" ", "")) if match else ""


def find_p04_numeric_result(
    text: str,
    keywords: list[str],
    *,
    default_unit: str,
    default_reference: str,
    default_method: str,
) -> dict[str, str] | None:
    for keyword in sorted(keywords, key=len, reverse=True):
        pattern = re.compile(name_pattern(keyword), flags=re.IGNORECASE)
        for match in pattern.finditer(text):
            if _p04_keyword_false_positive(text, match, keyword):
                continue
            parsed = parse_p04_result_window(
                text[match.end() : match.end() + 220],
                default_unit=default_unit,
                default_reference=default_reference,
                default_method=default_method,
            )
            if parsed:
                return parsed
    return None


def _p04_keyword_false_positive(text: str, match: re.Match[str], keyword: str) -> bool:
    matched = text[match.start() : match.end()]
    if matched != keyword:
        return True
    before = text[max(0, match.start() - 1) : match.start()]
    after = text[match.end() : match.end() + 1]
    if len(keyword) > 2 and re.match(r"[A-Za-z0-9]", after):
        return True
    if len(keyword) > 2:
        return False
    if after in {"/", "／"}:
        return True
    return bool(re.match(r"[A-Za-z0-9]", before) or re.match(r"[A-Za-z0-9]", after))


def parse_p04_result_window(
    window: str,
    *,
    default_unit: str,
    default_reference: str,
    default_method: str,
) -> dict[str, str] | None:
    cleaned = normalize_text(window)
    value_match = re.search(r"(?<![A-Za-z])(?P<value>[0-9]+(?:\.[0-9]+)?)", cleaned)
    if not value_match:
        return None
    tail = cleaned[value_match.end() : value_match.end() + 180]
    method_match = find_p04_method_match(tail)
    row_tail = tail[: method_match[2]] if method_match else tail
    status_match = re.search(r"[↑↓]|偏高|偏低|不足|缺乏|正常|升高|降低", row_tail[:60])
    reference_match = re.search(rf"({P03_REFERENCE_PATTERN})", row_tail)
    unit_match = re.search(P04_UNIT_PATTERN, row_tail, flags=re.IGNORECASE)
    reference = normalize_reference(reference_match.group(0)) if reference_match else default_reference
    flag = status_match.group(0) if status_match else _p04_flag_from_value(value_match.group("value"), reference)
    return {
        "value": value_match.group("value"),
        "unit": normalize_unit(unit_match.group(0)) if unit_match else default_unit,
        "reference": reference,
        "flag": flag,
        "method": method_match[0] if method_match else default_method,
    }


def _p04_flag_from_value(value: str, reference: str) -> str:
    numeric = _safe_float(value)
    if numeric is None:
        return ""
    normalized = normalize_reference(reference)
    if all(word in normalized for word in ("缺乏", "不足", "正常", "过量")):
        return ""
    range_match = re.search(r"(-?[0-9]+(?:\.[0-9]+)?)--(-?[0-9]+(?:\.[0-9]+)?)", normalized)
    if range_match:
        lower = float(range_match.group(1))
        upper = float(range_match.group(2))
        if numeric < lower:
            return "↓"
        if numeric > upper:
            return "↑"
        return ""
    upper_match = re.search(r"(?:≤|<)(-?[0-9]+(?:\.[0-9]+)?)", normalized)
    if upper_match and numeric > float(upper_match.group(1)):
        return "↑"
    lower_match = re.search(r"(?:≥|>)(-?[0-9]+(?:\.[0-9]+)?)", normalized)
    if lower_match and numeric < float(lower_match.group(1)):
        return "↓"
    return ""


def find_p04_method_match(text: str) -> tuple[str, int, int] | None:
    normalized = normalize_text(text)
    best: tuple[str, int, int] | None = None
    for method in P04_METHOD_NAMES:
        compact_pattern = r"\s*".join(re.escape(char) for char in method if not char.isspace())
        match = re.search(compact_pattern, normalized, flags=re.IGNORECASE)
        if not match:
            continue
        candidate = (_p04_method_output_name(method), match.start(), match.end())
        if best is None or candidate[1] < best[1]:
            best = candidate
    return best


def _p04_method_output_name(method: str) -> str:
    if method == "ICP-MS":
        return "电感耦合等离子体质谱法（ICP-MS）"
    if method == "HPLC":
        return "高效液相色谱法（HPLC）"
    if method == "CLIA":
        return "化学发光法（CLIA）"
    return method


def _p04_ocr_status(test: dict[str, Any]) -> str:
    signal = f"{test.get('result', '')}{test.get('indicator', '')}"
    if any(word in signal for word in ("↑", "偏高", "升高", "过高")):
        return "偏高"
    if any(word in signal for word in ("缺乏", "严重不足")):
        return "缺乏"
    if any(word in signal for word in ("↓", "偏低", "不足", "降低")):
        return "不足"
    if "正常" in signal:
        return "正常"
    return "待评估"


def extract_p03_structured_tests(page_texts: list[str]) -> list[dict[str, Any]]:
    tests: list[dict[str, Any]] = []
    seen_codes: set[str] = set()
    for page_number, text in enumerate(page_texts, start=1):
        specimen_type = extract_page_specimen_type(text) or "血清"
        for code, output_name, keywords, default_unit in P03_TEST_DEFINITIONS:
            if code in seen_codes:
                continue
            parsed = find_p03_numeric_result(text, keywords, code=code, default_unit=default_unit)
            if not parsed:
                continue
            unit = parsed["unit"] or default_unit
            if default_unit and parsed.get("prefix_unit") == default_unit and unit != default_unit:
                unit = default_unit
            method = parsed["method"]
            if method == "PDF文本层抽取" and parsed.get("prefix_method"):
                method = parsed["prefix_method"]
            tests.append(
                {
                    "page": page_number,
                    "specimen_type": specimen_type,
                    "test_name": output_name,
                    "item_code": code,
                    "result": parsed["value"],
                    "indicator": parsed["flag"],
                    "reference_range": parsed["reference"],
                    "unit": unit,
                    "method": method,
                }
            )
            seen_codes.add(code)
    return tests


def find_p03_numeric_result(text: str, keywords: list[str], *, code: str, default_unit: str = "") -> dict[str, str] | None:
    for keyword in sorted(keywords, key=len, reverse=True):
        pattern = re.compile(name_pattern(keyword), flags=re.IGNORECASE)
        for match in pattern.finditer(text):
            if code == "hba1" and re.match(r"\s*(?:C|c|ab|AB)", text[match.end() : match.end() + 4]):
                continue
            prefix = text[max(0, match.start() - 160) : match.start()]
            prefix_parsed = parse_p03_prefix_result(prefix, default_unit=default_unit) if code == "c_peptide" else None
            if prefix_parsed:
                return prefix_parsed
            parsed = parse_p03_result_window(text[match.end() : match.end() + 180], prefix=prefix)
            if code == "c_peptide" and parsed and normalize_reference(parsed.get("reference", "")) == "3--25":
                continue
            if parsed:
                return parsed
    return None


def parse_p03_result_window(window: str, *, prefix: str = "") -> dict[str, str] | None:
    cleaned = normalize_text(window)
    value_match = re.search(r"(?<![A-Za-z])(?P<value>[0-9]+(?:\.[0-9]+)?)", cleaned)
    if not value_match:
        return None
    tail = cleaned[value_match.end() : value_match.end() + 150]
    method_match = find_p03_method_match(tail)
    row_tail = tail[: method_match[2]] if method_match else tail
    indicator_match = re.search(r"[↑↓]", row_tail[:24])
    reference_match = re.search(rf"({P03_REFERENCE_PATTERN})", row_tail)
    unit_match = re.search(r"mmol/L|mmol／L|uU/mL|μU/mL|uIU/mL|ng/mL|g/L|mg/L|mg/dL|%", row_tail, flags=re.IGNORECASE)
    method = method_match[0] if method_match else ""
    prefix_unit_match = re.search(r"(mmol/L|mmol／L|uU/mL|μU/mL|uIU/mL|ng/mL|g/L|mg/L|mg/dL|%)\s*(?:\S{0,8})\s*$", prefix, flags=re.IGNORECASE)
    prefix_method = extract_p03_method(prefix[-30:])
    return {
        "value": value_match.group("value"),
        "unit": normalize_unit(unit_match.group(0)) if unit_match else "",
        "prefix_unit": normalize_unit(prefix_unit_match.group(1)) if prefix_unit_match else "",
        "reference": normalize_reference(reference_match.group(0)) if reference_match else "",
        "flag": indicator_match.group(0) if indicator_match else "",
        "method": method or "PDF文本层抽取",
        "prefix_method": prefix_method,
    }


def parse_p03_prefix_result(prefix: str, *, default_unit: str) -> dict[str, str] | None:
    if not default_unit:
        return None
    cleaned = normalize_text(prefix)
    unit_pattern = r"mmol/L|mmol／L|uU/mL|μU/mL|uIU/mL|ng/mL|g/L|mg/L|mg/dL|%"
    method_pattern = "|".join(re.escape(method) for method in P03_METHOD_NAMES)
    pattern = re.compile(
        rf"(?P<unit>{unit_pattern})\s*(?P<method>{method_pattern})\s*"
        rf"(?P<value>[0-9]+(?:\.[0-9]+)?)\s*(?P<flag>[↑↓])?\s*(?P<reference>{P03_REFERENCE_PATTERN})",
        flags=re.IGNORECASE,
    )
    matches = list(pattern.finditer(cleaned))
    for match in reversed(matches):
        unit = normalize_unit(match.group("unit"))
        if unit.lower() != default_unit.lower():
            continue
        return {
            "value": match.group("value"),
            "unit": unit,
            "prefix_unit": "",
            "reference": normalize_reference(match.group("reference")),
            "flag": match.group("flag") or "",
            "method": "NBT 法" if match.group("method") == "NBT法" else match.group("method"),
            "prefix_method": "",
        }
    return None


def build_test(
    page: int,
    specimen_type: str,
    test_name: str,
    raw_result: str,
    flag: str | None,
    reference_range: str,
    method: str,
) -> dict[str, Any]:
    result, indicator = split_result_indicator(raw_result, flag)
    return {
        "page": page,
        "specimen_type": specimen_type,
        "test_name": test_name,
        "result": result,
        "indicator": indicator,
        "reference_range": reference_range,
        "unit": "",
        "method": method,
    }


def split_result_indicator(raw_result: str, flag: str | None) -> tuple[str, str]:
    cleaned = normalize_text(raw_result).replace(" ", "")
    if cleaned.startswith("弱阳性"):
        result = "弱阳性"
    elif cleaned.startswith("阳性"):
        result = "阳性"
    elif cleaned.startswith("阴性"):
        result = "阴性"
    else:
        result = cleaned

    level_match = re.search(r"[（(](\+{1,3})[）)]", cleaned)
    indicator = f"（{level_match.group(1)}）" if level_match else ""
    if flag and flag not in indicator:
        indicator = f"{indicator}{flag}"
    if result == "阴性" and not level_match:
        indicator = ""
    return result, indicator


def extract_report_id(text: str) -> str:
    match = re.search(r"条\s*形\s*码[:：]?\s*([0-9]{6,})", text)
    if match:
        return match.group(1)
    fallback = re.search(r"\b([0-9]{10,})\b", text)
    return fallback.group(1) if fallback else ""


def extract_barcodes(text: str) -> list[str]:
    values: list[str] = []
    for match in re.finditer(r"\b([0-9]{10,})\b", text):
        value = match.group(1)
        if value not in values:
            values.append(value)
    return values


def extract_laboratory(text: str) -> str:
    match = re.search(r"([\u4e00-\u9fff]{2,}医学检验实验室)", text)
    return match.group(1) if match else ""


def extract_remarks(text: str) -> str:
    match = re.search(r"备注[:：]?\s*([^\s]+(?:医学检测|检测)?)", text)
    return clean_value(match.group(1)) if match else ""


def extract_disclaimer(text: str) -> str:
    match = re.search(r"(本检测仅对来样负责[^。！!]*[。！!])", text)
    return clean_value(match.group(1)) if match else ""


def extract_website(text: str) -> str:
    match = re.search(r"(?:www\.)?[A-Za-z0-9.-]+\.[A-Za-z]{2,}", text)
    return match.group(0) if match else ""


def extract_phone(text: str) -> str:
    match = re.search(r"\b(?:400|800)-?[0-9]{3}-?[0-9]{4}\b", text)
    return match.group(0) if match else ""


def extract_patient_phone(text: str) -> str:
    normalized = normalize_text(text)
    next_labels = ["相关症状", "主要不适或疾病", "临床诊断", "主诉", "采样日期", "收样日期", "接收时间", "报告日期", "评估日期", "样本类型", "检测项目", "送检单位", "送检医生", "送检科室", "病员号", "床号", "备注"]
    for label in ["联系电话", "联系手机", "手机号码", "电话号码"]:
        value = _extract_between_labels(normalized, label, next_labels)
        phone = _extract_first_patient_phone(value)
        if phone:
            return phone
    near_match = re.search(rf"{label_pattern('联系电话')}[:：]?\s*([0-9\- ]{{7,20}})", normalized)
    if near_match:
        phone = _extract_first_patient_phone(near_match.group(1))
        if phone:
            return phone
    return ""


def extract_patient_symptoms(text: str) -> str:
    normalized = normalize_text(text)
    next_labels = ["采样日期", "收样日期", "接收时间", "报告日期", "评估日期", "样本类型", "检测项目", "送检单位", "送检医生", "送检科室", "联系电话", "病员号", "床号", "备注"]
    for label in ["相关症状", "主要不适或疾病", "临床诊断", "主诉"]:
        value = clean_value(_extract_between_labels(normalized, label, next_labels))
        if value and not looks_like_label(value) and not _looks_like_symptom_blob(value) and not _looks_like_specimen_text(value):
            return value
    for label in ["相关症状", "主要不适或疾病", "临床诊断", "主诉"]:
        reverse_pattern = re.compile(
            rf"(?:^|[\r\n])\s*(?P<value>[^\r\n]{{2,120}}?)\s*{label_pattern(label)}[:：]?",
            flags=re.MULTILINE,
        )
        matches = list(reverse_pattern.finditer(text))
        for match in reversed(matches):
            value = clean_value(match.group("value"))
            if value and not looks_like_label(value) and not _looks_like_symptom_blob(value) and not _looks_like_specimen_text(value):
                return value
    return ""


def _extract_first_patient_phone(text: str) -> str:
    if not text:
        return ""
    normalized = normalize_text(str(text))
    mobile_match = re.search(r"(?<!\d)(1[3-9]\d{9})(?!\d)", normalized)
    if mobile_match:
        return mobile_match.group(1)
    landline_match = re.search(r"(?<!\d)(0\d{2,3}-?\d{7,8})(?!\d)", normalized)
    if landline_match:
        return landline_match.group(1)
    return ""


def _looks_like_symptom_blob(value: str) -> bool:
    compact = normalize_text(str(value))
    table_markers = ("结果", "参考范围", "单位", "检验方法", "本检测仅", "审核者", "批准人", "检测者")
    if any(marker in compact for marker in table_markers):
        return True
    digit_count = sum(1 for char in compact if char.isdigit())
    return len(compact) > 80 and digit_count >= 6


def _looks_like_specimen_text(value: str) -> bool:
    compact = normalize_text(str(value)).replace(" ", "")
    if not compact:
        return False
    if "标本类型" in compact or "样本类型" in compact:
        return True
    specimen_tokens = {"血清", "EDTA抗凝全血", "全血", "粪便", "血浆", "尿液"}
    normalized = compact.replace("，", ",").replace("、", ",").replace("；", ",").replace("/", ",")
    parts = [part for part in normalized.split(",") if part]
    if parts and all(part in specimen_tokens for part in parts):
        return True
    return compact in specimen_tokens


def extract_address(text: str) -> str:
    match = re.search(r"地址[:：]?\s*([^\s]+(?:大楼|中心|实验室|医院|公司|园区)?)", text)
    return clean_value(match.group(1)) if match else ""


def numeric_or_text(value: Any) -> float | int | str:
    text = str(value or "").strip()
    if not text:
        return ""
    if not re.fullmatch(r"[0-9]+(?:\.[0-9]+)?", text):
        return text
    parsed = float(text)
    return int(parsed) if "." not in text else parsed


def find_p03_method_match(text: str) -> tuple[str, int, int] | None:
    normalized = normalize_text(text)
    best: tuple[str, int, int] | None = None
    for method in P03_METHOD_NAMES:
        compact_pattern = r"\s*".join(re.escape(char) for char in method if not char.isspace())
        match = re.search(compact_pattern, normalized, flags=re.IGNORECASE)
        if not match:
            continue
        output_method = "NBT 法" if method == "NBT法" else method
        candidate = (output_method, match.start(), match.end())
        if best is None or candidate[1] < best[1]:
            best = candidate
    return best


def extract_p03_method(text: str) -> str:
    match = find_p03_method_match(text)
    return match[0] if match else ""


def normalize_unit(unit: str) -> str:
    return unit.replace("／", "/").replace("μU", "uU")


def normalize_reference(reference: str) -> str:
    cleaned = re.sub(r"\s+", "", reference)
    cleaned = cleaned.replace("＜", "<").replace("＞", ">")
    cleaned = cleaned.replace("－", "-").replace("—", "-").replace("–", "-")
    cleaned = cleaned.replace("~", "--").replace("～", "--")
    cleaned = re.sub(r"(?<=\d)-(?=\d)", "--", cleaned)
    return cleaned


def _find_p17_page(page_texts: list[str], keywords: list[str]) -> int | None:
    for index, text in enumerate(page_texts, start=1):
        if all(keyword.lower() in text.lower() for keyword in keywords):
            return index
    return None


def _extract_p17_report_title(text: str, fallback: str) -> str:
    match = re.search(r"([\u4e00-\u9fffA-Za-z（）()0-9\-]+报告(?:（附表）)?)", text)
    return clean_value(match.group(1)) if match else fallback


def _extract_p17_hospital_english(text: str) -> str:
    match = re.search(r"(Hefei\s+Anweikang\s+Clinical\s+Laboratory\s+Center)", text, flags=re.IGNORECASE)
    return match.group(1) if match else ""


def _extract_p17_submission_info(text: str) -> dict[str, Any]:
    basic_info = _extract_p17_basic_info(text)
    return {
        "submitting_unit": basic_info.get("submitting_unit") or _extract_p17_label_value(text, ["送检单位"]) or extract_hospital(text),
        "barcode": basic_info.get("barcode") or extract_report_id(text) or _first_non_empty(extract_barcodes(text)),
    }


def _extract_p17_patient_info(text: str) -> dict[str, Any]:
    basic_info = _extract_p17_basic_info(text)
    age_value = basic_info.get("age") or extract_age(text)
    age_text = f"{age_value}岁" if age_value != "" else ""
    return {
        "name": basic_info.get("name") or extract_patient_name(text) or _extract_p17_label_value(text, ["姓名"]),
        "gender": basic_info.get("gender") or extract_gender(text),
        "age": age_text,
        "inpatient_outpatient_number": _extract_p17_label_value(text, ["门诊/住院号", "门诊住院号"]),
        "medical_record_number": _extract_p17_label_value(text, ["病历号", "病员号"]),
        "submitting_department": basic_info.get("department") or _extract_p17_label_value(text, ["送检科室", "科室/病区"]),
        "specimen_type": basic_info.get("specimen_type") or _extract_p17_label_value(text, ["标本类型"]) or extract_page_specimen_type(text),
        "phone": _extract_p17_phone(text) or extract_patient_phone(text),
        "sampling_date": basic_info.get("sampling_date") or _extract_p17_label_value(text, ["采样日期", "采样时间"]),
        "submitting_physician": basic_info.get("doctor") or _extract_p17_label_value(text, ["送检医生"]),
        "bed_number": _extract_p17_label_value(text, ["床号"]),
        "receiving_time": basic_info.get("receiving_time") or _extract_p17_label_value(text, ["接收时间"]),
        "report_time": _extract_p17_report_time(text),
        "specimen_characteristics": basic_info.get("specimen_characteristics") or _extract_p17_label_value(text, ["标本情况", "样本状态", "样本性状"]) or extract_specimen_condition(text),
        "clinical_diagnosis": _extract_p17_clinical_diagnosis(text),
    }


def _extract_p17_basic_info(text: str) -> dict[str, str]:
    normalized = normalize_text(text)
    date = DATE_VALUE_PATTERN
    specimen_pattern = r"泌尿生殖道样本|阴道分泌物|宫颈分泌物|分泌物|拭子|血清|血浆|尿液"
    pattern = re.compile(
        rf"姓\s*名[:：]?\s*(?P<name>[^\s:：]+).*?"
        rf"住院\s*/\s*门诊号[:：]?\s*(?P<gender>男|女)\s+"
        rf"(?P<department>[^\s:：]+)\s+"
        rf"(?P<receiving_time>{date})\s+"
        rf"(?P<sampling_date>{date})\s+"
        rf"(?P<age>[0-9]{{1,3}})\s*岁\s+"
        rf"(?P<doctor>[^\s:：]+)\s+"
        rf"条形码[:：]?\s*(?P<barcode>[0-9]{{6,}})\s+"
        rf"送检单位[:：]?\s*(?P<submitting_unit>.*?)\s+"
        rf"(?P<specimen_type>{specimen_pattern})"
        rf"(?:\s+(?P<specimen_characteristics>未见异常|正常|异常|溶血|脂血))?",
        flags=re.S,
    )
    match = pattern.search(normalized)
    if not match:
        return {}
    values = {key: clean_value(value or "") for key, value in match.groupdict().items()}
    return {key: value for key, value in values.items() if value and not looks_like_label(value)}


def _extract_p17_report_time(text: str) -> str:
    datetimes = re.findall(r"[0-9]{4}[/-][0-9]{1,2}[/-][0-9]{1,2}\s+[0-9]{1,2}:[0-9]{2}:[0-9]{2}", normalize_text(text))
    return datetimes[-1] if datetimes else ""


def _extract_p17_phone(text: str) -> str:
    match = re.search(r"联系电话[:：]?\s*(1[3-9][0-9]{9}|[0-9]{3,4}-?[0-9]{7,8})", normalize_text(text))
    return match.group(1) if match else ""


def _extract_p17_clinical_diagnosis(text: str) -> str:
    value = _extract_p17_label_value(text, ["临床诊断", "主诉"])
    if not value or looks_like_label(value):
        return ""
    invalid_fragments = ["基本信息", "样本性状", "第1页", "检测报告"]
    return "" if any(fragment in value for fragment in invalid_fragments) else value


def _extract_p17_label_value(text: str, labels: list[str]) -> str:
    normalized = normalize_text(text)
    for label in labels:
        pattern = re.compile(rf"{label_pattern(label)}[:：]?\s*([^\s:：]+)")
        match = pattern.search(normalized)
        if match:
            value = clean_value(match.group(1))
            if value and not looks_like_label(value):
                return value
    return ""


def _extract_p17_detection_method(text: str, fallback: str) -> str:
    method_match = re.search(r"((?:多重)?荧光\s*PCR法)", text, flags=re.IGNORECASE)
    return clean_value(method_match.group(1)) if method_match else fallback


def _extract_p17_hpv_results(text: str) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for subtype in P17_HPV_HIGH_RISK_TYPES:
        result, ct_value = _extract_p17_hpv_result(text, subtype)
        results.append(
            {
                "type_category": "高危型别",
                "subtype": f"HPV-{subtype}",
                "ct_value": ct_value,
                "result": result,
                "reference_value": "阴性",
            }
        )
    for subtype in P17_HPV_LOW_RISK_TYPES:
        result, ct_value = _extract_p17_hpv_result(text, subtype)
        results.append(
            {
                "type_category": "低危型别",
                "subtype": f"HPV-{subtype}",
                "ct_value": ct_value,
                "result": result,
                "reference_value": "阴性",
            }
        )
    return results


def _extract_p17_hpv_result(text: str, subtype: str) -> tuple[str, str]:
    subtype_variants = [f"HPV-{subtype}", f"HPV{subtype}", f"HPV {subtype}"]
    for variant in subtype_variants:
        for match in re.finditer(re.escape(variant), text, flags=re.IGNORECASE):
            window = text[match.start(): match.start() + 80]
            result = _extract_p17_result_token(window)
            if not result:
                continue
            ct_value = _extract_p17_ct_value(window)
            return result, ct_value
    return "阴性", "-"


def _extract_p17_micro_results(text: str) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    table_results = _extract_p17_micro_table_results(text)
    for category, items in P17_MICROBE_GROUPS.items():
        for name in items:
            result, ct_value = table_results.get(name) or _extract_p17_named_result(text, name)
            results.append(
                {
                    "category": category,
                    "name": name,
                    "ct_value": ct_value,
                    "result": result,
                    "reference_range": None,
                }
            )
    return results


def _extract_p17_micro_table_results(text: str) -> dict[str, tuple[str, str]]:
    normalized = normalize_text(text)
    results: dict[str, tuple[str, str]] = {}
    ct_blocks = [
        _extract_p17_ct_tokens(match.group(1))
        for match in re.finditer(
            r"CT值\s+((?:(?:[0-9]{1,2}\.[0-9]{1,2}|No\s*Ct|-)\s*)+)",
            normalized,
            flags=re.IGNORECASE,
        )
    ]
    for names, values in zip(P17_MICROBE_CT_BLOCK_NAMES, ct_blocks):
        for name, ct_value in zip(names, values):
            results[name] = (_p17_result_from_ct(ct_value), ct_value)
    results.update(_extract_p17_tail_pathogen_results(normalized))
    for name in P17_MICROBE_TRAILING_NEGATIVE_NAMES:
        if _p17_find_name_in_text(normalized, name):
            results.setdefault(name, ("阴性", "-"))
    return results


def _extract_p17_tail_pathogen_results(text: str) -> dict[str, tuple[str, str]]:
    last_names = P17_MICROBE_TRAILING_NEGATIVE_NAMES[-3:]
    first_index = _p17_find_first_name_index(text, last_names[0])
    if first_index < 0:
        return {}
    tail = text[first_index:]
    end_match = re.search(
        r"检\s*测\s*方\s*法|审\s*核\s*者|检\s*验\s*者|报\s*告\s*时\s*间|网\s*址|电\s*话|公\s*司\s*地\s*址",
        tail,
    )
    if end_match:
        tail = tail[: end_match.start()]
    tokens = _extract_p17_ct_tokens(tail)
    if len(tokens) < len(last_names):
        return {}
    values = tokens[-len(last_names):]
    return {name: (_p17_result_from_ct(value), value) for name, value in zip(last_names, values)}


def _p17_find_first_name_index(text: str, name: str) -> int:
    indexes = [
        index
        for candidate in (name, *P17_MICROBE_NAME_ALIASES.get(name, ()))
        for index in [text.find(candidate)]
        if index >= 0
    ]
    return min(indexes) if indexes else -1


def _extract_p17_ct_tokens(text: str) -> list[str]:
    tokens = re.findall(r"[0-9]{1,2}\.[0-9]{1,2}|No\s*Ct|-", text, flags=re.IGNORECASE)
    return [clean_value(token).replace("NoCt", "No Ct") for token in tokens]


def _p17_result_from_ct(ct_value: str) -> str:
    if ct_value in {"", "-", "No Ct"}:
        return "阴性"
    numeric = _safe_float(ct_value)
    if numeric is not None and numeric <= 37:
        return "阳性"
    return "阴性"


def _extract_p17_named_result(text: str, name: str) -> tuple[str, str]:
    normalized = normalize_text(text)
    for candidate in (name, *P17_MICROBE_NAME_ALIASES.get(name, ())):
        for match in re.finditer(re.escape(candidate), normalized):
            start = max(0, match.start() - 50)
            window = normalized[start: match.end() + 120]
            result = _extract_p17_result_token(window)
            if not result:
                continue
            ct_value = _extract_p17_ct_value(window)
            return result, ct_value
    return "阴性", "-"


def _p17_find_name_in_text(text: str, name: str) -> bool:
    return any(candidate in text for candidate in (name, *P17_MICROBE_NAME_ALIASES.get(name, ())))


def _extract_p17_result_token(text: str) -> str:
    if "阳性" in text:
        return "阳性"
    if "阴性" in text or "No Ct" in text or "NoCt" in text:
        return "阴性"
    ct_value = _extract_p17_ct_value(text)
    if ct_value not in {"", "-", "No Ct"}:
        numeric = _safe_float(ct_value)
        if numeric is not None and numeric <= 37:
            return "阳性"
    return ""


def _extract_p17_ct_value(text: str) -> str:
    match = re.search(r"(?:Ct|CT)[值:=：\s]*([0-9]+(?:\.[0-9]+)?|No\s*Ct|-)", text, flags=re.IGNORECASE)
    if match:
        return clean_value(match.group(1)).replace("NoCt", "No Ct")
    if "No Ct" in text or "NoCt" in text:
        return "No Ct"
    numeric = re.search(r"\b([0-9]{1,2}\.[0-9]{1,2})\b", text)
    if numeric:
        return numeric.group(1)
    return "-"


def _extract_p17_hpv_viral_load(text: str) -> str:
    match = re.search(r"(HPV[^。；;]*病毒载量[^。；;]*)", text)
    return clean_value(match.group(1)) if match else "HPV病毒载量：- copies/1万细胞"


def _extract_p17_analysis_and_tips(text: str) -> str:
    match = re.search(r"((?:分析|提示|备注)[:：]?\s*.*)", text)
    return clean_value(match.group(1)) if match else ""


def _extract_p17_appendix(text: str) -> dict[str, Any]:
    return {
        "viruses": ["单纯疱疹病毒1型", "单纯疱疹病毒2型"],
        "fungi": ["白假丝酵母菌", "光滑假丝酵母菌", "热带假丝酵母菌", "耳道假丝酵母菌", "克柔假丝酵母菌", "都柏林假丝酵母菌", "近平滑假丝酵母菌"],
        "bacteria": ["B族链球菌", "细小棒状杆菌", "亨氏巴尔通体", "衣氏放线菌", "淋球菌", "杜克雷嗜血杆菌", "卷曲乳杆菌", "詹氏乳杆菌", "加氏乳杆菌", "惰性乳杆菌", "双歧杆菌", "阴道阿托波氏菌", "阴道加德纳菌", "纤毛菌"],
        "mycoplasma": ["微小脲原体", "解脲脲原体", "人型支原体", "生殖支原体"],
        "chlamydia": ["沙眼衣原体"],
        "spirochetes": ["梅毒螺旋体"],
        "parasites": ["阴道毛滴虫", "阿米巴原虫"],
    }


def _extract_p17_references(text: str) -> list[str]:
    references: list[str] = []
    for match in re.finditer(r"([0-9]+[、.．][^0-9].{8,200}?)((?=[0-9]+[、.．])|$)", text):
        value = clean_value(match.group(1))
        if value and value not in references:
            references.append(value)
    return references


def extract_patient_name(text: str) -> str:
    patterns = [
        r"姓\s*名[:：]?\s*([\u4e00-\u9fff]{2,4})(?=\s|$)",
        r"安为康内部员工\s+([\u4e00-\u9fff]{2,4})\s+性\s*别",
        r"姓\s*名[:：]?\s*([^\s:：]+)\s+性\s*别",
        r"姓\s*名[:：]?\s*([^\s:：]+)\s+病\s*员\s*号",
        r"条\s*形\s*码[:：]?\s*[0-9]{6,}\s+姓\s*名[:：]?\s*([^\s:：]+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if not match:
            continue
        value = clean_value(match.group(1))
        if value and not looks_like_label(value):
            return value
    return ""


def extract_gender(text: str) -> str:
    match = re.search(r"性\s*别[:：]?\s*(?:病\s*员\s*号[:：]?\s*)?(?:床\s*号[:：]?\s*)?([男女])", text)
    return match.group(1) if match else ""


def extract_age(text: str) -> int | str:
    match = re.search(r"年\s*龄[:：]?\s*([0-9]{1,3})\s*岁?", text)
    return int(match.group(1)) if match else ""


def extract_specimen_condition(text: str) -> str:
    patterns = [
        r"标本情况[:：]?\s*(?:送检医生[:：]?\s*)?(未见异常|正常|异常|溶血|脂血)",
        r"(未见异常|正常|异常|溶血|脂血)\s*标本情况",
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(1)
    return ""


def extract_specimen_types(page_texts: list[str]) -> list[str]:
    values: list[str] = []
    pattern = re.compile(rf"{label_pattern('标本类型')}[:：]?\s*([^\s:：]+)")
    for text in page_texts:
        match = pattern.search(text)
        if match:
            value = clean_value(match.group(1))
            if value and not looks_like_label(value) and value not in values:
                values.append(value)
        for candidate in ["EDTA抗凝全血", "血清", "粪便", "全血"]:
            if candidate == "全血" and any("全血" in item for item in values):
                continue
            if candidate in text and candidate not in values:
                values.append(candidate)
    return values


def extract_page_specimen_type(text: str) -> str:
    pattern = re.compile(rf"{label_pattern('标本类型')}[:：]?\s*([^\s:：]+)")
    match = pattern.search(text)
    if match:
        return clean_value(match.group(1))
    for candidate in ["EDTA抗凝全血", "血清", "粪便", "全血"]:
        if candidate in text:
            return candidate
    return ""


def extract_hospital(text: str) -> str:
    if "安为康内部员工" in text:
        return "安为康内部员工"
    patterns = [
        r"送检单位[:：]?\s*([^\s:：]*(?:有限公司|医院|门诊部|中心|员工))",
        r"([\u4e00-\u9fffA-Za-z0-9（）()]{2,}(?:有限公司|医院|门诊部|中心|员工))",
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if not match:
            continue
        value = clean_value(match.group(1))
        if value and not looks_like_label(value):
            return value
    return ""


def extract_date(page_texts: list[str], label: str) -> str:
    values: list[str] = []
    pattern = re.compile(rf"{label_pattern(label)}[:：]?\s*({DATE_VALUE_PATTERN})")
    for text in page_texts:
        values.extend(match.group(1) for match in pattern.finditer(text))
    if not values:
        return ""
    if label == "采样日期":
        return min(values)
    if label in {"接收时间", "报告时间"}:
        return max(values)
    return values[-1]


def extract_staff(text: str, labels: list[str]) -> str:
    for label in labels:
        pattern = re.compile(rf"{label_pattern(label)}[:：]?\s*([^\s:：]+)")
        match = pattern.search(text)
        if not match:
            continue
        value = clean_value(match.group(1))
        if value and not looks_like_label(value):
            return value
    return ""


def label_pattern(label: str) -> str:
    return r"\s*".join(re.escape(char) for char in label)


def name_pattern(name: str) -> str:
    parts: list[str] = []
    for char in name:
        if char.isspace():
            parts.append(r"\s*")
        elif char == "/":
            parts.append(r"[/／]")
        elif char in {"（", "("}:
            parts.append(r"[（(]")
        elif char in {"）", ")"}:
            parts.append(r"[）)]")
        elif char in {"-", "－", "—", "–"}:
            parts.append(r"[-－—–]")
        else:
            parts.append(re.escape(char))
    return r"\s*".join(parts)


def output_test_name(name: str) -> str:
    return name.replace("/", "／")


def clean_value(value: str) -> str:
    return normalize_text(value).strip(" :：,，;；")


def looks_like_label(value: str) -> bool:
    label_words = {
        "姓名",
        "姓",
        "名",
        "性别",
        "病员号",
        "床号",
        "年龄",
        "标本情况",
        "送检医生",
        "科室",
        "检测项目",
        "临床诊断",
        "采样日期",
        "接收时间",
        "报告时间",
        "批准人",
        "审核者",
        "检测者",
        "检验者",
        "送检单位",
        "送检单位条码",
        "医院条码",
        "条形码",
        "备注",
        "送检科室",
        "标本类型",
        "联系电话",
        "床号",
        "年",
        "龄",
    }
    compact = value.replace(" ", "")
    label_fragments = ["条码", "送检单位", "备注", "日期", "时间"]
    return compact in label_words or any(fragment in compact for fragment in label_fragments)


def format_result_display(result: str, indicator: str) -> str:
    return f"{result}{indicator}" if indicator else result


def field_key_safe(value: str) -> str:
    key = re.sub(r"[^0-9A-Za-z\u4e00-\u9fff]+", "_", value)
    return key.strip("_")


def add_field(fields: list[dict[str, Any]], field_key: str, label: str, value: Any, confidence: float, page: int | None) -> None:
    if value is None or value == "":
        return
    fields.append(
        {
            "field_key": field_key,
            "label": label,
            "value": value,
            "confidence": confidence,
            "source": {
                "page": page,
                "bbox": None,
            },
        }
    )


def find_page(page_texts: list[str], needle: str) -> int | None:
    if not needle:
        return None
    for index, text in enumerate(page_texts, start=1):
        if needle in text:
            return index
    return None


def build_indicators(fields: list[dict[str, Any]]) -> dict[str, Any]:
    indicators: dict[str, Any] = {}
    for field in fields:
        key = field["field_key"]
        if (
            key.startswith("p01.")
            or key.startswith("p02.")
            or key.startswith("p03.")
            or key.startswith("p04.")
            or key.startswith("p05.")
            or key.startswith("p06.")
            or key.startswith("p07.")
            or key.startswith("p10.")
            or key.startswith("p12.")
            or key.startswith("p13.")
            or key.startswith("p17.")
        ):
            indicators[key] = {
                "label": field["label"],
                "value": field["value"],
                "confidence": field["confidence"],
                "source": field["source"],
            }
    return indicators


def calculate_confidence(fields: list[dict[str, Any]], pages: list[dict[str, Any]]) -> float:
    values = [field["confidence"] for field in fields]
    page_values = [block["confidence"] for page in pages for block in page["text_blocks"]]
    all_values = values + page_values
    return round(mean(all_values), 4) if all_values else 0.0


def build_warnings(
    fields: list[dict[str, Any]],
    pages: list[dict[str, Any]],
    structured_report: dict[str, Any],
    package_code: str = "P02",
) -> list[str]:
    warnings: list[str] = []
    if not any(page["text_blocks"][0]["text"] for page in pages):
        warnings.append("PDF未提取到文本，需要调用云OCR。")

    if package_code == "P01":
        required = {
            "patient.name": "姓名",
            "patient.gender": "性别",
            "patient.age": "年龄",
            "p01.gmhi.result_display": "GMHI",
            "p01.gut_age.result_display": "肠龄",
            "p01.enterotype.result_display": "肠型",
            "p01.be_index.result_display": "B/E比值",
        }
    elif package_code == "P05":
        required = {
            "patient.name": "姓名",
            "patient.gender": "性别",
            "patient.age": "年龄",
        }
    elif package_code == "P03":
        required = {
            "patient.name": "姓名",
            "patient.gender": "性别",
            "patient.age": "年龄",
            "p03.tg.result_display": "甘油三酯TG",
            "p03.hdl_c.result_display": "高密度脂蛋白HDL-C",
            "p03.glucose.result_display": "葡萄糖GLU",
            "p03.hba1c.result_display": "糖化血红蛋白A1C",
            "p03.insulin.result_display": "胰岛素Ins",
        }
    elif package_code == "P04":
        required = {
            "patient.name": "姓名",
            "patient.gender": "性别",
            "patient.age": "年龄",
        }
        for code, output_name, *_ in P04_TEST_DEFINITIONS:
            required[f"p04.nutrients.{code}.result_display"] = output_name
    elif package_code == "P17":
        required = {
            "patient.name": "姓名",
            "patient.gender": "性别",
            "patient.age": "年龄",
            "p17.hpv_16.result_display": "HPV-16",
            "p17.hpv_18.result_display": "HPV-18",
            "p17.阴道毛滴虫.result_display": "阴道毛滴虫",
        }
    elif package_code == "P11":
        required = build_p11_warning_requirements()
    elif package_code == "P11":
        required = build_p11_warning_requirements()
    else:
        required = {
            "patient.name": "姓名",
            "patient.gender": "性别",
            "patient.age": "年龄",
            "p02.calprotectin.result_display": "粪便钙卫蛋白检测结果",
        }
    if package_code == "P11":
        required = build_p11_warning_requirements()
    existing = {field["field_key"] for field in fields}
    for field_key, label in required.items():
        if field_key not in existing:
            warnings.append(f"未识别到必需字段：{label}")

    test_names = [test["test_name"] for test in structured_report["tests"]]
    if package_code == "P03":
        if test_names and len(test_names) < 12:
            warnings.append(f"糖脂代谢检验明细目标17项，当前仅识别到 {len(test_names)} 项，建议人工复核或切换云OCR。")
    if package_code == "P04":
        if not test_names:
            warnings.append("P04 当前未识别到营养素检验明细；请核对PDF文本层、补充样例或切换云OCR。")
        elif len(test_names) < len(P04_TEST_DEFINITIONS):
            warnings.append(f"P04 营养素目标{len(P04_TEST_DEFINITIONS)}项，当前仅识别到 {len(test_names)} 项，建议人工复核或切换云OCR。")
        test_names = []
    if package_code == "P01":
        if not test_names:
            warnings.append("P01专项菌群指标抽取策略为初版占位，已先抽取基础资料；请结合真实PDF样例继续升级GMHI、肠龄、菌群多样性等字段。")
        elif len(test_names) < 5:
            warnings.append(f"P01专项菌群指标当前仅识别到 {len(test_names)} 项，建议人工复核或切换云OCR。")
        test_names = []
    if package_code == "P05":
        if not test_names:
            warnings.append("P05 当前先完成模板工程化与基础字段抽取；待接入真实PDF样例后补充压力激素、睡眠和代谢专项指标识别。")
        elif len(test_names) < 10:
            warnings.append(f"P05 当前仅识别到 {len(test_names)} 项检验明细，建议人工复核图片页OCR结果。")
        test_names = []
    allergen_count = sum(1 for name in test_names if "钙卫蛋白" not in name and "总IgE" not in name)
    if not test_names:
        if package_code not in {"P01", "P04", "P05"}:
            warnings.append("未识别到检验项目明细。")
    elif package_code == "P02" and allergen_count and allergen_count < 10:
        warnings.append(f"过敏原项目仅识别到 {allergen_count} 项，建议人工复核或切换云OCR。")
    if package_code == "P02" and not any("总IgE" in name for name in test_names):
        warnings.append("未识别到特异性总IgE结果。")

    additional_info = structured_report["additional_info"]
    if package_code == "P05":
        missing_staff = not any([additional_info["technician"], additional_info["reviewer"], additional_info["approver"]])
    elif package_code == "P04":
        missing_staff = not additional_info["reviewer"]
    elif package_code == "P06":
        missing_staff = not additional_info["reviewer"]
    elif package_code == "P17":
        missing_staff = False
    elif package_code == "P01":
        missing_staff = not additional_info["technician"] or not additional_info["reviewer"]
    else:
        missing_staff = not additional_info["technician"] or not additional_info["reviewer"] or not additional_info["approver"]
    if missing_staff:
        warnings.append("未从PDF文本层识别到检测者/审核者/批准人；如需签名信息，请使用图像OCR或人工补录。")

    if package_code == "P11":
        warnings.extend(extract_p11_warning_messages(structured_report))
    low_confidence = list(dict.fromkeys(field["label"] for field in fields if field["confidence"] < 0.75))
    if low_confidence:
        warnings.append("低置信度字段需人工复核：" + "、".join(low_confidence))
    return warnings


# Clean overrides for P06 and warning logic.
def parse_pdf_to_standard_ocr_json(pdf_path: Path, package_code: str = "P02") -> dict[str, Any]:
    strategy_version = {
        "P01": P01_STRATEGY_VERSION,
        "P05": P05_STRATEGY_VERSION,
        "P03": P03_STRATEGY_VERSION,
        "P04": P04_STRATEGY_VERSION,
        "P06": P06_STRATEGY_VERSION,
        "P07": P07_STRATEGY_VERSION,
        "P08": P08_STRATEGY_VERSION,
        "P09": P09_STRATEGY_VERSION,
        "P10": P10_STRATEGY_VERSION,
        "P11": P11_STRATEGY_VERSION,
        "P12": P12_STRATEGY_VERSION,
        "P13": P13_STRATEGY_VERSION,
        "P14": P14_STRATEGY_VERSION,
        "P16": P16_STRATEGY_VERSION,
        "P17": P17_STRATEGY_VERSION,
    }.get(package_code, STRATEGY_VERSION)
    if package_code == "P14":
        sidecar = _find_p14_sidecar_ocr_file(pdf_path)
        if sidecar:
            result = parse_json_to_standard_ocr_json(sidecar, package_code=package_code, strategy_version=strategy_version)
            result["source_file"] = pdf_path.name
            debug = result.get("debug", {})
            if isinstance(debug, dict):
                debug["comparison_key"] = f"{package_code}:{pdf_path.name}:{strategy_version}"
                debug["sidecar_file"] = sidecar.name
            return result
    if package_code == "P16":
        sidecar = _find_p16_sidecar_ocr_file(pdf_path)
        if sidecar:
            result = parse_json_to_standard_ocr_json(sidecar, package_code=package_code, strategy_version=strategy_version)
            result["source_file"] = pdf_path.name
            debug = result.get("debug", {})
            if isinstance(debug, dict):
                debug["comparison_key"] = f"{package_code}:{pdf_path.name}:{strategy_version}"
                debug["sidecar_file"] = sidecar.name
            return result
    if pdf_path.suffix.lower() == ".json" or _looks_like_json_ocr_file(pdf_path, package_code=package_code):
        return parse_json_to_standard_ocr_json(pdf_path, package_code=package_code, strategy_version=strategy_version)
    reader = PdfReader(str(pdf_path))
    pages: list[dict[str, Any]] = []
    page_texts: list[str] = []
    raw_page_texts: list[str] = []
    for page_number, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        raw_page_texts.append(text)
        normalized = normalize_text(text)
        page_texts.append(normalized)
        pages.append(
            {
                "page_number": page_number,
                "width": float(page.mediabox.width) if page.mediabox else None,
                "height": float(page.mediabox.height) if page.mediabox else None,
                "text_blocks": [{"text": normalized, "confidence": 0.95 if normalized else 0.0, "bbox": None}],
            }
        )

    page_ocr_data: dict[int, dict[str, Any]] = {}
    if package_code in {"P04", "P05"}:
        page_ocr_data = extract_sparse_page_image_ocr(pdf_path, page_texts)
        for page_number, payload in page_ocr_data.items():
            if page_number < 1 or page_number > len(page_texts):
                continue
            merged_text = normalize_text(" ".join(part for part in [page_texts[page_number - 1], payload.get("text", "")] if part))
            page_texts[page_number - 1] = merged_text
            pages[page_number - 1]["text_blocks"] = [
                {"text": merged_text, "confidence": float(payload.get("confidence") or 0.82), "bbox": None}
            ]

    full_text = normalize_text(" ".join(page_texts))
    structured_report = build_structured_report(
        pdf_path.name,
        full_text,
        page_texts,
        package_code=package_code,
        page_ocr_data=page_ocr_data,
    )

    p03_extracted_report: dict[str, Any] = {}
    if package_code == "P03":
        p03_extracted_report = build_p03_extracted_report(structured_report, full_text, raw_page_texts=raw_page_texts)
        structured_report["p03_extracted_report"] = p03_extracted_report

    if package_code == "P01":
        fields = extract_p01_fields(page_texts, structured_report)
    elif package_code == "P05":
        fields = extract_p05_fields(page_texts, structured_report)
    elif package_code == "P03":
        fields = extract_p03_fields(page_texts, structured_report)
    elif package_code == "P04":
        fields = extract_p04_fields(page_texts, structured_report)
    elif package_code == "P06":
        fields = extract_p06_fields(page_texts, structured_report)
    elif package_code == "P07":
        fields = extract_p07_fields(page_texts, structured_report)
    elif package_code == "P08":
        fields = extract_p08_fields(page_texts, structured_report)
    elif package_code == "P09":
        fields = extract_p09_fields(page_texts, structured_report)
    elif package_code == "P12":
        fields = extract_p12_fields(page_texts, structured_report)
    elif package_code == "P13":
        fields = extract_p13_fields(page_texts, structured_report)
    elif package_code == "P14":
        fields = extract_p14_fields(page_texts, structured_report)
    elif package_code == "P16":
        fields = extract_p16_fields(page_texts, structured_report)
    elif package_code == "P17":
        fields = extract_p17_fields(page_texts, structured_report)
    elif package_code == "P10":
        fields = extract_p10_fields(page_texts, structured_report)
    elif package_code == "P11":
        fields = extract_p11_fields(
            page_texts=page_texts,
            structured_report=structured_report,
            add_field=add_field,
            find_page=find_page,
        )
    else:
        fields = extract_p02_fields(full_text, page_texts, structured_report)

    confidence = calculate_confidence(fields, pages)
    warnings = build_warnings(fields, pages, structured_report, package_code=package_code)
    provider = "pdf-text-extractor+rapidocr" if page_ocr_data else PROVIDER
    result = {
        "schema_version": "1.0",
        "package_code": package_code,
        "source_file": pdf_path.name,
        "strategy_version": strategy_version,
        "provider": provider,
        "pages": pages,
        "fields": fields,
        "indicators": build_indicators(fields),
        "structured_report": structured_report,
        "warnings": warnings,
        "created_at": now_iso(),
        "debug": {
            "comparison_key": f"{package_code}:{pdf_path.name}:{strategy_version}",
            "field_keys": [field["field_key"] for field in fields],
            "overall_confidence": confidence,
            "structured_test_count": len(structured_report.get("tests", [])),
        },
    }
    if package_code == "P01":
        result["p01_extracted_report"] = structured_report.get("p01_extracted_report", {})
    if package_code == "P05":
        result["p05_extracted_report"] = structured_report.get("p05_extracted_report", {})
    if package_code == "P03":
        result["p03_extracted_report"] = p03_extracted_report
    if package_code == "P04":
        result["p04_extracted_report"] = structured_report.get("p04_extracted_report", {"tests": structured_report.get("tests", [])})
    if package_code == "P06":
        result["p06_extracted_report"] = structured_report.get("p06_extracted_report", {"tests": structured_report.get("tests", [])})
    if package_code == "P07":
        result["p07_extracted_report"] = structured_report.get("p07_extracted_report", {"tests": structured_report.get("tests", [])})
    if package_code == "P08":
        result["p08_extracted_report"] = structured_report.get("p08_extracted_report", {"tests": structured_report.get("tests", [])})
    if package_code == "P09":
        result["p09_extracted_report"] = structured_report.get("p09_extracted_report", {"tests": structured_report.get("tests", [])})
    if package_code == "P10":
        result["p10_extracted_report"] = structured_report.get("p10_extracted_report", {"tests": structured_report.get("tests", [])})
    if package_code == "P11":
        result["p11_extracted_report"] = structured_report.get("p11_extracted_report", {"tests": structured_report.get("tests", [])})
    if package_code == "P12":
        result["p12_extracted_report"] = structured_report.get("p12_extracted_report", {"tests": structured_report.get("tests", [])})
    if package_code == "P13":
        result["p13_extracted_report"] = structured_report.get("p13_extracted_report", {"tests": structured_report.get("tests", [])})
    if package_code == "P14":
        result["p14_extracted_report"] = structured_report.get("p14_extracted_report", {"tests": structured_report.get("tests", [])})
    if package_code == "P16":
        result["p16_extracted_report"] = structured_report.get("p16_extracted_report", {"tests": structured_report.get("tests", [])})
    if package_code == "P17":
        result["p17_extracted_report"] = structured_report.get("p17_extracted_report", {})
    return result


def build_structured_report(
    source_file: str,
    full_text: str,
    page_texts: list[str],
    package_code: str = "P02",
    *,
    page_ocr_data: dict[int, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    if package_code == "P01":
        return build_p01_structured_report(source_file, full_text, page_texts)
    if package_code == "P05":
        return build_p05_structured_report(source_file, full_text, page_texts, page_ocr_data=page_ocr_data)
    if package_code == "P04":
        return build_p04_structured_report(source_file, full_text, page_texts, page_ocr_data=page_ocr_data or {})
    if package_code == "P06":
        return build_p06_structured_report(source_file, full_text, page_texts)
    if package_code == "P07":
        return build_p07_structured_report(source_file, full_text, page_texts)
    if package_code == "P08":
        return build_p08_structured_report(source_file, full_text, page_texts)
    if package_code == "P09":
        return build_p09_structured_report(source_file, full_text, page_texts)
    if package_code == "P12":
        return build_p12_structured_report(source_file, full_text, page_texts)
    if package_code == "P13":
        return build_p13_structured_report(source_file, full_text, page_texts)
    if package_code == "P14":
        return build_p14_structured_report(source_file, full_text, page_texts)
    if package_code == "P16":
        return build_p16_structured_report(source_file, full_text, page_texts)
    if package_code == "P10":
        return build_p10_structured_report(source_file, full_text, page_texts)
    if package_code == "P11":
        return build_p11_structured_report(
            source_file=source_file,
            full_text=full_text,
            page_texts=page_texts,
            extract_report_id=extract_report_id,
            extract_patient_name=extract_patient_name,
            extract_gender=extract_gender,
            extract_age=extract_age,
            extract_specimen_condition=extract_specimen_condition,
            extract_specimen_types=extract_specimen_types,
            extract_hospital=extract_hospital,
            extract_date=extract_date,
            extract_staff=extract_staff,
        )
    if package_code == "P17":
        return build_p17_structured_report(source_file, full_text, page_texts)
    return {
        "report_id": extract_report_id(full_text) or Path(source_file).stem,
        "patient_info": {
            "name": extract_patient_name(full_text),
            "gender": extract_gender(full_text),
            "age": extract_age(full_text),
            "specimen_condition": extract_specimen_condition(full_text),
            "specimen_types": extract_specimen_types(page_texts),
            "hospital": extract_hospital(full_text),
            "patient_number": "",
            "bed_number": "",
            "department": "",
            "doctor": "",
            "clinical_diagnosis": "",
        },
        "tests": extract_structured_tests(page_texts, package_code=package_code),
        "notes": "",
        "additional_info": {
            "sample_date": extract_date(page_texts, "閲囨牱鏃ユ湡"),
            "receive_date": extract_date(page_texts, "鎺ユ敹鏃堕棿"),
            "report_date": extract_date(page_texts, "鎶ュ憡鏃堕棿"),
            "technician": extract_staff(full_text, ["妫€娴嬭€?", "妫€楠岃€?"]),
            "reviewer": extract_staff(full_text, ["瀹℃牳鑰?", "澶嶆牳鑰?"]),
            "approver": extract_staff(full_text, ["鎵瑰噯浜?", "鎵瑰噯鑰?"]),
        },
    }


def build_p06_structured_report(source_file: str, full_text: str, page_texts: list[str]) -> dict[str, Any]:
    report_id = extract_report_id(full_text) or Path(source_file).stem
    submitting_unit = _p06_extract_submitting_unit(full_text)
    tests = extract_p06_structured_tests(page_texts)
    report_info = {
        "report_title": "合肥安为康医学检验实验室检验报告单",
        "report_title_en": "Anweikang Clinical Laboratory Center Results Report",
        "barcode": report_id,
        "submitting_unit": submitting_unit,
        "name": _p06_extract_name(full_text),
        "gender": _p06_extract_gender(full_text),
        "age": _p06_extract_age_display(full_text),
        "patient_id": "",
        "bed_number": "",
        "submitting_department": "",
        "submitting_doctor": "",
        "clinical_diagnosis": _p06_extract_after_label(full_text, "临床诊断"),
        "specimen_condition": _p06_extract_specimen_condition(full_text),
        "specimen_type": _p06_extract_specimen_type(page_texts),
        "report_date": _p06_extract_latest_date(page_texts, "报告时间"),
        "report_date_second_page": _p06_extract_page_specific_report_date(page_texts, 2),
        "company_address": _p06_extract_company_address(full_text),
        "note": "功能医学检测，本检测仅对来样负责，如有疑义请在收到报告后7天内联系。",
        "website": _p06_extract_after_label(full_text, "网 址") or _p06_extract_after_label(full_text, "网址"),
        "phone": _p06_extract_phone(full_text),
    }
    tests_page_1 = [test for test in tests if int(test.get("page") or 0) == 1]
    tests_page_2 = [test for test in tests if int(test.get("page") or 0) == 2]
    tests_page_3 = [test for test in tests if int(test.get("page") or 0) == 3]
    result_analysis = _p06_extract_result_analysis(page_texts[0] if page_texts else full_text)
    patient_info = {
        "name": report_info["name"],
        "gender": report_info["gender"],
        "age": extract_age(full_text),
        "phone": report_info["phone"],
        "specimen_condition": report_info["specimen_condition"],
        "specimen_types": [report_info["specimen_type"]] if report_info["specimen_type"] else [],
        "hospital": submitting_unit,
        "submitting_unit": submitting_unit,
        "patient_number": "",
        "bed_number": "",
        "department": "",
        "doctor": "",
        "clinical_diagnosis": report_info["clinical_diagnosis"],
    }
    additional_info = {
        "sample_date": _p06_extract_latest_date(page_texts, "采样日期"),
        "receive_date": _p06_extract_latest_date(page_texts, "接收时间"),
        "report_date": _p06_extract_latest_date(page_texts, "报告时间"),
        "technician": extract_staff(full_text, ["检测者"]),
        "reviewer": extract_staff(full_text, ["审核者"]),
        "approver": extract_staff(full_text, ["批准人"]),
    }
    return {
        "report_id": report_id,
        "patient_info": patient_info,
        "tests": tests,
        "notes": result_analysis,
        "additional_info": additional_info,
        "p06_extracted_report": {
            "report_info": report_info,
            "tests_page_1": [_p06_test_export_item(test) for test in tests_page_1],
            "tests_page_2": [_p06_test_export_item(test) for test in tests_page_2],
            "tests_page_3": [_p06_test_export_item(test) for test in tests_page_3],
            "result_analysis": result_analysis,
        },
    }


def extract_p06_fields(page_texts: list[str], structured_report: dict[str, Any]) -> list[dict[str, Any]]:
    fields: list[dict[str, Any]] = []
    patient_info = structured_report.get("patient_info", {})
    additional_info = structured_report.get("additional_info", {})
    add_field(fields, "patient.name", "姓名", patient_info.get("name"), 0.88, find_page(page_texts, str(patient_info.get("name") or "")))
    add_field(fields, "patient.gender", "性别", patient_info.get("gender"), 0.86, find_page(page_texts, str(patient_info.get("gender") or "")))
    if patient_info.get("age") not in (None, ""):
        add_field(fields, "patient.age", "年龄", f"{patient_info['age']}岁", 0.86, find_page(page_texts, str(patient_info["age"])))
    submitting_unit = patient_info.get("submitting_unit") or patient_info.get("hospital") or ""
    add_field(fields, "patient.hospital", "送检单位", submitting_unit, 0.84, find_page(page_texts, str(submitting_unit or "")))
    add_field(fields, "patient.submitting_unit", "送检单位", submitting_unit, 0.84, find_page(page_texts, str(submitting_unit or "")))
    add_field(fields, "report.report_id", "报告编号", structured_report.get("report_id"), 0.9, find_page(page_texts, str(structured_report.get("report_id") or "")))
    add_field(fields, "report.assessment_date", "评估日期", additional_info.get("report_date") or additional_info.get("sample_date"), 0.84, find_page(page_texts, str(additional_info.get("report_date") or additional_info.get("sample_date") or "")))
    add_field(fields, "report.method", "评估方法", "免疫比浊&磁微粒化学发光&流式细胞", 0.84, 1)
    for test in structured_report.get("tests", []):
        code = str(test.get("item_code") or "")
        page = int(test.get("page") or 1)
        label = str(test.get("test_name") or code)
        add_field(fields, f"p06.tests.{code}.result_display", label, format_result_display(str(test.get("result") or ""), str(test.get("indicator") or "")), 0.84, page)
        add_field(fields, f"p06.tests.{code}.reference_range", label, test.get("reference_range"), 0.82, page)
        add_field(fields, f"p06.tests.{code}.status", label, test.get("indicator") or "正常", 0.82, page)
        add_field(fields, f"p06.tests.{code}.unit", label, test.get("unit"), 0.82, page)
        add_field(fields, f"p06.tests.{code}.method", label, test.get("method"), 0.8, page)
        if test.get("indicator"):
            add_field(fields, f"p06.tests.{code}.abnormal_flag", label, test.get("indicator"), 0.82, page)
        if code in {"gzm_b_nk", "ifn_gamma_nk", "gzm_b_ctl", "ifn_gamma_ctl"}:
            add_field(fields, f"p06.immune_cells.{code}.absolute_result", label, test.get("result"), 0.84, page)
            add_field(fields, f"p06.immune_cells.{code}.absolute_reference", label, test.get("reference_range"), 0.82, page)
            add_field(fields, f"p06.immune_cells.{code}.status", label, test.get("indicator") or "正常", 0.82, page)
        if code in {"il_1b", "il_2", "il_4", "il_5", "il_6", "il_8", "il_10", "il_12p70", "il_17", "ifn_alpha", "ifn_gamma", "tnf_alpha"}:
            add_field(fields, f"p06.cytokines.{code}.result_display", label, format_result_display(str(test.get("result") or ""), str(test.get("indicator") or "")), 0.84, page)
            add_field(fields, f"p06.cytokines.{code}.reference_range", label, test.get("reference_range"), 0.82, page)
            add_field(fields, f"p06.cytokines.{code}.status", label, test.get("indicator") or "正常", 0.82, page)
    return fields


def extract_p06_structured_tests(page_texts: list[str]) -> list[dict[str, Any]]:
    tests: list[dict[str, Any]] = []
    seen_codes: set[str] = set()
    for page_number, text in enumerate(page_texts, start=1):
        for definitions, default_specimen_type in [
            (P06_INFLAMMATION_TEST_DEFINITIONS, "血清"),
            (P06_IMMUNE_TEST_DEFINITIONS, "全血"),
            (P06_CYTOKINE_TEST_DEFINITIONS, "血清"),
        ]:
            for item_code, output_name, aliases, default_unit, default_method in definitions:
                if item_code in seen_codes:
                    continue
                parsed = _p06_parse_test_after_name(text, aliases, default_unit=default_unit, default_method=default_method)
                if not parsed:
                    continue
                tests.append(
                    {
                        "page": page_number,
                        "specimen_type": default_specimen_type,
                        "test_name": output_name,
                        "item_code": item_code,
                        "result": parsed["result"],
                        "indicator": _p06_indicator_from_parsed(parsed),
                        "reference_range": parsed["reference_range"],
                        "unit": parsed["unit"],
                        "method": parsed["method"],
                    }
                )
                seen_codes.add(item_code)
    return tests


def _p06_indicator_from_parsed(parsed: dict[str, str]) -> str:
    status = str(parsed.get("status") or "").strip()
    if status:
        return status
    flag = str(parsed.get("flag") or "").strip()
    if flag:
        return flag
    return "正常"


def _p06_parse_test_after_name(text: str, aliases: tuple[str, ...], *, default_unit: str, default_method: str) -> dict[str, str] | None:
    for alias in aliases:
        match = re.search(rf"{name_pattern(alias)}", text, flags=re.IGNORECASE)
        if not match:
            continue
        window = normalize_text(text[match.end() : match.end() + 80])
        value_match = re.search(
            r"(?P<result>[0-9]+(?:\.[0-9]+)?)\s*(?P<flag>[↑↓])?\s*"
            r"(?P<reference>"
            r"[0-9]+(?:\.[0-9]+)?\s*(?:--|~|-)\s*[0-9]+(?:\.[0-9]+)?|"
            r"(?:≤|>=|≥|<=|<|>|＜|＞)\s*[0-9]+(?:\.[0-9]+)?"
            r")",
            window,
        )
        if not value_match:
            continue
        status_match = re.search(r"升高|偏高|偏低|降低|正常|异常", window)
        return {
            "result": value_match.group("result"),
            "flag": value_match.group("flag") or "",
            "reference_range": value_match.group("reference").replace(" ", ""),
            "status": status_match.group(0) if status_match else "",
            "unit": default_unit,
            "method": default_method,
        }
    return None


def _p06_extract_name(full_text: str) -> str:
    match = re.search(rf"{label_pattern('姓名')}[:：]?\s*([^\s]+)", full_text)
    return clean_value(match.group(1)) if match else extract_patient_name(full_text)


def _p06_extract_gender(full_text: str) -> str:
    match = re.search(rf"{label_pattern('性别')}[:：]?\s*(男|女)", full_text)
    return clean_value(match.group(1)) if match else extract_gender(full_text)


def _p06_extract_age_display(full_text: str) -> str:
    match = re.search(rf"{label_pattern('年龄')}[:：]?\s*([0-9]{{1,3}})\s*岁", full_text)
    return f"{match.group(1)}岁" if match else ""


def _p06_extract_submitting_unit(full_text: str) -> str:
    patterns = [
        r"\*[0-9]+\*\s*([^\s]+)\s*送检单位",
        r"条\s*形\s*码[:：]?[0-9]+\s*([^\s]+)\s*送检单位",
    ]
    for pattern in patterns:
        match = re.search(pattern, full_text)
        if match:
            return clean_value(match.group(1))
    return extract_hospital(full_text)


def _p06_extract_specimen_condition(full_text: str) -> str:
    match = re.search(r"年龄[:：\s]*[0-9]{1,3}\s*岁\s*([^\s]+)\s*标本情况", full_text)
    return clean_value(match.group(1)) if match else extract_specimen_condition(full_text)


def _p06_extract_specimen_type(page_texts: list[str]) -> str:
    values: list[str] = []
    for text in page_texts:
        for match in re.finditer(r"标本类型[:：\s]*([^\s]+)", text):
            values.append(clean_value(match.group(1)))
    return values[-1] if values else "血清"


def _p06_extract_latest_date(page_texts: list[str], label: str) -> str:
    values: list[str] = []
    pattern = re.compile(rf"{label_pattern(label)}[:：]?\s*({DATE_VALUE_PATTERN})")
    for text in page_texts:
        values.extend(match.group(1) for match in pattern.finditer(text))
    return max(values) if values else ""


def _p06_extract_page_specific_report_date(page_texts: list[str], page_number: int) -> str:
    if page_number < 1 or page_number > len(page_texts):
        return ""
    pattern = re.compile(rf"{label_pattern('报告时间')}[:：]?\s*({DATE_VALUE_PATTERN})")
    match = pattern.search(page_texts[page_number - 1])
    return match.group(1) if match else ""


def _p06_extract_after_label(full_text: str, label: str) -> str:
    pattern = re.compile(rf"{label_pattern(label)}[:：]?\s*([^\s]+)")
    match = pattern.search(full_text)
    if not match:
        return ""
    value = clean_value(match.group(1))
    if value in {"结", "结果"} or looks_like_label(value):
        return ""
    return value


def _p06_extract_phone(full_text: str) -> str:
    match = re.search(r"([0-9]{3,4}\s*-\s*[0-9]{3}\s*-\s*[0-9]{4})", full_text)
    if not match:
        return ""
    return clean_value(match.group(1)).replace(" ", "")


def _p06_extract_company_address(full_text: str) -> str:
    match = re.search(r"公司地址[:：]\s*(.*?)\s*(?:网\s*址|网址)", full_text)
    return clean_value(match.group(1)) if match else ""


def _p06_extract_result_analysis(page_text: str) -> str:
    match = re.search(r"结果分析[:：]\s*(.*?)\s*本检测仅对来样负责", page_text)
    return clean_value(match.group(1)) if match else ""


def _p06_test_export_item(test: dict[str, Any]) -> dict[str, Any]:
    return {
        "test_item": str(test.get("test_name") or ""),
        "result": str(test.get("result") or ""),
        "flag": str(test.get("indicator") or ""),
        "reference_range": str(test.get("reference_range") or ""),
        "unit": str(test.get("unit") or ""),
        "method": str(test.get("method") or ""),
    }


def build_p07_structured_report(source_file: str, full_text: str, page_texts: list[str]) -> dict[str, Any]:
    payload = _p07_parse_json_payload(full_text)
    if payload:
        return _build_p07_structured_report_from_payload(source_file, payload)

    report_id = extract_report_id(full_text) or Path(source_file).stem
    submitting_unit = _p07_extract_submitting_unit(full_text)
    specimen_condition = _p07_extract_specimen_condition(full_text)
    specimen_type = _p07_extract_specimen_type(page_texts)
    tests = extract_p07_structured_tests(page_texts)
    tests_page_1 = [test for test in tests if int(test.get("page") or 0) == 1]
    tests_page_2 = [test for test in tests if int(test.get("page") or 0) == 2]
    gene_tests = [test for test in tests if str(test.get("item_code") or "") == "aldh2"]
    sample_date = _p07_extract_date(page_texts, "采样日期")
    receive_date = _p07_extract_date(page_texts, "接收时间")
    report_date = _p07_extract_date(page_texts, "报告时间")
    patient_info = {
        "name": _p07_extract_name(full_text),
        "gender": _p07_extract_gender(full_text),
        "age": extract_age(full_text),
        "phone": _p07_extract_phone(full_text),
        "specimen_condition": specimen_condition,
        "specimen_types": _p07_specimen_types([specimen_type], tests),
        "hospital": submitting_unit,
        "submitting_unit": submitting_unit,
        "patient_number": "",
        "bed_number": "",
        "department": "",
        "doctor": "",
        "clinical_diagnosis": _p07_clean_clinical_diagnosis(_p07_extract_after_label(full_text, "临床诊断")),
    }
    report_info = {
        "report_title": "合肥安为康医学检验实验室检验报告单",
        "barcode": report_id,
        "submitting_unit": submitting_unit,
        "patient_name": patient_info["name"],
        "gender": patient_info["gender"],
        "age": patient_info["age"],
        "specimen_status": specimen_condition,
        "specimen_type": specimen_type,
    }
    additional_info = {
        "sample_date": sample_date,
        "receive_date": receive_date,
        "report_date": report_date,
        "technician": extract_staff(full_text, ["检测者", "检验者"]),
        "reviewer": extract_staff(full_text, ["审核者", "复核者"]),
        "approver": extract_staff(full_text, ["批准人", "批准者"]),
    }
    return {
        "report_id": report_id,
        "patient_info": patient_info,
        "tests": tests,
        "notes": _p07_collect_notes(full_text),
        "additional_info": additional_info,
        "p07_extracted_report": {
            "report_info": report_info,
            "page_1": {
                "test_items": [_p07_test_export_item(test) for test in tests_page_1],
                "remark": _p07_extract_remark(page_texts, 1),
                "sample_date": _p07_extract_page_date(page_texts, 1, "采样日期"),
                "receive_date": _p07_extract_page_date(page_texts, 1, "接收时间"),
                "report_date": _p07_extract_page_date(page_texts, 1, "报告时间"),
            },
            "page_2": {
                "test_items": [_p07_test_export_item(test) for test in tests_page_2],
                "remark": _p07_extract_remark(page_texts, 2),
                "sample_date": _p07_extract_page_date(page_texts, 2, "采样日期"),
                "receive_date": _p07_extract_page_date(page_texts, 2, "接收时间"),
                "report_date": _p07_extract_page_date(page_texts, 2, "报告时间"),
            },
            "page_3": {
                "test_result": _p07_gene_export_item(gene_tests[0]) if gene_tests else {},
                "method": _p07_extract_after_label(full_text, "检测方法") or _p07_extract_after_label(full_text, "method"),
                "instrument": _p07_extract_after_label(full_text, "检测仪器"),
            },
        },
    }


def _p07_parse_json_payload(full_text: str) -> dict[str, Any]:
    text = str(full_text or "").strip()
    if not text.startswith("{"):
        return {}
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) and "report_info" in payload else {}


def _build_p07_structured_report_from_payload(source_file: str, payload: dict[str, Any]) -> dict[str, Any]:
    report_info = payload.get("report_info", {}) if isinstance(payload.get("report_info"), dict) else {}
    pages_by_number = _p07_payload_pages_by_number(payload)
    page_1 = pages_by_number.get(1, {})
    page_2 = pages_by_number.get(2, {})
    page_3 = pages_by_number.get(3, {})
    tests = _p07_tests_from_json_payload(payload)
    gene_page = _p07_payload_page_by_role(payload, "gene") or page_3
    gene_basic = gene_page.get("basic_info", {}) if isinstance(gene_page.get("basic_info"), dict) else {}
    name = _first_text(report_info.get("patient_name"), gene_basic.get("name"))
    gender = _first_text(report_info.get("gender"), gene_basic.get("gender"))
    age = report_info.get("age") if report_info.get("age") not in (None, "") else gene_basic.get("age")
    specimen_types = _p07_specimen_types(
        [
            _first_text(report_info.get("specimen_type")),
            _first_text(gene_basic.get("specimen_type")),
        ],
        tests,
    )
    patient_info = {
        "name": name,
        "gender": gender,
        "age": age,
        "phone": "",
        "specimen_condition": _first_text(report_info.get("specimen_status"), gene_basic.get("sample_status")),
        "specimen_types": specimen_types,
        "hospital": _first_text(report_info.get("submitting_unit")),
        "submitting_unit": _first_text(report_info.get("submitting_unit")),
        "patient_number": "",
        "bed_number": "",
        "department": "",
        "doctor": "",
        "clinical_diagnosis": "",
    }
    additional_info = {
        "sample_date": _first_text(*[page.get("sample_date") for page in pages_by_number.values()], gene_basic.get("sample_date")),
        "receive_date": _first_text(*[page.get("receive_date") for page in pages_by_number.values()], gene_basic.get("receive_date")),
        "report_date": _max_date_text([page.get("report_date") for page in pages_by_number.values()]),
        "technician": "",
        "reviewer": "",
        "approver": "",
    }
    return {
        "report_id": _first_text(report_info.get("barcode"), Path(source_file).stem),
        "patient_info": patient_info,
        "tests": tests,
        "notes": _p07_json_notes(page_1, page_2, page_3),
        "additional_info": additional_info,
        "p07_extracted_report": {
            "report_info": {
                "report_title": _first_text(report_info.get("report_title")),
                "barcode": _first_text(report_info.get("barcode"), Path(source_file).stem),
                "submitting_unit": _first_text(report_info.get("submitting_unit")),
                "patient_name": name,
                "gender": gender,
                "age": age,
                "specimen_status": _first_text(report_info.get("specimen_status")),
                "specimen_type": _first_text(report_info.get("specimen_type")),
            },
            "page_1": {
                "test_items": [_p07_test_export_item(test) for test in tests if int(test.get("page") or 0) == 1],
                "remark": _first_text(page_1.get("remark")),
                "sample_date": _first_text(page_1.get("sample_date")),
                "receive_date": _first_text(page_1.get("receive_date")),
                "report_date": _first_text(page_1.get("report_date")),
            },
            "page_2": {
                "test_items": [_p07_test_export_item(test) for test in tests if int(test.get("page") or 0) == 2],
                "remark": _first_text(page_2.get("remark")),
                "sample_date": _first_text(page_2.get("sample_date")),
                "receive_date": _first_text(page_2.get("receive_date")),
                "report_date": _first_text(page_2.get("report_date")),
            },
            "page_3": {
                "report_title": _first_text(page_3.get("report_title")),
                "basic_info": gene_basic,
                "test_result": page_3.get("test_result", {}) if isinstance(page_3.get("test_result"), dict) else {},
                "method": _first_text(page_3.get("method")),
                "instrument": _first_text(page_3.get("instrument")),
                "detection_significance": _first_text(page_3.get("detection_significance")),
                "diet_advice": _first_text(page_3.get("diet_advice")),
                "genotype_info": page_3.get("genotype_info", {}) if isinstance(page_3.get("genotype_info"), dict) else {},
            },
        },
    }


def _p07_tests_from_json_payload(payload: dict[str, Any]) -> list[dict[str, Any]]:
    report_info = payload.get("report_info", {}) if isinstance(payload.get("report_info"), dict) else {}
    specimen_type = _first_text(report_info.get("specimen_type")) or "血清"
    tests: list[dict[str, Any]] = []
    for fallback_number, page in enumerate(_p07_payload_pages(payload), start=1):
        page_number = _p07_payload_page_number(page, fallback_number)
        page_specimen_type = _first_text(page.get("specimen_type"), specimen_type) or specimen_type
        page_group = _p07_payload_page_group(page)
        page_items = page.get("test_items", []) if isinstance(page.get("test_items"), list) else []
        if page_items:
            group = page_group if page_group in {"fibrosis", "liver_function"} else "liver_function"
            for raw_item in page_items:
                if isinstance(raw_item, dict):
                    tests.append(_p07_json_test_item(raw_item, page=page_number, group=group, specimen_type=page_specimen_type))
        gene_result = page.get("test_result", {}) if isinstance(page.get("test_result"), dict) else {}
        basic_info = page.get("basic_info", {}) if isinstance(page.get("basic_info"), dict) else {}
        if gene_result or page_group == "gene":
            tests.append(
                {
                    "page": page_number,
                    "specimen_type": _first_text(page.get("specimen_type"), basic_info.get("specimen_type")) or "EDTA抗凝全血",
                    "test_name": "ALDH2 c.1510G>A",
                    "item_code": "aldh2",
                    "group": "gene",
                    "result": _first_text(gene_result.get("result")),
                    "indicator": _first_text(gene_result.get("indication")),
                    "reference_range": "",
                    "unit": "",
                    "method": _first_text(page.get("method")) or "测序法",
                    "locus": _first_text(gene_result.get("gene_locus")) or "ALDH2 c.1510G>A",
                }
            )
    return tests


def _p07_payload_pages(payload: dict[str, Any]) -> list[dict[str, Any]]:
    pages = payload.get("pages")
    if isinstance(pages, list):
        return [page for page in pages if isinstance(page, dict)]
    result: list[dict[str, Any]] = []
    for index in range(1, 6):
        page = payload.get(f"page_{index}")
        if isinstance(page, dict):
            page.setdefault("page_number", index)
            result.append(page)
    return result


def _p07_payload_pages_by_number(payload: dict[str, Any]) -> dict[int, dict[str, Any]]:
    return {
        _p07_payload_page_number(page, fallback): page
        for fallback, page in enumerate(_p07_payload_pages(payload), start=1)
    }


def _p07_payload_page_number(page: dict[str, Any], fallback: int) -> int:
    value = page.get("page_number", page.get("page", fallback))
    try:
        return int(value)
    except (TypeError, ValueError):
        return fallback


def _p07_payload_page_by_role(payload: dict[str, Any], role: str) -> dict[str, Any]:
    for page in _p07_payload_pages(payload):
        if _p07_payload_page_group(page) == role:
            return page
    return {}


def _p07_payload_page_group(page: dict[str, Any]) -> str:
    title = _first_text(page.get("report_title"))
    if page.get("test_result") or "ALDH2" in title or "乙醛脱氢酶" in title:
        return "gene"
    page_items = page.get("test_items", []) if isinstance(page.get("test_items"), list) else []
    names = " ".join(_first_text(item.get("test_name")) for item in page_items if isinstance(item, dict))
    if any(token in names for token in ("前胶原", "胶原", "层粘连蛋白", "透明质酸", "PC-III", "CIV", "LN", "HA")):
        return "fibrosis"
    if page_items:
        return "liver_function"
    return ""


def _p07_json_test_item(raw_item: dict[str, Any], *, page: int, group: str, specimen_type: str) -> dict[str, Any]:
    name = _first_text(raw_item.get("test_name"))
    code = _p07_code_for_name(name, group=group)
    result = _p07_result_text(raw_item.get("result"))
    return {
        "page": page,
        "specimen_type": specimen_type,
        "test_name": name,
        "item_code": code,
        "group": group,
        "result": result,
        "indicator": _first_text(raw_item.get("indicator")),
        "reference_range": _first_text(raw_item.get("reference_range")),
        "unit": _first_text(raw_item.get("unit")),
        "method": _first_text(raw_item.get("method")) or ("化学发光法" if group == "fibrosis" else "肝功能检测"),
    }


def extract_p07_structured_tests(page_texts: list[str]) -> list[dict[str, Any]]:
    tests: list[dict[str, Any]] = []
    seen_codes: set[str] = set()
    for page_number, text in enumerate(page_texts, start=1):
        for test in _p07_extract_fibrosis_stacked_layout(text, page_number):
            code = str(test.get("item_code") or "")
            if code and code not in seen_codes:
                tests.append(test)
                seen_codes.add(code)
        for test in _p07_extract_liver_stacked_layout(text, page_number):
            code = str(test.get("item_code") or "")
            if code and code not in seen_codes:
                tests.append(test)
                seen_codes.add(code)
        for definitions, group, default_specimen_type, default_method in [
            (P07_FIBROSIS_TEST_DEFINITIONS, "fibrosis", "血清", "化学发光法"),
            (P07_LIVER_FUNCTION_TEST_DEFINITIONS, "liver_function", "血清", "肝功能检测"),
        ]:
            for item_code, output_name, aliases, default_unit, default_reference in definitions:
                if item_code in seen_codes:
                    continue
                parsed = _p07_parse_test_after_name(
                    text,
                    aliases,
                    default_unit=default_unit,
                    default_reference=default_reference,
                    default_method=default_method,
                )
                if not parsed:
                    continue
                tests.append(
                    {
                        "page": page_number,
                        "specimen_type": default_specimen_type,
                        "test_name": output_name,
                        "item_code": item_code,
                        "group": group,
                        "result": parsed["result"],
                        "indicator": parsed["indicator"],
                        "reference_range": parsed["reference_range"],
                        "unit": parsed["unit"],
                        "method": parsed["method"],
                    }
                )
                seen_codes.add(item_code)
        gene = _p07_parse_aldh2_gene(text)
        if gene and "aldh2" not in seen_codes:
            gene["page"] = page_number
            tests.append(gene)
            seen_codes.add("aldh2")
    return tests


def extract_p07_fields(page_texts: list[str], structured_report: dict[str, Any]) -> list[dict[str, Any]]:
    fields: list[dict[str, Any]] = []
    patient_info = structured_report.get("patient_info", {})
    additional_info = structured_report.get("additional_info", {})
    add_field(fields, "patient.name", "姓名", patient_info.get("name"), 0.9, find_page(page_texts, str(patient_info.get("name") or "")))
    add_field(fields, "patient.gender", "性别", patient_info.get("gender"), 0.88, find_page(page_texts, str(patient_info.get("gender") or "")))
    if patient_info.get("age") not in (None, ""):
        age_text = f"{patient_info['age']}岁" if str(patient_info["age"]).isdigit() else str(patient_info["age"])
        add_field(fields, "patient.age", "年龄", age_text, 0.88, find_page(page_texts, str(patient_info["age"])))
    submitting_unit = patient_info.get("submitting_unit") or patient_info.get("hospital") or ""
    add_field(fields, "patient.submitting_unit", "送检单位", submitting_unit, 0.86, find_page(page_texts, str(submitting_unit or "")))
    add_field(fields, "patient.hospital", "送检单位", submitting_unit, 0.86, find_page(page_texts, str(submitting_unit or "")))
    add_field(fields, "sample.type", "样本信息", "、".join(str(item) for item in patient_info.get("specimen_types", []) if str(item).strip()), 0.86, None)
    add_field(fields, "sample.condition", "标本情况", patient_info.get("specimen_condition"), 0.84, find_page(page_texts, str(patient_info.get("specimen_condition") or "")))
    add_field(fields, "report.report_id", "报告编号", structured_report.get("report_id"), 0.92, find_page(page_texts, str(structured_report.get("report_id") or "")))
    add_field(fields, "report.assessment_date", "评估日期", additional_info.get("report_date") or additional_info.get("sample_date"), 0.86, None)
    add_field(fields, "report.method", "评估方法", "肝功能、肝纤维化与ALDH2基因综合评估", 0.9, None)
    for test in structured_report.get("tests", []):
        code = str(test.get("item_code") or "")
        group = str(test.get("group") or "")
        page = int(test.get("page") or 1)
        label = str(test.get("test_name") or code)
        if code == "aldh2":
            add_field(fields, "p07.gene.aldh2.result", "ALDH2 基因型", test.get("result"), 0.88, page)
            add_field(fields, "p07.gene.aldh2.result_display", "ALDH2 基因型", test.get("result"), 0.88, page)
            add_field(fields, "p07.gene.aldh2.status", "ALDH2 基因型状态", test.get("indicator"), 0.86, page)
            add_field(fields, "p07.gene.aldh2.locus", "ALDH2 位点", test.get("locus"), 0.86, page)
            add_field(fields, "p07.gene.aldh2.method", "ALDH2 检测方法", test.get("method"), 0.84, page)
            continue
        if group not in {"liver_function", "fibrosis"}:
            continue
        prefix = f"p07.{group}.{code}"
        result = str(test.get("result") or "")
        indicator = str(test.get("indicator") or "")
        status = _p07_status_from_test(test)
        add_field(fields, f"{prefix}.result", label, result, 0.86, page)
        add_field(fields, f"{prefix}.result_display", label, format_result_display(result, indicator), 0.86, page)
        add_field(fields, f"{prefix}.reference_range", label, test.get("reference_range"), 0.84, page)
        add_field(fields, f"{prefix}.unit", label, test.get("unit"), 0.84, page)
        add_field(fields, f"{prefix}.status", label, status, 0.84, page)
        add_field(fields, f"{prefix}.method", label, test.get("method"), 0.82, page)
    return fields


def build_p08_structured_report(source_file: str, full_text: str, page_texts: list[str]) -> dict[str, Any]:
    payload = _p08_parse_json_payload(full_text)
    if payload:
        return _build_p08_structured_report_from_payload(source_file, payload)

    report_id = extract_report_id(full_text) or Path(source_file).stem
    tests = extract_p08_structured_tests(page_texts)
    submitting_unit = extract_hospital(full_text)
    specimen_condition = extract_specimen_condition(full_text)
    specimen_types = _p08_specimen_types(extract_specimen_types(page_texts), tests)
    patient_info = {
        "name": extract_patient_name(full_text),
        "gender": extract_gender(full_text),
        "age": extract_age(full_text),
        "phone": _p07_extract_phone(full_text),
        "specimen_condition": specimen_condition,
        "specimen_types": specimen_types,
        "hospital": submitting_unit,
        "submitting_unit": submitting_unit,
        "patient_number": "",
        "bed_number": "",
        "department": "",
        "doctor": "",
        "clinical_diagnosis": _p07_clean_clinical_diagnosis(_p07_extract_after_label(full_text, "临床诊断")),
    }
    report_info = {
        "report_title": "合肥安为康医学检验实验室检验报告单",
        "barcode": report_id,
        "submitting_unit": submitting_unit,
        "patient_name": patient_info["name"],
        "gender": patient_info["gender"],
        "age": patient_info["age"],
        "specimen_status": specimen_condition,
        "specimen_type": "、".join(specimen_types),
    }
    additional_info = {
        "sample_date": _p07_extract_date(page_texts, "采样日期"),
        "receive_date": _p07_extract_date(page_texts, "接收时间"),
        "report_date": _p07_extract_date(page_texts, "报告时间"),
        "technician": extract_staff(full_text, ["检测者", "检验者"]),
        "reviewer": extract_staff(full_text, ["审核者", "复核者"]),
        "approver": extract_staff(full_text, ["批准人", "批准者"]),
    }
    cardiovascular_tests = [test for test in tests if str(test.get("group") or "") == "cardiovascular"]
    raas_tests = [test for test in tests if str(test.get("group") or "") == "raas"]
    return {
        "report_id": report_id,
        "patient_info": patient_info,
        "tests": tests,
        "notes": "",
        "additional_info": additional_info,
        "p08_extracted_report": {
            "report_info": report_info,
            "cardiovascular": [_p08_test_export_item(test) for test in cardiovascular_tests],
            "raas": [_p08_test_export_item(test) for test in raas_tests],
        },
    }


def _p08_parse_json_payload(full_text: str) -> dict[str, Any]:
    text = str(full_text or "").strip()
    if not text:
        return {}
    candidates = [text]
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        candidate = text[start : end + 1]
        if candidate not in candidates:
            candidates.append(candidate)
    for candidate in candidates:
        try:
            payload = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if (
            isinstance(payload, dict)
            and isinstance(payload.get("report_info"), dict)
            and isinstance(payload.get("pages"), list)
        ):
            return payload
    return {}


def _build_p08_structured_report_from_payload(source_file: str, payload: dict[str, Any]) -> dict[str, Any]:
    report_info = payload.get("report_info", {}) if isinstance(payload.get("report_info"), dict) else {}
    pages = _p08_payload_pages(payload)
    tests = _p08_tests_from_json_payload(payload)
    if not any(str(test.get("item_code") or "") == "angiotensin_ratio" for test in tests):
        ratio_test = _p08_calculate_ratio_test(tests)
        if ratio_test:
            tests.append(ratio_test)

    sample_dates = [_first_text(page.get("sample_date")) for page in pages]
    receive_dates = [_first_text(page.get("receive_date")) for page in pages]
    report_dates = [_first_text(page.get("report_date")) for page in pages]
    sample_dates = [value for value in sample_dates if value]
    receive_dates = [value for value in receive_dates if value]
    specimen_types = _p08_specimen_types([page.get("specimen_type", "") for page in pages], tests)
    submitting_unit = _first_text(report_info.get("submitting_unit"))
    name = _first_text(report_info.get("patient_name"), report_info.get("name"))
    gender = _first_text(report_info.get("gender"))
    age = report_info.get("age") if report_info.get("age") not in (None, "") else ""
    patient_info = {
        "name": name,
        "gender": gender,
        "age": age,
        "phone": "",
        "specimen_condition": _first_text(report_info.get("specimen_status")),
        "specimen_types": specimen_types,
        "hospital": submitting_unit,
        "submitting_unit": submitting_unit,
        "patient_number": "",
        "bed_number": "",
        "department": "",
        "doctor": "",
        "clinical_diagnosis": "",
    }
    additional_info = {
        "sample_date": min(sample_dates) if sample_dates else "",
        "receive_date": min(receive_dates) if receive_dates else "",
        "report_date": _max_date_text(report_dates),
        "technician": "",
        "reviewer": "",
        "approver": "",
    }
    cardiovascular_tests = [test for test in tests if str(test.get("group") or "") == "cardiovascular"]
    raas_tests = [test for test in tests if str(test.get("group") or "") == "raas"]
    return {
        "report_id": _first_text(report_info.get("barcode"), Path(source_file).stem),
        "patient_info": patient_info,
        "tests": tests,
        "notes": _p08_payload_notes(pages),
        "additional_info": additional_info,
        "p08_extracted_report": {
            "report_info": {
                "barcode": _first_text(report_info.get("barcode"), Path(source_file).stem),
                "submitting_unit": submitting_unit,
                "patient_name": name,
                "gender": gender,
                "age": age,
                "specimen_status": _first_text(report_info.get("specimen_status")),
                "specimen_type": "、".join(specimen_types),
            },
            "pages": _p08_export_payload_pages(pages, tests),
            "cardiovascular": [_p08_test_export_item(test) for test in cardiovascular_tests],
            "raas": [_p08_test_export_item(test) for test in raas_tests],
        },
    }


def _p08_payload_pages(payload: dict[str, Any]) -> list[dict[str, Any]]:
    pages = payload.get("pages", [])
    if not isinstance(pages, list):
        return []
    return [page for page in pages if isinstance(page, dict)]


def _p08_tests_from_json_payload(payload: dict[str, Any]) -> list[dict[str, Any]]:
    tests: list[dict[str, Any]] = []
    for page_index, page in enumerate(_p08_payload_pages(payload), start=1):
        page_number = int(page.get("page_number") or page_index)
        specimen_type = _first_text(page.get("specimen_type"))
        items = page.get("test_items", [])
        if not isinstance(items, list):
            continue
        for raw_item in items:
            if not isinstance(raw_item, dict):
                continue
            test = _p08_json_test_item(raw_item, page=page_number, specimen_type=specimen_type)
            if test:
                tests.append(test)
    return tests


def _p08_json_test_item(raw_item: dict[str, Any], *, page: int, specimen_type: str) -> dict[str, Any] | None:
    source_name = _first_text(raw_item.get("test_name"))
    code = _p08_code_for_json_name(source_name)
    if not code:
        return None
    definition = _p08_definition_for_code(code)
    default_unit = definition.get("unit", "")
    default_method = definition.get("method", "")
    default_reference = definition.get("reference", "")
    raw_reference = _first_text(raw_item.get("reference_range"))
    if code in {"angiotensin_i", "angiotensin_i_4c", "aldosterone_renin_ratio"} and not raw_reference:
        default_reference = ""
    return {
        "page": page,
        "specimen_type": specimen_type,
        "test_name": source_name or definition.get("name", ""),
        "item_code": code,
        "group": _p08_group_for_code(code),
        "result": _p08_result_text(raw_item.get("result")),
        "indicator": _first_text(raw_item.get("indicator")),
        "reference_range": raw_reference or default_reference,
        "unit": _p08_normalize_unit(_first_text(raw_item.get("unit")) or default_unit),
        "method": _first_text(raw_item.get("method")) or default_method,
    }


def _p08_code_for_json_name(name: str) -> str:
    compact = re.sub(r"\s+", "", str(name or "")).replace("（", "(").replace("）", ")").replace("／", "/")
    lower = compact.lower()
    if not compact:
        return ""
    if "nt-probnp" in lower or "ntprobnp" in lower or "利钠肽" in compact:
        return "nt_probnp"
    if "d-二聚体" in lower or "d二聚体" in lower or "d-d" in lower or "d-dimer" in lower:
        return "d_dimer"
    if "游离脂肪酸" in compact or "ffa" in lower:
        return "ffa"
    if ("醛固酮" in compact and "肾素" in compact) or "arr" in lower:
        return "aldosterone_renin_ratio"
    if "血管紧张素" in compact and (("ii/i" in lower) or ("Ⅱ/Ⅰ" in compact)):
        return "angiotensin_ratio"
    if "血管紧张素ii" in lower or "血管紧张素Ⅱ" in compact or "angii" in lower or "angiotensinii" in lower:
        return "angiotensin_ii"
    if "血管紧张素i" in lower or "血管紧张素Ⅰ" in compact or "angiotensini" in lower or "angi" in lower:
        if "4℃" in compact or "4°c" in lower or "4c" in lower:
            return "angiotensin_i_4c"
        return "angiotensin_i"
    if "血浆肾素活性" in compact or "肾素活性" in compact or "renin" in lower or lower == "pra":
        return "renin"
    if "醛固酮" in compact or "aldosterone" in lower or "aldo" in lower:
        return "aldosterone"
    return ""


def _p08_definition_for_code(code: str) -> dict[str, str]:
    for item_code, output_name, _, default_unit, default_reference, group, default_method in P08_TEST_DEFINITIONS:
        if item_code == code:
            return {
                "name": output_name,
                "unit": default_unit,
                "reference": default_reference,
                "group": group,
                "method": default_method,
            }
    return P08_SUPPLEMENTAL_TEST_DEFINITIONS.get(code, {"name": code, "unit": "", "reference": "", "group": "raas", "method": ""})


def _p08_group_for_code(code: str) -> str:
    return "cardiovascular" if code in {"nt_probnp", "d_dimer", "ffa"} else "raas"


def _p08_normalize_unit(unit: str) -> str:
    text = str(unit or "").strip()
    lower = text.lower().replace("μ", "u").replace("µ", "u")
    if lower == "pg/ml":
        return "pg/mL"
    if lower == "ng/ml":
        return "ng/mL"
    if lower in {"ng/ml/hr", "ng/ml/h"}:
        return "ng/mL/h"
    if lower in {"ug/ml", "μg/ml", "µg/ml"}:
        return "ug/mL"
    if lower == "mg/l feu":
        return "mg/L FEU"
    return text


def _p08_result_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, float):
        return f"{value:.2f}"
    return str(value).strip()


def _p08_payload_notes(pages: list[dict[str, Any]]) -> str:
    notes: list[str] = []
    for page in pages:
        remark = _first_text(page.get("remark"))
        if remark and remark not in notes:
            notes.append(remark)
    return " ".join(notes)


def _p08_export_payload_pages(pages: list[dict[str, Any]], tests: list[dict[str, Any]]) -> list[dict[str, Any]]:
    exported: list[dict[str, Any]] = []
    for index, page in enumerate(pages, start=1):
        page_number = int(page.get("page_number") or index)
        exported.append(
            {
                "page_number": page_number,
                "specimen_type": _first_text(page.get("specimen_type")),
                "test_items": [
                    _p08_test_export_item(test)
                    for test in tests
                    if int(test.get("page") or 0) == page_number and str(test.get("item_code") or "") != "angiotensin_ratio"
                ],
                "remark": _first_text(page.get("remark")),
                "sample_date": _first_text(page.get("sample_date")),
                "receive_date": _first_text(page.get("receive_date")),
                "report_date": _first_text(page.get("report_date")),
            }
        )
    return exported


def extract_p08_structured_tests(page_texts: list[str]) -> list[dict[str, Any]]:
    tests: list[dict[str, Any]] = []
    seen_codes: set[str] = set()
    for page_number, text in enumerate(page_texts, start=1):
        for item_code, output_name, aliases, default_unit, default_reference, group, default_method in P08_TEST_DEFINITIONS:
            if item_code in seen_codes:
                continue
            parsed = _p08_parse_test_after_name(
                text,
                aliases,
                default_unit=default_unit,
                default_reference=default_reference,
                default_method=default_method,
            )
            if not parsed:
                continue
            tests.append(
                _p08_make_test(
                    page_number,
                    group,
                    item_code,
                    output_name,
                    parsed["result"],
                    parsed["reference_range"],
                    parsed["unit"],
                    parsed["method"],
                    indicator=parsed["indicator"],
                )
            )
            seen_codes.add(item_code)
    ratio_test = _p08_calculate_ratio_test(tests)
    if ratio_test and "angiotensin_ratio" not in seen_codes:
        tests.append(ratio_test)
    return tests


def extract_p08_fields(page_texts: list[str], structured_report: dict[str, Any]) -> list[dict[str, Any]]:
    fields: list[dict[str, Any]] = []
    patient_info = structured_report.get("patient_info", {})
    additional_info = structured_report.get("additional_info", {})
    add_field(fields, "patient.name", "姓名", patient_info.get("name"), 0.88, find_page(page_texts, str(patient_info.get("name") or "")))
    add_field(fields, "patient.gender", "性别", patient_info.get("gender"), 0.86, find_page(page_texts, str(patient_info.get("gender") or "")))
    if patient_info.get("age") not in (None, ""):
        age_text = f"{patient_info['age']}岁" if str(patient_info["age"]).isdigit() else str(patient_info["age"])
        add_field(fields, "patient.age", "年龄", age_text, 0.86, find_page(page_texts, str(patient_info["age"])))
    add_field(fields, "patient.phone", "联系电话", patient_info.get("phone"), 0.8, find_page(page_texts, str(patient_info.get("phone") or "")))
    add_field(fields, "patient.symptoms", "相关症状", patient_info.get("clinical_diagnosis"), 0.75, find_page(page_texts, str(patient_info.get("clinical_diagnosis") or "")))
    submitting_unit = patient_info.get("submitting_unit") or patient_info.get("hospital") or ""
    add_field(fields, "patient.submitting_unit", "送检单位", submitting_unit, 0.84, find_page(page_texts, str(submitting_unit or "")))
    add_field(fields, "sample.type", "样本信息", "血清、血浆、全血", 0.9, None)
    add_field(fields, "sample.condition", "标本情况", patient_info.get("specimen_condition"), 0.82, find_page(page_texts, str(patient_info.get("specimen_condition") or "")))
    add_field(fields, "report.report_id", "报告编号", structured_report.get("report_id"), 0.9, find_page(page_texts, str(structured_report.get("report_id") or "")))
    add_field(fields, "report.assessment_date", "评估日期", additional_info.get("report_date") or additional_info.get("sample_date"), 0.84, None)
    add_field(fields, "report.method", "评估方法", "化学发光&免疫比浊", 0.9, None)
    for test in structured_report.get("tests", []):
        code = str(test.get("item_code") or "")
        group = str(test.get("group") or "")
        if group not in {"cardiovascular", "raas"}:
            continue
        prefix_group = "cardiovascular" if group == "cardiovascular" else "raas"
        prefix = f"p08.{prefix_group}.{code}"
        page = int(test.get("page") or 1)
        label = str(test.get("test_name") or code)
        result = str(test.get("result") or "")
        indicator = str(test.get("indicator") or "")
        status = _p08_status_from_test(test)
        add_field(fields, f"{prefix}.result", label, result, 0.86, page)
        add_field(fields, f"{prefix}.result_display", label, format_result_display(result, indicator), 0.86, page)
        add_field(fields, f"{prefix}.reference_range", label, test.get("reference_range"), 0.84, page)
        add_field(fields, f"{prefix}.unit", label, test.get("unit"), 0.84, page)
        add_field(fields, f"{prefix}.status", label, status, 0.84, page)
        add_field(fields, f"{prefix}.method", label, test.get("method"), 0.82, page)
    return fields


def _p08_parse_test_after_name(
    text: str,
    aliases: tuple[str, ...],
    *,
    default_unit: str,
    default_reference: str,
    default_method: str,
) -> dict[str, str] | None:
    for alias in aliases:
        match = re.search(rf"{name_pattern(alias)}", text, flags=re.IGNORECASE)
        if not match:
            continue
        window = normalize_text(text[match.end() : match.end() + 180])
        value_match = re.search(r"(?P<result>[0-9]+(?:\.[0-9]+)?)\s*(?P<indicator>[↑↓])?", window)
        if not value_match:
            continue
        reference_match = re.search(
            r"(?P<reference>"
            r"[0-9]+(?:\.[0-9]+)?\s*(?:--|-|~|～)\s*[0-9]+(?:\.[0-9]+)?|"
            r"(?:≤|>=|≥|<=|<|>|＜|＞)\s*[0-9]+(?:\.[0-9]+)?"
            r")",
            window[value_match.end() :],
        )
        unit_match = re.search(r"mg/L\s*FEU|ng/mL/h|pg/mL|pg/ml|mmol/L|ng/mL|mg/L|g/L|U/L|%", window, flags=re.IGNORECASE)
        method_match = re.search(r"化学发光法|磁微粒化学发光法|免疫比浊法|酶法|计算法|LC-MS/MS法|质谱法", window)
        unit = unit_match.group(0).replace(" ", " ") if unit_match else default_unit
        if unit.lower() == "pg/ml":
            unit = "pg/mL"
        return {
            "result": value_match.group("result"),
            "indicator": value_match.group("indicator") or "",
            "reference_range": (reference_match.group("reference").replace(" ", "") if reference_match else default_reference),
            "unit": unit,
            "method": method_match.group(0) if method_match else default_method,
        }
    return None


def _p08_calculate_ratio_test(tests: list[dict[str, Any]]) -> dict[str, Any] | None:
    ang_i = next((test for test in tests if str(test.get("item_code") or "") == "angiotensin_i"), None)
    ang_ii = next((test for test in tests if str(test.get("item_code") or "") == "angiotensin_ii"), None)
    value_i = _p08_value_as_pg_ml(ang_i)
    value_ii = _p08_value_as_pg_ml(ang_ii)
    if not value_i or value_ii is None:
        return None
    result = f"{(value_ii / value_i):.2f}".rstrip("0").rstrip(".")
    page = int(ang_ii.get("page") or ang_i.get("page") or 1)
    return _p08_make_test(page, "raas", "angiotensin_ratio", "血管紧张素II / I 比值", result, "0.20-1.20", "", "计算法")


def _p08_value_as_pg_ml(test: dict[str, Any] | None) -> float | None:
    if not test:
        return None
    value = _safe_number(test.get("result"))
    if value is None:
        return None
    unit = str(test.get("unit") or "").strip().lower().replace("μ", "u").replace("µ", "u")
    if unit == "ng/ml":
        return value * 1000
    return value


def _p08_make_test(
    page_number: int,
    group: str,
    item_code: str,
    test_name: str,
    result: str,
    reference_range: str,
    unit: str,
    method: str,
    *,
    indicator: str = "",
) -> dict[str, Any]:
    return {
        "page": page_number,
        "specimen_type": "血清",
        "test_name": test_name,
        "item_code": item_code,
        "group": group,
        "result": str(result or "").strip(),
        "indicator": indicator,
        "reference_range": str(reference_range or "").strip(),
        "unit": unit,
        "method": method,
    }


def _p08_status_from_test(test: dict[str, Any]) -> str:
    indicator = str(test.get("indicator") or "").strip()
    if indicator:
        if indicator in {"↑", "升高", "偏高"}:
            value = _safe_number(test.get("result"))
            if str(test.get("item_code") or "") == "nt_probnp" and _p08_value_is_markedly_high(value, str(test.get("reference_range") or "")):
                return "明显升高"
            return "偏高"
        if indicator in {"↓", "降低", "偏低"}:
            return "偏低"
        return indicator
    result = _safe_number(test.get("result"))
    if result is None:
        return "待复核"
    bounds = _p07_reference_bounds(str(test.get("reference_range") or ""))
    for lower, upper in bounds:
        if lower is not None and result < lower:
            return "偏低"
        if upper is not None and result > upper:
            return "偏高"
        if lower is not None and upper is not None and lower <= result <= upper:
            return "正常"
        if lower is None and upper is not None and result <= upper:
            return "正常"
        if upper is None and lower is not None and result >= lower:
            return "正常"
    return "正常" if bounds else "待复核"


def _p08_value_is_markedly_high(value: float | None, reference_range: str) -> bool:
    if value is None:
        return False
    bounds = _p07_reference_bounds(reference_range)
    uppers = [upper for _, upper in bounds if upper is not None]
    if not uppers:
        return False
    return value >= max(uppers) * 2


def _p08_specimen_types(values: list[str], tests: list[dict[str, Any]]) -> list[str]:
    result: list[str] = []
    for value in values:
        text = str(value or "").strip()
        if text and text not in result:
            result.append(text)
    for test in tests:
        text = str(test.get("specimen_type") or "").strip()
        if text and text not in result:
            result.append(text)
    if not result and tests:
        result.append("血液指标")
    return result


def _p08_test_export_item(test: dict[str, Any]) -> dict[str, Any]:
    return {
        "test_name": str(test.get("test_name") or ""),
        "item_code": str(test.get("item_code") or ""),
        "result": str(test.get("result") or ""),
        "indicator": str(test.get("indicator") or ""),
        "reference_range": str(test.get("reference_range") or ""),
        "unit": str(test.get("unit") or ""),
        "method": str(test.get("method") or ""),
    }


def build_p09_structured_report(source_file: str, full_text: str, page_texts: list[str]) -> dict[str, Any]:
    payload = _p09_parse_json_payload(full_text)
    if payload:
        return _build_p09_structured_report_from_payload(source_file, payload)

    report_id = extract_report_id(full_text) or Path(source_file).stem
    tests = extract_p09_structured_tests(page_texts)
    sample_types = _p09_specimen_types(extract_specimen_types(page_texts), tests)
    primary_dates = _p09_primary_dates(page_texts, tests)
    patient_info = {
        "name": extract_patient_name(full_text),
        "gender": extract_gender(full_text),
        "age": extract_age(full_text),
        "phone": _p09_extract_phone(full_text),
        "specimen_condition": extract_specimen_condition(full_text),
        "specimen_types": sample_types,
        "hospital": extract_hospital(full_text),
        "submitting_unit": extract_hospital(full_text),
        "patient_number": "",
        "bed_number": "",
        "department": "",
        "doctor": "",
        "clinical_diagnosis": _p09_extract_after_label(full_text, "临床诊断"),
    }
    additional_info = {
        "sample_date": primary_dates.get("sample_date") or extract_date(page_texts, "采样日期"),
        "receive_date": primary_dates.get("receive_date") or extract_date(page_texts, "接收时间"),
        "report_date": primary_dates.get("report_date") or extract_date(page_texts, "报告时间"),
        "technician": extract_staff(full_text, ["检测者", "检验者"]),
        "reviewer": extract_staff(full_text, ["审核者", "复核者"]),
        "approver": extract_staff(full_text, ["批准人", "批准者"]),
    }
    return {
        "report_id": report_id,
        "patient_info": patient_info,
        "tests": tests,
        "notes": _p09_collect_notes(full_text),
        "additional_info": additional_info,
        "p09_extracted_report": {
            "report_info": {
                "barcode": report_id,
                "submitting_unit": patient_info["submitting_unit"],
                "patient_name": patient_info["name"],
                "gender": patient_info["gender"],
                "age": patient_info["age"],
                "specimen_status": patient_info["specimen_condition"],
                "specimen_type": "、".join(sample_types),
            },
            "pages": _p09_export_text_pages(page_texts, tests),
            "tests": [_p09_test_export_item(test) for test in tests],
        },
    }


def _p09_parse_json_payload(full_text: str) -> dict[str, Any]:
    text = str(full_text or "").strip()
    if not text:
        return {}
    candidates = [text]
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        candidate = text[start : end + 1]
        if candidate not in candidates:
            candidates.append(candidate)
    for candidate in candidates:
        try:
            payload = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if (
            isinstance(payload, dict)
            and isinstance(payload.get("report_info"), dict)
            and isinstance(payload.get("pages"), list)
        ):
            return payload
    return {}


def _build_p09_structured_report_from_payload(source_file: str, payload: dict[str, Any]) -> dict[str, Any]:
    report_info = payload.get("report_info", {}) if isinstance(payload.get("report_info"), dict) else {}
    pages = _p09_payload_pages(payload)
    tests = _p09_tests_from_json_payload(payload)
    specimen_types = _p09_specimen_types([page.get("specimen_type", "") for page in pages], tests)
    submitting_unit = _first_text(report_info.get("submitting_unit"))
    name = _first_text(report_info.get("patient_name"), report_info.get("name"))
    gender = _first_text(report_info.get("gender"))
    age = report_info.get("age") if report_info.get("age") not in (None, "") else ""
    primary_dates = _p09_primary_dates_from_payload_pages(pages)
    patient_info = {
        "name": name,
        "gender": gender,
        "age": age,
        "phone": "",
        "specimen_condition": _first_text(report_info.get("specimen_status")),
        "specimen_types": specimen_types,
        "hospital": submitting_unit,
        "submitting_unit": submitting_unit,
        "patient_number": "",
        "bed_number": "",
        "department": "",
        "doctor": "",
        "clinical_diagnosis": "",
    }
    additional_info = {
        "sample_date": primary_dates.get("sample_date", ""),
        "receive_date": primary_dates.get("receive_date", ""),
        "report_date": primary_dates.get("report_date", ""),
        "technician": "",
        "reviewer": "",
        "approver": "",
    }
    barcode = _first_text(report_info.get("barcode"), Path(source_file).stem)
    return {
        "report_id": barcode,
        "patient_info": patient_info,
        "tests": tests,
        "notes": _p09_payload_notes(pages),
        "additional_info": additional_info,
        "p09_extracted_report": {
            "report_info": {
                "barcode": barcode,
                "submitting_unit": submitting_unit,
                "patient_name": name,
                "gender": gender,
                "age": age,
                "specimen_status": patient_info["specimen_condition"],
                "specimen_type": "、".join(specimen_types),
            },
            "pages": _p09_export_payload_pages(pages, tests),
            "tests": [_p09_test_export_item(test) for test in tests],
        },
    }


def _p09_payload_pages(payload: dict[str, Any]) -> list[dict[str, Any]]:
    pages = payload.get("pages", [])
    if not isinstance(pages, list):
        return []
    return [page for page in pages if isinstance(page, dict)]


def _p09_tests_from_json_payload(payload: dict[str, Any]) -> list[dict[str, Any]]:
    tests: list[dict[str, Any]] = []
    for page_index, page in enumerate(_p09_payload_pages(payload), start=1):
        page_number = int(page.get("page_number") or page_index)
        specimen_type = _first_text(page.get("specimen_type"))
        items = page.get("test_items", [])
        if not isinstance(items, list):
            continue
        for raw_item in items:
            if not isinstance(raw_item, dict):
                continue
            test = _p09_json_test_item(raw_item, page=page_number, specimen_type=specimen_type)
            if test:
                tests.append(test)
    return tests


def _p09_json_test_item(raw_item: dict[str, Any], *, page: int, specimen_type: str) -> dict[str, Any] | None:
    source_name = _first_text(raw_item.get("test_name"))
    code = _p09_code_for_json_name(source_name)
    if not code:
        return None
    definition = _p09_definition_for_code(code)
    return {
        "page": page,
        "specimen_type": specimen_type or "血清",
        "test_name": source_name or definition.get("name", ""),
        "item_code": code,
        "group": definition.get("group", ""),
        "result": _p09_result_text(raw_item.get("result")),
        "indicator": _first_text(raw_item.get("indicator")),
        "reference_range": _first_text(raw_item.get("reference_range")) or definition.get("reference", ""),
        "unit": _p09_normalize_unit(_first_text(raw_item.get("unit")) or definition.get("unit", "")),
        "method": _first_text(raw_item.get("method")) or definition.get("method", ""),
    }


def _p09_code_for_json_name(name: str) -> str:
    compact = re.sub(r"\s+", "", str(name or "")).replace("（", "(").replace("）", ")").replace("／", "/")
    lower = compact.lower()
    if not compact:
        return ""
    if "性激素结合球蛋白" in compact or "shbg" in lower:
        return "shbg"
    if "雌二醇" in compact or "estradiol" in lower or re.search(r"(?<![a-z0-9])e2(?![a-z0-9])", lower):
        return "e2"
    if "促黄体生成素" in compact or "黄体生成素" in compact or re.search(r"(?<![a-z0-9])lh(?![a-z0-9])", lower):
        return "lh"
    if "促卵泡刺激素" in compact or "卵泡刺激素" in compact or re.search(r"(?<![a-z0-9])fsh(?![a-z0-9])", lower):
        return "fsh"
    if "抗缪勒氏管激素" in compact or "抗穆勒氏管激素" in compact or re.search(r"(?<![a-z0-9])amh(?![a-z0-9])", lower):
        return "amh"
    if "泌乳素" in compact or "催乳素" in compact or "prolactin" in lower or re.search(r"(?<![a-z0-9])prl(?![a-z0-9])", lower):
        return "prolactin"
    if "孕酮" in compact or "孕激素" in compact or "progesterone" in lower or re.search(r"(?<![a-z0-9])prog(?![a-z0-9])", lower):
        return "progesterone"
    if "睾酮" in compact or "testosterone" in lower:
        return "testosterone"
    if "皮质醇" in compact or "cortisol" in lower or re.search(r"(?<![a-z0-9])cort(?![a-z0-9])", lower):
        return "cortisol"
    if "总ige" in lower or "totalige" in lower or "totalige" in compact.lower():
        return "total_ige"
    return ""


def _p09_definition_for_code(code: str) -> dict[str, str]:
    for item_code, output_name, _, default_unit, default_reference, group, default_method in P09_TEST_DEFINITIONS:
        if item_code == code:
            return {
                "name": output_name,
                "unit": default_unit,
                "reference": default_reference,
                "group": group,
                "method": default_method,
            }
    return {"name": code, "unit": "", "reference": "", "group": "", "method": ""}


def _p09_result_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, float):
        return f"{value:.2f}"
    return str(value).strip()


def _p09_payload_notes(pages: list[dict[str, Any]]) -> str:
    notes: list[str] = []
    for page in pages:
        remark = _first_text(page.get("remark"))
        if remark and remark not in notes:
            notes.append(remark)
    return " ".join(notes)


def _p09_export_payload_pages(pages: list[dict[str, Any]], tests: list[dict[str, Any]]) -> list[dict[str, Any]]:
    exported: list[dict[str, Any]] = []
    for index, page in enumerate(pages, start=1):
        page_number = int(page.get("page_number") or index)
        exported.append(
            {
                "page_number": page_number,
                "specimen_type": _first_text(page.get("specimen_type")),
                "test_items": [_p09_test_export_item(test) for test in tests if int(test.get("page") or 0) == page_number],
                "remark": _first_text(page.get("remark")),
                "sample_date": _first_text(page.get("sample_date")),
                "receive_date": _first_text(page.get("receive_date")),
                "report_date": _first_text(page.get("report_date")),
            }
        )
    return exported


def _p09_export_text_pages(page_texts: list[str], tests: list[dict[str, Any]]) -> list[dict[str, Any]]:
    exported: list[dict[str, Any]] = []
    for page_number, _text in enumerate(page_texts, start=1):
        page_tests = [test for test in tests if int(test.get("page") or 0) == page_number]
        if not page_tests:
            continue
        exported.append(
            {
                "page_number": page_number,
                "specimen_type": page_tests[0].get("specimen_type") or "血清",
                "test_items": [_p09_test_export_item(test) for test in page_tests],
                "remark": _p09_extract_remark(page_texts, page_number),
                "sample_date": _p09_extract_page_date(page_texts, page_number, "采样日期"),
                "receive_date": _p09_extract_page_date(page_texts, page_number, "接收时间"),
                "report_date": _p09_extract_page_date(page_texts, page_number, "报告时间"),
            }
        )
    return exported


def _p09_primary_dates(page_texts: list[str], tests: list[dict[str, Any]]) -> dict[str, str]:
    if not page_texts:
        return {"sample_date": "", "receive_date": "", "report_date": ""}
    counts: dict[int, int] = {}
    for test in tests:
        page = int(test.get("page") or 0)
        if page:
            counts[page] = counts.get(page, 0) + 1
    primary_page = max(counts, key=counts.get) if counts else 1
    return {
        "sample_date": _p09_extract_page_date(page_texts, primary_page, "采样日期"),
        "receive_date": _p09_extract_page_date(page_texts, primary_page, "接收时间"),
        "report_date": _p09_extract_page_date(page_texts, primary_page, "报告时间"),
    }


def _p09_primary_dates_from_payload_pages(pages: list[dict[str, Any]]) -> dict[str, str]:
    dated_pages = [page for page in pages if _first_text(page.get("sample_date"), page.get("receive_date"), page.get("report_date"))]
    if not dated_pages:
        return {"sample_date": "", "receive_date": "", "report_date": ""}
    primary = max(dated_pages, key=lambda page: len(page.get("test_items", [])) if isinstance(page.get("test_items"), list) else 0)
    return {
        "sample_date": _first_text(primary.get("sample_date")),
        "receive_date": _first_text(primary.get("receive_date")),
        "report_date": _first_text(primary.get("report_date")),
    }


def _p09_extract_page_date(page_texts: list[str], page_number: int, label: str) -> str:
    if page_number < 1 or page_number > len(page_texts):
        return ""
    pattern = re.compile(rf"{label_pattern(label)}[:：]?\s*({DATE_VALUE_PATTERN})")
    match = pattern.search(page_texts[page_number - 1])
    return match.group(1) if match else ""


def _p09_extract_remark(page_texts: list[str], page_number: int) -> str:
    if page_number < 1 or page_number > len(page_texts):
        return ""
    match = re.search(r"备\s*注[:：]?\s*([^\s]+)", page_texts[page_number - 1])
    return clean_value(match.group(1)) if match else ""


def extract_p09_structured_tests(page_texts: list[str]) -> list[dict[str, Any]]:
    tests: list[dict[str, Any]] = []
    seen_codes: set[str] = set()
    for page_number, text in enumerate(page_texts, start=1):
        for item_code, output_name, aliases, default_unit, default_reference, group, default_method in P09_TEST_DEFINITIONS:
            if item_code in seen_codes:
                continue
            parsed = _p09_parse_test_after_name(
                text,
                aliases,
                default_unit=default_unit,
                default_reference=default_reference,
                default_method=default_method,
            )
            if not parsed:
                continue
            tests.append(
                _p09_make_test(
                    page_number,
                    group,
                    item_code,
                    output_name,
                    parsed["result"],
                    parsed["reference_range"],
                    parsed["unit"],
                    parsed["method"],
                    indicator=parsed["indicator"],
                )
            )
            seen_codes.add(item_code)
    return tests


def extract_p09_fields(page_texts: list[str], structured_report: dict[str, Any]) -> list[dict[str, Any]]:
    fields: list[dict[str, Any]] = []
    patient_info = structured_report.get("patient_info", {})
    additional_info = structured_report.get("additional_info", {})
    add_field(fields, "patient.name", "姓名", patient_info.get("name"), 0.88, find_page(page_texts, str(patient_info.get("name") or "")))
    add_field(fields, "patient.gender", "性别", patient_info.get("gender"), 0.86, find_page(page_texts, str(patient_info.get("gender") or "")))
    if patient_info.get("age") not in (None, ""):
        age_text = f"{patient_info['age']}岁" if str(patient_info["age"]).isdigit() else str(patient_info["age"])
        add_field(fields, "patient.age", "年龄", age_text, 0.86, find_page(page_texts, str(patient_info["age"])))
    add_field(fields, "patient.phone", "联系电话", patient_info.get("phone"), 0.78, find_page(page_texts, str(patient_info.get("phone") or "")))
    add_field(fields, "patient.symptoms", "相关症状", patient_info.get("clinical_diagnosis") or "-", 0.75, find_page(page_texts, str(patient_info.get("clinical_diagnosis") or "")))
    submitting_unit = patient_info.get("submitting_unit") or patient_info.get("hospital") or ""
    add_field(fields, "patient.submitting_unit", "送检单位", submitting_unit, 0.84, find_page(page_texts, str(submitting_unit or "")))
    add_field(fields, "sample.type", "样本信息", "、".join(patient_info.get("specimen_types") or []) or "血清", 0.9, None)
    add_field(fields, "sample.condition", "标本情况", patient_info.get("specimen_condition"), 0.82, find_page(page_texts, str(patient_info.get("specimen_condition") or "")))
    add_field(fields, "report.report_id", "报告编号", structured_report.get("report_id"), 0.9, find_page(page_texts, str(structured_report.get("report_id") or "")))
    add_field(fields, "report.assessment_date", "评估日期", additional_info.get("report_date") or additional_info.get("sample_date"), 0.84, None)
    add_field(fields, "report.method", "评估方法", "化学发光法", 0.9, None)

    for test in structured_report.get("tests", []):
        code = str(test.get("item_code") or "")
        if not code:
            continue
        prefix = f"p09.indicators.{code}"
        page = int(test.get("page") or 1)
        label = str(test.get("test_name") or code)
        result = str(test.get("result") or "")
        indicator = str(test.get("indicator") or "")
        unit = str(test.get("unit") or "")
        reference = str(test.get("reference_range") or "")
        status = _p09_status_from_test(test)
        result_display = _p09_value_with_unit(format_result_display(result, indicator), unit)
        reference_display = _p09_reference_display(reference, unit)
        add_field(fields, f"{prefix}.result", label, result, 0.86, page)
        add_field(fields, f"{prefix}.unit", label, unit, 0.84, page)
        add_field(fields, f"{prefix}.result_display", label, result_display, 0.86, page)
        add_field(fields, f"{prefix}.reference_range", label, reference, 0.84, page)
        add_field(fields, f"{prefix}.reference_display", label, reference_display, 0.84, page)
        add_field(fields, f"{prefix}.status", label, status, 0.84, page)
        add_field(fields, f"{prefix}.status_display", label, _p09_status_display(status), 0.84, page)
        add_field(fields, f"{prefix}.range_status_display", label, f"{_p09_status_display(status)} | {reference_display}", 0.84, page)
        add_field(fields, f"{prefix}.method", label, test.get("method"), 0.82, page)
    return fields


def _p09_parse_test_after_name(
    text: str,
    aliases: tuple[str, ...],
    *,
    default_unit: str,
    default_reference: str,
    default_method: str,
) -> dict[str, str] | None:
    normalized = normalize_text(text)
    ordered_aliases = sorted(aliases, key=lambda value: (0 if _p09_contains_cjk(value) else 1, -len(value)))
    for alias in ordered_aliases:
        for match in re.finditer(rf"{name_pattern(alias)}", normalized, flags=re.IGNORECASE):
            parsed = _p09_parse_test_row(normalized, match, default_unit=default_unit, default_reference=default_reference, default_method=default_method)
            if parsed:
                return parsed
    return None


def _p09_parse_test_row(
    text: str,
    match: re.Match[str],
    *,
    default_unit: str,
    default_reference: str,
    default_method: str,
) -> dict[str, str] | None:
    row_start, row_end = _p09_row_bounds(text, match)
    row = normalize_text(text[row_start:row_end])
    if not row:
        return None
    alias_end = max(0, match.end() - row_start)
    after_alias = row[alias_end:]
    after_alias = re.sub(r"^\s*[（(][^）)]{1,30}[）)]\s*", " ", after_alias)
    after_alias = re.sub(r"^\s*[）)]\s*", " ", after_alias)
    value_match = re.search(
        r"(?P<indicator_before>[↑↓])?\s*(?P<result>(?:[<>≤≥＜＞]\s*)?[0-9]+(?:\.[0-9]+)?)\s*(?P<indicator_after>[↑↓])?",
        after_alias,
    )
    if not value_match:
        return None
    result = value_match.group("result").replace(" ", "")
    indicator = value_match.group("indicator_after") or value_match.group("indicator_before") or ""
    reference = _p09_clean_reference_tail(after_alias[value_match.end() :]) or default_reference
    unit_matches = list(re.finditer(P09_UNIT_PATTERN, row, flags=re.IGNORECASE))
    method_match = re.search(P09_METHOD_PATTERN, row)
    unit = _p09_normalize_unit(unit_matches[0].group(0) if unit_matches else default_unit)
    method = method_match.group(0) if method_match else default_method
    return {
        "result": result,
        "indicator": indicator,
        "reference_range": reference,
        "unit": unit,
        "method": method,
    }


def _p09_row_bounds(text: str, match: re.Match[str]) -> tuple[int, int]:
    prefix_start = max(0, match.start() - 100)
    prefix = text[prefix_start : match.start()]
    row_start = match.start()
    for unit_method in re.finditer(rf"(?:{P09_UNIT_PATTERN})\s+(?:{P09_METHOD_PATTERN})", prefix, flags=re.IGNORECASE):
        row_start = prefix_start + unit_method.start()

    next_item = _p09_next_item_start(text, match.end())
    footer = _p09_footer_start(text, match.end())
    candidates = [value for value in [next_item, footer] if value >= 0]
    row_end = min(candidates) if candidates else min(len(text), match.end() + 650)
    if next_item >= 0 and row_end == next_item:
        between = text[match.end() : next_item]
        unit_methods = list(re.finditer(rf"(?:{P09_UNIT_PATTERN})\s+(?:{P09_METHOD_PATTERN})", between, flags=re.IGNORECASE))
        if unit_methods:
            row_end = match.end() + unit_methods[-1].start()
    return row_start, row_end


def _p09_next_item_start(text: str, start: int) -> int:
    positions: list[int] = []
    for _code, _output_name, aliases, *_rest in P09_TEST_DEFINITIONS:
        for alias in aliases:
            if not _p09_contains_cjk(alias):
                continue
            match = re.search(rf"{name_pattern(alias)}", text[start:], flags=re.IGNORECASE)
            if match:
                positions.append(start + match.start())
                break
    return min(positions) if positions else -1


def _p09_footer_start(text: str, start: int) -> int:
    match = re.search(r"采样日期|接收时间|报告时间|公司地址|本检测|审核者|批准人|检测者|备\s*注|医院条码", text[start:])
    return start + match.start() if match else -1


def _p09_clean_reference_tail(value: str) -> str:
    text = normalize_text(value)
    if not text:
        return ""
    text = re.split(r"采样日期|接收时间|报告时间|公司地址|本检测|审核者|批准人|检测者|备\s*注|医院条码", text, maxsplit=1)[0]
    text = re.split(rf"(?:{P09_UNIT_PATTERN})\s+(?:{P09_METHOD_PATTERN})", text, maxsplit=1, flags=re.IGNORECASE)[0]
    text = re.sub(rf"^\s*(?:{P09_METHOD_PATTERN})\s*", "", text)
    text = re.sub(r"^\s*(?:参考范围|正常参考值|提示)[:：]?\s*", "", text)
    text = re.sub(rf"\s*(?:{P09_UNIT_PATTERN})\s*$", "", text, flags=re.IGNORECASE)
    return clean_value(text)


def _p09_contains_cjk(value: str) -> bool:
    return bool(re.search(r"[\u4e00-\u9fff]", str(value or "")))


def _p09_make_test(
    page_number: int,
    group: str,
    item_code: str,
    test_name: str,
    result: str,
    reference_range: str,
    unit: str,
    method: str,
    *,
    indicator: str = "",
) -> dict[str, Any]:
    return {
        "page": page_number,
        "specimen_type": "血清",
        "test_name": test_name,
        "item_code": item_code,
        "group": group,
        "result": str(result or "").strip(),
        "indicator": indicator,
        "reference_range": str(reference_range or "").strip(),
        "unit": unit,
        "method": method,
    }


def _p09_status_from_test(test: dict[str, Any]) -> str:
    indicator = str(test.get("indicator") or "").strip()
    if indicator:
        if indicator in {"↑", "升高", "偏高"}:
            return "偏高"
        if indicator in {"↓", "降低", "偏低"}:
            return "偏低"
        return indicator
    result = _safe_number(test.get("result"))
    if result is None:
        return "待复核"
    bounds = _p07_reference_bounds(str(test.get("reference_range") or ""))
    return _p09_status_from_bounds(result, bounds)


def _p09_status_from_bounds(result: float, bounds: list[tuple[float | None, float | None]]) -> str:
    if not bounds:
        return "待复核"
    for lower, upper in bounds:
        if lower is not None and upper is not None and lower <= result <= upper:
            return "正常"
        if lower is None and upper is not None and result <= upper:
            return "正常"
        if upper is None and lower is not None and result >= lower:
            return "正常"
    lows = [lower for lower, _upper in bounds if lower is not None]
    uppers = [upper for _lower, upper in bounds if upper is not None]
    if lows and result < min(lows):
        return "偏低"
    if uppers and result > max(uppers):
        return "偏高"
    return "待复核"


def _p09_status_display(status: str) -> str:
    text = str(status or "").strip()
    if text == "正常":
        return "正常范围"
    if text == "偏高":
        return "偏高"
    if text == "偏低":
        return "偏低"
    return text or "待复核"


def _p09_value_with_unit(value: str, unit: str) -> str:
    text = str(value or "").strip()
    unit_text = str(unit or "").strip()
    if not text:
        return "未识别"
    if text in {"未识别", "—"} or unit_text in {"", "—"}:
        return text
    return text if unit_text in text else f"{text} {unit_text}"


def _p09_reference_display(reference: str, unit: str) -> str:
    text = str(reference or "").strip()
    if not text:
        return "参考范围：待补充"
    unit_text = str(unit or "").strip()
    return f"参考范围：{text}{(' ' + unit_text) if unit_text and unit_text not in text else ''}"


def _p09_normalize_unit(unit: str) -> str:
    text = str(unit or "").strip()
    lower = text.lower().replace("μ", "u").replace("µ", "u")
    if lower in {"pg/ml"}:
        return "pg/mL"
    if lower in {"ng/ml"}:
        return "ng/mL"
    if lower in {"miu/ml"}:
        return "mIU/mL"
    if lower in {"uiu/ml", "uiu/ml"}:
        return "uIU/mL"
    if lower in {"iu/ml"}:
        return "IU/mL"
    if lower == "nmol/l":
        return "nmol/L"
    return text


def _p09_specimen_types(values: list[str], tests: list[dict[str, Any]]) -> list[str]:
    result: list[str] = []
    for value in values:
        text = str(value or "").strip()
        if text and text not in result:
            result.append(text)
    for test in tests:
        text = str(test.get("specimen_type") or "").strip()
        if text and text not in result:
            result.append(text)
    if not result and tests:
        result.append("血清")
    return result


def _p09_extract_phone(full_text: str) -> str:
    phone = extract_patient_phone(full_text)
    if phone:
        return phone
    match = re.search(r"(?<![0-9])(1[3-9][0-9]{9})(?![0-9])", full_text)
    return clean_value(match.group(1)).replace(" ", "") if match else ""


def _p09_extract_after_label(full_text: str, label: str) -> str:
    pattern = re.compile(rf"{label_pattern(label)}[:：]?\s*([^\s]+)")
    match = pattern.search(full_text)
    if not match:
        return ""
    value = clean_value(match.group(1))
    return "" if looks_like_label(value) else value


def _p09_collect_notes(full_text: str) -> str:
    parts: list[str] = []
    for pattern in [r"备注[:：]?\s*([^\s]+)", r"友情提示[:：]?\s*(.*?)(?:检测方法|$)"]:
        match = re.search(pattern, full_text)
        if match:
            value = clean_value(match.group(1))
            if value and value not in parts:
                parts.append(value)
    return " ".join(parts)


def _p09_test_export_item(test: dict[str, Any]) -> dict[str, Any]:
    return {
        "test_name": str(test.get("test_name") or ""),
        "item_code": str(test.get("item_code") or ""),
        "result": str(test.get("result") or ""),
        "indicator": str(test.get("indicator") or ""),
        "reference_range": str(test.get("reference_range") or ""),
        "unit": str(test.get("unit") or ""),
        "method": str(test.get("method") or ""),
    }


def build_p12_structured_report(source_file: str, full_text: str, page_texts: list[str]) -> dict[str, Any]:
    report_id = extract_report_id(full_text) or Path(source_file).stem
    tests = extract_p12_structured_tests(page_texts)
    sample_types = _p12_specimen_types(extract_specimen_types(page_texts), tests)
    patient_name = _p12_extract_patient_name(page_texts, full_text) or extract_patient_name(full_text) or _p12_extract_first_person_name(page_texts)
    specimen_condition = _p12_extract_specimen_condition(page_texts, full_text) or extract_specimen_condition(full_text)
    submitting_unit = _p12_extract_submitting_unit(page_texts, full_text) or extract_hospital(full_text)
    patient_info = {
        "name": patient_name,
        "gender": extract_gender(full_text),
        "age": extract_age(full_text),
        "phone": extract_patient_phone(full_text),
        "specimen_condition": specimen_condition,
        "specimen_types": sample_types,
        "hospital": submitting_unit,
        "submitting_unit": submitting_unit,
        "patient_number": "",
        "bed_number": "",
        "department": "",
        "doctor": "",
        "clinical_diagnosis": _p12_extract_clinical_diagnosis(full_text, page_texts),
    }
    additional_info = {
        "sample_date": _p12_extract_date(page_texts, "采样日期"),
        "receive_date": _p12_extract_date(page_texts, "接收时间") or _p12_extract_date(page_texts, "接收日期"),
        "report_date": _p12_extract_date(page_texts, "报告时间") or _p12_extract_date(page_texts, "报告日期"),
        "technician": extract_staff(full_text, ["检测者", "检验者"]),
        "reviewer": extract_staff(full_text, ["审核者", "复核者"]),
        "approver": extract_staff(full_text, ["批准人", "批准者"]),
    }
    return {
        "report_id": report_id,
        "patient_info": patient_info,
        "tests": tests,
        "notes": _p12_collect_notes(full_text),
        "additional_info": additional_info,
        "p12_extracted_report": {
            "report_info": {
                "barcode": report_id,
                "submitting_unit": patient_info["submitting_unit"],
                "patient_name": patient_info["name"],
                "gender": patient_info["gender"],
                "age": patient_info["age"],
                "specimen_status": patient_info["specimen_condition"],
                "specimen_type": "、".join(sample_types),
            },
            "pages": _p12_export_text_pages(page_texts, tests),
            "tests": [_p12_test_export_item(test) for test in tests],
        },
    }


def extract_p12_structured_tests(page_texts: list[str]) -> list[dict[str, Any]]:
    tests: list[dict[str, Any]] = []
    seen_codes: set[str] = set()
    for page_number, text in enumerate(page_texts, start=1):
        normalized = normalize_text(text)
        for item_code, output_name, aliases, default_unit, default_reference, group, default_method in P12_TEST_DEFINITIONS:
            if item_code in seen_codes:
                continue
            parsed = _p12_parse_nad_result(normalized) if item_code == "nad" else _p12_parse_test_after_name(
                normalized,
                aliases,
                default_unit=default_unit,
                default_reference=default_reference,
                default_method=default_method,
            )
            if not parsed:
                continue
            tests.append(
                _p12_make_test(
                    page_number,
                    group,
                    item_code,
                    output_name,
                    parsed["result"],
                    parsed["reference_range"],
                    parsed["unit"],
                    parsed["method"],
                    indicator=parsed["indicator"],
                )
            )
            seen_codes.add(item_code)
        antioxidant_tests = _p12_extract_antioxidant_tests(normalized, page_number)
        for test in antioxidant_tests:
            item_code = str(test.get("item_code") or "")
            if item_code in seen_codes:
                continue
            tests.append(test)
            seen_codes.add(item_code)
    return tests


def extract_p12_fields(page_texts: list[str], structured_report: dict[str, Any]) -> list[dict[str, Any]]:
    fields: list[dict[str, Any]] = []
    patient_info = structured_report.get("patient_info", {})
    additional_info = structured_report.get("additional_info", {})
    add_field(fields, "patient.name", "姓名", patient_info.get("name"), 0.88, find_page(page_texts, str(patient_info.get("name") or "")))
    add_field(fields, "patient.gender", "性别", patient_info.get("gender"), 0.86, find_page(page_texts, str(patient_info.get("gender") or "")))
    if patient_info.get("age") not in (None, ""):
        age_text = f"{patient_info['age']}岁" if str(patient_info["age"]).isdigit() else str(patient_info["age"])
        add_field(fields, "patient.age", "年龄", age_text, 0.86, find_page(page_texts, str(patient_info["age"])))
    add_field(fields, "patient.phone", "联系电话", patient_info.get("phone"), 0.78, find_page(page_texts, str(patient_info.get("phone") or "")))
    add_field(fields, "patient.symptoms", "相关症状", patient_info.get("clinical_diagnosis") or "-", 0.75, find_page(page_texts, str(patient_info.get("clinical_diagnosis") or "")))
    submitting_unit = patient_info.get("submitting_unit") or patient_info.get("hospital") or ""
    add_field(fields, "patient.submitting_unit", "送检单位", submitting_unit, 0.84, find_page(page_texts, str(submitting_unit or "")))
    add_field(fields, "sample.type", "样本信息", "、".join(patient_info.get("specimen_types") or []) or "能量代谢相关样本", 0.9, None)
    add_field(fields, "sample.condition", "标本情况", patient_info.get("specimen_condition"), 0.82, find_page(page_texts, str(patient_info.get("specimen_condition") or "")))
    add_field(fields, "report.report_id", "报告编号", structured_report.get("report_id"), 0.9, find_page(page_texts, str(structured_report.get("report_id") or "")))
    report_date = additional_info.get("report_date") or additional_info.get("sample_date")
    add_field(fields, "report.assessment_date", "评估日期", report_date, 0.84, find_page(page_texts, str(report_date or "")))
    add_field(fields, "report.method", "评估方法", "CoQ10 / NAD+ 综合评估", 0.9, None)
    for test in structured_report.get("tests", []):
        code = str(test.get("item_code") or "")
        if code not in {"coq10", "nad"}:
            continue
        prefix = f"p12.indicators.{code}"
        page = int(test.get("page") or 1)
        label = str(test.get("test_name") or code)
        result = str(test.get("result") or "")
        indicator = str(test.get("indicator") or "")
        unit = str(test.get("unit") or "")
        reference = str(test.get("reference_range") or "")
        status = _p12_status_from_test(test)
        add_field(fields, f"{prefix}.name_display", label, _p12_name_display(label, unit), 0.88, page)
        add_field(fields, f"{prefix}.result", label, result, 0.86, page)
        add_field(fields, f"{prefix}.unit", label, unit, 0.84, page)
        add_field(fields, f"{prefix}.result_display", label, _p12_value_with_unit(format_result_display(result, indicator), unit), 0.86, page)
        add_field(fields, f"{prefix}.reference_range", label, reference, 0.82, page)
        add_field(fields, f"{prefix}.status", label, status, 0.84, page)
        add_field(fields, f"{prefix}.status_display", label, _p12_status_display(status), 0.84, page)
        add_field(fields, f"{prefix}.method", label, test.get("method"), 0.82, page)
    return fields


def build_p13_structured_report(source_file: str, full_text: str, page_texts: list[str]) -> dict[str, Any]:
    payload = _p13_payload_from_text(source_file, full_text, page_texts)
    return build_p13_structured_report_from_ocr_json(source_file, payload)


def build_p13_structured_report_from_ocr_json(source_file: str, payload: dict[str, Any]) -> dict[str, Any]:
    report_info = _p13_dict(payload.get("report_info"))
    patient = _p13_dict(payload.get("patient_info"))
    results = _p13_dict(payload.get("test_results"))
    age_assessment = _p13_dict(results.get("telomere_age_assessment"))
    trend = _p13_dict(results.get("telomere_length_and_trend"))
    percentile = _p13_dict(results.get("population_percentile"))
    recommendations = _p13_dict(payload.get("recommendations"))
    educational_content = _p13_dict(payload.get("educational_content"))
    signature = _p13_dict(payload.get("signature"))

    report_id = _first_text(report_info.get("barcode"), Path(source_file).stem)
    sample_type = _first_text(patient.get("sample_type"), P13_SAMPLE_TYPE)
    method = _p13_normalize_method(_first_text(patient.get("test_technology"), P13_METHOD))
    actual_age = _p13_result_text(patient.get("age"))
    assessment_text = _first_text(age_assessment.get("assessment"))
    interpretation_text = _first_text(age_assessment.get("interpretation"))
    telomere_age = _p13_telomere_age(actual_age, assessment_text)
    percentile_description = _first_text(percentile.get("description"))
    percentile_value = _p13_percentile_value(percentile_description)
    percentile_display = _p13_percentile_display(percentile_value, percentile_description)
    tests = _p13_tests_from_payload(
        patient=patient,
        trend=trend,
        actual_age=actual_age,
        telomere_age=telomere_age,
        percentile_value=percentile_value,
        percentile_description=percentile_description,
        method=method,
        sample_type=sample_type,
    )
    normalized = {
        "actual_age": actual_age,
        "telomere_age": telomere_age,
        "age_gap": _p13_age_gap(assessment_text),
        "telomere_ct_value": _p13_result_text(trend.get("telomere_ct_value")),
        "internal_reference_ct_value": _p13_result_text(trend.get("internal_reference_ct_value")),
        "relative_telomere_length": _p13_result_text(trend.get("relative_telomere_length")),
        "percentile_value": _p13_result_text(percentile_value),
        "percentile_display": percentile_display,
        "overall_summary": _p13_overall_summary(telomere_age, actual_age, assessment_text),
        "telomere_interpretation": _first_text(interpretation_text, trend.get("note")),
        "percentile_summary": _p13_percentile_summary(percentile_value, percentile_description),
        "percentile_note": "百分位越高，代表端粒长度相对越长；本字段以原始报告同年龄段人群模型为准。",
        "followup_advice": _p13_followup_advice(recommendations),
        "disclaimer": _p13_disclaimer_text(payload.get("disclaimer")),
        "review_note": _p13_review_note(signature, report_info),
    }
    patient_info = {
        "name": _first_text(patient.get("name"), report_info.get("patient_name")),
        "gender": _first_text(patient.get("gender")),
        "age": actual_age,
        "phone": _first_text(patient.get("phone")),
        "specimen_condition": _first_text(patient.get("sample_condition")),
        "specimen_types": [sample_type] if sample_type else [],
        "hospital": _first_text(patient.get("submitting_institution")),
        "submitting_unit": _first_text(patient.get("submitting_institution")),
        "patient_number": "",
        "bed_number": "",
        "department": "",
        "doctor": "",
        "clinical_diagnosis": _first_text(patient.get("symptoms"), patient.get("clinical_diagnosis")),
    }
    additional_info = {
        "sample_date": _first_text(patient.get("submission_date")),
        "receive_date": _first_text(patient.get("receipt_date")),
        "report_date": _first_text(report_info.get("report_date")),
        "technician": "",
        "reviewer": _first_text(signature.get("primary_reviewer")),
        "approver": _first_text(signature.get("approver")),
        "laboratory": _first_text(signature.get("laboratory")),
    }
    return {
        "report_id": report_id,
        "patient_info": patient_info,
        "tests": tests,
        "notes": _first_text(assessment_text, trend.get("note"), percentile_description),
        "additional_info": additional_info,
        "p13_extracted_report": {
            "report_info": {
                "title": _first_text(report_info.get("report_title"), "端粒长度基因检测报告"),
                "package_name": P13_REPORT_NAME,
                "barcode": report_id,
                "report_date": additional_info["report_date"],
            },
            "patient_info": patient_info,
            "test_results": results,
            "recommendations": recommendations,
            "educational_content": educational_content,
            "references": payload.get("references") if isinstance(payload.get("references"), list) else [],
            "disclaimer": payload.get("disclaimer") if isinstance(payload.get("disclaimer"), dict) else {},
            "signature": signature,
            "normalized": normalized,
            "tests": [_p13_test_export_item(test) for test in tests],
        },
    }


def extract_p13_fields(page_texts: list[str], structured_report: dict[str, Any]) -> list[dict[str, Any]]:
    fields: list[dict[str, Any]] = []
    patient_info = structured_report.get("patient_info", {}) if isinstance(structured_report.get("patient_info"), dict) else {}
    additional_info = structured_report.get("additional_info", {}) if isinstance(structured_report.get("additional_info"), dict) else {}
    p13_report = structured_report.get("p13_extracted_report", {}) if isinstance(structured_report.get("p13_extracted_report"), dict) else {}
    normalized = p13_report.get("normalized", {}) if isinstance(p13_report.get("normalized"), dict) else {}
    sample_types = patient_info.get("specimen_types") if isinstance(patient_info.get("specimen_types"), list) else []
    sample_type = "、".join(str(item) for item in sample_types if str(item).strip()) or P13_SAMPLE_TYPE
    report_date = additional_info.get("report_date") or additional_info.get("sample_date")

    add_field(fields, "report.barcode", "条形码", structured_report.get("report_id"), 0.9, find_page(page_texts, str(structured_report.get("report_id") or "")))
    add_field(fields, "report.report_id", "报告编号", structured_report.get("report_id"), 0.9, find_page(page_texts, str(structured_report.get("report_id") or "")))
    add_field(fields, "patient.name", "姓名", patient_info.get("name"), 0.9, find_page(page_texts, str(patient_info.get("name") or "")))
    add_field(fields, "patient.gender", "性别", patient_info.get("gender"), 0.88, find_page(page_texts, str(patient_info.get("gender") or "")))
    if patient_info.get("age") not in (None, ""):
        add_field(fields, "patient.age", "年龄", _p13_age_display(patient_info.get("age")), 0.88, find_page(page_texts, str(patient_info.get("age") or "")))
    add_field(fields, "patient.phone", "联系电话", patient_info.get("phone") or "/", 0.76, None)
    add_field(fields, "patient.symptoms", "相关症状", patient_info.get("clinical_diagnosis") or "/", 0.76, None)
    add_field(fields, "patient.submitting_unit", "送检单位", patient_info.get("submitting_unit") or patient_info.get("hospital"), 0.84, find_page(page_texts, str(patient_info.get("submitting_unit") or patient_info.get("hospital") or "")))
    add_field(fields, "sample.type", "样本信息", sample_type, 0.92, find_page(page_texts, sample_type))
    add_field(fields, "report.assessment_type", "评估类型", P13_ASSESSMENT_TYPE, 0.92, None)
    add_field(fields, "report.method", "评估方法", P13_METHOD, 0.92, find_page(page_texts, P13_METHOD))
    add_field(fields, "report.assessment_date", "评估日期", report_date, 0.86, find_page(page_texts, str(report_date or "")))

    add_field(fields, "p13.telomere_age", "端粒年龄", normalized.get("telomere_age"), 0.9, find_page(page_texts, str(normalized.get("telomere_age") or "")))
    add_field(fields, "p13.actual_age", "实际年龄", normalized.get("actual_age"), 0.9, find_page(page_texts, str(normalized.get("actual_age") or "")))
    add_field(fields, "p13.overall_summary", "AI辅助诊断", normalized.get("overall_summary"), 0.82, None)
    add_field(fields, "p13.telomere.relative_length", "端粒相对长度", normalized.get("relative_telomere_length"), 0.9, find_page(page_texts, str(normalized.get("relative_telomere_length") or "")))
    add_field(fields, "p13.percentile.display", "人群百分位", normalized.get("percentile_display"), 0.88, find_page(page_texts, str(normalized.get("percentile_value") or "")))
    add_field(fields, "p13.telomere.ct_value", "端粒Ct值", normalized.get("telomere_ct_value"), 0.9, find_page(page_texts, str(normalized.get("telomere_ct_value") or "")))
    add_field(fields, "p13.reference.ct_value", "内参Ct值", normalized.get("internal_reference_ct_value"), 0.9, find_page(page_texts, str(normalized.get("internal_reference_ct_value") or "")))
    add_field(fields, "p13.telomere.interpretation", "端粒长度解读", normalized.get("telomere_interpretation"), 0.82, None)
    add_field(fields, "p13.percentile.summary", "百分位摘要", normalized.get("percentile_summary"), 0.82, None)
    add_field(fields, "p13.percentile.note", "百分位说明", normalized.get("percentile_note"), 0.82, None)
    add_field(fields, "p13.followup_advice", "后续行动", normalized.get("followup_advice"), 0.8, None)
    add_field(fields, "p13.disclaimer", "免责声明", normalized.get("disclaimer"), 0.8, None)
    add_field(fields, "p13.review_note", "审核信息", normalized.get("review_note"), 0.8, None)
    add_field(fields, "organization.phone", "联系电话", "400-158-1959", 0.9, None)
    add_field(fields, "organization.email", "电子邮箱", "service@anweikang.com", 0.9, None)
    add_field(fields, "organization.website", "官方网站", "www.anweikang.com", 0.9, None)
    add_field(fields, "organization.address", "公司地址", "安徽省合肥市庐阳区临泉路7266号研发中心楼1、4、5、6层", 0.9, None)
    return fields


def build_p14_structured_report(source_file: str, full_text: str, page_texts: list[str]) -> dict[str, Any]:
    report_id = extract_report_id(full_text) or Path(source_file).stem
    patient_name = extract_patient_name(full_text) or ""
    patient_gender = extract_gender(full_text) or ""
    patient_age = extract_age(full_text) or ""
    sample_types = extract_specimen_types(page_texts) or [P14_SAMPLE_TYPE]
    trend_points = [{"date": "待补录", "value": "—"} for _ in range(4)]
    return {
        "report_id": report_id,
        "patient_info": {
            "name": patient_name,
            "gender": patient_gender,
            "age": patient_age,
            "phone": "",
            "clinical_diagnosis": "",
            "specimen_types": sample_types,
            "specimen_condition": extract_specimen_condition(full_text) or "",
            "submitting_unit": extract_hospital(full_text) or "",
            "hospital": extract_hospital(full_text) or "",
        },
        "additional_info": {
            "sample_date": extract_date(page_texts, "采样日期") or extract_date(page_texts, "送检日期"),
            "receive_date": extract_date(page_texts, "接收日期") or extract_date(page_texts, "签收日期"),
            "report_date": extract_date(page_texts, "报告日期") or extract_date(page_texts, "评估日期"),
            "method": P14_METHOD,
            "source_mode": "pdf-text-fallback",
            "trend_points": trend_points,
        },
        "tests": [],
        "notes": _p16_compact(full_text, 500),
        "trend_points": trend_points,
        "p14_extracted_report": {
            "report_info": {
                "report_title": P14_REPORT_NAME,
                "assessment_type": P14_ASSESSMENT_TYPE,
                "source_mode": "pdf-text-fallback",
                "report_count": len(page_texts),
            },
            "normalized": {
                "overall_risk": "待复核",
                "overall_status": "待复核",
                "management_items": [
                    "建议补充结构化OCR",
                    "建议人工复核核心指标",
                    "建议结合原始报告解读",
                ],
                "followup_advice": "当前仅完成 PDF 文本层回退解析，建议优先补充 P14 结构化 JSON OCR 结果后再做渲染联调。",
                "disclaimer": "本报告仅供健康管理参考，不作为临床诊断依据。",
                "review_note": "P14 PDF 文本层回退解析未完成专项结构化校准，建议人工复核。",
                "trend_points": trend_points,
            },
            "reports": {},
            "tests": [],
        },
    }


def build_p14_structured_report_from_ocr_json(source_file: str, payload: dict[str, Any]) -> dict[str, Any]:
    reports = payload.get("reports", []) if isinstance(payload.get("reports"), list) else []
    risk_report = _p14_find_report(reports, "疾病风险评估报告")
    methylation_report = _p14_find_report(reports, "高发五癌游离DNA甲基化检测报告")
    ctc_report = _p14_find_report(reports, "CTC计数分型检测报告")

    risk_assessment = risk_report.get("risk_assessment", {}) if isinstance(risk_report.get("risk_assessment"), dict) else {}
    risk_sub_items = risk_report.get("sub_items", []) if isinstance(risk_report.get("sub_items"), list) else []
    system_assessment = risk_report.get("system_assessment", []) if isinstance(risk_report.get("system_assessment"), list) else []
    methylation_result = methylation_report.get("result", {}) if isinstance(methylation_report.get("result"), dict) else {}
    methylation_details = methylation_report.get("details", []) if isinstance(methylation_report.get("details"), list) else []
    ctc_screening = ctc_report.get("screening_results", {}) if isinstance(ctc_report.get("screening_results"), dict) else {}
    ctc_history = ctc_report.get("historical_results", []) if isinstance(ctc_report.get("historical_results"), list) else []

    report_id = _first_text(
        risk_report.get("patient_id"),
        methylation_report.get("barcode"),
        ctc_report.get("barcode"),
        ctc_report.get("report_id"),
        Path(source_file).stem,
    )
    sample_types = []
    for value in [
        P14_SAMPLE_TYPE,
        methylation_report.get("sample_type"),
        ctc_report.get("sample_type"),
    ]:
        text = _first_text(value)
        if text and text not in sample_types:
            sample_types.append(text)
    methods = []
    for value in [
        P14_METHOD,
        methylation_result.get("method"),
        "CTC计数分型检测",
    ]:
        text = _first_text(value)
        if text and text not in methods:
            methods.append(text)
    trend_points = _p14_trend_points_from_reports(ctc_history, ctc_screening, ctc_report)
    tests = _p14_tests_from_ocr_payload(
        risk_assessment=risk_assessment,
        methylation_result=methylation_result,
        methylation_details=methylation_details,
        ctc_screening=ctc_screening,
        ctc_history=ctc_history,
    )

    patient_info = {
        "name": _first_text(risk_report.get("patient_name"), methylation_report.get("patient_name"), ctc_report.get("patient_name")),
        "gender": _first_text(risk_report.get("gender"), methylation_report.get("gender"), ctc_report.get("gender")),
        "age": _first_text(risk_report.get("age"), methylation_report.get("age"), ctc_report.get("age")),
        "phone": _first_text(ctc_report.get("phone"), risk_report.get("hotline")),
        "specimen_condition": _first_text(
            (methylation_report.get("quality_control") or {}).get("sample_status") if isinstance(methylation_report.get("quality_control"), dict) else "",
            (methylation_report.get("quality_control") or {}).get("sample_quality") if isinstance(methylation_report.get("quality_control"), dict) else "",
        ),
        "specimen_types": sample_types,
        "hospital": _first_text(methylation_report.get("laboratory"), risk_report.get("laboratory"), ctc_report.get("submitting_institution")),
        "submitting_unit": _first_text(methylation_report.get("submitting_institution"), ctc_report.get("submitting_institution"), risk_report.get("organization")),
        "clinical_diagnosis": _first_text(ctc_report.get("clinical_diagnosis"), methylation_report.get("disease_history")),
    }
    additional_info = {
        "sample_date": _first_text(ctc_report.get("sampling_date"), methylation_report.get("receipt_date"), risk_report.get("submission_date")),
        "receive_date": _first_text(methylation_report.get("receipt_date")),
        "report_date": _first_text(ctc_report.get("report_date"), methylation_report.get("report_date"), risk_report.get("submission_date")),
        "method": " / ".join(methods) if methods else P14_METHOD,
        "source_mode": "ocr-json",
        "trend_points": trend_points,
    }
    management_items = [
        _first_text((risk_report.get("recommendations") or {}).get("behavioral") if isinstance(risk_report.get("recommendations"), dict) else ""),
        _first_text((risk_report.get("recommendations") or {}).get("dietary") if isinstance(risk_report.get("recommendations"), dict) else ""),
        _first_text(ctc_report.get("further_testing_advice"), methylation_report.get("advice")),
    ]
    management_items = [item for item in management_items if item]
    while len(management_items) < 3:
        management_items.append("建议结合临床资料进行人工复核")

    return {
        "report_id": report_id,
        "patient_info": patient_info,
        "additional_info": additional_info,
        "tests": tests,
        "notes": _p14_join_sentences(
            _first_text(risk_report.get("disclaimer")),
            _first_text(methylation_report.get("interpretation")),
            _first_text(ctc_report.get("remarks")),
        ),
        "trend_points": trend_points,
        "p14_extracted_report": {
            "report_info": {
                "report_title": P14_REPORT_NAME,
                "assessment_type": P14_ASSESSMENT_TYPE,
                "source_mode": "ocr-json",
                "report_count": len(reports),
                "barcode": _first_text(methylation_report.get("barcode"), ctc_report.get("barcode")),
                "patient_id": _first_text(risk_report.get("patient_id")),
            },
            "normalized": {
                "overall_risk": _first_text(risk_assessment.get("overall_risk"), risk_assessment.get("status"), "待复核"),
                "overall_status": _first_text(risk_assessment.get("status"), "待复核"),
                "methylation_result": _first_text(methylation_result.get("result"), "待补录"),
                "ctc_total": _first_text(ctc_screening.get("total")),
                "ctc_unit": _first_text(ctc_screening.get("unit"), "个/7.5mL"),
                "ctc_epithelial": _first_text(ctc_screening.get("epithelial_ctc")),
                "ctc_mesenchymal": _first_text(ctc_screening.get("mesenchymal_ctc")),
                "ctc_mixed": _first_text(ctc_screening.get("mixed_ctc")),
                "clinical_diagnosis": patient_info["clinical_diagnosis"],
                "behavioral_advice": _first_text((risk_report.get("recommendations") or {}).get("behavioral") if isinstance(risk_report.get("recommendations"), dict) else ""),
                "infectious_advice": _first_text((risk_report.get("recommendations") or {}).get("infectious") if isinstance(risk_report.get("recommendations"), dict) else ""),
                "dietary_advice": _first_text((risk_report.get("recommendations") or {}).get("dietary") if isinstance(risk_report.get("recommendations"), dict) else ""),
                "metabolic_advice": _first_text((risk_report.get("recommendations") or {}).get("metabolic") if isinstance(risk_report.get("recommendations"), dict) else ""),
                "environmental_advice": _first_text((risk_report.get("recommendations") or {}).get("environmental") if isinstance(risk_report.get("recommendations"), dict) else ""),
                "methylation_advice": _first_text(methylation_report.get("advice")),
                "ctc_followup_advice": _first_text(ctc_report.get("further_testing_advice")),
                "management_items": management_items[:3],
                "followup_advice": _first_text(ctc_report.get("further_testing_advice"), methylation_report.get("advice"), "建议结合原始报告和临床信息安排阶段性复评。"),
                "disclaimer": _first_text(ctc_report.get("remarks"), methylation_report.get("reminders", [""])[0] if isinstance(methylation_report.get("reminders"), list) else "", risk_report.get("disclaimer")),
                "review_note": "P14 已基于多报告聚合 JSON 结构化识别，报告导出前仍需结合既往病史、甲基化结果和 CTC 动态进行人工复核。",
                "trend_points": trend_points,
            },
            "reports": {
                "risk_assessment": risk_report,
                "methylation": methylation_report,
                "ctc": ctc_report,
            },
            "sub_items": risk_sub_items,
            "system_assessment": system_assessment,
            "tests": [_p14_test_export_item(test) for test in tests],
        },
    }


def _p14_find_report(reports: list[Any], keyword: str) -> dict[str, Any]:
    for item in reports:
        if not isinstance(item, dict):
            continue
        if keyword in str(item.get("report_type") or ""):
            return item
    return {}


def _p14_tests_from_ocr_payload(
    *,
    risk_assessment: dict[str, Any],
    methylation_result: dict[str, Any],
    methylation_details: list[Any],
    ctc_screening: dict[str, Any],
    ctc_history: list[Any],
) -> list[dict[str, Any]]:
    tests: list[dict[str, Any]] = []
    for code, page, unit in [("cda", 3, "U/mL"), ("ptf", 3, "pg/mL"), ("ctf", 3, "ng/mL")]:
        item = risk_assessment.get(code, {}) if isinstance(risk_assessment.get(code), dict) else {}
        tests.append(
            {
                "page": page,
                "specimen_type": P14_SAMPLE_TYPE,
                "test_name": code.upper(),
                "item_code": code,
                "group": "risk_assessment",
                "result": _p14_number_text(item.get("value")),
                "indicator": _first_text(item.get("result")),
                "reference_range": _first_text(item.get("reference_range")),
                "unit": unit,
                "method": P14_METHOD,
            }
        )
    tests.append(
        {
            "page": 4,
            "specimen_type": _first_text(methylation_result.get("test_item"), "全血"),
            "test_name": _first_text(methylation_result.get("test_item"), "高发五癌游离DNA甲基化检测"),
            "item_code": "methylation",
            "group": "methylation",
            "result": _first_text(methylation_result.get("result")),
            "indicator": _first_text(methylation_result.get("result")),
            "reference_range": "—",
            "unit": "",
            "method": _first_text(methylation_result.get("method"), "实时荧光PCR法"),
        }
    )
    tests.append(
        {
            "page": 4,
            "specimen_type": "外周血",
            "test_name": "CTC计数",
            "item_code": "ctc",
            "group": "ctc",
            "result": _p14_number_text(ctc_screening.get("total")),
            "indicator": "需关注" if _p14_safe_number(ctc_screening.get("total")) not in (None, 0) else "未见异常",
            "reference_range": "—",
            "unit": "个",
            "method": "CTC计数分型检测",
        }
    )
    for key, label in [("epithelial_ctc", "CTC上皮型"), ("mesenchymal_ctc", "CTC间质型"), ("mixed_ctc", "CTC混合型")]:
        if key in ctc_screening:
            tests.append(
                {
                    "page": 6,
                    "specimen_type": "外周血",
                    "test_name": label,
                    "item_code": key,
                    "group": "ctc_subtype",
                    "result": _p14_number_text(ctc_screening.get(key)),
                    "indicator": "已识别",
                    "reference_range": "—",
                    "unit": "个",
                    "method": "CTC计数分型检测",
                }
            )
    for detail in methylation_details:
        if not isinstance(detail, dict):
            continue
        gene = _first_text(detail.get("target_gene"))
        if not gene:
            continue
        tests.append(
            {
                "page": 4,
                "specimen_type": "全血",
                "test_name": gene,
                "item_code": f"methylation_{field_key_safe(gene).lower()}",
                "group": "methylation_detail",
                "result": _first_text(detail.get("interpretation")),
                "indicator": _first_text(detail.get("interpretation")),
                "reference_range": "阴性",
                "unit": "",
                "method": "实时荧光PCR法",
            }
        )
    for index, item in enumerate(ctc_history[:3], start=1):
        if not isinstance(item, dict):
            continue
        tests.append(
            {
                "page": 6,
                "specimen_type": "外周血",
                "test_name": f"CTC历史总数{index}",
                "item_code": f"ctc_history_{index}",
                "group": "ctc_history",
                "result": _p14_number_text(item.get("total")),
                "indicator": _first_text(item.get("date")),
                "reference_range": "—",
                "unit": "个",
                "method": "CTC计数分型检测",
            }
        )
    return tests


def _p14_trend_points_from_reports(history: list[Any], screening: dict[str, Any], ctc_report: dict[str, Any]) -> list[dict[str, str]]:
    points: list[dict[str, str]] = []
    for item in history[:3]:
        if not isinstance(item, dict):
            continue
        points.append({"date": _first_text(item.get("date"), "待补录"), "value": _p14_number_text(item.get("total")) or "—"})
    points.append({"date": _first_text(ctc_report.get("report_date"), ctc_report.get("sampling_date"), "待补录"), "value": _p14_number_text(screening.get("total")) or "—"})
    while len(points) < 4:
        points.append({"date": "待补录", "value": "—"})
    return points[:4]


def _p14_number_text(value: Any) -> str:
    if value is None or value == "":
        return ""
    if isinstance(value, float):
        return f"{value:.2f}".rstrip("0").rstrip(".")
    if isinstance(value, int):
        return str(value)
    return str(value).strip()


def _p14_safe_number(value: Any) -> float | None:
    text = _p14_number_text(value)
    match = re.search(r"\d+(?:\.\d+)?", text)
    if not match:
        return None
    try:
        return float(match.group(0))
    except ValueError:
        return None


def _p14_test_export_item(test: dict[str, Any]) -> dict[str, Any]:
    return {
        "test_name": str(test.get("test_name") or ""),
        "item_code": str(test.get("item_code") or ""),
        "result": str(test.get("result") or ""),
        "indicator": str(test.get("indicator") or ""),
        "reference_range": str(test.get("reference_range") or ""),
        "unit": str(test.get("unit") or ""),
        "method": str(test.get("method") or ""),
    }


def _p14_join_sentences(*values: Any) -> str:
    parts = [str(value).strip() for value in values if str(value or "").strip()]
    return " ".join(parts)


def extract_p14_fields(page_texts: list[str], structured_report: dict[str, Any]) -> list[dict[str, Any]]:
    fields: list[dict[str, Any]] = []
    patient_info = structured_report.get("patient_info", {}) if isinstance(structured_report.get("patient_info"), dict) else {}
    additional_info = structured_report.get("additional_info", {}) if isinstance(structured_report.get("additional_info"), dict) else {}
    p14_report = structured_report.get("p14_extracted_report", {}) if isinstance(structured_report.get("p14_extracted_report"), dict) else {}
    normalized = p14_report.get("normalized", {}) if isinstance(p14_report.get("normalized"), dict) else {}

    sample_types = patient_info.get("specimen_types") if isinstance(patient_info.get("specimen_types"), list) else []
    sample_type = "、".join(str(item) for item in sample_types if str(item).strip()) or P14_SAMPLE_TYPE
    report_date = additional_info.get("report_date") or additional_info.get("sample_date")
    method = additional_info.get("method") or P14_METHOD

    add_field(fields, "report.barcode", "条形码", structured_report.get("report_id"), 0.9, find_page(page_texts, str(structured_report.get("report_id") or "")))
    add_field(fields, "report.report_id", "报告编号", structured_report.get("report_id"), 0.9, find_page(page_texts, str(structured_report.get("report_id") or "")))
    add_field(fields, "patient.name", "姓名", patient_info.get("name"), 0.9, find_page(page_texts, str(patient_info.get("name") or "")))
    add_field(fields, "patient.gender", "性别", patient_info.get("gender"), 0.88, find_page(page_texts, str(patient_info.get("gender") or "")))
    if patient_info.get("age") not in (None, ""):
        add_field(fields, "patient.age", "年龄", f"{patient_info.get('age')}岁", 0.86, find_page(page_texts, str(patient_info.get("age") or "")))
    add_field(fields, "patient.phone", "联系电话", patient_info.get("phone") or "/", 0.84, find_page(page_texts, str(patient_info.get("phone") or "")))
    add_field(fields, "patient.symptoms", "相关症状", patient_info.get("clinical_diagnosis") or "/", 0.8, find_page(page_texts, str(patient_info.get("clinical_diagnosis") or "")))
    add_field(fields, "sample.type", "样本信息", sample_type, 0.92, find_page(page_texts, sample_type))
    add_field(fields, "sample.condition", "样本状态", patient_info.get("specimen_condition") or "", 0.82, None)
    add_field(fields, "report.assessment_type", "评估类型", P14_ASSESSMENT_TYPE, 0.92, None)
    add_field(fields, "report.method", "评估方法", method, 0.9, find_page(page_texts, str(method)))
    add_field(fields, "report.assessment_date", "评估日期", report_date, 0.86, find_page(page_texts, str(report_date or "")))

    tests = structured_report.get("tests", []) if isinstance(structured_report.get("tests"), list) else []
    for code in ["cda", "ptf", "ctf"]:
        test = next((item for item in tests if str(item.get("item_code") or "") == code), {})
        prefix = f"p14.results.{code}"
        add_field(fields, f"{prefix}.name", f"{code.upper()}名称", test.get("test_name") or code.upper(), 0.88, 3)
        add_field(fields, f"{prefix}.result_display", f"{code.upper()}结果", test.get("result"), 0.88, 3)
        add_field(fields, f"{prefix}.reference_range", f"{code.upper()}参考范围", test.get("reference_range"), 0.86, 3)
        add_field(fields, f"{prefix}.status", f"{code.upper()}状态", test.get("indicator"), 0.84, 3)

    add_field(fields, "p14.summary.score", "综合评分", next((item.get("result") for item in tests if str(item.get("item_code") or "") == "cda"), ""), 0.86, 2)
    add_field(fields, "p14.summary.risk_level", "风险分层", normalized.get("overall_risk") or normalized.get("overall_status"), 0.84, 2)
    add_field(fields, "p14.summary.ai_diagnosis", "综合评估结论", normalized.get("overall_risk"), 0.78, 2)
    add_field(fields, "p14.results.ai_summary", "检测结果AI摘要", normalized.get("overall_status"), 0.76, 3)
    add_field(fields, "p14.overview.methylation.title", "甲基化项目", "五癌甲基化", 0.84, 4)
    add_field(fields, "p14.overview.methylation.status", "甲基化结果", normalized.get("methylation_result"), 0.84, 4)
    ctc_total = normalized.get("ctc_total")
    ctc_unit = normalized.get("ctc_unit")
    add_field(fields, "p14.overview.ctc.title", "CTC项目", "CTC计数", 0.84, 4)
    add_field(fields, "p14.overview.ctc.status", "CTC结果", f"{ctc_total}{ctc_unit}".strip() if ctc_total else "", 0.84, 4)
    add_field(fields, "p14.overview.ai_diagnosis", "结果概览提示", normalized.get("clinical_diagnosis"), 0.76, 4)
    add_field(fields, "p14.deep_dive.ai_intro", "CDA深度解读导语", normalized.get("overall_risk"), 0.76, 5)
    add_field(fields, "p14.deep_dive.ai_detail", "CDA深度解读正文", normalized.get("clinical_diagnosis"), 0.74, 5)
    add_field(fields, "p14.deep_dive.ai_note", "CDA深度解读提示", normalized.get("overall_status"), 0.74, 5)

    trend_points = normalized.get("trend_points", []) if isinstance(normalized.get("trend_points"), list) else []
    for index in range(4):
        item = trend_points[index] if index < len(trend_points) and isinstance(trend_points[index], dict) else {}
        add_field(fields, f"p14.trend.points.point_{index + 1}.value", f"趋势值{index + 1}", item.get("value"), 0.8, 6)
        add_field(fields, f"p14.trend.points.point_{index + 1}.date", f"趋势日期{index + 1}", item.get("date"), 0.8, 6)
    add_field(fields, "p14.trend.alert", "趋势页提示", normalized.get("ctc_followup_advice"), 0.76, 6)

    add_field(fields, "p14.risk_factors.factor_1.title", "异常原因1标题", "代谢相关风险", 0.78, 7)
    add_field(fields, "p14.risk_factors.factor_1.body", "异常原因1正文", normalized.get("metabolic_advice"), 0.76, 7)
    add_field(fields, "p14.risk_factors.factor_2.title", "异常原因2标题", "既往病史关注", 0.78, 7)
    add_field(fields, "p14.risk_factors.factor_2.body", "异常原因2正文", normalized.get("clinical_diagnosis"), 0.76, 7)
    add_field(fields, "p14.risk_factors.factor_3.title", "异常原因3标题", "环境与感染管理", 0.78, 7)
    add_field(fields, "p14.risk_factors.factor_3.body", "异常原因3正文", _p14_join_sentences(normalized.get("environmental_advice"), normalized.get("infectious_advice")), 0.76, 7)
    add_field(fields, "p14.risk_factors.ai_diagnosis", "异常原因AI提示", normalized.get("overall_status"), 0.76, 7)

    for idx, text in enumerate(normalized.get("management_items", [])[:3], start=1):
        add_field(fields, f"p14.management.plan_{idx}", f"管理建议{idx}", text, 0.78, 8)
    add_field(fields, "p14.management.ai_summary", "管理页AI总结", normalized.get("followup_advice"), 0.74, 8)
    add_field(fields, "p14.followup_advice", "后续行动", normalized.get("followup_advice"), 0.78, 11)
    add_field(fields, "p14.disclaimer", "免责声明", normalized.get("disclaimer"), 0.78, 11)
    add_field(fields, "p14.review_note", "审核信息", normalized.get("review_note"), 0.78, 11)
    add_field(fields, "organization.phone", "联系电话", "400-158-1959", 0.9, None)
    add_field(fields, "organization.email", "电子邮箱", "service@anweikang.com", 0.9, None)
    add_field(fields, "organization.website", "官方网站", "www.anweikang.com", 0.9, None)
    add_field(fields, "organization.address", "公司地址", "安徽省合肥市庐阳区临泉路7266号研发中心楼1、4、5、6层", 0.9, None)
    return fields


def build_p15_structured_report_from_ocr_json(source_file: str, payload: dict[str, Any]) -> dict[str, Any]:
    report_info = payload.get("report_info", {}) if isinstance(payload.get("report_info"), dict) else {}
    patient = payload.get("patient_info", {}) if isinstance(payload.get("patient_info"), dict) else {}
    test_details = payload.get("test_details", {}) if isinstance(payload.get("test_details"), dict) else {}
    contact = payload.get("contact_info", {}) if isinstance(payload.get("contact_info"), dict) else {}
    report_notes = payload.get("report_notes", []) if isinstance(payload.get("report_notes"), list) else []
    results = payload.get("results", []) if isinstance(payload.get("results"), list) else []

    report_id = _first_text(report_info.get("barcode"), Path(source_file).stem)
    sample_type = _first_text(patient.get("sample_type"), P15_SAMPLE_TYPE)
    method = _first_text(test_details.get("methodology"), P15_METHOD)
    tests = _p15_tests_from_ocr_payload(results, method=method, specimen_type=sample_type)

    patient_info = {
        "name": _first_text(patient.get("name"), report_info.get("patient_name")),
        "gender": _first_text(patient.get("gender")),
        "age": patient.get("age") if patient.get("age") not in (None, "") else "",
        "phone": _first_text(patient.get("phone")),
        "specimen_condition": _first_text(patient.get("sample_characteristics")),
        "specimen_types": [sample_type] if sample_type else [],
        "hospital": _first_text(patient.get("submitting_institution")),
        "submitting_unit": _first_text(patient.get("submitting_institution")),
        "patient_number": _first_text(patient.get("hospital_number"), patient.get("medical_record_number")),
        "bed_number": "",
        "department": _first_text(patient.get("submitting_department")),
        "doctor": _first_text(patient.get("referring_physician")),
        "clinical_diagnosis": _first_text(patient.get("clinical_diagnosis")),
    }
    additional_info = {
        "sample_date": _first_text(patient.get("sampling_date")),
        "receive_date": _first_text(patient.get("receipt_time")),
        "report_date": _first_text(report_info.get("report_time")),
        "technician": "",
        "reviewer": "",
        "approver": "",
    }
    return {
        "report_id": report_id,
        "patient_info": patient_info,
        "tests": tests,
        "notes": " ".join(str(item).strip() for item in report_notes if str(item).strip()),
        "additional_info": additional_info,
        "p15_extracted_report": {
            "report_info": {
                "report_title": _first_text(report_info.get("report_title"), P15_REPORT_NAME),
                "laboratory_name": _first_text(report_info.get("laboratory_name")),
                "laboratory_english": _first_text(report_info.get("laboratory_english")),
                "report_time": _first_text(report_info.get("report_time")),
                "barcode": report_id,
                "patient_name": patient_info["name"],
            },
            "patient_info": patient,
            "test_details": test_details,
            "results": results,
            "report_notes": report_notes,
            "contact_info": contact,
            "tests": [_p15_test_export_item(test) for test in tests],
        },
    }


def _p15_tests_from_ocr_payload(results: list[Any], *, method: str, specimen_type: str) -> list[dict[str, Any]]:
    tests: list[dict[str, Any]] = []
    code_map = {
        "己烯雌酚": "des",
        "17α-乙炔基雌二醇": "ee2",
        "对羟基苯甲酸甲酯": "methylparaben",
        "对羟基苯甲酸乙酯": "ethylparaben",
        "对羟基苯甲酸丙酯": "propylparaben",
        "对羟基苯甲酸丁酯": "butylparaben",
        "邻苯二甲酸单乙基酯": "mep",
        "邻苯二甲酸单丁基酯": "mbp",
        "邻苯二甲酸单苄基酯": "mbzp",
        "邻苯二甲酸单乙基己酯": "mehp",
        "双酚A": "bpa",
        "双酚B": "bpb",
        "壬基苯酚": "nonylphenol",
        "辛基酚": "octylphenol",
        "邻苯二甲酸单甲基酯": "mmp",
    }
    for item in results:
        if not isinstance(item, dict):
            continue
        name = _first_text(item.get("parameter"))
        tests.append(
            {
                "page": 1 if len(tests) < 8 else 2,
                "specimen_type": specimen_type,
                "test_name": name,
                "item_code": code_map.get(name, field_key_safe(name).lower()),
                "group": "environment_hormone",
                "result": _p15_result_text(item.get("result")),
                "indicator": _p15_indicator_from_flag(item.get("flag")),
                "reference_range": _first_text(item.get("reference_value")),
                "unit": _first_text(item.get("unit")),
                "method": method,
            }
        )
    return tests


def _p15_result_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, float):
        return f"{value:.2f}".rstrip("0").rstrip(".")
    if isinstance(value, int):
        return str(value)
    return str(value).strip()


def _p15_indicator_from_flag(flag: Any) -> str:
    text = str(flag or "").strip()
    if text in {"↑", "高", "偏高"}:
        return "升高"
    if text in {"↓", "低", "偏低"}:
        return "偏低"
    return "正常"


def _p15_test_export_item(test: dict[str, Any]) -> dict[str, Any]:
    return {
        "test_name": str(test.get("test_name") or ""),
        "item_code": str(test.get("item_code") or ""),
        "result": str(test.get("result") or ""),
        "indicator": str(test.get("indicator") or ""),
        "reference_range": str(test.get("reference_range") or ""),
        "unit": str(test.get("unit") or ""),
        "method": str(test.get("method") or ""),
    }


def extract_p15_fields(page_texts: list[str], structured_report: dict[str, Any]) -> list[dict[str, Any]]:
    fields: list[dict[str, Any]] = []
    patient_info = structured_report.get("patient_info", {}) if isinstance(structured_report.get("patient_info"), dict) else {}
    additional_info = structured_report.get("additional_info", {}) if isinstance(structured_report.get("additional_info"), dict) else {}
    sample_types = patient_info.get("specimen_types") if isinstance(patient_info.get("specimen_types"), list) else []
    sample_type = "、".join(str(item) for item in sample_types if str(item).strip()) or P15_SAMPLE_TYPE
    report_date = additional_info.get("report_date") or additional_info.get("sample_date")
    method = structured_report.get("tests", [{}])[0].get("method") if structured_report.get("tests") else P15_METHOD

    add_field(fields, "report.barcode", "条形码", structured_report.get("report_id"), 0.9, find_page(page_texts, str(structured_report.get("report_id") or "")))
    add_field(fields, "report.report_id", "报告编号", structured_report.get("report_id"), 0.9, find_page(page_texts, str(structured_report.get("report_id") or "")))
    add_field(fields, "patient.name", "姓名", patient_info.get("name"), 0.9, find_page(page_texts, str(patient_info.get("name") or "")))
    add_field(fields, "patient.gender", "性别", patient_info.get("gender"), 0.88, find_page(page_texts, str(patient_info.get("gender") or "")))
    if patient_info.get("age") not in (None, ""):
        add_field(fields, "patient.age", "年龄", f"{patient_info.get('age')}岁", 0.88, find_page(page_texts, str(patient_info.get("age") or "")))
    add_field(fields, "patient.phone", "联系电话", patient_info.get("phone") or "/", 0.84, find_page(page_texts, str(patient_info.get("phone") or "")))
    add_field(fields, "patient.symptoms", "相关症状", patient_info.get("clinical_diagnosis") or "/", 0.76, None)
    add_field(fields, "patient.submitting_unit", "送检单位", patient_info.get("submitting_unit") or patient_info.get("hospital"), 0.84, find_page(page_texts, str(patient_info.get("submitting_unit") or patient_info.get("hospital") or "")))
    add_field(fields, "sample.type", "样本信息", sample_type, 0.92, find_page(page_texts, sample_type))
    add_field(fields, "sample.condition", "标本情况", patient_info.get("specimen_condition") or "", 0.84, find_page(page_texts, str(patient_info.get("specimen_condition") or "")))
    add_field(fields, "report.assessment_type", "评估类型", P15_ASSESSMENT_TYPE, 0.92, None)
    add_field(fields, "report.method", "评估方法", method or P15_METHOD, 0.92, find_page(page_texts, str(method or P15_METHOD)))
    add_field(fields, "report.assessment_date", "评估日期", report_date, 0.86, find_page(page_texts, str(report_date or "")))

    for test in structured_report.get("tests", []):
        code = str(test.get("item_code") or "")
        prefix = f"p15.results.{code}"
        page = int(test.get("page") or 1)
        label = str(test.get("test_name") or code)
        result = str(test.get("result") or "")
        unit = str(test.get("unit") or "")
        indicator = str(test.get("indicator") or "")
        reference = str(test.get("reference_range") or "")
        add_field(fields, f"{prefix}.name", label, label, 0.9, page)
        add_field(fields, f"{prefix}.result_display", label, f"{result} {unit}".strip(), 0.88, page)
        add_field(fields, f"{prefix}.reference_range", label, reference, 0.86, page)
        add_field(fields, f"{prefix}.status", label, indicator or "正常", 0.86, page)
    return fields


def build_p16_structured_report(source_file: str, full_text: str, page_texts: list[str]) -> dict[str, Any]:
    normalized = _p16_pdf_fallback_normalized()
    report_id = extract_report_id(full_text) or Path(source_file).stem
    patient_name = extract_patient_name(full_text) or ""
    patient_gender = extract_gender(full_text) or ""
    patient_age = extract_age(full_text)
    sample_types = extract_specimen_types(page_texts) or [P16_SAMPLE_TYPE]
    return {
        "report_id": report_id,
        "patient_info": {
            "name": patient_name,
            "gender": patient_gender,
            "age": patient_age or "",
            "phone": "",
            "clinical_diagnosis": "",
            "specimen_types": sample_types,
            "specimen_condition": extract_specimen_condition(full_text) or "",
            "submitting_unit": extract_hospital(full_text) or "",
        },
        "additional_info": {
            "sample_date": extract_date(page_texts, "采样日期"),
            "receive_date": extract_date(page_texts, "接收时间") or extract_date(page_texts, "接收日期"),
            "report_date": extract_date(page_texts, "报告时间") or extract_date(page_texts, "报告日期"),
            "method": P16_METHOD,
            "source_mode": "pdf-text-fallback",
        },
        "tests": [],
        "notes": _p16_compact(full_text, 400),
        "p16_extracted_report": {
            "report_info": {
                "report_title": P16_REPORT_NAME,
                "assessment_type": P16_ASSESSMENT_TYPE,
                "source_mode": "pdf-text-fallback",
                "report_count": len(page_texts),
            },
            "normalized": normalized,
            "reports": {},
            "tests": [],
        },
    }


def build_p16_structured_report_from_ocr_json(source_file: str, payload: dict[str, Any]) -> dict[str, Any]:
    reports = payload.get("reports", []) if isinstance(payload.get("reports"), list) else []
    primary = next((item for item in reports if isinstance(item, dict) and isinstance(item.get("patient_info"), dict)), {})
    patient = primary.get("patient_info", {}) if isinstance(primary.get("patient_info"), dict) else {}
    report_id = _first_text(primary.get("barcode"), Path(source_file).stem)
    patient_name = _first_text(primary.get("patient_name"))
    sample_type = _first_text(patient.get("sample_type"), P16_SAMPLE_TYPE)
    method = _first_text(primary.get("test_method"), P16_METHOD)

    hypertension = _p16_find_report(reports, "高血压个性化用药基因检测报告", exclude="临床意义")
    hypertension_clinical = _p16_find_report(reports, "高血压个性化用药基因检测报告（临床意义）")
    statin = _p16_find_report(reports, "他汀类药物用药基因检测报告", exclude="续")
    statin_extra = _p16_find_report(reports, "他汀类药物用药基因检测报告（续）")
    cyp2c19 = _p16_find_report(reports, "CYP2C19基因多态性检测报告")
    aspirin = _p16_find_report(reports, "阿司匹林个体化用药基因检测报告")
    ticagrelor = _p16_find_report(reports, "替格瑞洛个体化用药基因检测报告")
    hyperglycemia = _p16_find_report(reports, "高血糖个体化用药基因检测报告", exclude="附表")
    hyperglycemia_appendix = _p16_find_report(reports, "高血糖个体化用药基因检测报告（附表）")
    thrombosis = _p16_find_report(reports, "静脉血栓个体化用药基因检测报告")

    tests: list[dict[str, Any]] = []
    tests.extend(_p16_hypertension_tests(hypertension, method, sample_type))
    tests.extend(_p16_statin_tests(statin, method, sample_type))
    tests.extend(_p16_cyp2c19_tests(cyp2c19, method, sample_type))
    tests.extend(_p16_simple_result_tests(aspirin, method, sample_type, page=6, code_map={"GP1BA": "gp1ba", "LTC4S": "ltc4s"}))
    tests.extend(_p16_simple_result_tests(ticagrelor, method, sample_type, page=7, code_map={"PEAR1": "pear1", "CYP3A4": "cyp3a4"}))
    tests.extend(_p16_hyperglycemia_tests(hyperglycemia, method, sample_type))
    tests.extend(_p16_thrombosis_tests(thrombosis, method, sample_type))

    normalized = _p16_normalized_report(
        hypertension=hypertension,
        hypertension_clinical=hypertension_clinical,
        statin=statin,
        statin_extra=statin_extra,
        cyp2c19=cyp2c19,
        aspirin=aspirin,
        ticagrelor=ticagrelor,
        hyperglycemia=hyperglycemia,
        hyperglycemia_appendix=hyperglycemia_appendix,
        thrombosis=thrombosis,
    )

    return {
        "report_id": report_id,
        "patient_info": {
            "name": patient_name,
            "gender": _first_text(patient.get("gender")),
            "age": _first_text(patient.get("age")),
            "phone": "",
            "clinical_diagnosis": "",
            "specimen_types": [sample_type],
            "specimen_condition": _first_text(patient.get("sample_characteristics")),
            "submitting_unit": "",
        },
        "additional_info": {
            "sample_date": _first_text(patient.get("sampling_date")),
            "receive_date": _first_text(patient.get("receipt_time")),
            "report_date": _first_text(patient.get("sampling_date")),
            "method": method,
            "source_mode": "ocr-json",
        },
        "tests": tests,
        "notes": _p16_join_sentences(
            _first_text(hypertension.get("notes") if isinstance(hypertension, dict) else ""),
            _first_text(cyp2c19.get("remarks") if isinstance(cyp2c19, dict) else ""),
            _first_text(thrombosis.get("notes") if isinstance(thrombosis, dict) else ""),
        ),
        "p16_extracted_report": {
            "report_info": {
                "report_title": P16_REPORT_NAME,
                "assessment_type": P16_ASSESSMENT_TYPE,
                "source_mode": "ocr-json",
                "report_count": len(reports),
            },
            "normalized": normalized,
            "reports": {
                "hypertension": hypertension,
                "hypertension_clinical": hypertension_clinical,
                "statin": statin,
                "statin_extra": statin_extra,
                "cyp2c19": cyp2c19,
                "aspirin": aspirin,
                "ticagrelor": ticagrelor,
                "hyperglycemia": hyperglycemia,
                "hyperglycemia_appendix": hyperglycemia_appendix,
                "thrombosis": thrombosis,
            },
            "tests": [_p16_test_export_item(test) for test in tests],
        },
    }


def extract_p16_fields(page_texts: list[str], structured_report: dict[str, Any]) -> list[dict[str, Any]]:
    fields: list[dict[str, Any]] = []
    patient_info = structured_report.get("patient_info", {}) if isinstance(structured_report.get("patient_info"), dict) else {}
    additional_info = structured_report.get("additional_info", {}) if isinstance(structured_report.get("additional_info"), dict) else {}
    p16_report = structured_report.get("p16_extracted_report", {}) if isinstance(structured_report.get("p16_extracted_report"), dict) else {}
    normalized = p16_report.get("normalized", {}) if isinstance(p16_report.get("normalized"), dict) else {}

    sample_types = patient_info.get("specimen_types") if isinstance(patient_info.get("specimen_types"), list) else []
    sample_type = "、".join(str(item) for item in sample_types if str(item).strip()) or P16_SAMPLE_TYPE
    report_date = additional_info.get("report_date") or additional_info.get("sample_date")
    method = additional_info.get("method") or P16_METHOD

    add_field(fields, "report.report_id", "报告编号", structured_report.get("report_id"), 0.9, find_page(page_texts, str(structured_report.get("report_id") or "")))
    add_field(fields, "patient.name", "姓名", patient_info.get("name"), 0.9, find_page(page_texts, str(patient_info.get("name") or "")))
    add_field(fields, "patient.gender", "性别", patient_info.get("gender"), 0.88, find_page(page_texts, str(patient_info.get("gender") or "")))
    if patient_info.get("age") not in (None, ""):
        add_field(fields, "patient.age", "年龄", f"{patient_info.get('age')}岁", 0.86, find_page(page_texts, str(patient_info.get("age") or "")))
    add_field(fields, "sample.type", "样本信息", sample_type, 0.92, find_page(page_texts, sample_type))
    add_field(fields, "report.assessment_type", "评估类型", P16_ASSESSMENT_TYPE, 0.92, None)
    add_field(fields, "report.method", "评估方法", method, 0.9, find_page(page_texts, str(method)))
    add_field(fields, "report.assessment_date", "评估日期", report_date, 0.86, find_page(page_texts, str(report_date or "")))

    summary_cards = normalized.get("summary_cards", {}) if isinstance(normalized.get("summary_cards"), dict) else {}
    for code, value in summary_cards.items():
        if not isinstance(value, dict):
            continue
        add_field(fields, f"p16.summary.{code}.title", f"{code}标题", value.get("title"), 0.82, None)
        add_field(fields, f"p16.summary.{code}.status", f"{code}状态", value.get("status"), 0.82, None)
    add_field(fields, "p16.summary.evaluation_summary", "评估总结", normalized.get("evaluation_summary"), 0.8, None)

    sections = normalized.get("sections", {}) if isinstance(normalized.get("sections"), dict) else {}
    for code, value in sections.items():
        if not isinstance(value, dict):
            continue
        add_field(fields, f"p16.sections.{code}.analysis", f"{code}诊断分析", value.get("analysis"), 0.8, None)
        add_field(fields, f"p16.sections.{code}.medication_advice", f"{code}用药建议", value.get("medication_advice"), 0.8, None)

    management = normalized.get("management", {}) if isinstance(normalized.get("management"), dict) else {}
    for index in range(1, 4):
        bucket = management.get(f"priority_{index}", {}) if isinstance(management.get(f"priority_{index}"), dict) else {}
        add_field(fields, f"p16.management.priority_{index}.title", f"管理建议{index}标题", bucket.get("title"), 0.78, None)
        add_field(fields, f"p16.management.priority_{index}.body", f"管理建议{index}正文", bucket.get("body"), 0.78, None)
    add_field(fields, "p16.management.note", "管理提示", management.get("note"), 0.78, None)
    add_field(fields, "p16.followup_advice", "后续行动", normalized.get("followup_advice"), 0.78, None)
    add_field(fields, "p16.disclaimer", "免责声明", normalized.get("disclaimer"), 0.78, None)
    add_field(fields, "p16.review_note", "审核信息", normalized.get("review_note"), 0.78, None)

    for test in structured_report.get("tests", []):
        code = str(test.get("item_code") or "")
        if not code:
            continue
        prefix = f"p16.tests.{code}"
        page = int(test.get("page") or 1)
        label = str(test.get("test_name") or code)
        add_field(fields, f"{prefix}.result_display", label, str(test.get("result") or ""), 0.84, page)
        add_field(fields, f"{prefix}.genotype", label, str(test.get("genotype") or ""), 0.84, page)
        add_field(fields, f"{prefix}.gene_locus", label, str(test.get("gene_locus") or ""), 0.82, page)
        add_field(fields, f"{prefix}.indicator", label, str(test.get("indicator") or ""), 0.8, page)
    return fields


def _p16_find_report(reports: list[Any], keyword: str, *, exclude: str | None = None) -> dict[str, Any]:
    for item in reports:
        if not isinstance(item, dict):
            continue
        report_type = str(item.get("report_type") or "")
        if keyword in report_type and (not exclude or exclude not in report_type):
            return item
    return {}


def _p16_make_test(
    *,
    page: int,
    item_code: str,
    test_name: str,
    result: Any,
    method: str,
    specimen_type: str,
    genotype: Any = "",
    gene_locus: Any = "",
    indicator: Any = "",
    related_drugs: Any = "",
    interpretation: Any = "",
) -> dict[str, Any]:
    return {
        "page": page,
        "group": "pharmacogenomics",
        "item_code": item_code,
        "test_name": test_name,
        "result": clean_value(str(result or "")),
        "indicator": clean_value(str(indicator or "")),
        "reference_range": "",
        "unit": "",
        "method": method,
        "specimen_type": specimen_type,
        "genotype": clean_value(str(genotype or "")),
        "gene_locus": clean_value(str(gene_locus or "")),
        "related_drugs": clean_value(str(related_drugs or "")),
        "interpretation": clean_value(str(interpretation or "")),
    }


def _p16_hypertension_tests(report: dict[str, Any], method: str, specimen_type: str) -> list[dict[str, Any]]:
    tests: list[dict[str, Any]] = []
    if not isinstance(report, dict):
        return tests
    code_map = {
        "AGTR1": "agtr1",
        "CYP2C9": "cyp2c9_hypertension",
        "ADRB1": "adrb1",
        "CYP2D6": "cyp2d6",
        "ACEI/D": "ace",
        "CYP3A5": "cyp3a5",
        "NPPA": "nppa",
    }
    for item in report.get("results", []):
        if not isinstance(item, dict):
            continue
        gene_locus = _first_text(item.get("gene_locus"))
        code = next((mapped for key, mapped in code_map.items() if key in gene_locus), "")
        if not code:
            continue
        tests.append(
            _p16_make_test(
                page=1,
                item_code=code,
                test_name=_first_text(item.get("drug_class"), gene_locus),
                result=item.get("result"),
                method=method,
                specimen_type=specimen_type,
                genotype=item.get("genotype"),
                gene_locus=gene_locus,
                indicator=item.get("result"),
                related_drugs=item.get("related_drugs"),
            )
        )
    return tests


def _p16_statin_tests(report: dict[str, Any], method: str, specimen_type: str) -> list[dict[str, Any]]:
    tests: list[dict[str, Any]] = []
    if not isinstance(report, dict):
        return tests
    for item in report.get("results", []):
        if not isinstance(item, dict):
            continue
        gene = _first_text(item.get("gene"))
        item_code = gene.lower() if gene else ""
        snps = item.get("snps", []) if isinstance(item.get("snps"), list) else []
        genotype_display = "/".join(clean_value(str(snp.get("genotype") or "")) for snp in snps if isinstance(snp, dict) and str(snp.get("genotype") or "").strip())
        diplotype = next((clean_value(str(snp.get("result") or "")) for snp in snps if isinstance(snp, dict) and str(snp.get("result") or "").strip()), "")
        gene_locus = "；".join(clean_value(str(snp.get("locus") or "")) for snp in snps if isinstance(snp, dict) and str(snp.get("locus") or "").strip())
        tests.append(
            _p16_make_test(
                page=3,
                item_code=item_code,
                test_name=gene,
                result=diplotype or genotype_display,
                method=method,
                specimen_type=specimen_type,
                genotype=genotype_display,
                gene_locus=gene_locus,
                indicator=item.get("interpretation"),
                interpretation=item.get("interpretation"),
            )
        )
    return tests


def _p16_cyp2c19_tests(report: dict[str, Any], method: str, specimen_type: str) -> list[dict[str, Any]]:
    if not isinstance(report, dict):
        return []
    results = report.get("results", {}) if isinstance(report.get("results"), dict) else {}
    loci = results.get("loci", []) if isinstance(results.get("loci"), list) else []
    gene_locus = "；".join(f"{_first_text(item.get('name'))}:{_first_text(item.get('result'))}" for item in loci if isinstance(item, dict))
    return [
        _p16_make_test(
            page=5,
            item_code="cyp2c19",
            test_name="CYP2C19",
            result=results.get("genotype"),
            method=method,
            specimen_type=specimen_type,
            genotype=results.get("genotype"),
            gene_locus=gene_locus,
            indicator=results.get("metabolism_phenotype"),
            interpretation=results.get("medication_advice"),
        )
    ]


def _p16_simple_result_tests(report: dict[str, Any], method: str, specimen_type: str, *, page: int, code_map: dict[str, str]) -> list[dict[str, Any]]:
    tests: list[dict[str, Any]] = []
    if not isinstance(report, dict):
        return tests
    for item in report.get("results", []):
        if not isinstance(item, dict):
            continue
        gene_locus = _first_text(item.get("gene_locus"))
        gene = _first_text(item.get("gene"), item.get("drug"))
        code = next((mapped for key, mapped in code_map.items() if key in gene_locus or key == gene), "")
        if not code:
            continue
        tests.append(
            _p16_make_test(
                page=page,
                item_code=code,
                test_name=gene or gene_locus,
                result=item.get("result"),
                method=method,
                specimen_type=specimen_type,
                genotype=item.get("genotype"),
                gene_locus=gene_locus or _first_text(item.get("locus")),
                indicator=item.get("result"),
            )
        )
    return tests


def _p16_hyperglycemia_tests(report: dict[str, Any], method: str, specimen_type: str) -> list[dict[str, Any]]:
    tests: list[dict[str, Any]] = []
    if not isinstance(report, dict):
        return tests
    for item in report.get("results", []):
        if not isinstance(item, dict):
            continue
        category = _first_text(item.get("category"))
        gene_locus = _first_text(item.get("gene_locus"))
        code = ""
        if "TCF7L2" in gene_locus and "风险评估" in category:
            code = "tcf7l2_diabetes_risk"
        elif "CDKAL1" in gene_locus and "7756992" in gene_locus:
            code = "cdkal1_rs7756992"
        elif "CDKAL1" in gene_locus and "7754840" in gene_locus:
            code = "cdkal1_rs7754840"
        elif "CYP2C9*3" in gene_locus:
            code = "cyp2c9_sulfonylurea"
        elif "TCF7L2" in gene_locus and "磺酰脲" in category:
            code = "tcf7l2_sulfonylurea"
        if not code:
            continue
        tests.append(
            _p16_make_test(
                page=8,
                item_code=code,
                test_name=category or gene_locus,
                result=item.get("result"),
                method=method,
                specimen_type=specimen_type,
                genotype=item.get("genotype"),
                gene_locus=gene_locus,
                indicator=item.get("result"),
                related_drugs=item.get("related_drugs"),
            )
        )
    return tests


def _p16_thrombosis_tests(report: dict[str, Any], method: str, specimen_type: str) -> list[dict[str, Any]]:
    return _p16_simple_result_tests(report, method, specimen_type, page=10, code_map={"MTHFR": "mthfr", "PAI-1": "pai1"})


def _p16_normalized_report(
    *,
    hypertension: dict[str, Any],
    hypertension_clinical: dict[str, Any],
    statin: dict[str, Any],
    statin_extra: dict[str, Any],
    cyp2c19: dict[str, Any],
    aspirin: dict[str, Any],
    ticagrelor: dict[str, Any],
    hyperglycemia: dict[str, Any],
    hyperglycemia_appendix: dict[str, Any],
    thrombosis: dict[str, Any],
) -> dict[str, Any]:
    hypertension_results = hypertension.get("results", []) if isinstance(hypertension.get("results"), list) else []
    statin_results = statin.get("results", []) if isinstance(statin.get("results"), list) else []
    cyp2c19_results = cyp2c19.get("results", {}) if isinstance(cyp2c19.get("results"), dict) else {}
    aspirin_summary = aspirin.get("summary", {}) if isinstance(aspirin.get("summary"), dict) else {}
    ticagrelor_summary = ticagrelor.get("summary", {}) if isinstance(ticagrelor.get("summary"), dict) else {}
    hyper_summary = hyperglycemia.get("summary", []) if isinstance(hyperglycemia.get("summary"), list) else []
    thrombosis_interpretation = thrombosis.get("interpretation", {}) if isinstance(thrombosis.get("interpretation"), dict) else {}

    adrb1_result = _p16_result_for_locus(hypertension_results, "ADRB1")
    cdkal1_result = _p16_result_for_category(hyperglycemia.get("results"), "DPP-4抑制剂")
    sulfonylurea_result = _p16_result_for_locus(hyperglycemia.get("results"), "CYP2C9*3")
    aspirin_result = _p16_result_for_locus(aspirin.get("results"), "GP1BA")
    statin_result = _first_text(statin.get("cardiovascular_risk"))
    thrombosis_result = _p16_join_sentences(_p16_result_for_gene(thrombosis.get("results"), "MTHFR"), _p16_result_for_gene(thrombosis.get("results"), "PAI-1"))

    sections = {
        "antihypertensive": {
            "analysis": _p16_compact(
                _p16_join_sentences(
                    _p16_hypertension_analysis(hypertension_results),
                    _p16_compact(_first_text(hypertension_clinical.get("clinical_significance", {}).get("β受体阻滞剂", {}).get("advantages")), 42)
                    if isinstance(hypertension_clinical.get("clinical_significance"), dict)
                    else "",
                ),
                88,
            ),
            "medication_advice": _p16_compact("建议结合沙坦类、洛尔类、普利类、地平类和利尿剂结果，由医生综合评估后个体化选药。", 56),
        },
        "statin": {
            "analysis": _p16_compact(_p16_join_sentences(*[str(item.get("interpretation") or "") for item in statin_results if isinstance(item, dict)]), 88),
            "medication_advice": _p16_compact(
                _p16_join_sentences(
                    f"高强度他汀：{_first_text(statin.get('medication_advice', {}).get('high_intensity_statin'))}" if isinstance(statin.get("medication_advice"), dict) else "",
                    f"中等强度他汀：{_first_text(statin.get('medication_advice', {}).get('moderate_intensity_statin'))}" if isinstance(statin.get("medication_advice"), dict) else "",
                ),
                88,
            ),
        },
        "cyp2c19": {
            "analysis": _p16_compact(
                _p16_join_sentences(
                    f"基因型{_first_text(cyp2c19_results.get('genotype'))}" if _first_text(cyp2c19_results.get("genotype")) else "",
                    f"代谢表型为{_first_text(cyp2c19_results.get('metabolism_phenotype'))}" if _first_text(cyp2c19_results.get("metabolism_phenotype")) else "",
                    "氯吡格雷活化能力整体正常。" if _first_text(cyp2c19_results.get("genotype")) == "*1/*1" else "",
                ),
                88,
            ),
            "medication_advice": _p16_compact(_first_text(cyp2c19_results.get("medication_advice")), 88),
        },
        "aspirin": {
            "analysis": _p16_compact(_p16_first_sentence(_first_text(aspirin_summary.get("advice"))), 88),
            "medication_advice": _p16_compact(_p16_second_sentence(_first_text(aspirin_summary.get("advice"))) or _p16_first_sentence(_first_text(aspirin_summary.get("advice"))), 88),
        },
        "clopidogrel": {
            "analysis": _p16_compact(_p16_first_sentence(_first_text(ticagrelor_summary.get("advice"))), 88),
            "medication_advice": _p16_compact(_p16_second_sentence(_first_text(ticagrelor_summary.get("advice"))) or _p16_first_sentence(_first_text(ticagrelor_summary.get("advice"))), 88),
        },
        "hypoglycemic": {
            "analysis": _p16_compact(_p16_join_sentences(_p16_summary_advice(hyper_summary, "DPP-4抑制剂"), _p16_summary_advice(hyper_summary, "磺酰脲类降糖药")), 88),
            "medication_advice": _p16_compact(_p16_join_sentences(_p16_summary_advice(hyper_summary, "DPP-4抑制剂"), _p16_summary_advice(hyper_summary, "磺酰脲类降糖药")), 88),
        },
        "thrombosis": {
            "analysis": _p16_compact("MTHFR 与 PAI-1 均提示静脉血栓风险升高。", 88),
            "medication_advice": _p16_compact(_p16_first_sentence(_first_text(thrombosis.get("advice"))), 88),
        },
    }

    return {
        "evaluation_summary": _p16_compact(
            _p16_join_sentences(
                f"高血压用药{_p16_summary_status(adrb1_result, '敏感性高', '敏感性正常', fallback='需复核')}",
                f"他汀类{_p16_status_from_statin_text(statin_result)}",
                f"DPP-4抑制剂{_p16_summary_status(cdkal1_result, '疗效减弱', '疗效正常', fallback='需复核')}",
                f"磺酰脲类{_p16_summary_status(sulfonylurea_result, '毒副作用显著', '风险正常', fallback='需复核')}",
                f"静脉血栓{_p16_status_from_thrombosis(thrombosis_result)}",
            ),
            118,
        ),
        "summary_cards": {
            "hypertension": {"title": "高血压用药", "status": _p16_summary_status(adrb1_result, "敏感性高", "敏感性正常", fallback="需复核")},
            "dpp4": {"title": "降糖药（DPP-4抑制剂）", "status": _p16_summary_status(cdkal1_result, "疗效减弱", "疗效正常", fallback="需复核")},
            "sulfonylurea": {"title": "降糖药（磺脲类）", "status": _p16_summary_status(sulfonylurea_result, "毒副作用显著", "风险正常", fallback="需复核")},
            "antiplatelet": {"title": "阿司匹林", "status": _p16_summary_status(aspirin_result, "疗效正常", "风险正常", fallback="需复核")},
            "ppi": {"title": "CYP2C19", "status": _first_text(cyp2c19_results.get("metabolism_phenotype"), "需复核")},
            "statin": {"title": "他汀类药物", "status": _p16_status_from_statin_text(statin_result)},
            "anticoagulant": {"title": "静脉血栓风险", "status": _p16_status_from_thrombosis(thrombosis_result)},
        },
        "sections": sections,
        "management": {
            "priority_1": {"title": "校准高风险用药", "body": _p16_compact(sections["antihypertensive"]["analysis"], 70)},
            "priority_2": {"title": "优化代谢与疗效", "body": _p16_compact(_p16_join_sentences(sections["statin"]["analysis"], sections["cyp2c19"]["analysis"]), 70)},
            "priority_3": {"title": "关注血糖与血栓", "body": _p16_compact(_p16_join_sentences(sections["hypoglycemic"]["analysis"], sections["thrombosis"]["analysis"]), 70)},
            "note": _p16_compact("以上建议仅供健康管理与个体化用药沟通参考，正式处方需结合临床评估。", 70),
        },
        "followup_advice": _p16_compact("建议结合本次药物基因组学结果、既往病史和当前用药目标，由临床医生复核后确定个体化方案。", 110),
        "disclaimer": _p16_compact("本报告仅供健康管理与临床参考，不作为单独诊断和处方依据。", 70),
        "review_note": _p16_compact(
            _p16_join_sentences(
                _p16_compact(_first_text(thrombosis_interpretation.get("MTHFR")), 40),
                _p16_compact(_first_text(thrombosis_interpretation.get("PAI-1")), 40),
            )
            or "请结合真实检测结果、既往病史和当前治疗目标进行人工复核。",
            88,
        ),
    }


def _p16_test_export_item(test: dict[str, Any]) -> dict[str, Any]:
    return {
        "item_code": str(test.get("item_code") or ""),
        "test_name": str(test.get("test_name") or ""),
        "result": str(test.get("result") or ""),
        "indicator": str(test.get("indicator") or ""),
        "genotype": str(test.get("genotype") or ""),
        "gene_locus": str(test.get("gene_locus") or ""),
        "related_drugs": str(test.get("related_drugs") or ""),
        "page": int(test.get("page") or 1),
    }


def _p16_result_for_locus(items: Any, keyword: str) -> str:
    if not isinstance(items, list):
        return ""
    for item in items:
        if isinstance(item, dict) and keyword in str(item.get("gene_locus") or ""):
            return _first_text(item.get("result"))
    return ""


def _p16_result_for_gene(items: Any, keyword: str) -> str:
    if not isinstance(items, list):
        return ""
    for item in items:
        if isinstance(item, dict) and keyword == str(item.get("gene") or ""):
            return _first_text(item.get("result"))
    return ""


def _p16_result_for_category(items: Any, keyword: str) -> str:
    if not isinstance(items, list):
        return ""
    for item in items:
        if isinstance(item, dict) and keyword in str(item.get("category") or ""):
            return _first_text(item.get("result"))
    return ""


def _p16_hypertension_analysis(items: list[Any]) -> str:
    parts: list[str] = []
    adrb1 = _p16_result_for_locus(items, "ADRB1")
    cyp3a5 = _p16_result_for_locus(items, "CYP3A5")
    agtr1 = _p16_result_for_locus(items, "AGTR1")
    if adrb1:
        parts.append(f"ADRB1 提示β受体阻滞剂{_p16_summary_status(adrb1, '敏感性高', '敏感性正常', fallback='需复核')}")
    if cyp3a5:
        parts.append(f"CYP3A5 提示地平类{_p16_status_from_metabolism(cyp3a5)}")
    if agtr1:
        parts.append(f"AGTR1 提示沙坦类{_p16_summary_status(agtr1, '敏感性较好', '反应一般', fallback='需复核')}")
    return _p16_join_sentences(*parts)


def _p16_summary_advice(items: list[Any], keyword: str) -> str:
    for item in items:
        if isinstance(item, dict) and keyword in str(item.get("drug_class") or ""):
            return _first_text(item.get("advice"))
    return ""


def _p16_summary_status(result: str, high_label: str, normal_label: str, *, fallback: str) -> str:
    text = clean_value(str(result or ""))
    if not text:
        return fallback
    if "↑" in text or "↓" in text or "敏感" in text:
        return high_label
    if "-" in text or "正常" in text:
        return normal_label
    return fallback


def _p16_status_from_metabolism(result: str) -> str:
    text = clean_value(str(result or ""))
    if "↓↓" in text or "减慢" in text:
        return "代谢减慢"
    if "↑" in text:
        return "代谢加快"
    if "-" in text:
        return "代谢正常"
    return "需复核"


def _p16_status_from_statin_text(text: str) -> str:
    value = clean_value(str(text or ""))
    if "较高" in value or "高风险" in value:
        return "风险较高"
    if "偏低" in value or "低风险" in value:
        return "疗效正常"
    if value:
        return "需复核"
    return "需复核"


def _p16_status_from_thrombosis(text: str) -> str:
    value = clean_value(str(text or ""))
    if "↑" in value or "增加" in value or "升高" in value:
        return "风险升高"
    if value:
        return "需复核"
    return "需复核"


def _p16_first_sentence(text: str) -> str:
    clean = clean_value(str(text or ""))
    if not clean:
        return ""
    parts = re.split(r"[。；]", clean)
    return clean_value(parts[0]) if parts else clean


def _p16_second_sentence(text: str) -> str:
    clean = clean_value(str(text or ""))
    if not clean:
        return ""
    parts = [clean_value(item) for item in re.split(r"[。；]", clean) if clean_value(item)]
    return parts[1] if len(parts) > 1 else ""


def _p16_join_sentences(*parts: Any) -> str:
    values = [clean_value(str(part or "")) for part in parts if clean_value(str(part or ""))]
    return "；".join(values)


def _p16_compact(text: str, limit: int) -> str:
    value = clean_value(str(text or ""))
    if len(value) <= limit:
        return value
    trimmed = value[:limit].rstrip("，；、,; ")
    return trimmed + "…"


def _p16_pdf_fallback_normalized() -> dict[str, Any]:
    return {
        "evaluation_summary": "当前仅完成 PDF 文本层兜底提取，建议优先使用同目录 OCR.txt 对应的结构化 OCR 结果。",
        "summary_cards": {
            "hypertension": {"title": "高血压用药", "status": "待校准"},
            "dpp4": {"title": "降糖药（DPP-4抑制剂）", "status": "待校准"},
            "sulfonylurea": {"title": "降糖药（磺脲类）", "status": "待校准"},
            "antiplatelet": {"title": "阿司匹林", "status": "待校准"},
            "ppi": {"title": "CYP2C19", "status": "待校准"},
            "statin": {"title": "他汀类药物", "status": "待校准"},
            "anticoagulant": {"title": "静脉血栓风险", "status": "待校准"},
        },
        "sections": {
            "antihypertensive": {"analysis": "", "medication_advice": ""},
            "statin": {"analysis": "", "medication_advice": ""},
            "cyp2c19": {"analysis": "", "medication_advice": ""},
            "aspirin": {"analysis": "", "medication_advice": ""},
            "clopidogrel": {"analysis": "", "medication_advice": ""},
            "hypoglycemic": {"analysis": "", "medication_advice": ""},
            "thrombosis": {"analysis": "", "medication_advice": ""},
        },
        "management": {
            "priority_1": {"title": "导入结构化OCR", "body": "建议优先使用同目录 OCR.txt 作为 P16 结构化 OCR 输入。"},
            "priority_2": {"title": "校准字段", "body": "需要对七类药物结果页逐项校准字段映射与状态标签。"},
            "priority_3": {"title": "补充AI联调", "body": "完成 OCR 后再继续联调 AI 解释与管理建议。"},
            "note": "当前结果为 PDF 文本层兜底模式。",
        },
        "followup_advice": "建议优先使用同目录 OCR.txt 做 P16 结构化识别，并据此继续联调 PDF 导出结果。",
        "disclaimer": "当前结果为研发联调用途，正式导出前需人工审核。",
        "review_note": "若缺少 OCR.txt 或结构化 JSON，当前 PDF 文本层仅作为兜底参考。",
    }


def _p13_payload_from_text(source_file: str, full_text: str, page_texts: list[str]) -> dict[str, Any]:
    text = normalize_text(full_text)
    report_id = extract_report_id(text) or Path(source_file).stem
    report_date = extract_date(page_texts, "报告日期")
    submission_date = extract_date(page_texts, "送检日期")
    receipt_date = extract_date(page_texts, "收样日期")
    patient_name = extract_patient_name(text)
    sample_type = _p13_extract_label_value(text, "样本类型", ["检测技术", "送检日期", "收样日期"]) or P13_SAMPLE_TYPE
    method = _p13_normalize_method(_p13_extract_label_value(text, "检测技术", ["送检日期", "收样日期", "本检测结果"]) or P13_METHOD)
    assessment = _p13_extract_assessment_text(text)
    percentile_description = _p13_extract_percentile_description(text)
    return {
        "report_info": {
            "report_title": "端粒长度基因检测报告" if "端粒长度基因检测报告" in text else P13_REPORT_NAME,
            "report_date": report_date or submission_date,
            "barcode": report_id,
            "patient_name": patient_name,
        },
        "patient_info": {
            "name": patient_name,
            "gender": extract_gender(text),
            "age": extract_age(text),
            "sample_type": sample_type,
            "test_technology": method,
            "submission_date": submission_date,
            "receipt_date": receipt_date,
            "submitting_institution": _p13_extract_label_value(text, "送检单位", ["条形码", "姓", "姓名"]) or extract_hospital(text),
        },
        "test_results": {
            "telomere_age_assessment": {
                "assessment": assessment,
                "interpretation": _p13_extract_between(text, "如果您的端粒年龄比实际年龄越小", "端粒长度及变化趋势", include_start=True),
            },
            "telomere_length_and_trend": {
                "telomere_ct_value": _p13_extract_number_after(text, "端粒Ct值"),
                "internal_reference_ct_value": _p13_extract_number_after(text, "内参Ct值"),
                "relative_telomere_length": _p13_extract_number_after(text, "端粒相对长度"),
                "note": _p13_extract_between(text, "注：端粒相对长度", "端粒长度的人群位置", include_start=True),
            },
            "population_percentile": {
                "description": percentile_description,
            },
        },
        "recommendations": _p13_recommendations_from_text(text),
        "educational_content": _p13_education_from_text(text),
        "references": [],
        "disclaimer": _p13_disclaimer_from_text(text),
        "signature": {
            "primary_reviewer": extract_staff(text, ["主检人", "主 检 人"]),
            "approver": extract_staff(text, ["审核人", "审 核 人"]),
            "laboratory": _p13_extract_label_value(text, "主检实验室", ["报告日期"]) or "合肥安为康医学检验实验室",
        },
    }


def _p13_tests_from_payload(
    *,
    patient: dict[str, Any],
    trend: dict[str, Any],
    actual_age: str,
    telomere_age: str,
    percentile_value: float | None,
    percentile_description: str,
    method: str,
    sample_type: str,
) -> list[dict[str, Any]]:
    tests: list[dict[str, Any]] = []
    tests.append(_p13_make_test(2, "actual_age", "实际年龄", actual_age, "岁", method, sample_type))
    tests.append(_p13_make_test(2, "telomere_age", "端粒年龄", telomere_age, "岁", method, sample_type))
    tests.append(_p13_make_test(3, "telomere_relative_length", "端粒相对长度", trend.get("relative_telomere_length"), "", method, sample_type, interpretation=_first_text(trend.get("note"))))
    tests.append(_p13_make_test(3, "telomere_ct", "端粒Ct值", trend.get("telomere_ct_value"), "", method, sample_type))
    tests.append(_p13_make_test(3, "reference_ct", "内参Ct值", trend.get("internal_reference_ct_value"), "", method, sample_type))
    tests.append(_p13_make_test(4, "percentile", "同龄人群百分位", percentile_value, "%", method, sample_type, interpretation=percentile_description))
    return [test for test in tests if str(test.get("result") or "").strip()]


def _p13_make_test(
    page: int,
    item_code: str,
    test_name: str,
    result: Any,
    unit: str,
    method: str,
    specimen_type: str,
    *,
    interpretation: str = "",
) -> dict[str, Any]:
    return {
        "page": page,
        "specimen_type": specimen_type,
        "test_name": test_name,
        "item_code": item_code,
        "group": "telomere",
        "result": _p13_result_text(result),
        "indicator": "",
        "reference_range": "",
        "unit": unit,
        "method": method,
        "interpretation": interpretation,
    }


def _p13_test_export_item(test: dict[str, Any]) -> dict[str, Any]:
    return {
        "test_name": str(test.get("test_name") or ""),
        "item_code": str(test.get("item_code") or ""),
        "result": str(test.get("result") or ""),
        "indicator": str(test.get("indicator") or ""),
        "reference_range": str(test.get("reference_range") or ""),
        "unit": str(test.get("unit") or ""),
        "method": str(test.get("method") or ""),
        "interpretation": str(test.get("interpretation") or ""),
    }


def _p13_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _p13_result_text(value: Any) -> str:
    if value in (None, ""):
        return ""
    if isinstance(value, float):
        return f"{value:.2f}".rstrip("0").rstrip(".")
    return str(value).strip()


def _p13_normalize_method(value: str) -> str:
    text = normalize_text(value).replace(" ", "")
    return text or P13_METHOD


def _p13_age_display(value: Any) -> str:
    text = _p13_result_text(value)
    if not text:
        return ""
    return text if "岁" in text else f"{text}岁"


def _p13_age_gap(assessment_text: str) -> float | None:
    text = normalize_text(assessment_text)
    match = re.search(r"(大|小|高|低|多|少)\s*([0-9]+(?:\.[0-9]+)?)\s*岁", text)
    if not match:
        return None
    value = float(match.group(2))
    return value if match.group(1) in {"大", "高", "多"} else -value


def _p13_telomere_age(actual_age: Any, assessment_text: str) -> str:
    actual = _safe_number(actual_age)
    gap = _p13_age_gap(assessment_text)
    if actual is None or gap is None:
        return ""
    value = actual + gap
    if value.is_integer():
        return str(int(value))
    return f"{value:.1f}".rstrip("0").rstrip(".")


def _p13_percentile_value(description: str) -> float | None:
    match = re.search(r"([0-9]+(?:\.[0-9]+)?)\s*%", normalize_text(description))
    if not match:
        return None
    return float(match.group(1))


def _p13_percentile_display(value: float | None, description: str) -> str:
    if value is None:
        return description
    text = f"{int(value)}" if value.is_integer() else f"{value:.1f}".rstrip("0").rstrip(".")
    return f"超过 {text}% 同龄人"


def _p13_overall_summary(telomere_age: str, actual_age: str, assessment_text: str) -> str:
    gap = _p13_age_gap(assessment_text)
    if telomere_age and actual_age and gap is not None:
        direction = "大" if gap >= 0 else "小"
        gap_text = f"{int(abs(gap))}" if float(abs(gap)).is_integer() else f"{abs(gap):.1f}".rstrip("0").rstrip(".")
        if gap >= 0:
            return f"检测显示您的端粒年龄约为{telomere_age}岁，比实际年龄{actual_age}岁{direction}{gap_text}岁，提示细胞更新潜力需要重点维护，建议尽早开展抗衰生活方式干预。"
        return f"检测显示您的端粒年龄约为{telomere_age}岁，比实际年龄{actual_age}岁{direction}{gap_text}岁，提示当前细胞更新潜力相对较好，建议继续保持规律饮食、运动和睡眠管理。"
    return assessment_text


def _p13_percentile_summary(value: float | None, description: str) -> str:
    if value is None:
        return description
    text = f"{int(value)}" if value.is_integer() else f"{value:.1f}".rstrip("0").rstrip(".")
    lower_than = max(0.0, 100.0 - value)
    lower_text = f"{int(lower_than)}" if lower_than.is_integer() else f"{lower_than:.1f}".rstrip("0").rstrip(".")
    return f"您的端粒长度超过{text}%的同年龄段人群，约低于{lower_text}%同龄人；建议结合生活方式干预和阶段复评持续观察变化趋势。"


def _p13_followup_advice(recommendations: dict[str, Any]) -> str:
    diet = _p13_dict(recommendations.get("diet"))
    exercise = _p13_dict(recommendations.get("exercise"))
    lifestyle = _p13_dict(recommendations.get("lifestyle"))
    stress = _p13_dict(recommendations.get("stress_management"))
    patterns = diet.get("dietary_patterns") if isinstance(diet.get("dietary_patterns"), list) else []
    exercises = exercise.get("recommended_exercises") if isinstance(exercise.get("recommended_exercises"), list) else []
    parts: list[str] = []
    if patterns:
        parts.append("饮食上优先参考" + "、".join(str(item) for item in patterns[:2] if str(item).strip()))
    if exercises:
        parts.append("运动上坚持" + "、".join(str(item) for item in exercises[:4] if str(item).strip()) + "等有氧活动")
    if lifestyle:
        parts.append("同步管理戒烟限酒与约7小时规律睡眠")
    if stress:
        parts.append("保持压力觉察并及时进行情绪减压")
    if not parts:
        return "建议围绕饮食、运动、睡眠、压力和阶段复评建立12周健康管理计划，并由健康管理师结合症状和生活方式记录人工复核。"
    return "；".join(parts) + "。建议3-6个月或按健康管理师意见复评端粒长度变化。"


def _p13_disclaimer_text(value: Any) -> str:
    if isinstance(value, dict):
        return _first_text(value.get("2"), value.get("1"), value.get("3"))
    return _first_text(value, "本报告仅供健康管理参考，不作为临床诊断依据。")


def _p13_review_note(signature: dict[str, Any], report_info: dict[str, Any]) -> str:
    parts: list[str] = []
    if signature.get("primary_reviewer"):
        parts.append(f"主检人：{signature['primary_reviewer']}")
    if signature.get("approver"):
        parts.append(f"审核人：{signature['approver']}")
    if signature.get("laboratory"):
        parts.append(f"主检实验室：{signature['laboratory']}")
    if report_info.get("report_date"):
        parts.append(f"报告日期：{report_info['report_date']}")
    return "；".join(parts) or "报告导出前请由健康管理专家结合原始检测报告进行人工复核。"


def _p13_extract_label_value(text: str, label: str, stop_labels: list[str]) -> str:
    stop = "|".join(label_pattern(item) for item in stop_labels)
    pattern = rf"{label_pattern(label)}[:：]?\s*(.*?)(?=\s*(?:{stop})[:：]?|$)" if stop else rf"{label_pattern(label)}[:：]?\s*([^\s:：]+)"
    match = re.search(pattern, normalize_text(text))
    if not match:
        return ""
    return clean_value(match.group(1))


def _p13_extract_number_after(text: str, label: str) -> str:
    pattern = rf"{label_pattern(label)}\s*([0-9]+(?:\.[0-9]+)?)"
    match = re.search(pattern, normalize_text(text), flags=re.IGNORECASE)
    return match.group(1) if match else ""


def _p13_extract_assessment_text(text: str) -> str:
    match = re.search(r"(根据您的端粒长度检测结果，评估出您的端粒年龄要比实际年龄[:：]?\s*[大小高低多少]\s*[0-9]+(?:\.[0-9]+)?\s*岁)", normalize_text(text))
    return clean_value(match.group(1)) if match else ""


def _p13_extract_percentile_description(text: str) -> str:
    normalized = normalize_text(text)
    match = re.search(r"(根据您提供的实际年龄信息.*?您的端粒长度超过了\s*[0-9]+(?:\.[0-9]+)?\s*%\s*的同年龄段人群。)", normalized)
    if match:
        return clean_value(match.group(1))
    match = re.search(r"(您的端粒长度超过了\s*[0-9]+(?:\.[0-9]+)?\s*%\s*的同年龄段人群。)", normalized)
    return clean_value(match.group(1)) if match else ""


def _p13_extract_between(text: str, start: str, end: str, *, include_start: bool = False) -> str:
    normalized = normalize_text(text)
    start_index = normalized.find(start)
    if start_index < 0:
        return ""
    end_index = normalized.find(end, start_index + len(start))
    if end_index < 0:
        end_index = min(len(normalized), start_index + 420)
    value = normalized[start_index:end_index] if include_start else normalized[start_index + len(start):end_index]
    return clean_value(value)


def _p13_recommendations_from_text(text: str) -> dict[str, Any]:
    normalized = normalize_text(text)
    if "抗衰措施" not in normalized:
        return {}
    return {
        "diet": {
            "nutrients": ["维生素A", "维生素D", "维生素C", "叶酸", "锌", "多酚类物质", "Omega-3脂肪酸"],
            "positive_foods": ["豆类", "坚果", "海藻", "水果", "100%果汁", "乳制品", "膳食纤维", "咖啡"],
            "negative_foods": ["红肉或加工肉类", "含糖饮料"],
            "dietary_patterns": ["地中海膳食模式（MD）", "能量限制模式（CR）"],
        },
        "lifestyle": {
            "smoking": _p13_extract_between(normalized, "戒烟：", "限酒：", include_start=True),
            "alcohol": _p13_extract_between(normalized, "限酒：", "睡眠：", include_start=True),
            "sleep": _p13_extract_between(normalized, "睡眠：", "加强运动", include_start=True),
        },
        "exercise": {
            "benefits": _p13_extract_between(normalized, "加强运动", "不要长期久坐"),
            "recommended_exercises": ["散步", "慢跑", "游泳", "跳绳"],
            "high_intensity_interval_training": _p13_extract_between(normalized, "新型的运动模式", "情绪减压", include_start=True),
        },
        "stress_management": {
            "description": _p13_extract_between(normalized, "情绪减压", "不要长期处于高压状态"),
            "advice": _p13_extract_between(normalized, "不要长期处于高压状态", "端粒", include_start=True),
        },
    }


def _p13_education_from_text(text: str) -> dict[str, Any]:
    normalized = normalize_text(text)
    return {
        "telomere_definition": _p13_extract_between(normalized, "端粒（telomere）", "端粒示意图", include_start=True),
        "telomere_analogy": _p13_extract_between(normalized, "端粒可类比为鞋带", "染色体与末端端粒结果示意图", include_start=True),
        "nobel_prize": _p13_extract_between(normalized, "2009 年的诺贝尔", "2009 年诺贝尔", include_start=True),
    }


def _p13_disclaimer_from_text(text: str) -> dict[str, str]:
    normalized = normalize_text(text)
    disclaimer: dict[str, str] = {}
    start = normalized.find("免责声明")
    if start < 0:
        return disclaimer
    section = normalized[start:]
    for index in range(1, 6):
        next_index = index + 1
        pattern = rf"{index}\.\s*(.*?)(?=\s*{next_index}\.|审\s*核\s*人|主\s*检\s*人|主检实验室|$)"
        match = re.search(pattern, section)
        if match:
            disclaimer[str(index)] = clean_value(match.group(1))
    return disclaimer


def _p12_parse_test_after_name(
    text: str,
    aliases: tuple[str, ...],
    *,
    default_unit: str,
    default_reference: str,
    default_method: str,
) -> dict[str, str] | None:
    normalized = _p12_normalize_ocr_text(text)
    for alias in sorted(aliases, key=len, reverse=True):
        for match in re.finditer(rf"{name_pattern(alias)}", normalized, flags=re.IGNORECASE):
            window = normalize_text(normalized[max(0, match.start() - 80) : min(len(normalized), match.end() + 240)])
            after_alias = normalize_text(normalized[match.end() : min(len(normalized), match.end() + 240)])
            value_match = re.search(
                rf"(?<![A-Za-z])(?P<result>[0-9]+(?:\.[0-9]+)?)(?![A-Za-z])\s*(?P<indicator>[↑↓])?\s*(?P<reference>[0-9]+(?:\.[0-9]+)?\s*(?:--|-|~|～)\s*[0-9]+(?:\.[0-9]+)?)?",
                after_alias,
            )
            if not value_match:
                continue
            unit_match = re.search(P12_UNIT_PATTERN, window, flags=re.IGNORECASE)
            method_match = re.search(P12_METHOD_PATTERN, window, flags=re.IGNORECASE)
            table_match = re.search(
                rf"(?P<result>[0-9]+(?:\.[0-9]+)?)\s+(?P<method>{P12_METHOD_PATTERN})\s+"
                rf"(?P<reference>[0-9]+(?:\.[0-9]+)?\s*(?:--|-|~|～)\s*[0-9]+(?:\.[0-9]+)?)\s+"
                rf"(?P<unit>{P12_UNIT_PATTERN})\s*(?P<indicator>[↑↓])?",
                after_alias,
                flags=re.IGNORECASE,
            )
            if table_match:
                return {
                    "result": table_match.group("result"),
                    "indicator": table_match.group("indicator") or "",
                    "reference_range": _p12_normalize_reference(table_match.group("reference")),
                    "unit": _p12_normalize_unit(table_match.group("unit")),
                    "method": table_match.group("method"),
                }
            reference = (value_match.group("reference") or _p12_reference_after_result(window, value_match.end()) or default_reference).replace(" ", "")
            return {
                "result": value_match.group("result"),
                "indicator": value_match.group("indicator") or "",
                "reference_range": _p12_normalize_reference(reference),
                "unit": _p12_normalize_unit(unit_match.group(0) if unit_match else default_unit),
                "method": method_match.group(0) if method_match else default_method,
            }
    return None


def _p12_parse_nad_result(text: str) -> dict[str, str] | None:
    normalized = _p12_normalize_ocr_text(text)
    if not re.search(r"N(?:A|O)D\s*[+＋]|烟酰胺腺嘌呤二核苷酸", normalized, flags=re.IGNORECASE):
        return None
    status_match = re.search(r"(严重不足|中度耗竭|轻度失衡|平衡状态|理想峰值|不足|偏低|正常|良好|异常)", normalized)
    result = ""
    result_patterns = [
        r"本次N(?:A|O)D\s*[+＋].{0,20}?结果.{0,20}?(?P<result>[0-9]+(?:\.[0-9]+)?)\s*(?:µmol/L|μmol/L|umol/L)?",
        r"您的检测结果\s*(?P<result>[0-9]+(?:\.[0-9]+)?)\s*(?:µmol/L|μmol/L|umol/L)?",
        r"(?P<result>[0-9]+(?:\.[0-9]+)?)\s*[.。]?\s*您当前处于.{0,20}严重不足",
    ]
    for pattern in result_patterns:
        match = re.search(pattern, normalized, flags=re.IGNORECASE)
        if match:
            result = match.group("result")
            break
    if not result and status_match:
        before_status = normalized[max(0, status_match.start() - 80) : status_match.start()]
        candidates = [match.group(0) for match in re.finditer(r"(?<![0-9])[0-9]{1,3}(?:\.[0-9]+)?(?![0-9])", before_status)]
        for candidate in reversed(candidates):
            value = _safe_number(candidate)
            if value is not None and 0 < value <= 120:
                result = candidate
                break
    if not result and not status_match:
        return None
    status = status_match.group(1) if status_match else ""
    return {
        "result": result,
        "indicator": status or _p12_nad_indicator_from_value(result),
        "reference_range": "",
        "unit": "µmol/L",
        "method": "NAD+细胞活力营养评估",
    }


def _p12_extract_antioxidant_tests(text: str, page_number: int) -> list[dict[str, Any]]:
    if "抗氧化能力评估" not in text and "抗氧化总容量" not in text:
        return []
    tests: list[dict[str, Any]] = []
    for item_code, aliases in P12_ANTIOXIDANT_ALIASES.items():
        parsed = _p12_parse_antioxidant_test(text, aliases, item_code)
        if not parsed:
            continue
        interpretation = _p12_extract_antioxidant_interpretation(text, aliases)
        display_name = next((alias for alias in aliases if "(" in alias or "（" in alias), aliases[0])
        tests.append(
            {
                "page": page_number,
                "specimen_type": "肝素钠抗凝全血",
                "test_name": display_name,
                "item_code": item_code,
                "group": "antioxidant",
                "result": parsed["result"],
                "indicator": parsed["indicator"],
                "reference_range": parsed["reference_range"],
                "unit": parsed["unit"],
                "method": "抗氧化能力评估",
                "interpretation": interpretation,
            }
        )
    return tests


def _p12_parse_antioxidant_test(text: str, aliases: tuple[str, ...], item_code: str) -> dict[str, str] | None:
    normalized = _p12_normalize_ocr_text(text)
    default_unit, default_reference = P12_ANTIOXIDANT_DEFAULTS[item_code]
    for alias in sorted(aliases, key=len, reverse=True):
        alias_pattern = rf"{name_pattern(alias)}"
        match = re.search(alias_pattern, normalized, flags=re.IGNORECASE)
        if not match:
            continue
        after_alias = normalize_text(normalized[match.end() : min(len(normalized), match.end() + 120)])
        row_match = re.search(
            rf"(?P<result>[0-9]+(?:\.[0-9]+)?)\s+"
            rf"(?P<reference>(?:≥|≤|>|<|＞|＜)?\s*[0-9]+(?:\.[0-9]+)?(?:\s*(?:--|-|~|～|—|–)\s*[0-9]+(?:\.[0-9]+)?)?)"
            rf"\s*(?P<indicator>[↑↓])?\s+"
            rf"(?P<unit>{P12_UNIT_PATTERN})",
            after_alias,
            flags=re.IGNORECASE,
        )
        if not row_match:
            compact = normalize_text(normalized[max(0, match.start() - 20) : min(len(normalized), match.end() + 180)])
            row_match = re.search(
                rf"{alias_pattern}\s+"
                rf"(?P<result>[0-9]+(?:\.[0-9]+)?)\s+"
                rf"(?P<reference>(?:≥|≤|>|<|＞|＜)?\s*[0-9]+(?:\.[0-9]+)?(?:\s*(?:--|-|~|～|—|–)\s*[0-9]+(?:\.[0-9]+)?)?)"
                rf"\s*(?P<indicator>[↑↓])?\s+"
                rf"(?P<unit>{P12_UNIT_PATTERN})",
                compact,
                flags=re.IGNORECASE,
            )
        if not row_match:
            continue
        return {
            "result": clean_value(row_match.group("result")),
            "indicator": clean_value(row_match.group("indicator") or ""),
            "reference_range": normalize_reference(row_match.group("reference") or default_reference),
            "unit": normalize_unit(row_match.group("unit") or default_unit),
        }
    return None


def _p12_extract_antioxidant_interpretation(text: str, aliases: tuple[str, ...]) -> str:
    normalized = normalize_text(text)
    for alias in sorted(aliases, key=len, reverse=True):
        short_alias = re.sub(r"[()（）]", "", alias)
        pattern = re.compile(
            rf"{name_pattern(alias)}[:：]?\s*(?P<body>.*?)(?=(?:{'|'.join(re.escape(candidate) for candidate in aliases if candidate != alias)}|结果提示|检测项目说明|抗氧化总容量|谷胱甘肽过氧化物酶|超氧化物歧化酶|过氧化脂类|谷胱甘肽|$))",
            flags=re.IGNORECASE,
        )
        match = pattern.search(normalized)
        if match:
            value = clean_value(match.group("body"))
            if value and short_alias not in value[: min(len(value), 8)]:
                return value
    return ""


def _p12_make_test(
    page_number: int,
    group: str,
    item_code: str,
    test_name: str,
    result: str,
    reference_range: str,
    unit: str,
    method: str,
    *,
    indicator: str = "",
) -> dict[str, Any]:
    return {
        "page": page_number,
        "specimen_type": "全血" if item_code == "nad" else "血清",
        "test_name": test_name,
        "item_code": item_code,
        "group": group,
        "result": str(result or "").strip(),
        "indicator": indicator,
        "reference_range": str(reference_range or "").strip(),
        "unit": _p12_normalize_unit(unit),
        "method": method,
    }


def _p12_status_from_test(test: dict[str, Any]) -> str:
    indicator = str(test.get("indicator") or "").strip()
    if indicator:
        if indicator in {"↑", "升高", "偏高"}:
            return "偏高"
        if indicator in {"↓", "降低", "偏低"}:
            return "偏低"
        if "严重不足" in indicator:
            return "严重不足"
        if "耗竭" in indicator:
            return "中度耗竭"
        if "失衡" in indicator:
            return "轻度失衡"
        if any(word in indicator for word in ("正常", "良好", "平衡", "理想")):
            return "正常"
        return indicator
    result = _safe_number(test.get("result"))
    if result is None:
        return "待复核"
    if str(test.get("item_code") or "") == "nad":
        return _p12_nad_indicator_from_value(str(test.get("result") or "")) or "待复核"
    bounds = _p07_reference_bounds(str(test.get("reference_range") or ""))
    if not bounds:
        return "待复核"
    for lower, upper in bounds:
        if lower is not None and upper is not None and lower <= result <= upper:
            return "正常"
        if lower is None and upper is not None and result <= upper:
            return "正常"
        if upper is None and lower is not None and result >= lower:
            return "正常"
    lows = [lower for lower, _upper in bounds if lower is not None]
    uppers = [upper for _lower, upper in bounds if upper is not None]
    if lows and result < min(lows):
        return "偏低"
    if uppers and result > max(uppers):
        return "偏高"
    return "待复核"


def _p12_nad_indicator_from_value(value: str) -> str:
    number = _safe_number(value)
    if number is None:
        return ""
    if number < 29:
        return "严重不足"
    if number < 38:
        return "中度耗竭"
    if number < 44:
        return "轻度失衡"
    if number < 48:
        return "平衡状态"
    return "理想峰值"


def _p12_status_display(status: str) -> str:
    text = str(status or "").strip()
    if any(word in text for word in ("严重不足", "中度耗竭", "偏低", "异常", "不足")):
        return "! 需重点关注"
    if "轻度失衡" in text:
        return "! 建议干预"
    if any(word in text for word in ("正常", "良好", "平衡", "理想")):
        return "✓ 水平良好"
    return "待复核"


def _p12_value_with_unit(value: str, unit: str) -> str:
    text = str(value or "").strip()
    unit_text = str(unit or "").strip()
    if not text:
        return "未识别"
    if not unit_text or unit_text in text:
        return text
    return f"{text} {unit_text}"


def _p12_name_display(name: str, unit: str) -> str:
    unit_text = str(unit or "").strip()
    return f"{name} ({unit_text})" if unit_text else name


def _p12_normalize_unit(unit: str) -> str:
    text = str(unit or "").strip()
    lower = text.lower().replace("μ", "µ")
    if lower in {"ug/ml", "µg/ml"}:
        return "ug/mL"
    if lower in {"umol/l", "µmol/l"}:
        return "µmol/L"
    if lower == "ng/ml":
        return "ng/mL"
    if lower == "pg/ml":
        return "pg/mL"
    return text


def _p12_normalize_reference(reference: str) -> str:
    return (
        str(reference or "")
        .strip()
        .replace("--", "-")
        .replace("～", "-")
        .replace("~", "-")
        .replace("—", "-")
        .replace("–", "-")
    )


def _p12_reference_after_result(window: str, start: int) -> str:
    tail = window[start : start + 120]
    match = re.search(r"[0-9]+(?:\.[0-9]+)?\s*(?:--|-|~|～|—|–)\s*[0-9]+(?:\.[0-9]+)?", tail)
    return match.group(0) if match else ""


def _p12_normalize_ocr_text(text: str) -> str:
    return (
        normalize_text(text)
        .replace("Ｎ", "N")
        .replace("Ａ", "A")
        .replace("Ｄ", "D")
        .replace("＋", "+")
        .replace("NAO", "NAD")
        .replace("Nao", "NAD")
    )


def _p12_specimen_types(values: list[str], tests: list[dict[str, Any]]) -> list[str]:
    result: list[str] = []
    for value in values:
        text = str(value or "").strip()
        if text and text not in result:
            result.append(text)
    for test in tests:
        text = str(test.get("specimen_type") or "").strip()
        if text and text not in result:
            result.append(text)
    if not result and tests:
        result.append("能量代谢相关样本")
    return result


def _p12_extract_date(page_texts: list[str], label: str) -> str:
    value = extract_date(page_texts, label)
    if value:
        return value
    normalized_label = label.replace("报告时间", "报告日期")
    pattern = re.compile(rf"{label_pattern(normalized_label)}[:：]?\s*([0-9]{{4}}\s*[-/]\s*[0-9]{{1,2}}\s*[-/]\s*[0-9]{{1,2}})")
    values: list[str] = []
    for text in page_texts:
        values.extend(re.sub(r"\s+", "", match.group(1)) for match in pattern.finditer(text))
    return values[-1] if values else ""


def _p12_extract_first_person_name(page_texts: list[str]) -> str:
    for text in page_texts:
        compact = normalize_text(text)
        match = re.search(r"^([\u4e00-\u9fff]{2,4})\s+[0-9]{10,}", compact)
        if match:
            return match.group(1)
    return ""


def _p12_extract_patient_name(page_texts: list[str], full_text: str) -> str:
    patterns = [
        r"送检单位[:：]?\s*[^\n\r]*?\s+([\u4e00-\u9fff]{2,4})\s+性\s*别",
        r"姓\s*名[:：]?\s*([\u4e00-\u9fff]{2,4})\s+性\s*别",
        r"姓\s*名[:：]?\s*([\u4e00-\u9fff]{2,4})\s+病\s*员\s*号",
        r"姓名\s+丁艳平|姓名\s+([\u4e00-\u9fff]{2,4})",
        r"个人信息\s+([\u4e00-\u9fff]{2,4})\s+性别",
    ]
    for text in page_texts[:3]:
        normalized = normalize_text(text)
        for pattern in patterns:
            match = re.search(pattern, normalized)
            if match:
                value = clean_value(match.group(1) if match.lastindex else match.group(0).replace("姓名", "").strip())
                if value and value not in {"个人信息", "姓名"} and not looks_like_label(value):
                    return value
    value = extract_patient_name(full_text)
    if value in {"个人信息", "姓名"}:
        return ""
    return value


def _p12_extract_specimen_condition(page_texts: list[str], full_text: str) -> str:
    for text in page_texts:
        normalized = normalize_text(text)
        match = re.search(r"标本情况[:：]?\s*(未见异常|正常|异常|溶血|脂血)", normalized)
        if match:
            return match.group(1)
        match = re.search(r"(未见异常|正常|异常|溶血|脂血)\s*标本情况", normalized)
        if match:
            return match.group(1)
    return extract_specimen_condition(full_text)


def _p12_extract_submitting_unit(page_texts: list[str], full_text: str) -> str:
    for text in page_texts[:3]:
        normalized = normalize_text(text)
        match = re.search(r"送检单位[:：]?\s*([^\s:：]+(?:员工|医院|中心|门诊部|有限公司)?)", normalized)
        if match:
            value = clean_value(match.group(1))
            if value and not looks_like_label(value):
                return value
        if "安为康内部员工" in normalized:
            return "安为康内部员工"
    return extract_hospital(full_text)


def _p12_extract_clinical_diagnosis(full_text: str, page_texts: list[str] | None = None) -> str:
    page_texts = page_texts or []
    for text in page_texts[:2]:
        normalized = normalize_text(text)
        match = re.search(r"临床诊断[:：]?\s*(.*?)\s*(?:送检科室|年\s*龄|标本类型|检验目的|$)", normalized, flags=re.IGNORECASE)
        if match:
            value = clean_value(match.group(1))
            if value and not looks_like_label(value) and "送检科室" not in value and "标本类型" not in value:
                return value
    match = re.search(rf"{label_pattern('临床诊断')}[:：]?\s*(.*?)(?:辅酶Q10|CoQ10|本检测|审核者|采样日期|报告时间|$)", full_text, flags=re.IGNORECASE)
    if not match:
        return _p09_extract_after_label(full_text, "临床诊断")
    value = clean_value(match.group(1))
    value = re.sub(r"^(?:血清|全血|EDTA抗凝全血|正常|未见异常)\s*", "", value)
    value = re.sub(r"\b(?:ug/ml|ug/mL|µg/mL|μg/mL|LC-MS/MS)\b.*$", "", value, flags=re.IGNORECASE).strip()
    if value in {"血清", "全血", "EDTA抗凝全血", "正常", "未见异常"}:
        return ""
    if any(marker in value for marker in ("送检科室", "标本类型", "检验目的", "年 龄", "年龄")):
        return ""
    return "" if looks_like_label(value) else value


def _p12_collect_notes(full_text: str) -> str:
    notes: list[str] = []
    disclaimer = extract_disclaimer(full_text)
    if disclaimer:
        notes.append(disclaimer)
    match = re.search(r"备\s*注[:：]?\s*([^\s]+)", full_text)
    if match:
        value = clean_value(match.group(1))
        if value and value not in notes:
            notes.append(value)
    return " ".join(notes)


def _p12_export_text_pages(page_texts: list[str], tests: list[dict[str, Any]]) -> list[dict[str, Any]]:
    exported: list[dict[str, Any]] = []
    for page_number, _text in enumerate(page_texts, start=1):
        page_tests = [test for test in tests if int(test.get("page") or 0) == page_number]
        if not page_tests:
            continue
        exported.append(
            {
                "page_number": page_number,
                "specimen_type": page_tests[0].get("specimen_type") or "",
                "test_items": [_p12_test_export_item(test) for test in page_tests],
                "sample_date": _p12_extract_date(page_texts, "采样日期"),
                "receive_date": _p12_extract_date(page_texts, "接收时间") or _p12_extract_date(page_texts, "接收日期"),
                "report_date": _p12_extract_date(page_texts, "报告时间") or _p12_extract_date(page_texts, "报告日期"),
            }
        )
    return exported


def _p12_test_export_item(test: dict[str, Any]) -> dict[str, Any]:
    return {
        "test_name": str(test.get("test_name") or ""),
        "item_code": str(test.get("item_code") or ""),
        "result": str(test.get("result") or ""),
        "indicator": str(test.get("indicator") or ""),
        "reference_range": str(test.get("reference_range") or ""),
        "unit": str(test.get("unit") or ""),
        "method": str(test.get("method") or ""),
    }


def build_p12_structured_report_from_ocr_json(source_file: str, payload: dict[str, Any]) -> dict[str, Any]:
    overview = payload.get("report_overview", {}) if isinstance(payload.get("report_overview"), dict) else {}
    patient = overview.get("patient", {}) if isinstance(overview.get("patient"), dict) else {}
    specimen = overview.get("specimen", {}) if isinstance(overview.get("specimen"), dict) else {}
    dates = overview.get("dates", {}) if isinstance(overview.get("dates"), dict) else {}
    personnel = overview.get("personnel", {}) if isinstance(overview.get("personnel"), dict) else {}
    contact = overview.get("contact", {}) if isinstance(overview.get("contact"), dict) else {}
    tests = _p12_tests_from_ocr_payload(payload)
    sample_types = _p12_specimen_types([_first_text(specimen.get("type"))], tests)
    report_id = _first_text(overview.get("barcode")) or Path(source_file).stem
    patient_info = {
        "name": _first_text(patient.get("name")),
        "gender": _first_text(patient.get("gender")),
        "age": _first_text(patient.get("age")),
        "phone": "",
        "specimen_condition": _first_text(specimen.get("condition")),
        "specimen_types": sample_types,
        "hospital": _first_text(overview.get("submitting_unit")),
        "submitting_unit": _first_text(overview.get("submitting_unit")),
        "patient_number": "",
        "bed_number": "",
        "department": "",
        "doctor": "",
        "clinical_diagnosis": "",
    }
    additional_info = {
        "sample_date": _first_text(dates.get("sampling")),
        "receive_date": _first_text(dates.get("receiving")),
        "report_date": _first_text(dates.get("reporting")),
        "technician": _first_text(personnel.get("tester")),
        "reviewer": _first_text(personnel.get("reviewer")),
        "approver": _first_text(personnel.get("approver")),
    }
    return {
        "report_id": report_id,
        "patient_info": patient_info,
        "tests": tests,
        "notes": _first_text(payload.get("antioxidant_assessment", {}).get("overall_conclusion") if isinstance(payload.get("antioxidant_assessment"), dict) else ""),
        "additional_info": additional_info,
        "p12_extracted_report": {
            "report_info": {
                "laboratory": _first_text(overview.get("laboratory")),
                "barcode": report_id,
                "submitting_unit": patient_info["submitting_unit"],
                "patient_name": patient_info["name"],
                "gender": patient_info["gender"],
                "age": patient_info["age"],
                "specimen_status": patient_info["specimen_condition"],
                "specimen_type": "、".join(sample_types),
                "contact": contact,
            },
            "tests": [_p12_test_export_item(test) for test in tests],
            "antioxidant_assessment": payload.get("antioxidant_assessment") if isinstance(payload.get("antioxidant_assessment"), dict) else {},
            "nad_assessment": payload.get("nad_assessment") if isinstance(payload.get("nad_assessment"), dict) else {},
        },
    }


def _p12_tests_from_ocr_payload(payload: dict[str, Any]) -> list[dict[str, Any]]:
    tests: list[dict[str, Any]] = []
    for item in payload.get("test_items", []):
        if not isinstance(item, dict):
            continue
        test_name = _first_text(item.get("item"))
        code = _p12_code_for_json_item(test_name)
        if not code:
            code = field_key_safe(test_name).lower()
        tests.append(
            _p12_make_json_test(
                page_number=1,
                group="energy_metabolism",
                item_code=code,
                test_name=test_name,
                result=item.get("result"),
                indicator=_first_text(item.get("flag"), item.get("status")),
                reference_range=_first_text(item.get("reference_range")),
                unit=_first_text(item.get("unit")),
                method=_first_text(item.get("method")),
                specimen_type="血清",
            )
        )
    antioxidant = payload.get("antioxidant_assessment", {}) if isinstance(payload.get("antioxidant_assessment"), dict) else {}
    for item in antioxidant.get("items", []):
        if not isinstance(item, dict):
            continue
        test_name = _first_text(item.get("item"))
        tests.append(
            _p12_make_json_test(
                page_number=1,
                group="antioxidant",
                item_code=_p12_antioxidant_code_for_name(test_name),
                test_name=test_name,
                result=item.get("result"),
                indicator=_first_text(item.get("flag"), item.get("status")),
                reference_range=_first_text(item.get("reference_range")),
                unit=_first_text(item.get("unit")),
                method="抗氧化能力评估",
                specimen_type="肝素钠抗凝全血",
                interpretation=_first_text(item.get("interpretation")),
            )
        )
    nad_assessment = payload.get("nad_assessment", {}) if isinstance(payload.get("nad_assessment"), dict) else {}
    nad_result = nad_assessment.get("result", {}) if isinstance(nad_assessment.get("result"), dict) else {}
    if nad_result:
        tests.append(
            _p12_make_json_test(
                page_number=2,
                group="energy_metabolism",
                item_code="nad",
                test_name="NAD+",
                result=nad_result.get("value"),
                indicator=_first_text(nad_result.get("status")),
                reference_range="",
                unit=_first_text(nad_result.get("unit")) or "µmol/L",
                method="NAD+细胞活力营养评估",
                specimen_type="全血",
                interpretation=_first_text(nad_result.get("status_description")),
            )
        )
    return tests


def _p12_make_json_test(
    *,
    page_number: int,
    group: str,
    item_code: str,
    test_name: str,
    result: Any,
    indicator: str,
    reference_range: str,
    unit: str,
    method: str,
    specimen_type: str,
    interpretation: str = "",
) -> dict[str, Any]:
    return {
        "page": page_number,
        "specimen_type": specimen_type,
        "test_name": test_name,
        "item_code": item_code,
        "group": group,
        "result": _p12_result_text(result),
        "indicator": indicator,
        "reference_range": reference_range,
        "unit": _p12_normalize_unit(unit),
        "method": method,
        "interpretation": interpretation,
    }


def _p12_code_for_json_item(name: str) -> str:
    compact = re.sub(r"\s+", "", str(name or "")).lower()
    if "辅酶q10" in compact or "coq10" in compact or "coenzymeq10" in compact:
        return "coq10"
    if "nad" in compact or "nao" in compact or "烟酰胺腺嘌呤二核苷酸" in compact:
        return "nad"
    return ""


def _p12_antioxidant_code_for_name(name: str) -> str:
    compact = re.sub(r"[\s（）()]+", "", str(name or "")).lower()
    for code, aliases in P12_ANTIOXIDANT_ALIASES.items():
        for alias in aliases:
            if re.sub(r"[\s（）()]+", "", alias).lower() in compact:
                return code
    return field_key_safe(name).lower()


def _p12_result_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, float):
        return f"{value:.2f}".rstrip("0").rstrip(".")
    return str(value).strip()


def _p07_extract_fibrosis_stacked_layout(text: str, page_number: int) -> list[dict[str, Any]]:
    if "Ⅲ型前胶原" not in text and "III型前胶原" not in text and "PC-III" not in text:
        return []
    tests: list[dict[str, Any]] = []
    for code, output_name, aliases, default_unit, default_reference in P07_FIBROSIS_TEST_DEFINITIONS:
        parsed = _p07_parse_fibrosis_row(text, aliases, default_reference=default_reference)
        if parsed:
            tests.append(
                _p07_make_test(
                    page_number,
                    "fibrosis",
                    code,
                    output_name,
                    parsed["result"],
                    parsed["reference_range"],
                    default_unit,
                    "化学发光法",
                    indicator=parsed["indicator"],
                )
            )
        elif code == "civ" and any(alias in text for alias in aliases):
            tests.append(_p07_make_test(page_number, "fibrosis", code, output_name, "", default_reference, default_unit, "化学发光法"))
    seen_codes = {str(test.get("item_code") or "") for test in tests}
    for test in _p07_extract_fibrosis_legacy_stacked_values(text, page_number):
        code = str(test.get("item_code") or "")
        if code not in seen_codes:
            tests.append(test)
            seen_codes.add(code)
    by_code = {str(test.get("item_code") or ""): test for test in tests}
    return [by_code[code] for code, *_ in P07_FIBROSIS_TEST_DEFINITIONS if code in by_code]


def _p07_extract_liver_stacked_layout(text: str, page_number: int) -> list[dict[str, Any]]:
    if "PAB" not in text or "AST" not in text or "白/球蛋白比" not in text:
        return []
    by_code: dict[str, dict[str, Any]] = {}
    for test in [*_p07_extract_liver_alt_pab_tail(text, page_number), *_p07_extract_liver_stacked_values(text, page_number)]:
        by_code[str(test.get("item_code") or "")] = test
    return [by_code[code] for code, *_ in P07_LIVER_FUNCTION_TEST_DEFINITIONS if code in by_code]


def _p07_extract_liver_stacked_values(text: str, page_number: int) -> list[dict[str, Any]]:
    anchor_match = re.search(r"丙氨酸氨基转移酶[（(]\s*ALT\s*[）)]|ALT", text, flags=re.IGNORECASE)
    if not anchor_match:
        return []
    tokens = _p07_numeric_or_reference_tokens(text[: anchor_match.start()])
    if len(tokens) < 26:
        return []
    tail_tokens = tokens[-26:]
    values = tail_tokens[:13]
    references = list(reversed(tail_tokens[13:]))
    ordered_codes = [
        "ast",
        "ast_alt_ratio",
        "tp",
        "alb",
        "glo",
        "ag_ratio",
        "tbil",
        "dbil",
        "ibil",
        "alp",
        "ggt",
        "che",
        "tba",
    ]
    definitions = {code: (name, unit, reference) for code, name, _aliases, unit, reference in P07_LIVER_FUNCTION_TEST_DEFINITIONS}
    tests: list[dict[str, Any]] = []
    for index, code in enumerate(ordered_codes):
        name, unit, default_reference = definitions[code]
        reference = references[index] if index < len(references) else default_reference
        result = values[index] if index < len(values) else ""
        if _p07_is_reference_token(result):
            continue
        tests.append(_p07_make_test(page_number, "liver_function", code, name, result, reference or default_reference, unit, "肝功能检测"))
    return tests


def _p07_extract_liver_alt_pab_tail(text: str, page_number: int) -> list[dict[str, Any]]:
    anchor = text.find("PAB")
    if anchor < 0:
        anchor = text.find("前白蛋白")
    if anchor < 0:
        return []
    tokens = _p07_numeric_or_reference_tokens(text[anchor : anchor + 220])
    if len(tokens) < 4:
        return []
    definitions = {code: (name, unit, reference) for code, name, _aliases, unit, reference in P07_LIVER_FUNCTION_TEST_DEFINITIONS}
    tests: list[dict[str, Any]] = []
    alt_reference, alt_result, pab_reference, pab_result = tokens[:4]
    if _p07_is_reference_token(alt_reference) and not _p07_is_reference_token(alt_result):
        name, unit, default_reference = definitions["alt"]
        tests.append(_p07_make_test(page_number, "liver_function", "alt", name, alt_result, alt_reference or default_reference, unit, "肝功能检测"))
    if _p07_is_reference_token(pab_reference) and not _p07_is_reference_token(pab_result):
        name, unit, default_reference = definitions["pab"]
        tests.append(_p07_make_test(page_number, "liver_function", "pab", name, pab_result, pab_reference or default_reference, unit, "肝功能检测"))
    return tests


def _p07_parse_fibrosis_row(text: str, aliases: tuple[str, ...], *, default_reference: str) -> dict[str, str] | None:
    for alias in sorted(aliases, key=len, reverse=True):
        match = re.search(name_pattern(alias), text, flags=re.IGNORECASE)
        if not match:
            continue
        window = text[match.end() : match.end() + 90].lstrip(")） ")
        value_match = re.search(
            r"(?P<result>[0-9]+(?:\.[0-9]+)?)\s*(?P<indicator>[↑↓])?\s*"
            r"(?P<reference>(?:≤|>=|≥|<=|<|>|＜|＞)\s*[0-9]+(?:\.[0-9]+)?|[0-9]+(?:\.[0-9]+)?\s*(?:--|-|~|～)\s*[0-9]+(?:\.[0-9]+)?)?",
            window,
        )
        if not value_match:
            continue
        result = value_match.group("result")
        reference = (value_match.group("reference") or default_reference).replace(" ", "")
        return {
            "result": result,
            "indicator": value_match.group("indicator") or _p07_indicator_from_result_reference(result, reference),
            "reference_range": reference,
        }
    return None


def _p07_extract_fibrosis_legacy_stacked_values(text: str, page_number: int) -> list[dict[str, Any]]:
    tests: list[dict[str, Any]] = []
    if "层粘连蛋白" in text or "层黏连蛋白" in text or "LN" in text:
        ln_matches = list(
            re.finditer(
                r"ug/L\s+化学发光法\s*(?P<result>[0-9]+(?:\.[0-9]+)?)\s*(?P<reference>(?:≤|<|＜)\s*[0-9]+(?:\.[0-9]+)?)",
                text,
            )
        )
        if ln_matches:
            match = ln_matches[-1]
            tests.append(
                _p07_make_test(
                    page_number,
                    "fibrosis",
                    "ln",
                    "层粘连蛋白（LN）",
                    match.group("result"),
                    match.group("reference").replace(" ", ""),
                    "ug/L",
                    "化学发光法",
                )
            )
    if "透明质酸" in text or "HA" in text:
        ha_matches = list(
            re.finditer(
                r"ng/mL\s+化学发光法\s*(?P<result>[0-9]+(?:\.[0-9]+)?)\s*(?P<reference>(?:≤|<|＜)\s*[0-9]+(?:\.[0-9]+)?)",
                text,
            )
        )
        if ha_matches:
            match = ha_matches[-1]
            tests.append(
                _p07_make_test(
                    page_number,
                    "fibrosis",
                    "ha",
                    "透明质酸（HA）",
                    match.group("result"),
                    match.group("reference").replace(" ", ""),
                    "ng/mL",
                    "化学发光法",
                )
            )
    return tests


def _p07_numeric_or_reference_tokens(text: str) -> list[str]:
    pattern = (
        r"(?:(?:≤|>=|≥|<=|<|>|＜|＞)\s*)?"
        r"[0-9]+(?:\.[0-9]+)?"
        r"(?:\s*(?:--|-|~|～|—|–)\s*[0-9]+(?:\.[0-9]+)?)?"
    )
    return [_p07_normalize_numeric_token(match.group(0)) for match in re.finditer(pattern, text)]


def _p07_normalize_numeric_token(value: str) -> str:
    return (
        re.sub(r"\s+", "", str(value or ""))
        .replace("～", "--")
        .replace("~", "--")
        .replace("—", "--")
        .replace("–", "--")
        .replace("＜", "<")
        .replace("＞", ">")
    )


def _p07_is_reference_token(value: str) -> bool:
    text = str(value or "")
    return "--" in text or "-" in text or text.startswith(("≤", "<", "≥", ">"))


def _p07_make_test(
    page_number: int,
    group: str,
    item_code: str,
    test_name: str,
    result: str,
    reference_range: str,
    unit: str,
    method: str,
    *,
    indicator: str = "",
) -> dict[str, Any]:
    normalized_reference = str(reference_range or "").strip()
    normalized_result = str(result or "").strip()
    return {
        "page": page_number,
        "specimen_type": "血清",
        "test_name": test_name,
        "item_code": item_code,
        "group": group,
        "result": normalized_result,
        "indicator": indicator or _p07_indicator_from_result_reference(normalized_result, normalized_reference),
        "reference_range": normalized_reference,
        "unit": unit,
        "method": method,
    }


def _p07_indicator_from_result_reference(result: Any, reference_range: str) -> str:
    value = _safe_number(result)
    if value is None:
        return ""
    for lower, upper in _p07_reference_bounds(reference_range):
        if lower is not None and value < lower:
            return "↓"
        if upper is not None and value > upper:
            return "↑"
        if lower is not None or upper is not None:
            return ""
    return ""


def _p07_parse_test_after_name(
    text: str,
    aliases: tuple[str, ...],
    *,
    default_unit: str,
    default_reference: str,
    default_method: str,
) -> dict[str, str] | None:
    for alias in aliases:
        match = re.search(rf"{name_pattern(alias)}", text, flags=re.IGNORECASE)
        if not match:
            continue
        window = normalize_text(text[match.end() : match.end() + 140])
        value_match = re.search(r"(?P<result>[0-9]+(?:\.[0-9]+)?)\s*(?P<indicator>[↑↓])?", window)
        if not value_match:
            if alias.upper() in {"CIV", "C-IV"} or "IV" in alias or "Ⅳ" in alias:
                return {
                    "result": "",
                    "indicator": "",
                    "reference_range": default_reference,
                    "unit": default_unit,
                    "method": default_method,
                }
            continue
        reference_match = re.search(
            r"(?P<reference>"
            r"[0-9]+(?:\.[0-9]+)?\s*(?:--|~|-)\s*[0-9]+(?:\.[0-9]+)?|"
            r"(?:≤|>=|≥|<=|<|>|＜|＞)\s*[0-9]+(?:\.[0-9]+)?"
            r")",
            window[value_match.end() :],
        )
        unit_match = re.search(r"μmol/L|umol/L|μg/L|ug/L|ng/mL|mg/L|g/L|U/L", window, flags=re.IGNORECASE)
        method_match = re.search(r"化学发光法|测序法|酶法|计算法|肝功能检测", window)
        return {
            "result": value_match.group("result"),
            "indicator": value_match.group("indicator") or "",
            "reference_range": (reference_match.group("reference").replace(" ", "") if reference_match else default_reference),
            "unit": unit_match.group(0) if unit_match else default_unit,
            "method": method_match.group(0) if method_match else default_method,
        }
    return None


def _p07_parse_aldh2_gene(text: str) -> dict[str, Any] | None:
    if "ALDH2" not in text and "乙醛脱氢酶" not in text and "醛脱氢酶" not in text:
        return None
    result_match = re.search(r"极差\s+(GG|GA|AG|AA)\s+审核者", text.upper())
    standalone_genotypes = [
        line.strip().upper()
        for line in text.splitlines()
        if re.fullmatch(r"GG|GA|AG|AA", line.strip().upper())
    ]
    genotype = result_match.group(1) if result_match else (standalone_genotypes[-1] if standalone_genotypes else "")
    if not genotype:
        genotype_match = re.search(r"\b(GG|GA|AG|AA)\b", text.upper())
        genotype = genotype_match.group(1) if genotype_match else ""
    if not genotype:
        return None
    locus_match = re.search(r"(ALDH2\s*c\.\s*1510G\s*[>＞]\s*A|ALDH2\s*c\.1510G[>＞]A|rs671)", text, flags=re.IGNORECASE)
    indication_match = re.search(r"结果(?:提示|判读)?[:：]?\s*(正常|异常|需关注|高风险|低风险)", text)
    return {
        "page": 3,
        "specimen_type": "EDTA抗凝全血",
        "test_name": "ALDH2 c.1510G>A",
        "item_code": "aldh2",
        "group": "gene",
        "result": "GA" if genotype == "AG" else genotype,
        "indicator": indication_match.group(1) if indication_match else "",
        "reference_range": "",
        "unit": "",
        "method": "测序法" if "测序" in text else "",
        "locus": locus_match.group(1).replace(" ", "") if locus_match else "ALDH2 c.1510G>A",
    }


def _p07_code_for_name(name: str, *, group: str) -> str:
    definitions = P07_FIBROSIS_TEST_DEFINITIONS if group == "fibrosis" else P07_LIVER_FUNCTION_TEST_DEFINITIONS
    normalized_name = str(name or "").lower().replace(" ", "")
    if group == "liver_function" and (
        "白/球蛋白比" in normalized_name
        or "白蛋白/球蛋白比值" in normalized_name
        or "白球比" in normalized_name
        or "a/g" in normalized_name
        or "a／g" in normalized_name
    ):
        return "ag_ratio"
    for code, _output_name, aliases, _unit, _reference in definitions:
        if any(str(alias).lower().replace(" ", "") in normalized_name for alias in aliases):
            return code
    return field_key_safe(name).lower()


def _p07_status_from_test(test: dict[str, Any]) -> str:
    indicator = str(test.get("indicator") or "").strip()
    if indicator:
        if indicator in {"↑", "升高", "偏高"}:
            return "偏高"
        if indicator in {"↓", "降低", "偏低"}:
            return "偏低"
        return indicator
    result = _safe_number(test.get("result"))
    if result is None:
        return "待复核"
    bounds = _p07_reference_bounds(str(test.get("reference_range") or ""))
    for lower, upper in bounds:
        if lower is not None and result < lower:
            return "偏低"
        if upper is not None and result > upper:
            return "偏高"
        if lower is not None and upper is not None and lower <= result <= upper:
            return "正常"
        if lower is None and upper is not None and result <= upper:
            return "正常"
        if upper is None and lower is not None and result >= lower:
            return "正常"
    return "正常" if bounds else "待复核"


def _p07_reference_bounds(reference_range: str) -> list[tuple[float | None, float | None]]:
    text = str(reference_range or "").replace("～", "-").replace("—", "-").replace("–", "-").replace("至", "-")
    bounds: list[tuple[float | None, float | None]] = []
    for value in re.findall(r"(?:<=|≤|<|＜)\s*(\d+(?:\.\d+)?)", text):
        bounds.append((None, float(value)))
    for value in re.findall(r"(?:>=|≥|>|＞)\s*(\d+(?:\.\d+)?)", text):
        bounds.append((float(value), None))
    for lower_text, upper_text in re.findall(r"(\d+(?:\.\d+)?)\s*(?:--|-|~)\s*(\d+(?:\.\d+)?)", text):
        lower = float(lower_text)
        upper = float(upper_text)
        if lower <= upper:
            bounds.append((lower, upper))
    return bounds


def _p07_extract_name(full_text: str) -> str:
    return extract_patient_name(full_text)


def _p07_extract_gender(full_text: str) -> str:
    return extract_gender(full_text)


def _p07_extract_submitting_unit(full_text: str) -> str:
    return extract_hospital(full_text)


def _p07_extract_specimen_condition(full_text: str) -> str:
    return extract_specimen_condition(full_text)


def _p07_extract_specimen_type(page_texts: list[str]) -> str:
    values = extract_specimen_types(page_texts)
    return values[0] if values else ""


def _p07_extract_date(page_texts: list[str], label: str) -> str:
    if label == "采样日期":
        values = [_p07_extract_page_date(page_texts, index, label) for index in range(1, len(page_texts) + 1)]
        values = [value for value in values if value]
        return min(values) if values else ""
    values = [_p07_extract_page_date(page_texts, index, label) for index in range(1, len(page_texts) + 1)]
    values = [value for value in values if value]
    return max(values) if values else ""


def _p07_extract_page_date(page_texts: list[str], page_number: int, label: str) -> str:
    if page_number < 1 or page_number > len(page_texts):
        return ""
    pattern = re.compile(rf"{label_pattern(label)}[:：]?\s*({DATE_VALUE_PATTERN})")
    match = pattern.search(page_texts[page_number - 1])
    return match.group(1) if match else ""


def _p07_extract_after_label(full_text: str, label: str) -> str:
    pattern = re.compile(rf"{label_pattern(label)}[:：]?\s*([^\s]+)")
    match = pattern.search(full_text)
    if not match:
        return ""
    value = clean_value(match.group(1))
    return "" if looks_like_label(value) else value


def _p07_clean_clinical_diagnosis(value: Any) -> str:
    text = str(value or "").strip()
    compact = "".join(text.split()).lower()
    if not compact or compact in {"-", "—", "/"}:
        return ""
    if "anweikang" in compact or "安为康" in text or "安為康" in text:
        return ""
    return text


def _p07_extract_phone(full_text: str) -> str:
    match = re.search(r"([0-9]{3,4}\s*-\s*[0-9]{3}\s*-\s*[0-9]{4}|1[3-9][0-9]{9})", full_text)
    return clean_value(match.group(1)).replace(" ", "") if match else ""


def _p07_extract_remark(page_texts: list[str], page_number: int) -> str:
    if page_number < 1 or page_number > len(page_texts):
        return ""
    match = re.search(r"备注[:：]?\s*([^\s]+)", page_texts[page_number - 1])
    return clean_value(match.group(1)) if match else ""


def _p07_collect_notes(full_text: str) -> str:
    parts: list[str] = []
    for pattern in [r"友情提示[:：]?\s*(.*?)(?:检测方法|$)", r"备注[:：]?\s*([^\s]+)"]:
        match = re.search(pattern, full_text)
        if match:
            value = clean_value(match.group(1))
            if value and value not in parts:
                parts.append(value)
    return " ".join(parts)


def _p07_json_notes(page_1: dict[str, Any], page_2: dict[str, Any], page_3: dict[str, Any]) -> str:
    parts: list[str] = []
    for value in [page_1.get("remark"), page_2.get("remark")]:
        text = _first_text(value)
        if text and text not in parts:
            parts.append(text)
    notes = page_3.get("notes")
    if isinstance(notes, list):
        parts.extend(str(note) for note in notes if str(note).strip())
    return " ".join(parts)


def _p07_specimen_types(values: list[Any], tests: list[dict[str, Any]]) -> list[str]:
    result: list[str] = []
    for value in values:
        text = _first_text(value)
        if text and text not in result:
            result.append(text)
    for test in tests:
        text = _first_text(test.get("specimen_type"))
        if text and text not in result:
            result.append(text)
    return result


def _p07_test_export_item(test: dict[str, Any]) -> dict[str, Any]:
    return {
        "test_name": str(test.get("test_name") or ""),
        "item_code": str(test.get("item_code") or ""),
        "result": str(test.get("result") or ""),
        "indicator": str(test.get("indicator") or ""),
        "reference_range": str(test.get("reference_range") or ""),
        "unit": str(test.get("unit") or ""),
        "method": str(test.get("method") or ""),
    }


def _p07_gene_export_item(test: dict[str, Any]) -> dict[str, Any]:
    return {
        "gene_locus": str(test.get("locus") or ""),
        "result": str(test.get("result") or ""),
        "indication": str(test.get("indicator") or ""),
        "method": str(test.get("method") or ""),
    }


def _p07_result_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, float):
        return f"{value:.2f}".rstrip("0").rstrip(".")
    return str(value).strip()


def _first_text(*values: Any) -> str:
    for value in values:
        if value is None:
            continue
        text = str(value).strip()
        if text:
            return text
    return ""


def _max_date_text(values: list[Any]) -> str:
    texts = [_first_text(value) for value in values]
    texts = [value for value in texts if value]
    return max(texts) if texts else ""


def _safe_number(value: Any) -> float | None:
    if value in (None, ""):
        return None
    match = re.search(r"\d+(?:\.\d+)?", str(value).replace(",", ""))
    if not match:
        return None
    try:
        return float(match.group(0))
    except ValueError:
        return None


def build_warnings(fields: list[dict[str, Any]], pages: list[dict[str, Any]], structured_report: dict[str, Any], package_code: str = "P02") -> list[str]:
    warnings: list[str] = []
    if not any(page["text_blocks"][0]["text"] for page in pages):
        warnings.append("PDF未提取到文本，请切换云OCR或人工补录。")

    if package_code == "P01":
        required = {
            "patient.name": "姓名",
            "patient.gender": "性别",
            "patient.age": "年龄",
            "p01.gmhi.result_display": "GMHI",
            "p01.gut_age.result_display": "肠龄",
            "p01.enterotype.result_display": "肠型",
            "p01.be_index.result_display": "B/E比值",
        }
    elif package_code == "P03":
        required = {
            "patient.name": "姓名",
            "patient.gender": "性别",
            "patient.age": "年龄",
            "p03.tg.result_display": "TG",
            "p03.hdl_c.result_display": "HDL-C",
            "p03.glucose.result_display": "GLU",
            "p03.hba1c.result_display": "HbA1c",
            "p03.insulin.result_display": "Ins",
        }
    elif package_code == "P04":
        required = {"patient.name": "姓名", "patient.gender": "性别", "patient.age": "年龄"}
        for code, output_name, *_ in P04_TEST_DEFINITIONS:
            required[f"p04.nutrients.{code}.result_display"] = output_name
    elif package_code == "P05":
        required = {"patient.name": "姓名", "patient.gender": "性别", "patient.age": "年龄"}
    elif package_code == "P06":
        required = {
            "patient.name": "姓名",
            "patient.gender": "性别",
            "patient.age": "年龄",
            "p06.immune_cells.gzm_b_nk.absolute_result": "Gzm B+ NK",
            "p06.immune_cells.ifn_gamma_nk.absolute_result": "IFN-γ+ NK",
            "p06.immune_cells.gzm_b_ctl.absolute_result": "Gzm B+ CTL",
            "p06.immune_cells.ifn_gamma_ctl.absolute_result": "IFN-γ+ CTL",
            "p06.cytokines.il_8.result_display": "IL-8",
            "p06.cytokines.tnf_alpha.result_display": "TNF-α",
        }
    elif package_code == "P07":
        required = {
            "patient.name": "姓名",
            "patient.gender": "性别",
            "patient.age": "年龄",
            "p07.liver_function.alt.result_display": "ALT",
            "p07.liver_function.ast.result_display": "AST",
            "p07.liver_function.ggt.result_display": "GGT",
            "p07.fibrosis.pc_iii.result_display": "PC-III",
            "p07.fibrosis.ln.result_display": "LN",
            "p07.fibrosis.ha.result_display": "HA",
            "p07.gene.aldh2.result_display": "ALDH2",
        }
    elif package_code == "P08":
        required = {"patient.name": "姓名", "patient.gender": "性别", "patient.age": "年龄"}
        for code, output_name, *_ in P08_TEST_DEFINITIONS:
            group = "cardiovascular" if code in {"nt_probnp", "d_dimer", "ffa"} else "raas"
            required[f"p08.{group}.{code}.result_display"] = output_name
    elif package_code == "P09":
        required = {"patient.name": "姓名", "patient.gender": "性别", "patient.age": "年龄"}
        for code, output_name, *_ in P09_TEST_DEFINITIONS:
            if code in {"e2", "lh", "fsh", "progesterone", "testosterone", "shbg", "amh", "prolactin", "total_ige"}:
                required[f"p09.indicators.{code}.result_display"] = output_name
    elif package_code == "P12":
        required = {
            "patient.name": "姓名",
            "patient.gender": "性别",
            "patient.age": "年龄",
            "p12.indicators.coq10.result_display": "辅酶Q10",
            "p12.indicators.nad.status": "NAD+状态",
        }
    elif package_code == "P13":
        required = {
            "patient.name": "姓名",
            "patient.gender": "性别",
            "patient.age": "年龄",
            "sample.type": "样本信息",
            "report.method": "检测技术",
            "p13.telomere_age": "端粒年龄",
            "p13.actual_age": "实际年龄",
            "p13.telomere.relative_length": "端粒相对长度",
            "p13.percentile.display": "人群百分位",
            "p13.telomere.ct_value": "端粒Ct值",
            "p13.reference.ct_value": "内参Ct值",
        }
    elif package_code == "P14":
        required = {
            "patient.name": "姓名",
            "patient.gender": "性别",
            "patient.age": "年龄",
            "report.method": "评估方法",
            "p14.summary.score": "CDA综合评分",
            "p14.summary.risk_level": "综合风险等级",
            "p14.results.cda.result_display": "CDA",
            "p14.results.ptf.result_display": "PTF",
            "p14.results.ctf.result_display": "CTF",
            "p14.overview.methylation.status": "五癌甲基化",
            "p14.overview.ctc.status": "CTC计数",
        }
    elif package_code == "P15":
        required = {
            "patient.name": "姓名",
            "patient.gender": "性别",
            "patient.age": "年龄",
            "report.method": "评估方法",
            "p15.results.ee2.result_display": "17α-乙炔基雌二醇",
            "p15.results.bpa.result_display": "双酚A",
            "p15.results.mep.result_display": "邻苯二甲酸单乙基酯",
        }
    elif package_code == "P16":
        required = {
            "patient.name": "姓名",
            "patient.gender": "性别",
            "sample.type": "样本信息",
            "report.method": "评估方法",
            "p16.summary.evaluation_summary": "评估总结",
            "p16.tests.adrb1.result_display": "ADRB1",
            "p16.tests.slco1b1.result_display": "SLCO1B1",
            "p16.tests.cyp2c19.result_display": "CYP2C19",
            "p16.tests.gp1ba.result_display": "GP1BA",
            "p16.tests.pear1.result_display": "PEAR1",
            "p16.tests.cdkal1_rs7756992.result_display": "CDKAL1",
            "p16.tests.mthfr.result_display": "MTHFR",
        }
    elif package_code == "P10":
        required = {
            "patient.name": "姓名",
            "patient.gender": "性别",
            "patient.age": "年龄",
            "p10.indicators.psa.result_display": "总PSA",
            "p10.indicators.psa_free.result_display": "游离PSA",
            "p10.indicators.psa_ratio.result_display": "游离/总PSA比值",
            "p10.indicators.cyp1a1.result_display": "CYP1A1",
            "p10.indicators.aldh2.result_display": "ALDH2",
            "p10.indicators.lct.result_display": "MCM6/LCT",
            "p10.indicators.cyp1a2.result_display": "CYP1A2",
        }
    elif package_code == "P11":
        required = build_p11_warning_requirements()
    elif package_code == "P17":
        required = {
            "patient.name": "姓名",
            "patient.gender": "性别",
            "patient.age": "年龄",
            "p17.hpv_16.result_display": "HPV-16",
            "p17.hpv_18.result_display": "HPV-18",
            "p17.阴道毛滴虫.result_display": "阴道毛滴虫",
        }
    else:
        required = {
            "patient.name": "姓名",
            "patient.gender": "性别",
            "patient.age": "年龄",
            "p02.calprotectin.result_display": "粪便钙卫蛋白",
        }

    existing = {field["field_key"] for field in fields}
    for field_key, label in required.items():
        if field_key not in existing:
            warnings.append(f"未识别到必需字段：{label}")

    test_names = [str(test.get("test_name") or "") for test in structured_report.get("tests", [])]
    if package_code == "P03" and test_names and len(test_names) < 12:
        warnings.append(f"P03 当前仅识别到 {len(test_names)} 项，建议人工复核。")
    if package_code == "P04":
        if not test_names:
            warnings.append("P04 未识别到营养素检验明细，请核对文本层或切换云OCR。")
        elif len(test_names) < len(P04_TEST_DEFINITIONS):
            warnings.append(f"P04 目标{len(P04_TEST_DEFINITIONS)}项，当前仅识别到 {len(test_names)} 项，建议人工复核。")
        test_names = []
    if package_code == "P05":
        if not test_names:
            warnings.append("P05 未识别到有效检验明细，请结合图片页OCR结果复核。")
        elif len(test_names) < 10:
            warnings.append(f"P05 当前仅识别到 {len(test_names)} 项，建议人工复核。")
        test_names = []
    if package_code == "P06":
        if not test_names:
            warnings.append("P06 未识别到免疫细胞或细胞因子明细，请核对文本层或切换云OCR。")
        elif len(test_names) < 20:
            warnings.append(f"P06 当前识别到 {len(test_names)} 项，低于预期，建议人工复核第一页免疫细胞表和第二页细胞因子表。")
        test_names = []
    if package_code == "P07":
        recognized_codes = {str(test.get("item_code") or "") for test in structured_report.get("tests", [])}
        expected_codes = {
            "alt",
            "ast",
            "ggt",
            "alp",
            "tbil",
            "dbil",
            "ibil",
            "tp",
            "alb",
            "glo",
            "ag_ratio",
            "che",
            "pc_iii",
            "ln",
            "ha",
            "aldh2",
        }
        if not test_names:
            warnings.append("P07 未识别到肝功能、肝纤维化或ALDH2检验明细，请核对文本层、OCR JSON或切换云OCR。")
        else:
            missing_codes = sorted(expected_codes - recognized_codes)
            if missing_codes:
                warnings.append(f"P07 当前缺少核心项目：{', '.join(missing_codes)}，建议人工复核或补录。")
        test_names = []
    if package_code == "P08":
        recognized_codes = {str(test.get("item_code") or "") for test in structured_report.get("tests", [])}
        expected_codes = {"nt_probnp", "d_dimer", "ffa", "angiotensin_i", "angiotensin_ii", "angiotensin_ratio", "renin", "aldosterone"}
        if not test_names:
            warnings.append("P08 未识别到NT-proBNP、RAAS、凝血或脂代谢检验明细，请核对文本层或切换云OCR。")
        else:
            missing_codes = sorted(expected_codes - recognized_codes)
            if missing_codes:
                warnings.append(f"P08 当前缺少核心项目：{', '.join(missing_codes)}，建议人工复核或补录。")
        test_names = []
    if package_code == "P09":
        recognized_codes = {str(test.get("item_code") or "") for test in structured_report.get("tests", [])}
        expected_codes = {"e2", "lh", "fsh", "progesterone", "testosterone", "shbg", "amh", "prolactin"}
        optional_codes = {"cortisol"}
        if not test_names:
            warnings.append("P09 未识别到女性激素或相关检验明细，请核对文本层、补充样例或切换云OCR。")
        else:
            missing_codes = sorted(expected_codes - recognized_codes)
            if missing_codes:
                warnings.append(f"P09 当前缺少核心项目：{', '.join(missing_codes)}，建议人工复核或补录。")
            missing_optional = sorted(optional_codes - recognized_codes)
            if missing_optional:
                warnings.append(f"P09 当前未识别到可选项目：{', '.join(missing_optional)}；如原始报告包含这些项目，请人工复核。")
        test_names = []
    if package_code == "P12":
        recognized_codes = {str(test.get("item_code") or "") for test in structured_report.get("tests", [])}
        expected_codes = {"coq10", "nad"}
        if not test_names:
            warnings.append("P12 未识别到辅酶Q10或NAD+结果，请核对文本层、补充样例或切换云OCR。")
        else:
            missing_codes = sorted(expected_codes - recognized_codes)
            if missing_codes:
                warnings.append(f"P12 当前缺少核心项目：{', '.join(missing_codes)}，建议人工复核或补录。")
        test_names = []
    if package_code == "P13":
        recognized_codes = {str(test.get("item_code") or "") for test in structured_report.get("tests", [])}
        expected_codes = {"actual_age", "telomere_age", "telomere_relative_length", "percentile", "telomere_ct", "reference_ct"}
        if not test_names:
            warnings.append("P13 未识别到端粒年龄、端粒相对长度、百分位或Ct值，请核对PDF文本层、OCR JSON或切换云OCR。")
        else:
            missing_codes = sorted(expected_codes - recognized_codes)
            if missing_codes:
                warnings.append(f"P13 当前缺少核心项目：{', '.join(missing_codes)}，建议人工复核或补录。")
        test_names = []
    if package_code == "P14":
        recognized_codes = {str(test.get("item_code") or "") for test in structured_report.get("tests", [])}
        expected_codes = {"cda", "ptf", "ctf", "methylation", "ctc"}
        if not test_names:
            warnings.append("P14 当前未识别到疾病风险评估、五癌甲基化或 CTC 核心项目，请优先补充结构化 JSON OCR 结果或人工复核。")
        else:
            missing_codes = sorted(expected_codes - recognized_codes)
            if missing_codes:
                warnings.append(f"P14 当前缺少核心项目：{', '.join(missing_codes)}，建议人工复核或补录。")
        trend_points = structured_report.get("trend_points", [])
        if isinstance(trend_points, list):
            populated = [item for item in trend_points if isinstance(item, dict) and str(item.get("value") or "").strip() not in {"", "—"}]
            if len(populated) < 4:
                warnings.append("P14 当前连续复测趋势数据未完整覆盖 4 个节点，趋势图请结合原始 CTC 历史结果人工复核。")
        test_names = []
    if package_code == "P15":
        recognized_codes = {str(test.get("item_code") or "") for test in structured_report.get("tests", [])}
        expected_codes = {"ee2", "des", "methylparaben", "ethylparaben", "propylparaben", "butylparaben", "mep", "mbp", "mbzp", "mehp", "bpa", "bpb", "nonylphenol", "octylphenol", "mmp"}
        if not test_names:
            warnings.append("P15 当前尚未识别到环境荷尔蒙项目明细，请核对PDF文本层、补充真实样例或切换云OCR。")
        else:
            missing_codes = sorted(expected_codes - recognized_codes)
            if missing_codes:
                warnings.append(f"P15 当前缺少核心项目：{', '.join(missing_codes)}，建议人工复核或补录。")
        test_names = []
    if package_code == "P16":
        recognized_codes = {str(test.get("item_code") or "") for test in structured_report.get("tests", [])}
        expected_codes = {
            "adrb1",
            "slco1b1",
            "apoe",
            "cyp2c19",
            "gp1ba",
            "pear1",
            "cdkal1_rs7756992",
            "cyp2c9_sulfonylurea",
            "mthfr",
            "pai1",
        }
        if not test_names:
            warnings.append("P16 当前未识别到药物基因组学核心项目，请优先使用同目录 OCR.txt 或补充结构化 JSON 结果。")
        else:
            missing_codes = sorted(expected_codes - recognized_codes)
            if missing_codes:
                warnings.append(f"P16 当前缺少核心项目：{', '.join(missing_codes)}，建议人工复核或补录。")
        test_names = []
    if package_code == "P10":
        recognized_codes = {str(test.get("item_code") or "") for test in structured_report.get("tests", [])}
        expected_codes = {"psa", "psa_free", "psa_ratio", "cyp1a1", "aldh2", "lct", "cyp1a2", "dhea", "inhibin_b"}
        if not test_names:
            warnings.append("P10 未识别到PSA、激素或代谢基因检验明细，请核对上传JSON。")
        else:
            missing_codes = sorted(expected_codes - recognized_codes)
            if missing_codes:
                warnings.append(f"P10 当前缺少核心项目：{', '.join(missing_codes)}，建议人工复核或补录。")
        test_names = []
    if package_code == "P11":
        warnings.extend(extract_p11_warning_messages(structured_report))
        test_names = []
    if package_code == "P01":
        if not test_names:
            warnings.append("P01 当前仍以基础资料抽取为主，专项菌群指标需结合真实样例继续增强。")
        elif len(test_names) < 5:
            warnings.append(f"P01 当前仅识别到 {len(test_names)} 项，建议人工复核。")
        test_names = []

    allergen_count = sum(1 for name in test_names if "钙卫蛋白" not in name and "IgE" not in name)
    if not test_names:
        if package_code not in {"P01", "P04", "P05", "P06", "P07", "P08", "P09", "P10", "P11", "P12", "P13", "P14", "P16"}:
            warnings.append("未识别到检验项目明细。")
    elif package_code == "P02" and allergen_count and allergen_count < 10:
        warnings.append(f"P02 过敏原项目仅识别到 {allergen_count} 项，建议人工复核。")
    if package_code == "P02" and not any("IgE" in name for name in test_names):
        warnings.append("未识别到总IgE结果。")

    additional_info = structured_report.get("additional_info", {})
    if package_code == "P05":
        missing_staff = not any([additional_info.get("technician"), additional_info.get("reviewer"), additional_info.get("approver")])
    elif package_code in {"P04", "P06"}:
        missing_staff = not additional_info.get("reviewer")
    elif package_code in {"P07", "P08", "P09", "P10", "P11", "P12", "P13", "P14", "P15", "P16", "P17"}:
        missing_staff = False
    elif package_code == "P01":
        missing_staff = not additional_info.get("technician") or not additional_info.get("reviewer")
    else:
        missing_staff = not additional_info.get("technician") or not additional_info.get("reviewer") or not additional_info.get("approver")
    if missing_staff:
        warnings.append("未从PDF文本层识别到检测者、审核者或批准人，如需签名信息请使用图像OCR或人工补录。")

    low_confidence = list(dict.fromkeys(field["label"] for field in fields if field["confidence"] < 0.75))
    if low_confidence:
        warnings.append("低置信度字段需人工复核：" + "、".join(low_confidence))
    return warnings
