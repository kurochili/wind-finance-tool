"""
wind_finance.country_profiles
=============================
东南亚及东亚各国风电项目默认融资/税费参数

选择国家后自动填充利率、税率等默认值，用户可手动覆盖。
数据基于公开政策文件和行业经验，仅供参考，需根据实际项目更新。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional, Tuple


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

    urban_maintenance_tax_rate: float = 0.0  # 城市维护建设税率（部分国家无此税种）
    education_surcharge_rate: float = 0.0    # 教育费附加率

    # ---- 电价参考 ----
    onshore_tariff_range: Tuple[float, float] = (0.0, 0.0)   # 陆上电价参考范围 (USD/kWh)
    offshore_tariff_range: Tuple[float, float] = (0.0, 0.0)  # 海上电价参考范围 (USD/kWh)

    # ---- 元数据 ----
    data_updated: str = "2025-01"           # 数据更新日期


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
    onshore_tariff_range=(0.035, 0.055),
    offshore_tariff_range=(0.055, 0.075),
    data_updated="2025-01",
))

_register(CountryProfile(
    country_name="Vietnam",
    country_name_cn="越南",
    currency="VND",
    exchange_rate_to_usd=25400,
    typical_equity_ratio=0.30,
    typical_loan_rate=0.08,
    typical_loan_term=15,
    corporate_income_tax_rate=0.20,
    vat_rate=0.10,
    has_wind_tax_incentive=True,
    tax_incentive_description="企业所得税4免9减半; 进口设备免增值税",
    income_tax_holiday=(1, 4, 0.0, 5, 13, 0.10),
    onshore_tariff_range=(0.065, 0.085),
    offshore_tariff_range=(0.080, 0.098),
    data_updated="2025-01",
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
    onshore_tariff_range=(0.060, 0.090),
    offshore_tariff_range=(0.0, 0.0),
    data_updated="2025-01",
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
    tax_incentive_description="可再生能源进口设备免增值税; 加速折旧",
    income_tax_holiday=(1, 5, 0.0, 6, 10, 0.11),
    onshore_tariff_range=(0.065, 0.095),
    offshore_tariff_range=(0.0, 0.0),
    data_updated="2025-01",
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
    tax_incentive_description="REC制度; RPS义务比例",
    income_tax_holiday=(1, 1, 0.242, 1, 1, 0.242),
    onshore_tariff_range=(0.080, 0.120),
    offshore_tariff_range=(0.150, 0.220),
    data_updated="2025-01",
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
    tax_incentive_description="FIT制度; 加速折旧; 投资抵减",
    income_tax_holiday=(1, 5, 0.0, 6, 10, 0.10),
    onshore_tariff_range=(0.065, 0.085),
    offshore_tariff_range=(0.125, 0.165),
    data_updated="2025-01",
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
