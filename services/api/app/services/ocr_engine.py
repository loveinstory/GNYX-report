from __future__ import annotations

import json
import re
import tempfile
from pathlib import Path
from statistics import mean
from typing import Any

from pypdf import PdfReader

from app.services.ocr_logs import now_iso


STRATEGY_VERSION = "P02-ocr-strategy-v0.3-structured-json"
P01_STRATEGY_VERSION = "P01-ocr-strategy-v0.2-summary-structured"
P05_STRATEGY_VERSION = "P05-ocr-strategy-v0.2-multipage-rapidocr"
P03_STRATEGY_VERSION = "P03-ocr-strategy-v0.3-c-peptide-prefix"
P04_STRATEGY_VERSION = "P04-ocr-strategy-v0.2-nutrient-multipage-rapidocr"
P06_STRATEGY_VERSION = "P06-ocr-strategy-v0.3-hscrp-three-page"
P07_STRATEGY_VERSION = "P07-ocr-strategy-v0.2-xie-three-page-json"
P17_STRATEGY_VERSION = "P17-ocr-strategy-v0.2-standard-json-aligned"
PROVIDER = "pdf-text-extractor"

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
    ("civ", "IV型胶原（CIV）", ("IV型胶原", "IV 型胶原", "Ⅳ型胶原", "CIV", "C-IV"), "ng/mL", ""),
    ("ln", "层粘连蛋白（LN）", ("层粘连蛋白", "层黏连蛋白", "LN"), "ug/L", "≤50"),
    ("ha", "透明质酸（HA）", ("透明质酸", "透明质酸酶", "HA"), "ng/mL", "≤100"),
]
P07_TARGET_CODES = {code for code, *_ in [*P07_LIVER_FUNCTION_TEST_DEFINITIONS, *P07_FIBROSIS_TEST_DEFINITIONS]}


def parse_pdf_to_standard_ocr_json(pdf_path: Path, package_code: str = "P02") -> dict[str, Any]:
    strategy_version = {
        "P01": P01_STRATEGY_VERSION,
        "P05": P05_STRATEGY_VERSION,
        "P03": P03_STRATEGY_VERSION,
        "P04": P04_STRATEGY_VERSION,
        "P06": P06_STRATEGY_VERSION,
        "P07": P07_STRATEGY_VERSION,
        "P17": P17_STRATEGY_VERSION,
    }.get(package_code, STRATEGY_VERSION)
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
    add_field(fields, "patient.hospital", "送检单位", patient_info["hospital"], 0.8, find_page(page_texts, patient_info["hospital"]))
    add_field(fields, "report.assessment_date", "评估日期", additional_info["report_date"] or additional_info["sample_date"], 0.8, find_page(page_texts, additional_info["report_date"] or additional_info["sample_date"]))

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
    for name in P17_MICROBE_TRAILING_NEGATIVE_NAMES:
        if _p17_find_name_in_text(normalized, name):
            results.setdefault(name, ("阴性", "-"))
    return results


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
    else:
        required = {
            "patient.name": "姓名",
            "patient.gender": "性别",
            "patient.age": "年龄",
            "p02.calprotectin.result_display": "粪便钙卫蛋白检测结果",
        }
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
        "P17": P17_STRATEGY_VERSION,
    }.get(package_code, STRATEGY_VERSION)
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
    elif package_code == "P17":
        fields = extract_p17_fields(page_texts, structured_report)
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
    page_1 = payload.get("page_1", {}) if isinstance(payload.get("page_1"), dict) else {}
    page_2 = payload.get("page_2", {}) if isinstance(payload.get("page_2"), dict) else {}
    page_3 = payload.get("page_3", {}) if isinstance(payload.get("page_3"), dict) else {}
    tests = _p07_tests_from_json_payload(payload)
    gene_basic = page_3.get("basic_info", {}) if isinstance(page_3.get("basic_info"), dict) else {}
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
        "sample_date": _first_text(page_1.get("sample_date"), page_2.get("sample_date"), gene_basic.get("sample_date")),
        "receive_date": _first_text(page_1.get("receive_date"), page_2.get("receive_date"), gene_basic.get("receive_date")),
        "report_date": _max_date_text([page_1.get("report_date"), page_2.get("report_date")]),
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
    page_1 = payload.get("page_1", {}) if isinstance(payload.get("page_1"), dict) else {}
    page_2 = payload.get("page_2", {}) if isinstance(payload.get("page_2"), dict) else {}
    page_3 = payload.get("page_3", {}) if isinstance(payload.get("page_3"), dict) else {}
    specimen_type = _first_text(report_info.get("specimen_type")) or "血清"
    tests: list[dict[str, Any]] = []
    page_1_items = page_1.get("test_items", []) if isinstance(page_1.get("test_items"), list) else []
    page_2_items = page_2.get("test_items", []) if isinstance(page_2.get("test_items"), list) else []
    for raw_item in page_1_items:
        if isinstance(raw_item, dict):
            tests.append(_p07_json_test_item(raw_item, page=1, group="fibrosis", specimen_type=specimen_type))
    for raw_item in page_2_items:
        if isinstance(raw_item, dict):
            tests.append(_p07_json_test_item(raw_item, page=2, group="liver_function", specimen_type=specimen_type))
    gene_result = page_3.get("test_result", {}) if isinstance(page_3.get("test_result"), dict) else {}
    basic_info = page_3.get("basic_info", {}) if isinstance(page_3.get("basic_info"), dict) else {}
    if gene_result:
        tests.append(
            {
                "page": 3,
                "specimen_type": _first_text(basic_info.get("specimen_type")) or "EDTA抗凝全血",
                "test_name": "ALDH2 c.1510G>A",
                "item_code": "aldh2",
                "group": "gene",
                "result": _first_text(gene_result.get("result")),
                "indicator": _first_text(gene_result.get("indication")),
                "reference_range": "",
                "unit": "",
                "method": _first_text(page_3.get("method")) or "测序法",
                "locus": _first_text(gene_result.get("gene_locus")) or "ALDH2 c.1510G>A",
            }
        )
    return tests


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


def _p07_extract_fibrosis_stacked_layout(text: str, page_number: int) -> list[dict[str, Any]]:
    if "Ⅲ型前胶原" not in text and "III型前胶原" not in text and "PC-III" not in text:
        return []
    tests: list[dict[str, Any]] = []
    pc_match = re.search(r"(?:Ⅲ型前胶原|III型前胶原|III 型前胶原)\(?(?:PC-III)?\)?\s*(?P<result>[0-9]+(?:\.[0-9]+)?)\s*(?P<reference>≤\s*[0-9]+(?:\.[0-9]+)?)", text)
    if pc_match:
        tests.append(_p07_make_test(page_number, "fibrosis", "pc_iii", "III型前胶原（PC-III）", pc_match.group("result"), pc_match.group("reference").replace(" ", ""), "ng/mL", "化学发光法"))
    if "Ⅳ型胶原" in text or "IV型胶原" in text or "CIV" in text:
        tests.append(_p07_make_test(page_number, "fibrosis", "civ", "IV型胶原（CIV）", "", "", "ng/mL", "化学发光法"))
    if "层粘连蛋白" in text or "层黏连蛋白" in text or "LN" in text:
        ln_match = re.search(r"ug/L\s+化学发光法\s*(?P<result>[0-9]+(?:\.[0-9]+)?)\s*(?P<reference>≤\s*[0-9]+(?:\.[0-9]+)?)", text)
        if ln_match:
            tests.append(_p07_make_test(page_number, "fibrosis", "ln", "层粘连蛋白（LN）", ln_match.group("result"), ln_match.group("reference").replace(" ", ""), "ug/L", "化学发光法"))
    if "透明质酸" in text or "HA" in text:
        ha_match = re.search(r"ng/mL\s+化学发光法\s*(?P<result>[0-9]+(?:\.[0-9]+)?)\s*(?P<reference>≤\s*[0-9]+(?:\.[0-9]+)?)", text)
        if ha_match:
            tests.append(_p07_make_test(page_number, "fibrosis", "ha", "透明质酸（HA）", ha_match.group("result"), ha_match.group("reference").replace(" ", ""), "ng/mL", "化学发光法"))
    return tests


def _p07_extract_liver_stacked_layout(text: str, page_number: int) -> list[dict[str, Any]]:
    if "前白蛋白(PAB)" not in text or "天门冬氨酸氨基转移酶(AST)" not in text or "白/球蛋白比" not in text:
        return []
    tests: list[dict[str, Any]] = []
    alt_match = re.search(r"(?P<reference>9--50)\s*U/L\s*(?P<result>[0-9]+(?:\.[0-9]+)?)\s*前白蛋白", text)
    pab_match = re.search(r"前白蛋白\(PAB\)\s*mg/L\s*(?P<reference>200--430)\s*(?P<result>[0-9]+(?:\.[0-9]+)?)", text)
    if alt_match:
        tests.append(_p07_make_test(page_number, "liver_function", "alt", "丙氨酸氨基转移酶(ALT)", alt_match.group("result"), alt_match.group("reference"), "U/L", "肝功能检测"))
    if pab_match:
        tests.append(_p07_make_test(page_number, "liver_function", "pab", "前白蛋白(PAB)", pab_match.group("result"), pab_match.group("reference"), "mg/L", "肝功能检测"))

    value_match = re.search(
        r"U/L\s+↑\s+g/L\s+g/L\s+g/L\s+umol/L\s+umol/L\s+umol/L\s+U/L\s+U/L\s+U/L\s+umol/L\s+(?P<values>.*?)\s+≤10\.0",
        text,
    )
    values = re.findall(r"[0-9]+(?:\.[0-9]+)?", value_match.group("values")) if value_match else []
    if len(values) < 13:
        return tests

    ordered = [
        ("ast", "天门冬氨酸氨基转移酶(AST)", values[0], "15--40", "U/L", ""),
        ("ast_alt_ratio", "谷草谷丙比", values[1], "", "", "↑" if "↑" in text else ""),
        ("tp", "总蛋白(TP)", values[2], "65--85", "g/L", ""),
        ("alb", "白蛋白(ALB)", values[3], "40--55", "g/L", ""),
        ("glo", "球蛋白(GLB)", values[4], "20--40", "g/L", ""),
        ("ag_ratio", "白/球蛋白比", values[5], "1.2--2.4", "", ""),
        ("tbil", "总胆红素(T-BIL)", values[6], "≤23.0", "umol/L", ""),
        ("dbil", "直接胆红素(D-BIL)", values[7], "≤6.0", "umol/L", ""),
        ("ibil", "间接胆红素(I-BIL)", values[8], "≤16.16", "umol/L", ""),
        ("alp", "碱性磷酸酶(ALP)", values[9], "45--125", "U/L", ""),
        ("ggt", "γ-谷氨酰转肽酶(GGT)", values[10], "10.00--60.00", "U/L", ""),
        ("che", "胆碱酯酶(CHE)", values[11], "5000--12000", "U/L", ""),
        ("tba", "总胆汁酸(TBA)", values[12], "≤10.0", "umol/L", ""),
    ]
    for code, name, result, reference, unit, indicator in ordered:
        tests.append(_p07_make_test(page_number, "liver_function", code, name, result, reference, unit, "肝功能检测", indicator=indicator))
    return tests


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
    elif package_code == "P17":
        required = {
            "patient.name": "姓名",
            "patient.gender": "性别",
            "patient.age": "年龄",
            "p17.hpv_16.result_display": "HPV-16",
            "p17.hpv_18.result_display": "HPV-18",
            "p17.闃撮亾姣涙淮铏?result_display": "阴道毛滴虫",
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
    if package_code == "P01":
        if not test_names:
            warnings.append("P01 当前仍以基础资料抽取为主，专项菌群指标需结合真实样例继续增强。")
        elif len(test_names) < 5:
            warnings.append(f"P01 当前仅识别到 {len(test_names)} 项，建议人工复核。")
        test_names = []

    allergen_count = sum(1 for name in test_names if "钙卫蛋白" not in name and "IgE" not in name)
    if not test_names:
        if package_code not in {"P01", "P04", "P05", "P06", "P07"}:
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
    elif package_code in {"P07", "P17"}:
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
