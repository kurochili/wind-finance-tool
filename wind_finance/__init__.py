"""
wind_finance - 风电项目经济性评估工具包
支持陆上 (onshore) 和海上 (offshore) 风电项目的财务测算、反算与可视化。
货币单位统一为 USD。
"""

from .models import (
    BasicInfo,
    OEMCost,
    InstallationCost,
    FoundationCost,
    BOPCost,
    OffshoreEPCBreakdown,
    OnshoreInvestment,
    InvestmentData,
    FinancingTerms,
    WarrantyPeriodCost,
    PostWarrantyPeriodCost,
    OffshoreExtraCost,
    OperationalCost,
    TaxAndFinancial,
    WindFarmFinancialInputs,
)
from .country_profiles import CountryProfile, get_country_profile, SUPPORTED_COUNTRIES
from .calculator import calculate, CalculationResult, AnnualCashFlow
from .reverse_solver import (
    solve_tariff_for_target_irr,
    solve_investment_for_target_lcoe,
    solve_hours_for_target_irr,
    solve_tariff_for_zero_npv,
)
from .excel_export import export_to_excel

__all__ = [
    "BasicInfo",
    "OEMCost",
    "InstallationCost",
    "FoundationCost",
    "BOPCost",
    "OffshoreEPCBreakdown",
    "OnshoreInvestment",
    "InvestmentData",
    "FinancingTerms",
    "WarrantyPeriodCost",
    "PostWarrantyPeriodCost",
    "OffshoreExtraCost",
    "OperationalCost",
    "TaxAndFinancial",
    "WindFarmFinancialInputs",
    "CountryProfile",
    "get_country_profile",
    "SUPPORTED_COUNTRIES",
]
