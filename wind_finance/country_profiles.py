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


# ════════════════════════════════════════════════════════════════════════════
# 分板块市场报告数据类
# ════════════════════════════════════════════════════════════════════════════

@dataclass
class OfficialIRRBenchmark:
    """官方/政府定价模型中的 IRR 基准"""
    source: str
    source_ref: str
    source_url: str
    project_type: str        # "onshore" / "offshore" / "nearshore" / "all"
    equity_irr: float        # 基准 Equity IRR (%)
    financing_structure: str
    notes: str = ""


@dataclass
class BNEFHurdleIRR:
    """BNEF 等国际研报 Hurdle IRR (含时间线预测)"""
    source: str
    report_name: str
    source_url: str
    year: int
    project_type: str        # "onshore" / "offshore" / "nearshore"
    current_value: str
    forecast_2030: str = ""
    forecast_2050: str = ""
    financing_assumption: str = ""


@dataclass
class ActualProjectCase:
    """实际项目 IRR 案例"""
    project_name: str
    project_type: str        # "onshore" / "offshore" / "nearshore"
    irr_value: str
    irr_type: str = "Equity IRR"
    capex_info: str = ""
    notes: str = ""
    source: str = ""
    source_url: str = ""


@dataclass
class WACCData:
    """WACC / 融资成本数据"""
    source: str
    source_url: str
    indicator: str
    value: str
    notes: str = ""


@dataclass
class MarketSummaryItem:
    """总结判断中的单项"""
    scenario: str
    irr_range: str


@dataclass
class CountryMarketReport:
    """某国家的完整市场报告"""
    official_benchmarks: List[OfficialIRRBenchmark] = field(default_factory=list)
    bnef_hurdles: List[BNEFHurdleIRR] = field(default_factory=list)
    actual_cases: List[ActualProjectCase] = field(default_factory=list)
    wacc_data: List[WACCData] = field(default_factory=list)
    summary: List[MarketSummaryItem] = field(default_factory=list)
    summary_conclusion: str = ""


@dataclass
class CountryOMDefaults:
    """国家推荐的运维计算默认值"""

    recommended_method: str = "fixed_escalation"

    # 固定单价法默认值
    onshore_base_om: float = 15.0      # $/kW/年
    offshore_base_om: float = 30.0     # $/kW/年
    escalation_rate: float = 0.02      # 2%

    # 投资百分比法默认值
    onshore_capex_pct: float = 0.015   # 1.5%
    offshore_capex_pct: float = 0.025  # 2.5%

    # 合同报价法默认值
    onshore_contract: str = ""         # 描述性文字
    offshore_contract: str = ""

    # 推荐理由
    rationale: str = ""

    # 行业数据来源
    sources: str = ""


@dataclass
class CountryProfile:
    """国家/地区默认财务参数"""

    country_name: str
    country_name_cn: str
    currency: str
    exchange_rate_to_usd: float

    # ---- 融资 ----
    typical_equity_ratio: float
    typical_loan_rate: float
    typical_loan_term: int

    # ---- 税费 ----
    corporate_income_tax_rate: float
    vat_rate: float
    has_wind_tax_incentive: bool
    tax_incentive_description: str

    income_tax_holiday: Tuple[int, int, float, int, int, float] = (1, 1, 0.0, 1, 1, 0.0)

    urban_maintenance_tax_rate: float = 0.0
    education_surcharge_rate: float = 0.0

    # ---- 电价参考 ----
    onshore_tariff_range: Tuple[float, float] = (0.0, 0.0)
    offshore_tariff_range: Tuple[float, float] = (0.0, 0.0)
    onshore_tariff_policy: str = ""
    offshore_tariff_policy: str = ""
    tariff_mechanism: str = ""

    # ---- 运维推荐 ----
    om_defaults: CountryOMDefaults = field(default_factory=CountryOMDefaults)

    # ---- 市场基准 ----
    benchmarks: List[MarketBenchmark] = field(default_factory=list)

    # ---- 分板块市场报告 ----
    market_report: CountryMarketReport = field(default_factory=CountryMarketReport)

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
    tariff_mechanism="Competitive bidding (market-based)",
    onshore_tariff_policy="2021+ full parity: competitive bidding, no subsidy. Regional benchmark 0.193-0.414 CNY/kWh (I-IV resource zones). Source: NDRC [2021] No.833",
    offshore_tariff_policy="2022+ full parity: competitive bidding by province. Reference: Guangdong 0.40-0.55 CNY/kWh, Fujian 0.38-0.45 CNY/kWh. Source: Provincial DRC announcements",
    om_defaults=CountryOMDefaults(
        recommended_method="chinese_feasibility",
        onshore_base_om=12.0, offshore_base_om=25.0, escalation_rate=0.02,
        onshore_capex_pct=0.012, offshore_capex_pct=0.020,
        rationale="中国项目通常采用可研标准算法，设计院和银行普遍认可。维修费按静态投资百分比递增是行业惯例。",
        sources="NDRC可研编制办法; CWEA行业统计; 各省设计院模板",
    ),
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
    market_report=CountryMarketReport(
        official_benchmarks=[
            OfficialIRRBenchmark(
                source="国家发改委 (NDRC) 建设项目经济评价方法与参数",
                source_ref="发改投资〔2006〕1325号 / 第三版参数",
                source_url="https://www.ndrc.gov.cn/",
                project_type="all",
                equity_irr=8.0,
                financing_structure="25%股权 + 75%债务",
                notes="全投资基准收益率8%, 资本金IRR通常要求10%以上; 风电项目普遍参照此基准",
            ),
        ],
        bnef_hurdles=[
            BNEFHurdleIRR(
                source="BloombergNEF",
                report_name="China Wind Power Market Outlook 2024",
                source_url="https://about.bnef.com/blog/china-wind-power-market-outlook-2024/",
                year=2024,
                project_type="onshore",
                current_value="10%",
                forecast_2030="8%",
                forecast_2050="7%",
                financing_assumption="债股比 75:25, 贷款期限 15年, 贷款利率 3.25%",
            ),
            BNEFHurdleIRR(
                source="BloombergNEF",
                report_name="China Wind Power Market Outlook 2024",
                source_url="https://about.bnef.com/blog/china-wind-power-market-outlook-2024/",
                year=2024,
                project_type="offshore",
                current_value="12%",
                forecast_2030="9%",
                forecast_2050="7.5%",
                financing_assumption="债股比 75:25, 贷款期限 18年, 贷款利率 3.5%",
            ),
        ],
        actual_cases=[
            ActualProjectCase(
                project_name="江苏如东 H6 海上风电项目 (400MW)",
                project_type="offshore",
                irr_value="~10%",
                irr_type="Equity IRR",
                capex_info="Capex: ~14000 CNY/kW",
                notes="2023年投运, 平价上网首批海上项目",
                source="中国风能协会 (CWEA) 统计年报 2024",
                source_url="http://www.cwea.org.cn/",
            ),
            ActualProjectCase(
                project_name="内蒙古乌兰察布 600MW 风电基地",
                project_type="onshore",
                irr_value="~8%",
                irr_type="Project IRR",
                capex_info="Capex: ~5500 CNY/kW",
                notes="UHV外送基地项目, 配套储能",
                source="国家能源局项目公示",
                source_url="http://zfxxgk.nea.gov.cn/",
            ),
        ],
        wacc_data=[
            WACCData(
                source="IRENA (2023)",
                source_url="https://www.irena.org/publications",
                indicator="中国陆上风电 WACC",
                value="4.5%",
                notes="全球最低水平之一, 受政策性银行低息贷款影响",
            ),
            WACCData(
                source="BloombergNEF (2024)",
                source_url="https://about.bnef.com/",
                indicator="中国可再生能源加权融资成本",
                value="~5%",
                notes="含国开行/农发行优惠贷款",
            ),
        ],
        summary=[
            MarketSummaryItem("发改委全投资基准收益率", "8%"),
            MarketSummaryItem("陆上风电 Equity IRR 实际范围", "8% ~ 12%"),
            MarketSummaryItem("海上风电 Equity IRR 实际范围", "8% ~ 10%"),
            MarketSummaryItem("国际开发商要求的门槛 Equity IRR", "10% ~ 12% (陆上), 10% ~ 14% (海上)"),
            MarketSummaryItem("长期趋势 (2030-2050)", "随平价上网推进, 预计降至 7% ~ 9%"),
        ],
        summary_conclusion=(
            "中国风电项目的 Equity IRR 目前在 8%~12% 区间, 海上风电约 8%~10%。"
            "得益于政策性银行低息贷款, 中国 WACC 为全球最低水平之一 (4.5%~6%)。"
            "随着平价上网全面推行和技术成本下降, IRR 门槛将逐步降低。"
        ),
    ),
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
    tariff_mechanism="FIT (transitioning to competitive bidding)",
    onshore_tariff_policy="Decision 39/2018/QD-TTg: FIT 8.5 UScent/kWh (1,928 VND) for 20 years. Decision 1508 (2025): pilot auction framework under development. Source: MOIT/EVN",
    offshore_tariff_policy="Decision 39/2018: Nearshore FIT 9.8 UScent/kWh (2,223 VND). Decision 1508/QD-BCT (2025.05.30): Nearshore FIT 2,186.1 VND/kWh (~0.085 USD), valid for 20 years. Offshore (6+ nautical miles): pending new decree. Source: MOIT",
    om_defaults=CountryOMDefaults(
        recommended_method="fixed_escalation",
        onshore_base_om=15.0, offshore_base_om=28.0, escalation_rate=0.02,
        onshore_capex_pct=0.015, offshore_capex_pct=0.025,
        rationale="越南海外项目建议采用固定单价法，与国际投资者和银行沟通更顺畅。近海项目O&M 25-35 $/kW/年(BNEF)。",
        sources="BNEF Vietnam RE Country Profile 2024; EVN tariff Decision 1508",
    ),
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
    market_report=CountryMarketReport(
        official_benchmarks=[
            OfficialIRRBenchmark(
                source="越南工贸部 (MOIT) 2025年电价框架",
                source_ref="Decision No. 1824/QĐ-BCT (2025年6月)",
                source_url="https://www.duanemorris.com/alerts/vietnam-issues-new-wind-power-pricing-framework-2025.html",
                project_type="onshore",
                equity_irr=12.0,
                financing_structure="30%股权 + 70%债务",
                notes="外债利率6.16%, 本地贷款利率9.12%, 平均贷款期限10年, 经济寿命20年",
            ),
            OfficialIRRBenchmark(
                source="越南工贸部 (MOIT) 2025年电价框架",
                source_ref="Decision No. 1824/QĐ-BCT (2025年6月)",
                source_url="https://www.duanemorris.com/alerts/vietnam-issues-new-wind-power-pricing-framework-2025.html",
                project_type="nearshore",
                equity_irr=12.0,
                financing_structure="30%股权 + 70%债务",
                notes="外债利率6.16%, 本地贷款利率9.12%, 平均贷款期限10年, 经济寿命20年",
            ),
        ],
        bnef_hurdles=[
            BNEFHurdleIRR(
                source="BloombergNEF",
                report_name="Vietnam: A Techno-Economic Analysis of Power Generation",
                source_url="https://about.bnef.com/blog/vietnam-a-techno-economic-analysis-of-power-generation/",
                year=2023,
                project_type="onshore",
                current_value="16%",
                forecast_2030="13.5%",
                forecast_2050="8.5%",
                financing_assumption="债股比 70:30, 贷款期限 15年, 债务成本 1000bps (2023) → 600bps (2050)",
            ),
            BNEFHurdleIRR(
                source="BloombergNEF",
                report_name="Vietnam: A Techno-Economic Analysis of Power Generation",
                source_url="https://about.bnef.com/blog/vietnam-a-techno-economic-analysis-of-power-generation/",
                year=2023,
                project_type="offshore",
                current_value="14%",
                forecast_2030="12%",
                forecast_2050="8.5%",
                financing_assumption="债股比 75:25, 贷款期限 15年, 债务成本 1000bps (2023) → 600bps (2050)",
            ),
            BNEFHurdleIRR(
                source="BloombergNEF",
                report_name="Vietnam: A Techno-Economic Analysis of Power Generation",
                source_url="https://about.bnef.com/blog/vietnam-a-techno-economic-analysis-of-power-generation/",
                year=2023,
                project_type="nearshore",
                current_value="~14%",
                forecast_2030="~12%",
                forecast_2050="~8.5%",
                financing_assumption="债股比 75:25, 贷款期限 15年, 债务成本 1000bps (2023) → 600bps (2050)",
            ),
        ],
        actual_cases=[
            ActualProjectCase(
                project_name="REE 近海风电项目 (Duyen Hai 48MW等)",
                project_type="nearshore",
                irr_value="~11%",
                irr_type="Equity IRR",
                capex_info="Capex: 440亿越盾/MW",
                notes="预计2026年中并网",
                source="Vietcap Securities (REE研报 2025年11月)",
                source_url="https://www.vietcap.com.vn/en/research",
            ),
            ActualProjectCase(
                project_name="平顺省 30MW 陆上风电",
                project_type="onshore",
                irr_value="12.4%",
                irr_type="Equity IRR",
                capex_info="NPV正值 $951,413",
                notes="WACC 5.8%, KfW 70%融资",
                source="Wind Power Project Appraisal (SlideShare)",
                source_url="https://www.slideshare.net/",
            ),
        ],
        wacc_data=[
            WACCData(
                source="IRENA (2023)",
                source_url="https://www.irena.org/publications",
                indicator="越南陆上风电 WACC",
                value="5.1%",
            ),
            WACCData(
                source="IRENA (2023)",
                source_url="https://www.irena.org/publications",
                indicator="越南海上风电 WACC",
                value="7.4%",
            ),
            WACCData(
                source="IEA (2024)",
                source_url="https://www.iea.org/data-and-statistics",
                indicator="越南光伏 WACC (可参考)",
                value="9.0%",
                notes="(名义、税后、本币)",
            ),
            WACCData(
                source="世界银行 (2025)",
                source_url="https://www.worldbank.org/en/topic/energy",
                indicator="新兴市场风电所需 Equity IRR",
                value="约16-20%",
                notes="远高于发达市场 8-9%",
            ),
        ],
        summary=[
            MarketSummaryItem("越南政府定价模型假设的基准 Equity IRR", "12%"),
            MarketSummaryItem("国际开发商对越南风电的门槛 Equity IRR", "13.5% ~ 16% (陆上), 12% ~ 14% (海上)"),
            MarketSummaryItem("实际已投运/在建项目", "11% ~ 12.4%"),
            MarketSummaryItem("长期趋势 (2030-2050)", "随融资成本下降, 预计降至 8.5% ~ 13.5%"),
        ],
        summary_conclusion=(
            "越南风电项目的 Equity IRR 目前普遍在 11%~16% 区间, 其中政府定价基准为 12%, "
            "国际投资者要求的门槛更高 (13.5%~16%), 而实际落地项目约在 11%~12.4%。"
            "随着越南监管环境改善和融资成本的下降, 未来 IRR 门槛预计将逐步降低。"
        ),
    ),
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
    tariff_mechanism="FIT + GEAP auction",
    onshore_tariff_policy="FIT-All (ERC Resolution 2018): 7.40 PHP/kWh (~0.13 USD) for 20 years. Green Energy Auction Program (GEAP): Round 1/2 achieved 5.5-6.0 PHP/kWh. Source: DOE/ERC Philippines",
    offshore_tariff_policy="Offshore Wind Roadmap (DOE 2022): Target 21 GW by 2040. No specific FIT yet; expected bilateral PSA or auction-based tariff 0.09-0.12 USD/kWh. Source: DOE Circular DC2022-09-0034",
    om_defaults=CountryOMDefaults(
        recommended_method="fixed_escalation",
        onshore_base_om=18.0, offshore_base_om=35.0, escalation_rate=0.025,
        onshore_capex_pct=0.018, offshore_capex_pct=0.028,
        rationale="菲律宾项目建议固定单价法。台风多发区域运维成本偏高，建议预留备件储备金。",
        sources="BNEF SEA RE Investment 2024; DOE Philippines RE Roadmap",
    ),
    benchmarks=[
        MarketBenchmark("Equity IRR", "onshore", 12.0, 15.0, "DOE RE Policy Framework", "", 2023, "菲律宾能源部 RE 法案项目预期"),
        MarketBenchmark("Equity IRR", "offshore", 12.0, 16.0, "BNEF SE Asia RE Outlook 2024", "", 2024, "海上风电开发商要求"),
        MarketBenchmark("WACC", "all", 8.0, 11.0, "ADB Philippines Energy Assessment 2023", "https://www.adb.org", 2023, "新兴市场较高融资成本"),
        MarketBenchmark("Project IRR", "onshore", 9.0, 12.0, "Burgos Wind Farm (150MW, Ilocos Norte)", "", 2023, "菲律宾最大在运风电场"),
        MarketBenchmark("Hurdle IRR", "all", 13.0, 15.0, "IRENA Renewable Energy Statistics 2024", "https://www.irena.org", 2024, "东南亚新兴市场门槛"),
    ],
    market_report=CountryMarketReport(
        official_benchmarks=[
            OfficialIRRBenchmark(
                source="菲律宾能源部 (DOE) RE法案投资框架",
                source_ref="Republic Act No. 9513 (Renewable Energy Act of 2008)",
                source_url="https://www.doe.gov.ph/renewable-energy",
                project_type="all",
                equity_irr=14.0,
                financing_structure="30%股权 + 70%债务",
                notes="RE法案框架下隐含 Equity IRR 13-15%, FIT 电价已于2022年到期, 转向竞价",
            ),
        ],
        bnef_hurdles=[
            BNEFHurdleIRR(
                source="BloombergNEF",
                report_name="Southeast Asia Renewable Energy Market Outlook 2024",
                source_url="https://about.bnef.com/blog/southeast-asia-renewable-energy-market-outlook/",
                year=2024,
                project_type="onshore",
                current_value="14%",
                forecast_2030="12%",
                forecast_2050="9%",
                financing_assumption="债股比 70:30, 贷款期限 12年, 本地银行利率 7-8%",
            ),
        ],
        actual_cases=[
            ActualProjectCase(
                project_name="Burgos Wind Farm (150MW, Ilocos Norte)",
                project_type="onshore",
                irr_value="~12%",
                irr_type="Project IRR",
                capex_info="Capex: ~$2800/kW",
                notes="菲律宾最大在运风电场, EDC运营",
                source="Energy Development Corporation (EDC) 年报",
                source_url="https://www.energy.com.ph/",
            ),
        ],
        wacc_data=[
            WACCData(
                source="ADB (2023)",
                source_url="https://www.adb.org/publications",
                indicator="菲律宾可再生能源 WACC",
                value="8% ~ 11%",
                notes="新兴市场较高融资成本, 汇率风险溢价",
            ),
        ],
        summary=[
            MarketSummaryItem("DOE RE法案框架隐含 Equity IRR", "13% ~ 15%"),
            MarketSummaryItem("国际开发商门槛 Equity IRR", "12% ~ 16%"),
            MarketSummaryItem("实际项目 Project IRR", "9% ~ 12%"),
            MarketSummaryItem("长期趋势", "随竞价机制推行, 预计降至 9% ~ 12%"),
        ],
        summary_conclusion=(
            "菲律宾风电市场属于较高门槛市场, Equity IRR 要求在 13%~16%。"
            "Burgos 等已投运项目 Project IRR 约 12%, 随着 RE 法案的推进和融资条件改善, "
            "IRR 门槛有下降空间。"
        ),
    ),
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
    tariff_mechanism="FIT (Adder) + PPA auction",
    onshore_tariff_policy="AEDP 2024: Adder 3.50 THB/kWh on top of wholesale (~1.5-2.0 THB), total ~5.0-5.5 THB/kWh (~0.075-0.089 USD). ERC competitive bidding for new projects. Source: EPPO/ERC Thailand",
    offshore_tariff_policy="No offshore wind projects or tariff policy yet. PDP 2024 includes offshore wind targets post-2030. Source: EPPO Thailand",
    om_defaults=CountryOMDefaults(
        recommended_method="fixed_escalation",
        onshore_base_om=14.0, offshore_base_om=30.0, escalation_rate=0.02,
        onshore_capex_pct=0.015, offshore_capex_pct=0.025,
        rationale="泰国项目建议固定单价法。BOI优惠下运维成本结构与国际接轨。",
        sources="BNEF Thailand Country Profile 2024; BOI Investment Guide",
    ),
    benchmarks=[
        MarketBenchmark("Equity IRR", "onshore", 10.0, 13.0, "EPPO Thailand PDP 2024", "", 2024, "泰国电力发展规划预期回报"),
        MarketBenchmark("WACC", "all", 6.0, 8.0, "IRENA Cost of Financing RE 2023", "https://www.irena.org", 2023, "东南亚中等水平"),
        MarketBenchmark("Project IRR", "onshore", 8.0, 11.0, "Korat Wind Farm 群 (呵叻府)", "", 2023, "泰国最大陆上风电集群"),
        MarketBenchmark("Hurdle IRR", "onshore", 11.0, 13.0, "BNEF SE Asia RE Outlook 2024", "", 2024, "国际开发商预期"),
    ],
    market_report=CountryMarketReport(
        official_benchmarks=[
            OfficialIRRBenchmark(
                source="泰国能源政策规划办公室 (EPPO) PDP 框架",
                source_ref="Thailand Power Development Plan 2024-2037",
                source_url="https://www.eppo.go.th/",
                project_type="onshore",
                equity_irr=11.5,
                financing_structure="30%股权 + 70%债务",
                notes="EPPO PDP 框架隐含 Equity IRR 10-13%, Adder/FiT 电价补贴机制",
            ),
        ],
        bnef_hurdles=[
            BNEFHurdleIRR(
                source="BloombergNEF",
                report_name="Southeast Asia Renewable Energy Market Outlook 2024",
                source_url="https://about.bnef.com/blog/southeast-asia-renewable-energy-market-outlook/",
                year=2024,
                project_type="onshore",
                current_value="12%",
                forecast_2030="10%",
                forecast_2050="8%",
                financing_assumption="债股比 70:30, 贷款期限 15年, 本地贷款利率 4.5-5.5%",
            ),
        ],
        actual_cases=[
            ActualProjectCase(
                project_name="呵叻府风电集群 (Korat Wind Cluster)",
                project_type="onshore",
                irr_value="~10%",
                irr_type="Project IRR",
                capex_info="Capex: ~$1800/kW",
                notes="泰国最大陆上风电集群, 总装机约 200MW",
                source="EGAT / Wind Energy Holding 年报",
                source_url="https://www.egat.co.th/en/",
            ),
        ],
        wacc_data=[
            WACCData(
                source="IRENA (2023)",
                source_url="https://www.irena.org/publications",
                indicator="泰国可再生能源 WACC",
                value="6% ~ 8%",
                notes="东南亚中等水平, 本地银行贷款条件较好",
            ),
        ],
        summary=[
            MarketSummaryItem("EPPO PDP 框架隐含 Equity IRR", "10% ~ 13%"),
            MarketSummaryItem("BNEF 开发商门槛 Equity IRR", "11% ~ 13%"),
            MarketSummaryItem("实际项目 Project IRR", "8% ~ 11%"),
            MarketSummaryItem("长期趋势", "随 FiT 转向竞价, 预计降至 8% ~ 10%"),
        ],
        summary_conclusion=(
            "泰国是东南亚中等水平风电市场, Equity IRR 通常在 10%~13%。"
            "得益于相对成熟的金融市场和较低的本地贷款利率, WACC 约 6%~8%。"
            "随着 PDP 计划推进和竞价机制引入, IRR 有望逐步降低。"
        ),
    ),
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
    tariff_mechanism="BOOT PPA (MEMR regulation)",
    onshore_tariff_policy="MEMR Regulation 5/2025: BOOT scheme, PPA with PLN up to 30 years. Tariff = BPP (regional generation cost) ceiling. Typical 6.5-9.5 UScent/kWh depending on region. Sulawesi/NTT higher. Source: MEMR/PLN Indonesia",
    offshore_tariff_policy="No offshore wind tariff regulation yet. RUPTL 2024 includes offshore exploration. Source: PLN RUPTL",
    om_defaults=CountryOMDefaults(
        recommended_method="fixed_escalation",
        onshore_base_om=16.0, offshore_base_om=32.0, escalation_rate=0.03,
        onshore_capex_pct=0.016, offshore_capex_pct=0.026,
        rationale="印尼项目建议固定单价法。群岛地形导致运维物流成本高，通胀率偏高(3%)。",
        sources="BNEF Indonesia Country Profile 2024; PLN RUPTL 2025",
    ),
    benchmarks=[
        MarketBenchmark("Equity IRR", "onshore", 13.0, 16.0, "MEMR RUPTL 2021-2030", "", 2023, "PLN 购电协议下的开发商预期"),
        MarketBenchmark("WACC", "all", 9.0, 12.0, "World Bank Indonesia Energy Transition 2023", "https://www.worldbank.org", 2023, "印尼 RE 项目较高融资成本"),
        MarketBenchmark("Project IRR", "onshore", 10.0, 13.0, "Sidrap Wind Farm (75MW, 南苏拉威西)", "", 2023, "印尼首个商业化风电场"),
        MarketBenchmark("Hurdle IRR", "all", 14.0, 16.0, "BNEF SE Asia RE Outlook 2024", "", 2024, "高融资成本市场"),
    ],
    market_report=CountryMarketReport(
        official_benchmarks=[
            OfficialIRRBenchmark(
                source="印尼能矿部 (MEMR) RUPTL 框架",
                source_ref="RUPTL 2021-2030 (PLN 电力采购计划)",
                source_url="https://web.pln.co.id/statics/uploads/2021/10/ruptl-2021-2030.pdf",
                project_type="onshore",
                equity_irr=14.5,
                financing_structure="30%股权 + 70%债务",
                notes="MEMR RUPTL 框架下 Equity IRR 13-16%, PLN 购电协议下开发商预期",
            ),
        ],
        bnef_hurdles=[
            BNEFHurdleIRR(
                source="BloombergNEF",
                report_name="Southeast Asia Renewable Energy Market Outlook 2024",
                source_url="https://about.bnef.com/blog/southeast-asia-renewable-energy-market-outlook/",
                year=2024,
                project_type="onshore",
                current_value="15%",
                forecast_2030="12%",
                forecast_2050="9%",
                financing_assumption="债股比 70:30, 贷款期限 12年, 本地贷款利率 8-10%",
            ),
        ],
        actual_cases=[
            ActualProjectCase(
                project_name="Sidrap Wind Farm (75MW, 南苏拉威西)",
                project_type="onshore",
                irr_value="~12%",
                irr_type="Project IRR",
                capex_info="Capex: ~$2500/kW",
                notes="印尼首个商业化风电场, 2018年投运",
                source="UPC Renewables / JICA 项目报告",
                source_url="https://www.jica.go.jp/english/our_work/climate_change/index.html",
            ),
        ],
        wacc_data=[
            WACCData(
                source="World Bank (2023)",
                source_url="https://www.worldbank.org/en/country/indonesia",
                indicator="印尼可再生能源 WACC",
                value="9% ~ 12%",
                notes="高利率环境, 汇率波动风险, 岛屿电网并网成本高",
            ),
        ],
        summary=[
            MarketSummaryItem("MEMR RUPTL 框架隐含 Equity IRR", "13% ~ 16%"),
            MarketSummaryItem("BNEF 开发商门槛 Equity IRR", "14% ~ 16%"),
            MarketSummaryItem("实际项目 Project IRR", "10% ~ 13%"),
            MarketSummaryItem("长期趋势", "随 JETP 和国际融资改善, 预计降至 9% ~ 12%"),
        ],
        summary_conclusion=(
            "印尼是高融资成本的风电市场, Equity IRR 要求在 13%~16%。"
            "Sidrap 等早期项目 Project IRR 约 12%, 但融资成本高达 9%~12%。"
            "随着 JETP 资金注入和 MEMR 新政推进, 融资条件有望改善。"
        ),
    ),
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
    tariff_mechanism="NEDA FIT + LSS competitive bidding",
    onshore_tariff_policy="SEDA FIT (2022 revision): 24-38 sen/kWh (~0.051-0.081 USD). Large Scale Solar/Wind (LSS) auctions achieve lower rates. Corporate PPA growing. Source: SEDA/Energy Commission Malaysia",
    offshore_tariff_policy="No offshore wind policy or projects yet. NETR 2050 roadmap under study. Source: MOT/SEDA Malaysia",
    om_defaults=CountryOMDefaults(
        recommended_method="fixed_escalation",
        onshore_base_om=14.0, offshore_base_om=28.0, escalation_rate=0.02,
        onshore_capex_pct=0.014, offshore_capex_pct=0.024,
        rationale="马来西亚项目建议固定单价法。运维市场较成熟，可参考半岛电力公司合同报价。",
        sources="BNEF Malaysia RE 2024; SEDA Malaysia Feed-in Tariff",
    ),
    benchmarks=[
        MarketBenchmark("Equity IRR", "onshore", 10.0, 13.0, "SEDA Malaysia RE Roadmap", "", 2024, "马来西亚可持续能源发展局"),
        MarketBenchmark("WACC", "all", 6.5, 8.5, "IRENA Cost of Financing RE 2023", "https://www.irena.org", 2023, "东南亚中低水平"),
        MarketBenchmark("Project IRR", "onshore", 8.0, 11.0, "马来西亚沙巴/沙捞越风电前期项目", "", 2024, "MIDA 投资数据"),
        MarketBenchmark("Hurdle IRR", "onshore", 11.0, 14.0, "BNEF SE Asia RE Outlook 2024", "", 2024, "开发商预期门槛"),
    ],
    market_report=CountryMarketReport(
        official_benchmarks=[
            OfficialIRRBenchmark(
                source="马来西亚可持续能源发展局 (SEDA) 框架",
                source_ref="SEDA Malaysia RE Policy & FiT Mechanism",
                source_url="https://www.seda.gov.my/",
                project_type="onshore",
                equity_irr=11.5,
                financing_structure="30%股权 + 70%债务",
                notes="SEDA FiT 框架隐含 Equity IRR 10-13%, 沙巴/沙捞越地区风资源较好",
            ),
        ],
        bnef_hurdles=[
            BNEFHurdleIRR(
                source="BloombergNEF",
                report_name="Southeast Asia Renewable Energy Market Outlook 2024",
                source_url="https://about.bnef.com/blog/southeast-asia-renewable-energy-market-outlook/",
                year=2024,
                project_type="onshore",
                current_value="13%",
                forecast_2030="10%",
                forecast_2050="8%",
                financing_assumption="债股比 70:30, 贷款期限 15年, 本地贷款利率 4-5%",
            ),
        ],
        actual_cases=[
            ActualProjectCase(
                project_name="沙巴/沙捞越风电前期项目",
                project_type="onshore",
                irr_value="8% ~ 11%",
                irr_type="Project IRR",
                capex_info="Capex: ~$2000/kW (预估)",
                notes="前期开发阶段, MIDA 投资数据",
                source="MIDA (马来西亚投资发展局)",
                source_url="https://www.mida.gov.my/",
            ),
        ],
        wacc_data=[
            WACCData(
                source="IRENA (2023)",
                source_url="https://www.irena.org/publications",
                indicator="马来西亚可再生能源 WACC",
                value="6.5% ~ 8.5%",
                notes="东南亚中低水平, 金融市场相对成熟",
            ),
        ],
        summary=[
            MarketSummaryItem("SEDA 框架隐含 Equity IRR", "10% ~ 13%"),
            MarketSummaryItem("BNEF 开发商门槛 Equity IRR", "11% ~ 14%"),
            MarketSummaryItem("前期项目 Project IRR 预估", "8% ~ 11%"),
            MarketSummaryItem("长期趋势", "随 NETR 政策推进, 预计稳定在 8% ~ 10%"),
        ],
        summary_conclusion=(
            "马来西亚风电市场处于东南亚中低水平, Equity IRR 约 10%~13%。"
            "风电开发主要集中在东马 (沙巴/沙捞越), 西马风资源有限。"
            "WACC 约 6.5%~8.5%, 金融市场相对成熟, 融资条件较好。"
        ),
    ),
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
    tariff_mechanism="Direct PPA with EdC/licensee",
    onshore_tariff_policy="Bilateral PPA with EdC (Electricite du Cambodge). Tariff negotiated per project, typical 7-10 UScent/kWh for 20-25 years. No standardized FIT for wind. Source: EAC/MME Cambodia",
    offshore_tariff_policy="No offshore wind development. Coastline limited. Source: EAC Cambodia",
    om_defaults=CountryOMDefaults(
        recommended_method="capex_percentage",
        onshore_base_om=16.0, offshore_base_om=30.0, escalation_rate=0.025,
        onshore_capex_pct=0.018, offshore_capex_pct=0.028,
        rationale="柬埔寨市场早期，缺乏本地运维供应链，建议用投资百分比法粗算后按合同报价法精算。",
        sources="BNEF Cambodia Country Profile 2024; EAC Cambodia",
    ),
    benchmarks=[
        MarketBenchmark("Equity IRR", "onshore", 14.0, 18.0, "ADB Cambodia Energy Sector Assessment 2023", "https://www.adb.org", 2023, "高风险市场溢价"),
        MarketBenchmark("WACC", "all", 10.0, 13.0, "World Bank Cambodia RE Assessment 2023", "https://www.worldbank.org", 2023, "前沿市场高融资成本"),
        MarketBenchmark("Project IRR", "onshore", 10.0, 14.0, "柬埔寨暹粒/磅清扬风电前期项目", "", 2024, "早期开发阶段"),
        MarketBenchmark("Hurdle IRR", "all", 15.0, 18.0, "BNEF Frontier Market RE 2024", "", 2024, "前沿市场高门槛"),
    ],
    market_report=CountryMarketReport(
        official_benchmarks=[
            OfficialIRRBenchmark(
                source="柬埔寨暂无明确风电 IRR 框架, 参考 ADB 评估",
                source_ref="ADB Cambodia Energy Sector Assessment 2023",
                source_url="https://www.adb.org/countries/cambodia/economy",
                project_type="onshore",
                equity_irr=16.0,
                financing_structure="30%股权 + 70%债务",
                notes="前沿市场, 尚无明确的风电定价框架, ADB 评估建议 15-18%",
            ),
        ],
        bnef_hurdles=[
            BNEFHurdleIRR(
                source="BloombergNEF",
                report_name="Frontier Market Renewable Energy Outlook 2024",
                source_url="https://about.bnef.com/",
                year=2024,
                project_type="onshore",
                current_value="17%",
                forecast_2030="14%",
                forecast_2050="10%",
                financing_assumption="债股比 70:30, 贷款期限 10年, 融资成本高达 10-12%",
            ),
        ],
        actual_cases=[
            ActualProjectCase(
                project_name="柬埔寨暹粒/磅清扬风电前期项目",
                project_type="onshore",
                irr_value="10% ~ 14%",
                irr_type="Project IRR",
                capex_info="前期预估",
                notes="早期开发阶段, 风资源评估中",
                source="ADB / 柬埔寨矿业与能源部",
                source_url="https://www.adb.org/countries/cambodia/economy",
            ),
        ],
        wacc_data=[
            WACCData(
                source="World Bank (2023)",
                source_url="https://www.worldbank.org/en/country/cambodia",
                indicator="柬埔寨可再生能源 WACC",
                value="10% ~ 13%",
                notes="前沿市场高融资成本, 缺乏本地长期贷款渠道",
            ),
        ],
        summary=[
            MarketSummaryItem("ADB 评估建议门槛 Equity IRR", "15% ~ 18%"),
            MarketSummaryItem("BNEF 前沿市场 Hurdle IRR", "15% ~ 18%"),
            MarketSummaryItem("实际项目预估 Project IRR", "10% ~ 14%"),
            MarketSummaryItem("长期趋势", "随基础设施改善, 预计降至 10% ~ 14%"),
        ],
        summary_conclusion=(
            "柬埔寨属于前沿市场, 风电 Equity IRR 门槛高达 15%~18%。"
            "融资成本高 (WACC 10%~13%), 缺乏成熟的本地融资渠道。"
            "风电项目尚处早期开发阶段, 主要依赖多边开发银行支持。"
        ),
    ),
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
    tariff_mechanism="FIT + FIP (Feed-in Premium)",
    onshore_tariff_policy="FIT (METI 2024): <50kW 16 JPY, >=50kW auction-based ~11-15 JPY/kWh (~0.10-0.16 USD). FIP premium for larger projects. Source: METI Procurement Price Committee",
    offshore_tariff_policy="Auction (METI/GIO): Round 1 Akita/Chiba ~29 JPY/kWh (~0.19 USD). Round 2+ expected 20-26 JPY/kWh (~0.19-0.26 USD). FIT ceiling 36 JPY/kWh for legacy projects. Source: METI/GIO Japan",
    om_defaults=CountryOMDefaults(
        recommended_method="fixed_escalation",
        onshore_base_om=20.0, offshore_base_om=45.0, escalation_rate=0.015,
        onshore_capex_pct=0.015, offshore_capex_pct=0.030,
        rationale="日本运维成本全球最高之一。海上O&M 40-55 $/kW(BNEF)，受限于港口和船舶资源。通胀低(1.5%)。",
        sources="BNEF Japan Offshore Wind Market Outlook 2025; METI/JWPA",
    ),
    benchmarks=[
        MarketBenchmark("Equity IRR", "onshore", 6.0, 9.0, "METI FIT/FIP 制度设计基础", "", 2024, "日本经产省 FIT 定价隐含收益率"),
        MarketBenchmark("Equity IRR", "offshore", 8.0, 12.0, "JWPA 日本风力发电协会", "", 2024, "海上风电投资预期"),
        MarketBenchmark("WACC", "all", 3.0, 5.0, "IEA Cost of Capital Observatory 2024", "https://www.iea.org", 2024, "低利率环境下融资成本"),
        MarketBenchmark("Project IRR", "onshore", 5.0, 8.0, "日本陆上风电项目统计 (METI)", "", 2024, "FIT 电价下"),
        MarketBenchmark("Project IRR", "offshore", 6.0, 9.0, "秋田県能代/三種 洋上風力 (140MW)", "", 2024, "日本首批商业海上风电"),
        MarketBenchmark("Hurdle IRR", "offshore", 8.0, 10.0, "BNEF Japan Offshore Wind 2024", "", 2024, "Round 2/3 竞标预期"),
    ],
    market_report=CountryMarketReport(
        official_benchmarks=[
            OfficialIRRBenchmark(
                source="日本经济产业省 (METI) FIT/FIP 制度",
                source_ref="METI FIT/FIP 定价委员会报告 (2024)",
                source_url="https://www.meti.go.jp/english/policy/energy_environment/renewable/index.html",
                project_type="onshore",
                equity_irr=7.5,
                financing_structure="30%股权 + 70%债务",
                notes="FIT 定价隐含 IRR 6-9% (陆上), 日本超低利率环境下合理回报",
            ),
            OfficialIRRBenchmark(
                source="日本经济产业省 (METI) FIT/FIP 制度",
                source_ref="METI 洋上風力促進区域指定制度",
                source_url="https://www.meti.go.jp/english/policy/energy_environment/renewable/index.html",
                project_type="offshore",
                equity_irr=10.0,
                financing_structure="30%股权 + 70%债务",
                notes="FIT/FIP 海上风电定价隐含 IRR 8-12%, 包含海域使用费等额外成本",
            ),
        ],
        bnef_hurdles=[
            BNEFHurdleIRR(
                source="BloombergNEF",
                report_name="Japan Offshore Wind Market Outlook 2024",
                source_url="https://about.bnef.com/blog/japan-offshore-wind-market-outlook/",
                year=2024,
                project_type="offshore",
                current_value="9%",
                forecast_2030="8%",
                forecast_2050="7%",
                financing_assumption="债股比 70:30, 贷款期限 18年, 贷款利率 1-2%",
            ),
        ],
        actual_cases=[
            ActualProjectCase(
                project_name="秋田県能代/三種 洋上風力 (140MW)",
                project_type="offshore",
                irr_value="~7%",
                irr_type="Project IRR",
                capex_info="Capex: ~¥500,000/kW",
                notes="日本首批商业海上风电, 2023年投运",
                source="JWPA 日本風力発電協会",
                source_url="https://jwpa.jp/english/",
            ),
        ],
        wacc_data=[
            WACCData(
                source="IEA (2024)",
                source_url="https://www.iea.org/data-and-statistics",
                indicator="日本可再生能源 WACC",
                value="3% ~ 5%",
                notes="低利率环境, 日本银行长期零利率/负利率政策影响",
            ),
        ],
        summary=[
            MarketSummaryItem("METI FIT/FIP 隐含 Equity IRR (陆上)", "6% ~ 9%"),
            MarketSummaryItem("METI FIT/FIP 隐含 Equity IRR (海上)", "8% ~ 12%"),
            MarketSummaryItem("BNEF 海上风电门槛 Equity IRR", "8% ~ 10%"),
            MarketSummaryItem("实际项目 Project IRR", "5% ~ 9%"),
            MarketSummaryItem("长期趋势", "低利率环境下稳定在 7% ~ 9%"),
        ],
        summary_conclusion=(
            "日本是低利率环境下的风电市场, Equity IRR 通常在 6%~12%。"
            "WACC 仅 3%~5%, 全球最低水平之一。海上风电是日本风电发展重点, "
            "Round 2/3 竞标正在推进, 预期收益率约 8%~10%。"
        ),
    ),
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
    tariff_mechanism="RPS + REC + Fixed-price PPA",
    onshore_tariff_policy="RPS system: SMP (market price ~50-70 KRW) + REC (wind multiplier 1.0-1.2). Total ~100-160 KRW/kWh (~0.08-0.12 USD). Long-term fixed-price PPA auction available. Source: MOTIE/KPX Korea",
    offshore_tariff_policy="REC weight 2.0-3.5x for offshore (distance-based). Fixed-price auction: 168-233 KRW/kWh (~0.127-0.175 USD) for 20 years. Ulsan/Shinan large projects in pipeline. Source: MOTIE Korea",
    om_defaults=CountryOMDefaults(
        recommended_method="fixed_escalation",
        onshore_base_om=18.0, offshore_base_om=40.0, escalation_rate=0.02,
        onshore_capex_pct=0.015, offshore_capex_pct=0.028,
        rationale="韩国海上风电市场快速发展，运维成本高于东南亚。建议固定单价法，参考MOTIE拍卖标准。",
        sources="BNEF South Korea Offshore Wind Outlook 2024; MOTIE/KEPCO",
    ),
    benchmarks=[
        MarketBenchmark("Equity IRR", "onshore", 7.0, 10.0, "MOTIE 韩国产业通商资源部", "", 2024, "RPS/REC 体系下"),
        MarketBenchmark("Equity IRR", "offshore", 8.0, 12.0, "KWEIA 韩国风能产业协会", "", 2024, "海上风电开发商预期"),
        MarketBenchmark("WACC", "all", 4.5, 6.5, "IEA Cost of Capital Observatory 2024", "https://www.iea.org", 2024, "OECD 成员国较低融资成本"),
        MarketBenchmark("Project IRR", "offshore", 7.0, 10.0, "西南海 해상풍력 (전남 신안, 8.2GW规划)", "", 2024, "韩国最大海上风电规划"),
        MarketBenchmark("Hurdle IRR", "offshore", 9.0, 11.0, "BNEF South Korea Offshore Wind 2024", "", 2024, "竞标项目门槛"),
    ],
    market_report=CountryMarketReport(
        official_benchmarks=[
            OfficialIRRBenchmark(
                source="韩国产业通商资源部 (MOTIE) RPS/REC 框架",
                source_ref="Renewable Portfolio Standard (RPS) & REC 定价机制",
                source_url="https://www.motie.go.kr/en/po/energy/renewableEnergy/renewableEnergy.do",
                project_type="onshore",
                equity_irr=8.5,
                financing_structure="30%股权 + 70%债务",
                notes="RPS/REC 体系下陆上风电 Equity IRR 7-10%",
            ),
            OfficialIRRBenchmark(
                source="韩国产业通商资源部 (MOTIE) 海上风电支持政策",
                source_ref="해상풍력 발전사업 허가지침 (海上风电许可指南)",
                source_url="https://www.motie.go.kr/en/po/energy/renewableEnergy/renewableEnergy.do",
                project_type="offshore",
                equity_irr=10.0,
                financing_structure="25%股权 + 75%债务",
                notes="海上风电 REC 加权系数 2.0-3.5, 隐含 Equity IRR 8-12%",
            ),
        ],
        bnef_hurdles=[
            BNEFHurdleIRR(
                source="BloombergNEF",
                report_name="South Korea Offshore Wind Market Outlook 2024",
                source_url="https://about.bnef.com/blog/south-korea-offshore-wind-market-outlook/",
                year=2024,
                project_type="offshore",
                current_value="10%",
                forecast_2030="8.5%",
                forecast_2050="7%",
                financing_assumption="债股比 75:25, 贷款期限 15年, 贷款利率 3-4%",
            ),
        ],
        actual_cases=[
            ActualProjectCase(
                project_name="西南海 해상풍력 (전남 신안, 8.2GW 规划)",
                project_type="offshore",
                irr_value="7% ~ 10%",
                irr_type="Project IRR",
                capex_info="Capex: 预估 ~$4000/kW",
                notes="韩国最大海上风电规划, 分阶段推进中",
                source="KWEIA 韩国风能产业协会",
                source_url="https://www.kweia.or.kr/eng/",
            ),
        ],
        wacc_data=[
            WACCData(
                source="IEA (2024)",
                source_url="https://www.iea.org/data-and-statistics",
                indicator="韩国可再生能源 WACC",
                value="4.5% ~ 6.5%",
                notes="OECD 成员国较低融资成本",
            ),
        ],
        summary=[
            MarketSummaryItem("MOTIE RPS 框架隐含 Equity IRR (陆上)", "7% ~ 10%"),
            MarketSummaryItem("MOTIE 框架隐含 Equity IRR (海上)", "8% ~ 12%"),
            MarketSummaryItem("BNEF 海上风电门槛 Equity IRR", "9% ~ 11%"),
            MarketSummaryItem("实际规划项目 Project IRR", "7% ~ 10%"),
            MarketSummaryItem("长期趋势", "随海上风电规模化, 预计降至 7% ~ 8.5%"),
        ],
        summary_conclusion=(
            "韩国是 OECD 市场, Equity IRR 通常在 7%~12%。海上风电是发展重点, "
            "西南海 8.2GW 规划为亚太最大海上风电项目之一。"
            "WACC 约 4.5%~6.5%, 融资条件良好。"
        ),
    ),
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
    tariff_mechanism="Merchant + PPA + LGC",
    onshore_tariff_policy="Merchant market (NEM/WEM spot) + bilateral PPA + LGC (Large-scale Generation Certificates ~30-45 AUD/MWh). Total revenue 70-130 AUD/MWh (~0.050-0.090 USD). CfD auctions emerging. Source: CER/AEMO Australia",
    offshore_tariff_policy="Offshore Electricity Infrastructure Act 2021: Declared areas (Gippsland, Hunter, Illawarra). No tariff mechanism yet; expected CfD or PPA-based. First projects 2028+. Source: DCCEEW Australia",
    om_defaults=CountryOMDefaults(
        recommended_method="fixed_escalation",
        onshore_base_om=15.0, offshore_base_om=35.0, escalation_rate=0.025,
        onshore_capex_pct=0.013, offshore_capex_pct=0.025,
        rationale="澳大利亚运维市场成熟，固定单价法最普遍。通胀2.5%。AUD计价需注意汇率风险。",
        sources="BNEF Australia RE Outlook 2024; AEMO/CER",
    ),
    benchmarks=[
        MarketBenchmark("Equity IRR", "onshore", 7.0, 10.0, "Clean Energy Council Australia", "", 2024, "含 LGC 绿证收入"),
        MarketBenchmark("WACC", "all", 5.0, 7.0, "IRENA Cost of Financing RE 2023", "https://www.irena.org", 2023, "发达市场中等水平"),
        MarketBenchmark("WACC", "all", 5.5, 7.5, "IEA Cost of Capital Observatory 2024", "https://www.iea.org", 2024, "加息周期后有所上升"),
        MarketBenchmark("Project IRR", "onshore", 6.0, 9.0, "Goldwind Stockyard Hill (530MW, Victoria)", "", 2024, "澳洲最大运营风电场"),
        MarketBenchmark("Hurdle IRR", "onshore", 8.0, 10.0, "BNEF Australia RE Outlook 2024", "", 2024, "PPA 市场化竞标"),
    ],
    market_report=CountryMarketReport(
        official_benchmarks=[
            OfficialIRRBenchmark(
                source="澳大利亚无固定框架, 市场化 PPA 定价",
                source_ref="Clean Energy Council / AEMO 市场框架",
                source_url="https://www.cleanenergycouncil.org.au/",
                project_type="onshore",
                equity_irr=9.0,
                financing_structure="30%股权 + 70%债务",
                notes="完全市场化定价, 通过 PPA 和 LGC 绿证收入实现回报, 无政府固定 IRR 基准",
            ),
        ],
        bnef_hurdles=[
            BNEFHurdleIRR(
                source="BloombergNEF",
                report_name="Australia Renewable Energy Market Outlook 2024",
                source_url="https://about.bnef.com/blog/australia-renewable-energy-market-outlook/",
                year=2024,
                project_type="onshore",
                current_value="9%",
                forecast_2030="8%",
                forecast_2050="7%",
                financing_assumption="债股比 70:30, 贷款期限 15年, 贷款利率 5-6%",
            ),
        ],
        actual_cases=[
            ActualProjectCase(
                project_name="Goldwind Stockyard Hill Wind Farm (530MW, Victoria)",
                project_type="onshore",
                irr_value="~8%",
                irr_type="Project IRR",
                capex_info="Capex: ~A$2200/kW",
                notes="澳洲最大运营风电场, 金风科技投资",
                source="Goldwind Australia / Clean Energy Council",
                source_url="https://www.goldwindaustralia.com/stockyard-hill-wind-farm/",
            ),
        ],
        wacc_data=[
            WACCData(
                source="IRENA (2023)",
                source_url="https://www.irena.org/publications",
                indicator="澳大利亚陆上风电 WACC",
                value="5% ~ 7%",
                notes="发达市场中等水平",
            ),
            WACCData(
                source="IEA (2024)",
                source_url="https://www.iea.org/data-and-statistics",
                indicator="澳大利亚可再生能源 WACC",
                value="5.5% ~ 7.5%",
                notes="加息周期后有所上升",
            ),
        ],
        summary=[
            MarketSummaryItem("市场化 PPA 隐含 Equity IRR", "7% ~ 10%"),
            MarketSummaryItem("BNEF 开发商门槛 Equity IRR", "8% ~ 10%"),
            MarketSummaryItem("实际项目 Project IRR", "6% ~ 9%"),
            MarketSummaryItem("长期趋势", "成熟市场稳定在 7% ~ 9%"),
        ],
        summary_conclusion=(
            "澳大利亚是成熟的市场化风电市场, Equity IRR 通常在 7%~10%。"
            "通过 PPA 和 LGC 绿证收入实现回报, 无政府固定定价。"
            "WACC 约 5%~7.5%, 属发达市场中等水平。"
        ),
    ),
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
    tariff_mechanism="FIT + competitive auction",
    onshore_tariff_policy="BOE FIT 2025: 1-30kW 8.6595 TWD, >30kW 2.1319-2.7826 TWD/kWh. ~0.065-0.085 USD/kWh for 20 years. Source: Bureau of Energy (BOE) Taiwan",
    offshore_tariff_policy="BOE FIT 2025: 4.5085 TWD/kWh (~0.139 USD) for 20 years (capacity weighted). Auction (Round 3+): 2.2-2.5 TWD/kWh (~0.068-0.077 USD). CPPA route also available. Changhua/Yunlin projects 0.106-0.161 USD/kWh. Source: BOE/MOEA Taiwan",
    om_defaults=CountryOMDefaults(
        recommended_method="fixed_escalation",
        onshore_base_om=16.0, offshore_base_om=42.0, escalation_rate=0.015,
        onshore_capex_pct=0.014, offshore_capex_pct=0.028,
        rationale="台湾海上风电运维成本偏高(台风+远岸)。参考R3竞标项目O&M报价。通胀低(1.5%)。",
        sources="BNEF Taiwan Offshore Wind Market 2024; BOE/MOEA",
    ),
    benchmarks=[
        MarketBenchmark("Equity IRR", "offshore", 7.0, 10.0, "经济部能源局 FIT 定价机制", "", 2024, "FIT 电价隐含回报"),
        MarketBenchmark("Equity IRR", "onshore", 8.0, 11.0, "经济部能源局 RE 政策框架", "", 2024, "陆上风电 FIT"),
        MarketBenchmark("WACC", "all", 4.0, 6.0, "IEA Cost of Capital Observatory 2024", "https://www.iea.org", 2024, "低利率经济体"),
        MarketBenchmark("Project IRR", "offshore", 6.0, 9.0, "海洋风电 Formosa 1 (128MW)", "", 2023, "台湾首个商业海上风电"),
        MarketBenchmark("Project IRR", "offshore", 7.0, 9.0, "沃旭大彰化 Greater Changhua (900MW)", "", 2024, "Round 2 最大项目"),
        MarketBenchmark("Hurdle IRR", "offshore", 8.0, 10.0, "BNEF Taiwan Offshore Wind 2024", "", 2024, "Round 3 竞标预期"),
    ],
    market_report=CountryMarketReport(
        official_benchmarks=[
            OfficialIRRBenchmark(
                source="经济部能源局 FIT 定价机制",
                source_ref="再生能源发电设备设置管理办法 / FIT 费率审定会",
                source_url="https://www.moeaboe.gov.tw/",
                project_type="offshore",
                equity_irr=8.5,
                financing_structure="30%股权 + 70%债务",
                notes="FIT 海上风电定价 (2025年: 4.5085 TWD/kWh, 20年), 隐含 Equity IRR 7-10%",
            ),
        ],
        bnef_hurdles=[
            BNEFHurdleIRR(
                source="BloombergNEF",
                report_name="Taiwan Offshore Wind Market Outlook 2024",
                source_url="https://about.bnef.com/blog/taiwan-offshore-wind-market-outlook/",
                year=2024,
                project_type="offshore",
                current_value="9%",
                forecast_2030="8%",
                forecast_2050="7%",
                financing_assumption="债股比 70:30, 贷款期限 18年, 贷款利率 2-3%",
            ),
        ],
        actual_cases=[
            ActualProjectCase(
                project_name="海洋风电 Formosa 1 (128MW)",
                project_type="offshore",
                irr_value="~8%",
                irr_type="Project IRR",
                capex_info="Capex: ~$4500/kW",
                notes="台湾首个商业海上风电场, 2019年投运",
                source="JERA / Macquarie / Swancor",
                source_url="https://www.formosa1windpower.com/",
            ),
            ActualProjectCase(
                project_name="沃旭大彰化 Greater Changhua (900MW)",
                project_type="offshore",
                irr_value="~8%",
                irr_type="Project IRR",
                capex_info="Capex: ~$4000/kW",
                notes="Round 2 最大项目, 分阶段建设, 2024-2025年投运",
                source="Ørsted 沃旭能源",
                source_url="https://orsted.tw/en/our-business/offshore-wind/greater-changhua",
            ),
        ],
        wacc_data=[
            WACCData(
                source="IEA (2024)",
                source_url="https://www.iea.org/data-and-statistics",
                indicator="台湾可再生能源 WACC",
                value="4% ~ 6%",
                notes="低利率经济体, 国际银行团积极参与项目融资",
            ),
        ],
        summary=[
            MarketSummaryItem("能源局 FIT 隐含 Equity IRR (海上)", "7% ~ 10%"),
            MarketSummaryItem("BNEF Round 3 竞标门槛 Equity IRR", "8% ~ 10%"),
            MarketSummaryItem("实际项目 Project IRR", "6% ~ 9%"),
            MarketSummaryItem("长期趋势", "随供应链本地化, 预计稳定在 7% ~ 9%"),
        ],
        summary_conclusion=(
            "中国台湾是亚太重要的海上风电市场, Equity IRR 通常在 7%~10%。"
            "Formosa 1 和 Greater Changhua 等项目 Project IRR 约 8%。"
            "WACC 约 4%~6%, 国际银行团积极参与融资, 条件良好。"
        ),
    ),
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


# ════════════════════════════════════════════════════════════════════════════
# 分国家健康度诊断基准
# ════════════════════════════════════════════════════════════════════════════

@dataclass
class CountryDiagThresholds:
    """Country-specific diagnostic thresholds for project health check."""
    country: str
    country_cn: str

    # IRR (project after-tax)
    irr_floor: float          # below this = red
    irr_low: float            # below this = orange
    irr_high: float           # above this = yellow (suspiciously high)
    irr_note: str = ""

    # Equity IRR
    eq_irr_floor: float = 0.0
    eq_irr_low: float = 0.06
    eq_irr_high: float = 0.30
    eq_irr_note: str = ""

    # LCOE (USD/kWh)
    lcoe_high_onshore: float = 0.06
    lcoe_high_offshore: float = 0.10

    # CAPEX (USD/kW)
    capex_high_onshore: float = 1200.0
    capex_high_offshore: float = 3000.0

    # Payback (years)
    payback_warning: float = 15.0
    payback_critical: float = 20.0

    # Tariff reference ranges (pulled from CountryProfile)
    tariff_onshore: Tuple[float, float] = (0.0, 0.0)
    tariff_offshore: Tuple[float, float] = (0.0, 0.0)

    # Policy source
    policy_source: str = ""
    data_year: int = 2025


def _build_diag_thresholds(p: CountryProfile) -> CountryDiagThresholds:
    """Derive diagnostic thresholds from a CountryProfile + its benchmarks."""
    irr_lo_vals = [b.value_low / 100 for b in p.benchmarks if "IRR" in b.metric and b.project_type in ("onshore", "all")]
    irr_hi_vals = [b.value_high / 100 for b in p.benchmarks if "IRR" in b.metric]
    eq_lo_vals = [b.value_low / 100 for b in p.benchmarks if b.metric == "Equity IRR"]
    eq_hi_vals = [b.value_high / 100 for b in p.benchmarks if b.metric == "Equity IRR"]

    irr_floor = min(irr_lo_vals) * 0.5 if irr_lo_vals else 0.02
    irr_low = min(irr_lo_vals) if irr_lo_vals else 0.05
    irr_high = max(irr_hi_vals) * 1.8 if irr_hi_vals else 0.20
    eq_floor = min(eq_lo_vals) * 0.5 if eq_lo_vals else 0.02
    eq_low = min(eq_lo_vals) if eq_lo_vals else 0.06
    eq_high = max(eq_hi_vals) * 2.0 if eq_hi_vals else 0.30

    sources = list(set(b.source for b in p.benchmarks[:3]))

    return CountryDiagThresholds(
        country=p.country_name,
        country_cn=p.country_name_cn,
        irr_floor=irr_floor, irr_low=irr_low, irr_high=irr_high,
        irr_note=f"Based on {', '.join(sources[:2])}" if sources else "",
        eq_irr_floor=eq_floor, eq_irr_low=eq_low, eq_irr_high=eq_high,
        tariff_onshore=p.onshore_tariff_range,
        tariff_offshore=p.offshore_tariff_range,
        policy_source=p.tariff_mechanism,
        data_year=int(p.data_updated.split("-")[0]) if p.data_updated else 2025,
    )


# Pre-built defaults per country, with manual overrides for key markets
_DIAG_OVERRIDES: Dict[str, dict] = {
    "china": dict(
        irr_floor=0.03, irr_low=0.06, irr_high=0.18,
        eq_irr_floor=0.04, eq_irr_low=0.08, eq_irr_high=0.25,
        lcoe_high_onshore=0.05, lcoe_high_offshore=0.07,
        capex_high_onshore=900, capex_high_offshore=2500,
        irr_note="NDRC基准收益率8%; 平价上网后项目IRR普遍6-10%",
        eq_irr_note="NDRC资本金IRR基准8%, 优质项目10-13%",
    ),
    "vietnam": dict(
        irr_floor=0.03, irr_low=0.05, irr_high=0.16,
        eq_irr_floor=0.03, eq_irr_low=0.06, eq_irr_high=0.20,
        lcoe_high_onshore=0.07, lcoe_high_offshore=0.09,
        capex_high_onshore=1200, capex_high_offshore=2000,
        irr_note="Decision 39 FIT下项目IRR 6-8%; Decision 1508过渡期IRR偏低",
        eq_irr_note="越南市场贷款利率高(5.5-8%), 杠杆效应有限",
    ),
    "philippines": dict(
        irr_floor=0.04, irr_low=0.08, irr_high=0.22,
        eq_irr_floor=0.05, eq_irr_low=0.10, eq_irr_high=0.35,
        lcoe_high_onshore=0.08, lcoe_high_offshore=0.12,
        capex_high_onshore=1300, capex_high_offshore=3500,
        irr_note="RE法案税收优惠大幅提高IRR; GESP FIT率$0.098/kWh偏高",
        eq_irr_note="7年免税+低资本金→资本金IRR可达15-25%属正常",
    ),
    "australia": dict(
        irr_floor=0.04, irr_low=0.07, irr_high=0.20,
        eq_irr_floor=0.05, eq_irr_low=0.08, eq_irr_high=0.28,
        lcoe_high_onshore=0.07, lcoe_high_offshore=0.12,
        capex_high_onshore=1100, capex_high_offshore=3500,
        irr_note="PPA竞拍价格$50-90/MWh; LGC绿证贡献额外收入",
        eq_irr_note="澳洲30%企业税率但加速折旧, 实际税负低",
    ),
    "japan": dict(
        irr_floor=0.03, irr_low=0.05, irr_high=0.14,
        eq_irr_floor=0.04, eq_irr_low=0.06, eq_irr_high=0.18,
        lcoe_high_onshore=0.12, lcoe_high_offshore=0.20,
        capex_high_onshore=2000, capex_high_offshore=5000,
        irr_note="日本FIT制度支撑; 海上风电FIP制度下IRR 6-8%",
        eq_irr_note="日本低利率环境, 杠杆效应明显",
    ),
    "south korea": dict(
        irr_floor=0.03, irr_low=0.06, irr_high=0.16,
        eq_irr_floor=0.04, eq_irr_low=0.07, eq_irr_high=0.22,
        lcoe_high_onshore=0.10, lcoe_high_offshore=0.15,
        capex_high_onshore=1500, capex_high_offshore=4000,
        irr_note="RPS+REC制度; 海上风电SMP+REC 3.5倍",
        eq_irr_note="韩国贷款利率3-5%, 杠杆效应中等",
    ),
    "taiwan": dict(
        irr_floor=0.03, irr_low=0.06, irr_high=0.16,
        eq_irr_floor=0.04, eq_irr_low=0.07, eq_irr_high=0.20,
        lcoe_high_onshore=0.08, lcoe_high_offshore=0.14,
        capex_high_onshore=1400, capex_high_offshore=4000,
        irr_note="FIT制度TWD 4.5/kWh (20年); 第三阶段竞价",
        eq_irr_note="台湾项目融资成熟, 资本金IRR 8-12%",
    ),
    "thailand": dict(
        irr_floor=0.03, irr_low=0.06, irr_high=0.18,
        eq_irr_floor=0.04, eq_irr_low=0.08, eq_irr_high=0.25,
        lcoe_high_onshore=0.07, lcoe_high_offshore=0.10,
        capex_high_onshore=1200, capex_high_offshore=3000,
    ),
    "indonesia": dict(
        irr_floor=0.04, irr_low=0.08, irr_high=0.20,
        eq_irr_floor=0.05, eq_irr_low=0.10, eq_irr_high=0.28,
        lcoe_high_onshore=0.08, lcoe_high_offshore=0.12,
        capex_high_onshore=1300, capex_high_offshore=3000,
        irr_note="MEMR 5/2025 PPA框架; PLN购电价偏低",
    ),
    "malaysia": dict(
        irr_floor=0.03, irr_low=0.06, irr_high=0.18,
        eq_irr_floor=0.04, eq_irr_low=0.08, eq_irr_high=0.25,
        lcoe_high_onshore=0.07, lcoe_high_offshore=0.10,
        capex_high_onshore=1200, capex_high_offshore=3000,
    ),
    "cambodia": dict(
        irr_floor=0.04, irr_low=0.08, irr_high=0.22,
        eq_irr_floor=0.05, eq_irr_low=0.10, eq_irr_high=0.30,
        lcoe_high_onshore=0.08, lcoe_high_offshore=0.12,
        capex_high_onshore=1300, capex_high_offshore=3000,
        irr_note="QIP优惠9年免税; 电力市场尚未成熟",
    ),
}


def get_diag_thresholds(country: str) -> CountryDiagThresholds:
    """Get country-specific diagnostic thresholds. Falls back to generic defaults."""
    key = country.lower().strip()
    profile = _PROFILES.get(key)

    if profile:
        base = _build_diag_thresholds(profile)
    else:
        base = CountryDiagThresholds(
            country=country, country_cn=country,
            irr_floor=0.02, irr_low=0.05, irr_high=0.20,
        )

    overrides = _DIAG_OVERRIDES.get(key, {})
    for field_name, value in overrides.items():
        if hasattr(base, field_name):
            setattr(base, field_name, value)

    return base
