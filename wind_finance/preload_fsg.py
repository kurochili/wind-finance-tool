"""
预装 FSG 澳大利亚陆上风电项目（2 种机型方案）
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
    tariff: float,
) -> tuple[WindFarmFinancialInputs, CalculationResult]:

    tsi_per_kw = rna_per_kw + tower_per_kw + transport_per_kw + install_per_kw
    bop_per_kw = foundation_per_kw + cable_per_kw + substation_road_building_per_kw
    total_per_kw = tsi_per_kw + bop_per_kw

    onshore = OnshoreInvestment(
        equipment_and_installation=tsi_per_kw,
        civil_works=foundation_per_kw + substation_road_building_per_kw,
        construction_auxiliary=0.0,
        other_costs=cable_per_kw,
        contingency_rate=0.0,
        storage_cost=0.0,
        grid_connection_cost=0.0,
    )

    basic = BasicInfo(
        project_name=f"FSG - {wtg_type}",
        project_type="onshore",
        country="Australia",
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
        long_term_loan_rate=0.055,
        loan_term_years=15,
        working_capital_loan_rate=0.055,
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
        staff_count=20,
        salary_per_person=3.0,
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
        tariff_with_tax=tariff,
        vat_rate=0.10,
        vat_refund_rate=0.0,
        income_tax_rate=0.30,
        income_tax_holiday=(1, 1, 0.30, 1, 1, 0.30),
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


ProjectEntry = tuple[str, str, str, WindFarmFinancialInputs, CalculationResult]


def get_all_projects() -> list[ProjectEntry]:
    """返回 FSG 澳大利亚全部机型方案"""

    variants = [
        # (wtg_type, units, mw, p90h, rna/cif, tower, transport, install, foundation, cable, sub+road+bldg, tariff)
        # ─── FOB 报价方案（RNA+Tower 分列）───
        ("MySE9.0-210(FOB)",  60, 9.0,  3177, 236.0, 94.87, 187.5, 56.1, 36.0, 18.0, 379.0, 0.085),
        ("MySE11.0-210(FOB)", 49, 11.0, 2725, 193.0, 77.62, 153.1, 48.1, 29.0, 15.0, 379.0, 0.085),
        # ─── CIF 报价方案（CIF到岸价，运输仅含内陆段）───
        ("MySE9.0-210(CIF)",  60, 9.0,  3177, 497.0, 0.0, 80.0, 56.1, 36.0, 18.0, 379.0, 0.085),
        ("MySE11.0-210(CIF)", 49, 11.0, 2725, 453.0, 0.0, 75.0, 48.1, 29.4, 14.7, 379.0, 0.085),
    ]

    GROUP = "FSG"
    COUNTRY = "Australia"

    projects: list[ProjectEntry] = []
    for v in variants:
        wtg = v[0]
        capacity = v[1] * v[2]
        inp, res = _build_variant(*v)
        display_name = f"FSG-{wtg} ({capacity:.0f}MW)"
        projects.append((display_name, GROUP, COUNTRY, inp, res))

    return projects
