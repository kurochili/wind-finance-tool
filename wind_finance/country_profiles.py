"""
wind_finance.country_profiles
=============================
东南亚及东亚各国风电项目默认融资/税费参数 + 市场基准数据

选择国家后自动填充利率、税率等默认值，用户可手动覆盖。
数据基于公开政策文件和行业经验，仅供参考，需根据实际项目更新。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


@dataclass
class MarketBenchmark:
    """单条市场基准数据（IRR / WACC / 实际案例等）"""
    metric: str            # "Equity IRR" / "Project IRR" / "WACC" / "Hurdle IRR"
    project_type: str      # "onshore" / "offshore" / "nearshore" / "all"
    value_low: float       # 区间下限 (百分比, 如 12.0 = 12%)
    value_high: float      # 区间上限
    source: str            # 来源简称
    source_url: str = ""   # 来源链接
    year: int = 2025       # 数据年份
    note: str = ""         # 备注


@dataclass
class CountryProfile:
    """国家/地区默认财务参数"""

    country_name: str                       # 国家名称 (英文)
    country_name_cn: str                    # 国家名称 (中文)
    currency: str                           # 当地货币代码
    exchange_rate_to_usd: float             # 当地货币兑 USD 汇率（1 USD = ? 当地货币）

    # ---- 融资 ----
    typical_equity_ratio: float             # 典型资本金比例（小数）
    typical_loan_rate: float                # 典型长期贷款利率（小数）
    typical_loan_term: int                  # 典型贷款期限（年）

    # ---- 税费 ----
    corporate_income_tax_rate: float        # 企业所得税标准税率（小数）
    vat_rate: float                         # 增值税 / 销售税率（小数）
    has_wind_tax_incentive: bool            # 是否有风电税收优惠
    tax_incentive_description: str          # 税收优惠简述

    # 所得税优惠：(免征起始年, 免征结束年, 免征期税率, 减半起始年, 减半结束年, 减半期税率)
    income_tax_holiday: Tuple[int, int, float, int, int, float] = (1, 1, 0.0, 1, 1, 0.0)

    urban_maintenance_tax_rate: float = 0.0
    education_surcharge_rate: float = 0.0

    # ---- 电价参考 ----
    onshore_tariff_range: Tuple[float, float] = (0.0, 0.0)
    offshore_tariff_range: Tuple[float, float] = (0.0, 0.0)

    # ---- 市场基准 ----
    benchmarks: List[MarketBenchmark] = field(default_factory=list)

    # ---- 元数据 ----
    data_updated: str = "2025-01"


# ════════════════════════════════════════════════════════════════════════════
# 各国预置参数
# ════════════════════════════════════════════════════════════════════════════

_PROFILES: Dict[str, CountryProfile] = {}


def _register(p: CountryProfile) -> None:
    _PROFILES[p.country_name.lower()] = p


_register(CountryProfile(
    country_name="China",
    country_name_cn="中国",
    currency="CNY",
    exchange_rate_to_usd=7.1,
    typical_equity_ratio=0.25,
    typical_loan_rate=0.0325,
    typical_loan_term=15,
    corporate_income_tax_rate=0.25,
    vat_rate=0.13,
    has_wind_tax_incentive=True,
    tax_incentive_description="三免三减半(前3年免征,4-6年12.5%); 增值税即征即退50%",
    income_tax_holiday=(1, 3, 0.0, 4, 6, 0.125),
    urban_maintenance_tax_rate=0.05,
    education_surcharge_rate=0.05,
    onshore_tariff_range=(0.027, 0.058),
    offshore_tariff_range=(0.056, 0.078),
    benchmarks=[
        MarketBenchmark("Equity IRR", "onshore", 8.0, 10.0, "NDRC 发改委基准收益率", "", 2024, "国内通用基准"),
        MarketBenchmark("Equity IRR", "offshore", 8.0, 10.0, "NDRC 发改委基准收益率", "", 2024, "海上风电同样适用"),
        MarketBenchmark("Equity IRR", "onshore", 8.0, 12.0, "BNEF 1H 2025 中国市场", "", 2025, "平价上网后项目实际范围"),
        MarketBenchmark("WACC", "all", 4.5, 6.0, "IRENA Renewable Power Generation Costs 2023", "https://www.irena.org/costs", 2023, "含税后加权平均"),
        MarketBenchmark("Project IRR", "onshore", 6.5, 9.0, "CWEA 中国风能协会统计", "", 2024, "全投资税后 IRR"),
        MarketBenchmark("Project IRR", "offshore", 6.0, 8.0, "CWEA 中国风能协会统计", "", 2024, "全投资税后 IRR"),
        MarketBenchmark("Equity IRR", "offshore", 9.5, 11.0, "江苏如东 H6 项目(400MW)", "", 2023, "实际案例"),
        MarketBenchmark("Equity IRR", "onshore", 10.0, 13.0, "内蒙古乌兰察布 600MW 基地", "", 2024, "UHV 外送基地项目"),
    ],
    data_updated="2026-02",
))

_register(CountryProfile(
    country_name="Vietnam",
    country_name_cn="越南",
    currency="VND",
    exchange_rate_to_usd=25700,
    typical_equity_ratio=0.30,
    typical_loan_rate=0.08,
    typical_loan_term=15,
    corporate_income_tax_rate=0.20,
    vat_rate=0.10,
    has_wind_tax_incentive=True,
    tax_incentive_description="企业所得税4免9减半; 进口设备免增值税",
    income_tax_holiday=(1, 4, 0.0, 5, 13, 0.10),
    onshore_tariff_range=(0.070, 0.076),
    offshore_tariff_range=(0.077, 0.085),
    benchmarks=[
        MarketBenchmark("Equity IRR", "all", 12.0, 12.0, "MOIT Decision 1824 (官方定价基准)", "", 2020, "越南工贸部 FIT 定价所用基准 Equity IRR"),
        MarketBenchmark("Equity IRR", "onshore", 10.5, 13.5, "BNEF Vietnam Wind Market Outlook 2024", "", 2024, "国际开发商要求的 hurdle rate"),
        MarketBenchmark("Equity IRR", "offshore", 10.0, 14.0, "BNEF Vietnam Wind Market Outlook 2024", "", 2024, "海上风电投资人预期"),
        MarketBenchmark("WACC", "all", 8.0, 10.0, "World Bank Vietnam Energy Outlook 2023", "https://www.worldbank.org", 2023, "VND 计价; USD 计价约 6-7%"),
        MarketBenchmark("WACC", "all", 7.5, 9.5, "IRENA Cost of Financing RE 2023", "https://www.irena.org", 2023, "新兴市场 RE 加权成本"),
        MarketBenchmark("Project IRR", "nearshore", 6.0, 7.0, "Ha Tinh 项目内部测算", "", 2025, "全投资税后; CAPEX 1400-1500 USD/kW"),
        MarketBenchmark("Project IRR", "onshore", 8.0, 10.0, "Quang Tri 风电集群(已投运)", "", 2023, "实际运营数据反推"),
        MarketBenchmark("Equity IRR", "nearshore", 6.0, 8.0, "Ha Tinh 近海项目(MySE8.5-230/MySE10-242)", "", 2025, "实际案例; 1987.4 VND/kWh 电价"),
        MarketBenchmark("Project IRR", "offshore", 7.0, 9.0, "PDP8 规划海上项目预期", "", 2024, "越南第八个电力发展规划"),
    ],
    data_updated="2025-05",
))

_register(CountryProfile(
    country_name="Philippines",
    country_name_cn="菲律宾",
    currency="PHP",
    exchange_rate_to_usd=56.0,
    typical_equity_ratio=0.30,
    typical_loan_rate=0.07,
    typical_loan_term=15,
    corporate_income_tax_rate=0.25,
    vat_rate=0.12,
    has_wind_tax_incentive=True,
    tax_incentive_description="RE法案: 7年所得税免征; 进口设备零关税; 10%优惠税率",
    income_tax_holiday=(1, 7, 0.0, 8, 14, 0.10),
    onshore_tariff_range=(0.070, 0.100),
    offshore_tariff_range=(0.090, 0.120),
    benchmarks=[
        MarketBenchmark("Equity IRR", "onshore", 12.0, 15.0, "DOE RE Policy Framework", "", 2023, "菲律宾能源部 RE 法案项目预期"),
        MarketBenchmark("Equity IRR", "offshore", 12.0, 16.0, "BNEF SE Asia RE Outlook 2024", "", 2024, "海上风电开发商要求"),
        MarketBenchmark("WACC", "all", 8.0, 11.0, "ADB Philippines Energy Assessment 2023", "https://www.adb.org", 2023, "新兴市场较高融资成本"),
        MarketBenchmark("Project IRR", "onshore", 9.0, 12.0, "Burgos Wind Farm (150MW, Ilocos Norte)", "", 2023, "菲律宾最大在运风电场"),
        MarketBenchmark("Hurdle IRR", "all", 13.0, 15.0, "IRENA Renewable Energy Statistics 2024", "https://www.irena.org", 2024, "东南亚新兴市场门槛"),
    ],
    data_updated="2025-01",
))

_register(CountryProfile(
    country_name="Thailand",
    country_name_cn="泰国",
    currency="THB",
    exchange_rate_to_usd=35.0,
    typical_equity_ratio=0.30,
    typical_loan_rate=0.05,
    typical_loan_term=15,
    corporate_income_tax_rate=0.20,
    vat_rate=0.07,
    has_wind_tax_incentive=True,
    tax_incentive_description="BOI优惠: 最长8年企业所得税免征; 进口设备免关税",
    income_tax_holiday=(1, 8, 0.0, 9, 13, 0.10),
    onshore_tariff_range=(0.075, 0.089),
    offshore_tariff_range=(0.0, 0.0),
    benchmarks=[
        MarketBenchmark("Equity IRR", "onshore", 10.0, 13.0, "EPPO Thailand PDP 2024", "", 2024, "泰国电力发展规划预期回报"),
        MarketBenchmark("WACC", "all", 6.0, 8.0, "IRENA Cost of Financing RE 2023", "https://www.irena.org", 2023, "东南亚中等水平"),
        MarketBenchmark("Project IRR", "onshore", 8.0, 11.0, "Korat Wind Farm 群 (呵叻府)", "", 2023, "泰国最大陆上风电集群"),
        MarketBenchmark("Hurdle IRR", "onshore", 11.0, 13.0, "BNEF SE Asia RE Outlook 2024", "", 2024, "国际开发商预期"),
    ],
    data_updated="2025-06",
))

_register(CountryProfile(
    country_name="Indonesia",
    country_name_cn="印度尼西亚",
    currency="IDR",
    exchange_rate_to_usd=15700,
    typical_equity_ratio=0.30,
    typical_loan_rate=0.09,
    typical_loan_term=12,
    corporate_income_tax_rate=0.22,
    vat_rate=0.11,
    has_wind_tax_incentive=True,
    tax_incentive_description="MEMR 5/2025: BOO模式; 可再生能源进口设备免增值税; 加速折旧; PPA最长30年",
    income_tax_holiday=(1, 5, 0.0, 6, 10, 0.11),
    onshore_tariff_range=(0.065, 0.095),
    offshore_tariff_range=(0.0, 0.0),
    benchmarks=[
        MarketBenchmark("Equity IRR", "onshore", 13.0, 16.0, "MEMR RUPTL 2021-2030", "", 2023, "PLN 购电协议下的开发商预期"),
        MarketBenchmark("WACC", "all", 9.0, 12.0, "World Bank Indonesia Energy Transition 2023", "https://www.worldbank.org", 2023, "印尼 RE 项目较高融资成本"),
        MarketBenchmark("Project IRR", "onshore", 10.0, 13.0, "Sidrap Wind Farm (75MW, 南苏拉威西)", "", 2023, "印尼首个商业化风电场"),
        MarketBenchmark("Hurdle IRR", "all", 14.0, 16.0, "BNEF SE Asia RE Outlook 2024", "", 2024, "高融资成本市场"),
    ],
    data_updated="2025-03",
))

_register(CountryProfile(
    country_name="Malaysia",
    country_name_cn="马来西亚",
    currency="MYR",
    exchange_rate_to_usd=4.5,
    typical_equity_ratio=0.30,
    typical_loan_rate=0.045,
    typical_loan_term=15,
    corporate_income_tax_rate=0.24,
    vat_rate=0.06,
    has_wind_tax_incentive=True,
    tax_incentive_description="绿色投资税收抵免(GITA); 进口绿色设备免税",
    income_tax_holiday=(1, 5, 0.0, 6, 10, 0.12),
    onshore_tariff_range=(0.060, 0.085),
    offshore_tariff_range=(0.0, 0.0),
    benchmarks=[
        MarketBenchmark("Equity IRR", "onshore", 10.0, 13.0, "SEDA Malaysia RE Roadmap", "", 2024, "马来西亚可持续能源发展局"),
        MarketBenchmark("WACC", "all", 6.5, 8.5, "IRENA Cost of Financing RE 2023", "https://www.irena.org", 2023, "东南亚中低水平"),
        MarketBenchmark("Project IRR", "onshore", 8.0, 11.0, "马来西亚沙巴/沙捞越风电前期项目", "", 2024, "MIDA 投资数据"),
        MarketBenchmark("Hurdle IRR", "onshore", 11.0, 14.0, "BNEF SE Asia RE Outlook 2024", "", 2024, "开发商预期门槛"),
    ],
    data_updated="2025-01",
))

_register(CountryProfile(
    country_name="Cambodia",
    country_name_cn="柬埔寨",
    currency="KHR",
    exchange_rate_to_usd=4100,
    typical_equity_ratio=0.30,
    typical_loan_rate=0.10,
    typical_loan_term=12,
    corporate_income_tax_rate=0.20,
    vat_rate=0.10,
    has_wind_tax_incentive=True,
    tax_incentive_description="QIP优惠: 最长9年企业所得税免征",
    income_tax_holiday=(1, 9, 0.0, 10, 12, 0.10),
    onshore_tariff_range=(0.070, 0.100),
    offshore_tariff_range=(0.0, 0.0),
    benchmarks=[
        MarketBenchmark("Equity IRR", "onshore", 14.0, 18.0, "ADB Cambodia Energy Sector Assessment 2023", "https://www.adb.org", 2023, "高风险市场溢价"),
        MarketBenchmark("WACC", "all", 10.0, 13.0, "World Bank Cambodia RE Assessment 2023", "https://www.worldbank.org", 2023, "前沿市场高融资成本"),
        MarketBenchmark("Project IRR", "onshore", 10.0, 14.0, "柬埔寨暹粒/磅清扬风电前期项目", "", 2024, "早期开发阶段"),
        MarketBenchmark("Hurdle IRR", "all", 15.0, 18.0, "BNEF Frontier Market RE 2024", "", 2024, "前沿市场高门槛"),
    ],
    data_updated="2025-01",
))

_register(CountryProfile(
    country_name="Japan",
    country_name_cn="日本",
    currency="JPY",
    exchange_rate_to_usd=150,
    typical_equity_ratio=0.30,
    typical_loan_rate=0.015,
    typical_loan_term=18,
    corporate_income_tax_rate=0.2337,
    vat_rate=0.10,
    has_wind_tax_incentive=True,
    tax_incentive_description="FIT/FIP制度; 绿色投资减税",
    income_tax_holiday=(1, 1, 0.2337, 1, 1, 0.2337),
    onshore_tariff_range=(0.100, 0.160),
    offshore_tariff_range=(0.190, 0.260),
    benchmarks=[
        MarketBenchmark("Equity IRR", "onshore", 6.0, 9.0, "METI FIT/FIP 制度设计基础", "", 2024, "日本经产省 FIT 定价隐含收益率"),
        MarketBenchmark("Equity IRR", "offshore", 8.0, 12.0, "JWPA 日本风力发电协会", "", 2024, "海上风电投资预期"),
        MarketBenchmark("WACC", "all", 3.0, 5.0, "IEA Cost of Capital Observatory 2024", "https://www.iea.org", 2024, "低利率环境下融资成本"),
        MarketBenchmark("Project IRR", "onshore", 5.0, 8.0, "日本陆上风电项目统计 (METI)", "", 2024, "FIT 电价下"),
        MarketBenchmark("Project IRR", "offshore", 6.0, 9.0, "秋田県能代/三種 洋上風力 (140MW)", "", 2024, "日本首批商业海上风电"),
        MarketBenchmark("Hurdle IRR", "offshore", 8.0, 10.0, "BNEF Japan Offshore Wind 2024", "", 2024, "Round 2/3 竞标预期"),
    ],
    data_updated="2025-01",
))

_register(CountryProfile(
    country_name="South Korea",
    country_name_cn="韩国",
    currency="KRW",
    exchange_rate_to_usd=1350,
    typical_equity_ratio=0.30,
    typical_loan_rate=0.035,
    typical_loan_term=15,
    corporate_income_tax_rate=0.242,
    vat_rate=0.10,
    has_wind_tax_incentive=True,
    tax_incentive_description="REC制度; RPS义务比例; 固定价格合约竞标",
    income_tax_holiday=(1, 1, 0.242, 1, 1, 0.242),
    onshore_tariff_range=(0.080, 0.120),
    offshore_tariff_range=(0.127, 0.175),
    benchmarks=[
        MarketBenchmark("Equity IRR", "onshore", 7.0, 10.0, "MOTIE 韩国产业通商资源部", "", 2024, "RPS/REC 体系下"),
        MarketBenchmark("Equity IRR", "offshore", 8.0, 12.0, "KWEIA 韩国风能产业协会", "", 2024, "海上风电开发商预期"),
        MarketBenchmark("WACC", "all", 4.5, 6.5, "IEA Cost of Capital Observatory 2024", "https://www.iea.org", 2024, "OECD 成员国较低融资成本"),
        MarketBenchmark("Project IRR", "offshore", 7.0, 10.0, "西南海 해상풍력 (전남 신안, 8.2GW规划)", "", 2024, "韩国最大海上风电规划"),
        MarketBenchmark("Hurdle IRR", "offshore", 9.0, 11.0, "BNEF South Korea Offshore Wind 2024", "", 2024, "竞标项目门槛"),
    ],
    data_updated="2026-04",
))

_register(CountryProfile(
    country_name="Australia",
    country_name_cn="澳大利亚",
    currency="AUD",
    exchange_rate_to_usd=1.55,
    typical_equity_ratio=0.30,
    typical_loan_rate=0.055,
    typical_loan_term=15,
    corporate_income_tax_rate=0.30,
    vat_rate=0.10,
    has_wind_tax_incentive=True,
    tax_incentive_description="LRET大型可再生能源目标; LGC绿证收入; 加速折旧",
    income_tax_holiday=(1, 1, 0.30, 1, 1, 0.30),
    onshore_tariff_range=(0.050, 0.090),
    offshore_tariff_range=(0.0, 0.0),
    benchmarks=[
        MarketBenchmark("Equity IRR", "onshore", 7.0, 10.0, "Clean Energy Council Australia", "", 2024, "含 LGC 绿证收入"),
        MarketBenchmark("WACC", "all", 5.0, 7.0, "IRENA Cost of Financing RE 2023", "https://www.irena.org", 2023, "发达市场中等水平"),
        MarketBenchmark("WACC", "all", 5.5, 7.5, "IEA Cost of Capital Observatory 2024", "https://www.iea.org", 2024, "加息周期后有所上升"),
        MarketBenchmark("Project IRR", "onshore", 6.0, 9.0, "Goldwind Stockyard Hill (530MW, Victoria)", "", 2024, "澳洲最大运营风电场"),
        MarketBenchmark("Hurdle IRR", "onshore", 8.0, 10.0, "BNEF Australia RE Outlook 2024", "", 2024, "PPA 市场化竞标"),
    ],
    data_updated="2026-03",
))

_register(CountryProfile(
    country_name="Taiwan",
    country_name_cn="中国台湾",
    currency="TWD",
    exchange_rate_to_usd=32,
    typical_equity_ratio=0.30,
    typical_loan_rate=0.025,
    typical_loan_term=18,
    corporate_income_tax_rate=0.20,
    vat_rate=0.05,
    has_wind_tax_incentive=True,
    tax_incentive_description="FIT制度(2025: 4.5085TWD/kWh 20年); 加速折旧; 投资抵减",
    income_tax_holiday=(1, 5, 0.0, 6, 10, 0.10),
    onshore_tariff_range=(0.065, 0.085),
    offshore_tariff_range=(0.106, 0.161),
    benchmarks=[
        MarketBenchmark("Equity IRR", "offshore", 7.0, 10.0, "经济部能源局 FIT 定价机制", "", 2024, "FIT 电价隐含回报"),
        MarketBenchmark("Equity IRR", "onshore", 8.0, 11.0, "经济部能源局 RE 政策框架", "", 2024, "陆上风电 FIT"),
        MarketBenchmark("WACC", "all", 4.0, 6.0, "IEA Cost of Capital Observatory 2024", "https://www.iea.org", 2024, "低利率经济体"),
        MarketBenchmark("Project IRR", "offshore", 6.0, 9.0, "海洋风电 Formosa 1 (128MW)", "", 2023, "台湾首个商业海上风电"),
        MarketBenchmark("Project IRR", "offshore", 7.0, 9.0, "沃旭大彰化 Greater Changhua (900MW)", "", 2024, "Round 2 最大项目"),
        MarketBenchmark("Hurdle IRR", "offshore", 8.0, 10.0, "BNEF Taiwan Offshore Wind 2024", "", 2024, "Round 3 竞标预期"),
    ],
    data_updated="2025-12",
))


# ════════════════════════════════════════════════════════════════════════════
# 公共接口
# ════════════════════════════════════════════════════════════════════════════

SUPPORTED_COUNTRIES: list[str] = sorted(_PROFILES.keys())


def get_country_profile(country: str) -> Optional[CountryProfile]:
    """
    根据国家名称获取预置参数（大小写不敏感）

    Args:
        country: 国家英文名，如 "Vietnam", "China"

    Returns:
        CountryProfile 或 None（如果国家不在预置列表中）
    """
    return _PROFILES.get(country.lower())


def list_countries() -> list[tuple[str, str]]:
    """列出所有支持的国家（英文名, 中文名）"""
    return [(p.country_name, p.country_name_cn) for p in _PROFILES.values()]
