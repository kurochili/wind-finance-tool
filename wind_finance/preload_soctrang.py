"""
预装 Soc Trang No.2 30MW (31.25MW) 越南朔庄省潮间带风电项目

MySE6.25-182 × 5台
CIF主机+塔筒: 1400 RMB/kW ≈ 200 USD/kW
两种BOP方案 × 两种发电量(P75/P90) = 4个变体
目标: 全投IRR(税前)=8%, 反算电价
"""

from .models import (
    BasicInfo,
    FinancingTerms,
    InvestmentData,
    OperationalCost,
    PostWarrantyPeriodCost,
    TaxAndFinancial,
    WarrantyPeriodCost,
    WindFarmFinancialInputs,
)
from .calculator import calculate, CalculationResult

FX = 7.0
NUM_WTG = 5
WTG_MW = 6.25
CAPACITY_KW = NUM_WTG * WTG_MW * 1000  # 31,250 kW

CIF_RMB_PER_KW = 1400
CIF_USD_PER_KW = CIF_RMB_PER_KW / FX

BOP_TOTAL_USD = {"V1": 3000e4, "V2": 3500e4}
P_HOURS = {"P75": 2750.9, "P90": 2677.4}

ProjectEntry = tuple[str, str, str, WindFarmFinancialInputs, CalculationResult]


def _build_inputs(static_per_kw: float, hours: float, tariff: float) -> WindFarmFinancialInputs:
    basic = BasicInfo(
        project_name="Soc Trang No.2",
        project_type="offshore",
        country="Vietnam",
        num_turbines=NUM_WTG,
        turbine_capacity_mw=WTG_MW,
        full_load_hours=hours,
        loss_rate=0.0,
        construction_months=18,
        investment_schedule=(0.6, 0.4),
    )
    investment = InvestmentData(
        unit_static_investment=static_per_kw,
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
            (6, 10, 0.010),
            (11, 15, 0.015),
            (16, 20, 0.020),
        ],
    )
    operational = OperationalCost(
        staff_count=10,
        salary_per_person=2.54,
        welfare_rate=0.60,
        insurance_rate=0.0025,
        depreciation_years=20,
        residual_rate=0.0,
        operation_years=20,
        warranty=warranty,
        post_warranty=post_warranty,
        offshore_extra=None,
    )
    tax = TaxAndFinancial(
        tariff_with_tax=tariff,
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
    return WindFarmFinancialInputs(
        basic=basic, investment=investment, financing=financing,
        operational=operational, tax_financial=tax,
    )


def _reverse_tariff(static_per_kw: float, hours: float, target_irr: float = 0.08) -> float:
    lo, hi = 0.01, 0.30
    for _ in range(80):
        mid = (lo + hi) / 2.0
        inp = _build_inputs(static_per_kw, hours, mid)
        r = calculate(inp)
        if r.project_irr_before_tax < target_irr:
            lo = mid
        else:
            hi = mid
        if abs(r.project_irr_before_tax - target_irr) < 1e-6:
            break
    return mid


def get_all_projects() -> list[ProjectEntry]:
    """返回 Soc Trang No.2 全部方案 (4个变体)"""
    GROUP = "Soc Trang No.2"
    COUNTRY = "Vietnam"

    projects: list[ProjectEntry] = []

    for bop_label, bop_total in BOP_TOTAL_USD.items():
        bop_per_kw = bop_total / CAPACITY_KW
        static_per_kw = CIF_USD_PER_KW + bop_per_kw

        for p_label, hours in P_HOURS.items():
            tariff = _reverse_tariff(static_per_kw, hours)
            inp = _build_inputs(static_per_kw, hours, tariff)
            result = calculate(inp)

            bop_wan = bop_total / 1e4
            display_name = (
                f"Soc Trang-6.25-182 BOP{bop_wan:.0f}万USD {p_label} "
                f"({static_per_kw:.0f}USD/kW)"
            )
            projects.append((display_name, GROUP, COUNTRY, inp, result))

    return projects
