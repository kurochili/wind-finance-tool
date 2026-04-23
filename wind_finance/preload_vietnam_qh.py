"""
预装 越南庆和省800MW海上风电项目（中南V2）
数据来源: 用户截图 - 越南庆和省800MW海风项目经济评价计算过程
原始数据单位: CNY, 汇率 1 USD = 7.1 CNY
"""

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

FX = 7.1  # 1 USD = 7.1 CNY

ProjectEntry = tuple[str, str, str, WindFarmFinancialInputs, CalculationResult]


def get_all_projects() -> list[ProjectEntry]:
    """返回越南庆和800MW海上风电方案"""

    # ── 原始数据(CNY) ──
    capacity_mw = 800.0
    num_turbines = 50          # 假设 MySE16.0 × 50台
    turbine_mw = 16.0
    p90_hours = 3539.7         # 已含尾流损失13.6% + 弃电5%
    construction_months = 36   # 3年建设期（但开算工期2.5年，schedule反映实际）

    # 投资 (CNY/kW → USD/kW)
    total_per_kw_cny = 14000.0  # 1.4万元/kW
    total_per_kw = total_per_kw_cny / FX  # ~1972 USD/kW

    # 融资
    equity_ratio = 0.30        # 注资比例30%
    loan_rate = 0.055          # 基建贷款利率5.5%
    loan_term = 15

    # 运维 (CNY → USD)
    staff_count = 58
    salary_cny = 25.0          # 万元/人/年
    salary_usd = salary_cny / FX  # 万USD/人/年
    welfare_rate = 0.90        # 福利费系数90%(越南1.5倍)
    material_per_kw = 36.0 / FX   # 材料费 36元/kW → USD
    other_per_kw = 60.0 / FX      # 其他费用 60元/kW → USD
    insurance_rate = 0.003 * 1.2  # 0.3%×1.2倍=0.36%

    # 修理费率(越南=国内×1.2)
    repair_rates = [
        (1,  5,  0.006),   # 0.5%×1.2
        (6,  10, 0.012),   # 1.0%×1.2
        (11, 15, 0.024),   # 2.0%×1.2
        (16, 20, 0.030),   # 2.5%×1.2
        (21, 25, 0.036),   # 3.0%×1.2
    ]

    # 海上额外费用
    sea_area_fee_cny = 768.0    # 万元/年(0.2万/公顷×3840公顷)
    sea_area_fee_usd = sea_area_fee_cny / FX  # 万USD/年 → 按USD总额
    # 转换为 USD/kW/年: 768万CNY / 800,000kW / 7.1
    # 在模型中 sea_area_usage_fee 的单位要查
    # 先按万USD存: 108万USD/年

    land_rental_cny = 80.0  # 万元/年

    # 电价
    tariff_incl_tax_cny = 0.53163  # 元/kWh (不含税0.4833×1.1)
    tariff_incl_tax_usd = tariff_incl_tax_cny / FX  # ~0.0749 USD/kWh

    # 税费
    vat_rate = 0.10
    income_tax_rate = 0.20     # 标准税率20%
    # 优惠: 1-4年免征, 5-15年10%
    income_tax_holiday = (1, 4, 0.0, 5, 15, 0.10)

    depreciation_years = 20
    residual_rate = 0.04

    # ── 构建模型输入 ──
    basic = BasicInfo(
        project_name="Vietnam QH 800MW Offshore",
        project_type="offshore",
        country="Vietnam",
        num_turbines=num_turbines,
        turbine_capacity_mw=turbine_mw,
        full_load_hours=p90_hours,
        loss_rate=0.0,   # 利用小时已含全部损失
        construction_months=construction_months,
        investment_schedule=(0.4, 0.3, 0.3),  # 三年日历期投资40/30/30%，开算工期2.5年
    )

    investment = InvestmentData(
        unit_static_investment=total_per_kw,
        working_capital_per_kw=36.0 / FX,  # 流动资金36元/kW
        deductible_vat_ratio=0.0,             # 越南项目暂无进项税抵扣
    )

    # 建设期利息 = 64,680万元 = 64680/7.1 万USD
    ci_override_usd = 64680.0 * 1e4 / FX

    financing = FinancingTerms(
        equity_ratio=equity_ratio,
        long_term_loan_rate=loan_rate,
        loan_term_years=loan_term,
        construction_interest_override=ci_override_usd,
        working_capital_loan_rate=0.04,
        working_capital_equity_ratio=0.70,
    )

    warranty = WarrantyPeriodCost(
        warranty_years=5,
        material_cost_per_kw=material_per_kw,
        repair_cost_per_kw=0.0,
        other_cost_per_kw=other_per_kw,
    )

    post_warranty = PostWarrantyPeriodCost(
        includes_major_components=True,
        material_cost_per_kw=material_per_kw,
        other_cost_per_kw=other_per_kw,
        maintenance_rates=repair_rates,
    )

    offshore_extra = OffshoreExtraCost(
        requires_sov=True,
        sov_annual_cost=0.0,
        sea_area_usage_fee=sea_area_fee_usd,  # ~108万USD/年
        storage_rental=land_rental_cny / FX,   # 土地租赁 ~11.3万USD/年
        decommissioning_rate=0.0,
    )

    operational = OperationalCost(
        staff_count=staff_count,
        salary_per_person=salary_usd,
        welfare_rate=welfare_rate,
        insurance_rate=insurance_rate,
        depreciation_years=depreciation_years,
        residual_rate=residual_rate,
        operation_years=25,
        warranty=warranty,
        post_warranty=post_warranty,
        offshore_extra=offshore_extra,
    )

    tax = TaxAndFinancial(
        tariff_with_tax=tariff_incl_tax_usd,
        vat_rate=vat_rate,
        vat_refund_rate=0.0,
        income_tax_rate=income_tax_rate,
        income_tax_holiday=income_tax_holiday,
        urban_maintenance_tax_rate=0.0,
        education_surcharge_rate=0.0,
        resource_tax_rate=0.01,        # 资源税 = 营收的1%
        statutory_reserve_rate=0.05,   # 法定公积金 = 净利润的5%
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

    GROUP = "Vietnam QH Offshore"
    COUNTRY = "Vietnam"
    display_name = "Vietnam-QH-800MW"

    return [(display_name, GROUP, COUNTRY, inputs, result)]
