"""
预装菲律宾 3 个海上风电项目
数据来源: 菲律宾项目造价拆分.xlsx
单位: 万 USD（转换为 USD 后输入模型）
汇率: 1 USD = 7.2 CNY（Excel 备注）
"""

from __future__ import annotations

from .models import (
    BasicInfo,
    FinancingTerms,
    InvestmentData,
    OffshoreExtraCost,
    OperationalCost,
    PostWarrantyPeriodCost,
    TaxAndFinancial,
    WarrantyPeriodCost,
    WindFarmFinancialInputs,
)
from .calculator import calculate, CalculationResult


WAN = 10_000  # 万 → 个


def _build_project(
    name: str,
    company: str,
    capacity_mw: float,
    num_turbines: int,
    turbine_mw: float,
    # 以下均为 万USD
    wtg_equipment: float,
    wtg_transport_install: float,
    foundation_supply: float,
    foundation_ti: float,
    cable_supply: float,
    cable_ti: float,
    onshore_substation: float,
    om_base: float,
    tech_design_pm: float,
    coordination_fee: float,
    full_load_hours: int = 3000,
) -> tuple[WindFarmFinancialInputs, CalculationResult]:

    capacity_kw = capacity_mw * 1000.0

    # 各项折算为 USD/kW
    wtg_equip_per_kw = wtg_equipment * WAN / capacity_kw
    wtg_ti_per_kw = wtg_transport_install * WAN / capacity_kw
    fnd_supply_per_kw = foundation_supply * WAN / capacity_kw
    fnd_ti_per_kw = foundation_ti * WAN / capacity_kw
    cable_supply_per_kw = cable_supply * WAN / capacity_kw
    cable_ti_per_kw = cable_ti * WAN / capacity_kw
    substation_per_kw = onshore_substation * WAN / capacity_kw
    om_base_per_kw = om_base * WAN / capacity_kw
    tech_pm_per_kw = tech_design_pm * WAN / capacity_kw
    coord_per_kw = coordination_fee * WAN / capacity_kw

    unit_investment = (
        wtg_equip_per_kw + wtg_ti_per_kw
        + fnd_supply_per_kw + fnd_ti_per_kw
        + cable_supply_per_kw + cable_ti_per_kw
        + substation_per_kw + om_base_per_kw
        + tech_pm_per_kw + coord_per_kw
    )

    basic = BasicInfo(
        project_name=f"{name} ({company})",
        project_type="offshore",
        country="Philippines",
        num_turbines=num_turbines,
        turbine_capacity_mw=turbine_mw,
        full_load_hours=full_load_hours,
        loss_rate=0.03,
        construction_months=24,
    )

    investment = InvestmentData(
        unit_static_investment=unit_investment,
        working_capital_per_kw=4.0,
        deductible_vat_ratio=0.0,
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
        material_cost_per_kw=4.0,
        repair_cost_per_kw=0.0,
        other_cost_per_kw=4.0,
    )

    post_warranty = PostWarrantyPeriodCost(
        includes_major_components=True,
        material_cost_per_kw=4.0,
        other_cost_per_kw=4.0,
        maintenance_rates=[
            (1, 5, 0.005),
            (6, 10, 0.010),
            (11, 15, 0.015),
            (16, 20, 0.020),
            (21, 25, 0.025),
        ],
    )

    offshore_extra = OffshoreExtraCost(
        requires_sov=False,
        sea_area_usage_fee=0.0,
        storage_rental=0.0,
        decommissioning_rate=0.02,
    )

    operational = OperationalCost(
        staff_count=35,
        salary_per_person=2.5,
        welfare_rate=0.40,
        insurance_rate=0.0035,
        depreciation_years=20,
        residual_rate=0.0,
        operation_years=25,
        warranty=warranty,
        post_warranty=post_warranty,
        offshore_extra=offshore_extra,
    )

    tax = TaxAndFinancial(
        tariff_with_tax=0.09,
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


def get_all_projects():
    """返回 3 个菲律宾海上项目: (name, group, country, inputs, result)"""

    projects = []

    # ---- 1. Frontera 450 MW ----
    inp, res = _build_project(
        name="Frontera",
        company="Ivisan Windkraft",
        capacity_mw=450,
        num_turbines=30,
        turbine_mw=15.0,
        wtg_equipment=29952.0,
        wtg_transport_install=8551.11,
        foundation_supply=25177.24,
        foundation_ti=52107.24,
        cable_supply=4044.14,
        cable_ti=4703.35,
        onshore_substation=3864.38,
        om_base=369.58,
        tech_design_pm=11671.10,
        coordination_fee=9129.50,
    )
    projects.append(("Frontera 450MW", "PH Offshore", "Philippines", inp, res))

    # ---- 2. Guimaras Strait Phase 1 - 600 MW ----
    inp, res = _build_project(
        name="Guimaras Strait Phase 1",
        company="Triconti Southwind",
        capacity_mw=600,
        num_turbines=40,
        turbine_mw=15.0,
        wtg_equipment=40248.0,
        wtg_transport_install=12422.22,
        foundation_supply=22682.98,
        foundation_ti=12142.72,
        cable_supply=5977.74,
        cable_ti=6510.96,
        onshore_substation=4487.97,
        om_base=518.84,
        tech_design_pm=17506.65,
        coordination_fee=10506.04,
    )
    projects.append(("Guimaras P1 600MW", "PH Offshore", "Philippines", inp, res))

    # ---- 3. Guimaras Strait Phase 2 - 600 MW ----
    inp, res = _build_project(
        name="Guimaras Strait Phase 2",
        company="Jet Stream Windkraft",
        capacity_mw=600,
        num_turbines=40,
        turbine_mw=15.0,
        wtg_equipment=40248.0,
        wtg_transport_install=12422.22,
        foundation_supply=22682.98,
        foundation_ti=12142.72,
        cable_supply=5977.74,
        cable_ti=6510.96,
        onshore_substation=4487.97,
        om_base=518.84,
        tech_design_pm=17506.65,
        coordination_fee=10506.04,
    )
    projects.append(("Guimaras P2 600MW", "PH Offshore", "Philippines", inp, res))

    return projects
