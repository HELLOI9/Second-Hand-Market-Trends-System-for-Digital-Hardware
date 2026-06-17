"""固定监控硬件池（默认商品）。

每个条目带 validation_rule：品类通用约束 + 型号专属约束，
作为最高优先级规则注入 LLM 校验提示词。/reset 重置时会一并写回，
因此默认商品的规则可长期保留。用户新增的非默认商品不在此列。
"""

# 各品类通用排除项（拼在每条规则前，作为该品类的共同约束）
CPU_COMMON = "排除板U套装/主板CPU套装、整机/准系统、笔记本移动版CPU、ES/QS测试不显正显版本（除非标题明确正式版）、仅扣具/支架/散热器。盒装与散片均有效。"
GPU_COMMON = "排除笔记本/移动版显卡、显卡支架/水冷头/背板/延长线等配件、亮机卡/亮机用、整机拆但只卖整机的。矿卡/全新/二手/拆机/公版/非公均有效。"
MEM_COMMON = "必须是成套两根（套条/2条），排除单根/单条、笔记本SO-DIMM内存（除非标题明确台式机/DIMM）、纯马甲/散热片配件。"
SSD_COMMON = "必须是M.2 NVMe固态硬盘本体，排除移动固态/便携硬盘、SATA固态、固态硬盘盒/扩展卡、机械硬盘、U盘。"


HARDWARE_POOL = [
    # === CPU - Intel Ultra ===
    {"name": "Ultra 9 285K",  "category": "cpu", "search_keywords": ["Ultra 9 285K"],  "validation_rule": CPU_COMMON + " 必须是 Ultra 9 285K，排除 265K/245K 等其他 Ultra 型号。"},
    {"name": "Ultra 7 265K",  "category": "cpu", "search_keywords": ["Ultra 7 265K"],  "validation_rule": CPU_COMMON + " 必须是 Ultra 7 265K（带核显），排除无核显的 265KF、以及 285K/245K。"},
    {"name": "Ultra 7 265KF", "category": "cpu", "search_keywords": ["Ultra 7 265KF"], "validation_rule": CPU_COMMON + " 必须是 Ultra 7 265KF（KF 无核显），排除带核显的 265K、以及 285K/245K。"},
    {"name": "Ultra 5 245K",  "category": "cpu", "search_keywords": ["Ultra 5 245K"],  "validation_rule": CPU_COMMON + " 必须是 Ultra 5 245K（带核显），排除无核显的 245KF、以及 285K/265K。"},
    {"name": "Ultra 5 245KF", "category": "cpu", "search_keywords": ["Ultra 5 245KF"], "validation_rule": CPU_COMMON + " 必须是 Ultra 5 245KF（KF 无核显），排除带核显的 245K、以及 285K/265K。"},

    # === CPU - Intel 14 代 ===
    {"name": "i9-14900K",  "category": "cpu", "search_keywords": ["i9 14900K"],  "validation_rule": CPU_COMMON + " 必须是 i9-14900K（带核显），排除无核显的 14900KF、以及 14900KS、13900K、14700K。"},
    {"name": "i9-14900KF", "category": "cpu", "search_keywords": ["14900KF"],    "validation_rule": CPU_COMMON + " 必须是 i9-14900KF（KF 无核显），排除带核显的 14900K、以及 14900KS、13900KF。"},
    {"name": "i7-14700K",  "category": "cpu", "search_keywords": ["i7 14700K"],  "validation_rule": CPU_COMMON + " 必须是 i7-14700K（带核显），排除无核显的 14700KF、以及 13700K、14900K、14600K。"},
    {"name": "i7-14700KF", "category": "cpu", "search_keywords": ["i7 14700KF"], "validation_rule": CPU_COMMON + " 必须是 i7-14700KF（KF 无核显），排除带核显的 14700K、以及 13700KF。"},
    {"name": "i5-14600K",  "category": "cpu", "search_keywords": ["i5 14600K"],  "validation_rule": CPU_COMMON + " 必须是 i5-14600K（带核显），排除无核显的 14600KF、以及 13600K、14700K、14500。"},
    {"name": "i5-14600KF", "category": "cpu", "search_keywords": ["i5 14600KF"], "validation_rule": CPU_COMMON + " 必须是 i5-14600KF（KF 无核显），排除带核显的 14600K、以及 13600KF。"},

    # === CPU - AMD 锐龙 9000 ===
    {"name": "R9-9950X",   "category": "cpu", "search_keywords": ["9950X"],   "validation_rule": CPU_COMMON + " 必须是 R9 9950X，排除带 3D 缓存的 9950X3D、以及 9900X/7950X。"},
    {"name": "R9-9900X",   "category": "cpu", "search_keywords": ["9900X"],   "validation_rule": CPU_COMMON + " 必须是 R9 9900X，排除 9900X3D、9950X、7900X。"},
    {"name": "R7-9700X",   "category": "cpu", "search_keywords": ["9700X"],   "validation_rule": CPU_COMMON + " 必须是 R7 9700X，排除 9800X3D、9600X、7700X。"},
    {"name": "R5-9600X",   "category": "cpu", "search_keywords": ["9600X"],   "validation_rule": CPU_COMMON + " 必须是 R5 9600X，排除 9700X、9500F、7600X。"},
    {"name": "R5-9500F",   "category": "cpu", "search_keywords": ["9500F"],   "validation_rule": CPU_COMMON + " 必须是 R5 9500F（无核显 F），排除 9600X、9500、7500F。"},
    {"name": "R9-9950X3D", "category": "cpu", "search_keywords": ["9950X3D"], "validation_rule": CPU_COMMON + " 必须是 R9 9950X3D（带 3D 缓存），排除不带 3D 的 9950X、以及 9800X3D、9900X3D。"},
    {"name": "R7-9850X3D", "category": "cpu", "search_keywords": ["9850X3D"], "validation_rule": CPU_COMMON + " 必须是 R7 9850X3D，排除 9800X3D、9950X3D。"},
    {"name": "R7-9800X3D", "category": "cpu", "search_keywords": ["9800X3D"], "validation_rule": CPU_COMMON + " 必须是 R7 9800X3D，排除 9850X3D、7800X3D、9700X。"},
    {"name": "R7-7800X3D", "category": "cpu", "search_keywords": ["7800X3D"], "validation_rule": CPU_COMMON + " 必须是 R7 7800X3D，排除新一代 9800X3D、以及 7700X、5800X3D。"},
    {"name": "R5-7500F",   "category": "cpu", "search_keywords": ["7500F"],   "validation_rule": CPU_COMMON + " 必须是 R5 7500F（无核显 F），排除 7600X、9500F、5600。"},

    # === GPU - NVIDIA 50 系 ===
    {"name": "RTX 5090",        "category": "gpu", "search_keywords": ["RTX 5090"],        "validation_rule": GPU_COMMON + " 必须是 RTX 5090（非 D 版、非 V2），排除国行特供 5090D / 5090D V2、以及 5080。"},
    {"name": "RTX 5090D",       "category": "gpu", "search_keywords": ["RTX 5090D"],       "validation_rule": GPU_COMMON + " 必须是 RTX 5090D（国行 D 版，初版/非 V2），排除标准版 5090、新版 5090D V2。"},
    {"name": "RTX 5090D V2",    "category": "gpu", "search_keywords": ["RTX 5090D V2"],    "validation_rule": GPU_COMMON + " 必须是 RTX 5090D V2（新修订版），排除标准版 5090、初版 5090D。"},
    {"name": "RTX 5080",        "category": "gpu", "search_keywords": ["RTX 5080"],        "validation_rule": GPU_COMMON + " 必须是 RTX 5080，排除 5090/5090D、5070 Ti。"},
    {"name": "RTX 5070 TI",     "category": "gpu", "search_keywords": ["RTX 5070 Ti"],     "validation_rule": GPU_COMMON + " 必须是 RTX 5070 Ti，排除不带 Ti 的 5070、以及 5080。"},
    {"name": "RTX 5070",        "category": "gpu", "search_keywords": ["RTX 5070"],        "validation_rule": GPU_COMMON + " 必须是 RTX 5070（不带 Ti），排除 5070 Ti、5060 Ti、5080。"},
    {"name": "RTX 5060 TI 8GB", "category": "gpu", "search_keywords": ["RTX 5060 Ti 8G"],  "validation_rule": GPU_COMMON + " 必须是 RTX 5060 Ti 8GB 显存版，排除 16GB 版、不带 Ti 的 5060。"},
    {"name": "RTX 5060 TI 16GB","category": "gpu", "search_keywords": ["RTX 5060 Ti 16G"], "validation_rule": GPU_COMMON + " 必须是 RTX 5060 Ti 16GB 显存版，排除 8GB 版、不带 Ti 的 5060。"},
    {"name": "RTX 5060",        "category": "gpu", "search_keywords": ["RTX 5060"],        "validation_rule": GPU_COMMON + " 必须是 RTX 5060（不带 Ti），排除 5060 Ti、5050、5070。"},
    {"name": "RTX 5050",        "category": "gpu", "search_keywords": ["RTX 5050"],        "validation_rule": GPU_COMMON + " 必须是 RTX 5050，排除 5060、4060。"},

    # === GPU - AMD RX 9000 ===
    {"name": "RX 9070 XT",      "category": "gpu", "search_keywords": ["RX 9070 XT"],      "validation_rule": GPU_COMMON + " 必须是 RX 9070 XT，排除不带 XT 的 9070、以及 9070 GRE。"},
    {"name": "RX 9070",         "category": "gpu", "search_keywords": ["RX 9070"],         "validation_rule": GPU_COMMON + " 必须是 RX 9070（不带 XT、非 GRE），排除 9070 XT、9070 GRE。"},
    {"name": "RX 9070 GRE",     "category": "gpu", "search_keywords": ["RX 9070 GRE"],     "validation_rule": GPU_COMMON + " 必须是 RX 9070 GRE 特供版，排除 9070、9070 XT。"},
    {"name": "RX 9060 XT 16GB", "category": "gpu", "search_keywords": ["RX 9060 XT 16G"],  "validation_rule": GPU_COMMON + " 必须是 RX 9060 XT 16GB 显存版，排除 8GB 版、9070 系列。"},
    {"name": "RX 9060 XT 8GB",  "category": "gpu", "search_keywords": ["RX 9060 XT 8G"],   "validation_rule": GPU_COMMON + " 必须是 RX 9060 XT 8GB 显存版，排除 16GB 版、9070 系列。"},

    # === GPU - Intel Arc ===
    {"name": "ARC B580",        "category": "gpu", "search_keywords": ["Arc B580"],        "validation_rule": GPU_COMMON + " 必须是 Intel Arc B580，排除 B570、A 系列 Arc。"},
    {"name": "ARC B570",        "category": "gpu", "search_keywords": ["Arc B570"],        "validation_rule": GPU_COMMON + " 必须是 Intel Arc B570，排除 B580、A 系列 Arc。"},

    # === GPU - NVIDIA 40 系 ===
    {"name": "RTX 4090",         "category": "gpu", "search_keywords": ["4090 24g"],           "validation_rule": GPU_COMMON + " 必须是 RTX 4090 24GB，排除 4090D、4080。注意区分魔改 48G 等非常规版（标题写 4090 即有效）。"},
    {"name": "RTX 4080 Super",   "category": "gpu", "search_keywords": ["RTX 4080 Super"],     "validation_rule": GPU_COMMON + " 必须是 RTX 4080 Super，排除不带 Super 的 4080、以及 4070 Ti Super。"},
    {"name": "RTX 4080",         "category": "gpu", "search_keywords": ["RTX 4080"],           "validation_rule": GPU_COMMON + " 必须是 RTX 4080（不带 Super），排除 4080 Super、4090。"},
    {"name": "RTX 4070 TI Super","category": "gpu", "search_keywords": ["RTX 4070 Ti Super"], "validation_rule": GPU_COMMON + " 必须是 RTX 4070 Ti Super，排除 4070 Ti（无 Super）、4070 Super、4080 Super。"},
    {"name": "RTX 4070 Super",   "category": "gpu", "search_keywords": ["RTX 4070 Super"],     "validation_rule": GPU_COMMON + " 必须是 RTX 4070 Super，排除 4070 Ti Super、4070 Ti、不带 Super 的 4070。"},
    {"name": "RTX 4070",         "category": "gpu", "search_keywords": ["RTX 4070"],           "validation_rule": GPU_COMMON + " 必须是 RTX 4070（不带 Super/Ti），排除 4070 Super、4070 Ti、4070 Ti Super。"},
    {"name": "RTX 4060 TI 16G",  "category": "gpu", "search_keywords": ["RTX 4060 Ti 16G"],    "validation_rule": GPU_COMMON + " 必须是 RTX 4060 Ti 16GB 显存版，排除 8GB 版、不带 Ti 的 4060。"},
    {"name": "RTX 4060",         "category": "gpu", "search_keywords": ["RTX 4060"],           "validation_rule": GPU_COMMON + " 必须是 RTX 4060（不带 Ti），排除 4060 Ti、4050、4070。"},

    # === GPU - AMD RX 7000 ===
    {"name": "RX 7900 XTX",     "category": "gpu", "search_keywords": ["RX 7900 XTX"],     "validation_rule": GPU_COMMON + " 必须是 RX 7900 XTX，排除 7900 XT、7900 GRE。"},
    {"name": "RX 7900 XT",      "category": "gpu", "search_keywords": ["RX 7900 XT"],      "validation_rule": GPU_COMMON + " 必须是 RX 7900 XT，排除 7900 XTX、7900 GRE、7800 XT。"},
    {"name": "RX 7800 XT",      "category": "gpu", "search_keywords": ["RX 7800 XT"],      "validation_rule": GPU_COMMON + " 必须是 RX 7800 XT，排除 7900 XT、7700 XT。"},
    {"name": "RX 7700 XT",      "category": "gpu", "search_keywords": ["RX 7700 XT"],      "validation_rule": GPU_COMMON + " 必须是 RX 7700 XT，排除 7800 XT、7600。"},
    {"name": "RX 7600",         "category": "gpu", "search_keywords": ["RX 7600"],         "validation_rule": GPU_COMMON + " 必须是 RX 7600（不带 XT），排除 7600 XT、7700 XT。"},

    # === 内存 ===
    {"name": "DDR4 8GB*2",  "category": "memory", "search_keywords": ["DDR4 8Gx2"],  "validation_rule": MEM_COMMON + " 必须是 DDR4、单根 8GB×2（共 16GB）套条，排除 DDR5、单根 16GB、其他容量。"},
    {"name": "DDR4 16GB*2", "category": "memory", "search_keywords": ["DDR4 16Gx2"], "validation_rule": MEM_COMMON + " 必须是 DDR4、单根 16GB×2（共 32GB）套条，排除 DDR5、单根 8GB/32GB、其他容量。"},
    {"name": "DDR5 16GB*2", "category": "memory", "search_keywords": ["DDR5 16Gx2"], "validation_rule": MEM_COMMON + " 必须是 DDR5、单根 16GB×2（共 32GB）套条，排除 DDR4、单根容量、24GB/32GB×2。"},
    {"name": "DDR5 24GB*2", "category": "memory", "search_keywords": ["DDR5 24Gx2"], "validation_rule": MEM_COMMON + " 必须是 DDR5、单根 24GB×2（共 48GB）套条，排除 DDR4、16GB/32GB×2。"},
    {"name": "DDR5 32GB*2", "category": "memory", "search_keywords": ["DDR5 32Gx2"], "validation_rule": MEM_COMMON + " 必须是 DDR5、单根 32GB×2（共 64GB）套条，排除 DDR4、16GB/24GB/48GB×2。"},
    {"name": "DDR5 48GB*2", "category": "memory", "search_keywords": ["DDR5 48Gx2"], "validation_rule": MEM_COMMON + " 必须是 DDR5、单根 48GB×2（共 96GB）套条，排除 DDR4、24GB/32GB×2。"},

    # === 固态硬盘 ===
    {"name": "PCIe 3.0 1TB", "category": "ssd", "search_keywords": ["PCIe 3.0 SSD 1TB 固态"], "validation_rule": SSD_COMMON + " 必须是 PCIe 3.0、1TB 容量，排除 PCIe 4.0/5.0、512GB、2TB。"},
    {"name": "PCIe 3.0 2TB", "category": "ssd", "search_keywords": ["PCIe 3.0 SSD 2TB 固态"], "validation_rule": SSD_COMMON + " 必须是 PCIe 3.0、2TB 容量，排除 PCIe 4.0/5.0、1TB、4TB。"},
    {"name": "PCIe 4.0 1TB", "category": "ssd", "search_keywords": ["PCIe 4.0 SSD 1TB 固态"], "validation_rule": SSD_COMMON + " 必须是 PCIe 4.0、1TB 容量，排除 PCIe 3.0/5.0、512GB、2TB。"},
    {"name": "PCIe 4.0 2TB", "category": "ssd", "search_keywords": ["PCIe 4.0 SSD 2TB 固态"], "validation_rule": SSD_COMMON + " 必须是 PCIe 4.0、2TB 容量，排除 PCIe 3.0/5.0、1TB、4TB。"},
]


SEARCH_KEYWORDS_BY_NAME = {
    item["name"]: item["search_keywords"]
    for item in HARDWARE_POOL
}


def get_search_keywords(hardware_name: str) -> list[str]:
    try:
        return SEARCH_KEYWORDS_BY_NAME[hardware_name]
    except KeyError as exc:
        raise KeyError(f"Hardware [{hardware_name}] not found in HARDWARE_POOL") from exc
