"""
预装 Ha Tinh (河静省) 海上风电项目 - 3个机型方案
数据来源: 经济性计算输入.xlsx
电价: 0.170 USD/kWh (含税, 北部湾区域上限)
"""

from .models import (
    BasicInfo, FinancingTerms, InvestmentData, OffshoreExtraCost,
    OperationalCost, PostWarrantyPeriodCost, TaxAndFinancial,
    WarrantyPeriodCost, WindFarmFinancialInputs,
)
from .calculator import calculate, CalculationResult

FX = 7.0
TARIFF = 0.170

VARIANTS = [
    {"wtg": "MySE8.5-230", "units": 47, "mw": 8.5, "p90_hrs": 2070,
     "tsi_per_kw": 563.40, "bop_per_kw": 838.60, "capex_per_kw": 1402.0},
    {"wtg": "MySE5.0-233", "units": 80, "mw": 5.0, "p90_hrs": 2353,
     "tsi_per_kw": 674.72, "bop_per_kw": 871.14, "capex_per_kw": 1545.86},
    {"wtg": "MySE9.0-210", "units": 45, "mw": 9.0, "p90_hrs": 1810,
     "tsi_per_kw": 451.43, "bop_per_kw": 826.77, "capex_per_kw": 1278.20},
]

ProjectEntry = tuple[str, str, str, WindFarmFinancialInputs, CalculationResult]


def _build(v) -> tuple[WindFarmFinancialInputs, CalculationResult]:
    basic = BasicInfo(
        project_name=f"Ha Tinh - {v['wtg']}",
        project_type="offshore",
        country="Vietnam",
        num_turbines=v["units"],
        turbine_capacity_mw=v["mw"],
        full_load_hours=v["p90_hrs"],
        loss_rate=0.0,
        construction_months=24,
        investment_schedule=(0.3, 0.4, 0.3),
    )
    investment = InvestmentData(
        unit_static_investment=v["capex_per_kw"],
        working_capital_per_kw=30.0 / FX,
        deductible_vat_ratio=0.0,
    )
    financing = FinancingTerms(
        equity_ratio=0.30,
        long_term_loan_rate=0.055,
        loan_term_years=15,
        working_capital_loan_rate=0.04,
        working_capital_equity_ratio=0.70,
    )
    warranty = WarrantyPeriodCost(
        warranty_years=5,
        material_cost_per_kw=0.63,
        repair_cost_per_kw=0.74,
        other_cost_per_kw=3.45,
    )
    post_warranty = PostWarrantyPeriodCost(
        includes_major_components=True,
        material_cost_per_kw=1.27,
        other_cost_per_kw=3.45,
        maintenance_rates=[
            (6, 10, 0.010), (11, 15, 0.015),
            (16, 20, 0.020), (21, 25, 0.025),
        ],
    )
    operational = OperationalCost(
        staff_count=35,
        salary_per_person=2.54,
        welfare_rate=0.60,
        insurance_rate=0.0035,
        depreciation_years=20,
        residual_rate=0.0,
        operation_years=25,
        warranty=warranty,
        post_warranty=post_warranty,
        offshore_extra=OffshoreExtraCost(
            requires_sov=True,
            sov_annual_cost=150.0,
            sea_area_usage_fee=50.0,
        ),
    )
    tax = TaxAndFinancial(
        tariff_with_tax=TARIFF,
        vat_rate=0.10,
        vat_refund_rate=0.0,
        income_tax_rate=0.20,
        income_tax_holiday=(1, 4, 0.0, 5, 15, 0.10),
        urban_maintenance_tax_rate=0.0,
        education_surcharge_rate=0.0,
        resource_tax_rate=0.01,
        statutory_reserve_rate=0.05,
        discount_rate=0.08,
    )
    inp = WindFarmFinancialInputs(
        basic=basic, investment=investment, financing=financing,
        operational=operational, tax_financial=tax,
    )
    return inp, calculate(inp)


def get_all_projects() -> list[ProjectEntry]:
    GROUP = "Ha Tinh Offshore"
    COUNTRY = "Vietnam"
    projects: list[ProjectEntry] = []
    for v in VARIANTS:
        cap = v["units"] * v["mw"]
        inp, res = _build(v)
        name = f"Ha Tinh-{v['wtg']} ({cap:.0f}MW)"
        projects.append((name, GROUP, COUNTRY, inp, res))
    return projects
