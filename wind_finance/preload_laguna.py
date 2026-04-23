"""
预装 Laguna East 菲律宾陆上风电项目（11 种机型方案）
数据来源: 用户截图
"""

from .models import (
    BasicInfo,
    FinancingTerms,
    InvestmentData,
    OnshoreInvestment,
    OperationalCost,
    PostWarrantyPeriodCost,
    TaxAndFinancial,
    WarrantyPeriodCost,
    WindFarmFinancialInputs,
)
from .calculator import calculate, CalculationResult


def _build_variant(
    wtg_type: str,
    num_turbines: int,
    turbine_mw: float,
    p90_hours: float,
    rna_per_kw: float,
    tower_per_kw: float,
    transport_per_kw: float,
    install_per_kw: float,
    foundation_per_kw: float,
    cable_per_kw: float,
    substation_road_building_per_kw: float,
) -> tuple[WindFarmFinancialInputs, CalculationResult]:

    tsi_per_kw = rna_per_kw + tower_per_kw + transport_per_kw + install_per_kw
    bop_per_kw = foundation_per_kw + cable_per_kw + substation_road_building_per_kw

    onshore = OnshoreInvestment(
        equipment_and_installation=tsi_per_kw,
        civil_works=foundation_per_kw + substation_road_building_per_kw,
        construction_auxiliary=0.0,
        other_costs=cable_per_kw,
        contingency_rate=0.0,
        storage_cost=0.0,
        grid_connection_cost=0.0,
    )

    total_per_kw = tsi_per_kw + bop_per_kw

    basic = BasicInfo(
        project_name=f"Laguna East - {wtg_type}",
        project_type="onshore",
        country="Philippines",
        num_turbines=num_turbines,
        turbine_capacity_mw=turbine_mw,
        full_load_hours=p90_hours,
        loss_rate=0.03,
        construction_months=18,
    )

    investment = InvestmentData(
        unit_static_investment=total_per_kw,
        working_capital_per_kw=4.0,
        deductible_vat_ratio=0.0,
        onshore_detail=onshore,
    )

    financing = FinancingTerms(
        equity_ratio=0.30,
        long_term_loan_rate=0.07,
        loan_term_years=15,
        working_capital_loan_rate=0.07,
        working_capital_equity_ratio=0.30,
    )

    warranty = WarrantyPeriodCost(
        warranty_years=5,
        material_cost_per_kw=3.0,
        repair_cost_per_kw=0.0,
        other_cost_per_kw=5.0,
    )

    post_warranty = PostWarrantyPeriodCost(
        includes_major_components=True,
        material_cost_per_kw=4.0,
        other_cost_per_kw=6.0,
        maintenance_rates=[
            (1, 5, 0.005),
            (6, 10, 0.010),
            (11, 15, 0.015),
            (16, 20, 0.020),
            (21, 25, 0.025),
        ],
    )

    operational = OperationalCost(
        staff_count=15,
        salary_per_person=1.0,
        welfare_rate=0.40,
        insurance_rate=0.0025,
        depreciation_years=20,
        residual_rate=0.0,
        operation_years=25,
        warranty=warranty,
        post_warranty=post_warranty,
        offshore_extra=None,
    )

    tax = TaxAndFinancial(
        tariff_with_tax=0.098,
        vat_rate=0.12,
        vat_refund_rate=0.0,
        income_tax_rate=0.25,
        income_tax_holiday=(1, 7, 0.0, 8, 14, 0.10),
        urban_maintenance_tax_rate=0.0,
        education_surcharge_rate=0.0,
        discount_rate=0.08,
    )

    inputs = WindFarmFinancialInputs(
        basic=basic,
        investment=investment,
        financing=financing,
        operational=operational,
        tax_financial=tax,
    )
    result = calculate(inputs)
    return inputs, result


# 返回格式: (display_name, group, country, inputs, result)
ProjectEntry = tuple[str, str, str, WindFarmFinancialInputs, CalculationResult]


def get_all_projects() -> list[ProjectEntry]:
    """返回 Laguna East 全部 11 种机型方案，附带分组信息"""

    variants = [
        # (wtg_type, units, mw, p90h, rna, tower, transport, install, foundation, cable, sub+road+bldg)
        # ─── 第一批: MySE 系列 (来自第一张截图) ───
        ("MySE9.0-210",    38, 9.0,  3429,    255.0, 118.0, 187.5,   56.1,  36.0, 18.0, 379.0),
        ("MySE9.5-210",    36, 9.5,  3341,    241.0, 112.0, 176.0,   53.8,  34.0, 17.0, 379.0),
        ("MySE10.0-210",   34, 10.0, 3264,    237.0, 107.0, 168.1,   51.8,  32.0, 16.0, 379.0),
        ("MySE10.5-210",   32, 10.5, 3191,    225.0, 101.0, 161.0,   50.0,  31.0, 15.0, 379.0),
        ("MySE11.0-210",   31, 11.0, 3122,    215.0,  97.0, 152.9,   48.1,  29.0, 15.0, 379.0),
        # ─── 第二批: Envision / Sany / Mingyang (修正数据, Total: 985.71 / 954.71 / 1000.36 USD/kW) ───
        # Envision8.0-182: TSI=550, BOP=435.37, Total=985.71
        ("Envision8.0-182-ACEN",   43, 8.0, 3195.59, 219.659, 135.0, 127.464, 67.877, 36.0, 20.37, 379.0),
        # Envision8.0-171: 同 182 成本结构, 不同 P90
        ("Envision8.0-171-ACEN",   43, 8.0, 2904.04, 219.659, 135.0, 127.464, 67.877, 36.0, 20.37, 379.0),
        # Sany8.0-185: TSI=520, BOP=434.37, Total=954.71
        ("Sany8.0-185-Aboitiz",    43, 8.0, 3125.56, 189.659, 135.0, 127.464, 67.877, 35.0, 20.37, 379.0),
        # Mingyang9.0-210: TSI=567.36, BOP=433, Total=1000.36
        ("Mingyang9.0-210-ACEN",   38, 9.0, 3297.04, 229.883, 107.687, 195.790, 34.0, 36.0, 18.0,  379.0),
        # ─── 第三批: MySE9.0 塔筒变体 (来自第三张截图) ───
        ("MySE9.0-210/140",  39, 9.0, 3609, 255.0, 117.0, 187.5,   56.1,  40.0, 18.0, 379.0),
        ("MySE9.0-210/150",  39, 9.0, 3711, 255.0, 138.0, 190.3125, 56.9415, 43.0, 18.0, 379.0),
    ]

    GROUP = "Laguna East"
    COUNTRY = "Philippines"

    projects: list[ProjectEntry] = []
    for v in variants:
        wtg = v[0]
        capacity = v[1] * v[2]
        inp, res = _build_variant(*v)
        display_name = f"Laguna-{wtg} ({capacity:.0f}MW)"
        projects.append((display_name, GROUP, COUNTRY, inp, res))

    return projects
