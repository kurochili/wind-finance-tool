"""
wind_finance.calculator
=======================
风电项目经济性评估 —— 正向计算引擎

核心功能：
1. 逐年现金流计算（全投资口径 + 资本金口径）
2. IRR（税前/税后）、NPV、投资回收期
3. 资本金 IRR、NPV
4. 度电成本 LCOE
5. 总投资收益率 ROI、资本金净利润率 ROE

所有货币单位为 USD。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

import numpy as np

from .models import WindFarmFinancialInputs


@dataclass
class AnnualCashFlow:
    """单年度现金流明细"""

    year: int                          # 年份序号（0=建设期第1年, 1=建设期第2年 或 运营期第1年, ...）
    is_construction: bool              # 是否为建设期

    # ---- 收入 ----
    revenue: float = 0.0               # 营业收入（不含增值税）
    vat_output: float = 0.0            # 销项增值税
    vat_input_deduction: float = 0.0   # 当年抵扣的进项增值税
    vat_refund: float = 0.0            # 增值税即征即退退税
    subsidy_income: float = 0.0        # 补贴收入（含即征即退退税 + 进项税抵扣节税）

    # ---- 成本 ----
    depreciation: float = 0.0          # 折旧费
    repair: float = 0.0                # 维修费
    material: float = 0.0              # 材料费
    staff_cost: float = 0.0            # 工资及福利
    insurance: float = 0.0             # 保险费
    other_opex: float = 0.0            # 其他费用
    offshore_extra: float = 0.0        # 海上专项费用
    total_opex: float = 0.0            # 经营成本合计（不含折旧、利息）

    # ---- 财务费用 ----
    loan_interest: float = 0.0         # 长期贷款利息
    wc_loan_interest: float = 0.0      # 流动资金贷款利息
    loan_principal: float = 0.0        # 当年还本

    # ---- 税费 ----
    vat_payable: float = 0.0           # 应缴增值税（抵扣后）
    surcharge: float = 0.0             # 销售税金附加
    resource_tax: float = 0.0          # 资源税
    income_tax: float = 0.0            # 所得税
    taxable_income: float = 0.0        # 应纳税所得额
    statutory_reserve: float = 0.0     # 法定盈余公积金

    # ---- 利润 ----
    total_cost: float = 0.0            # 总成本费用
    profit_before_tax: float = 0.0     # 利润总额（税前利润）
    net_profit: float = 0.0            # 净利润

    # ---- 现金流（全投资口径）----
    project_cash_inflow: float = 0.0   # 全投资现金流入
    project_cash_outflow: float = 0.0  # 全投资现金流出
    project_net_cf_before_tax: float = 0.0  # 全投资税前净现金流
    project_net_cf_after_tax: float = 0.0   # 全投资税后净现金流

    # ---- 现金流（资本金口径）----
    equity_cash_inflow: float = 0.0
    equity_cash_outflow: float = 0.0
    equity_net_cf: float = 0.0         # 资本金税后净现金流

    # ---- 其他 ----
    residual_value: float = 0.0        # 回收固定资产余值
    wc_recovery: float = 0.0           # 回收流动资金
    construction_outflow: float = 0.0  # 建设投资支出
    wc_outflow: float = 0.0            # 流动资金支出
    equity_outflow: float = 0.0        # 资本金支出
    remaining_loan: float = 0.0        # 年末剩余贷款余额


@dataclass
class CalculationResult:
    """计算结果汇总"""

    annual_flows: List[AnnualCashFlow]

    # ---- 全投资指标 ----
    project_irr_before_tax: float = 0.0
    project_irr_after_tax: float = 0.0
    project_npv_before_tax: float = 0.0
    project_npv_after_tax: float = 0.0
    payback_before_tax: float = 0.0    # 投资回收期（税前，年）
    payback_after_tax: float = 0.0     # 投资回收期（税后，年）

    # ---- 资本金指标 ----
    equity_irr: float = 0.0
    equity_npv: float = 0.0

    # ---- 收益率 ----
    lcoe: float = 0.0                  # 度电成本 (USD/kWh)
    roi: float = 0.0                   # 总投资收益率
    roe: float = 0.0                   # 资本金净利润率

    # ---- 其他 ----
    total_revenue: float = 0.0
    total_cost: float = 0.0
    total_profit: float = 0.0
    total_income_tax: float = 0.0


def calculate(inputs: WindFarmFinancialInputs) -> CalculationResult:
    """
    执行完整的风电项目财务评价计算

    Args:
        inputs: 完整的项目输入参数

    Returns:
        CalculationResult 包含逐年现金流和汇总指标
    """
    b = inputs.basic
    inv = inputs.investment
    fin = inputs.financing
    ops = inputs.operational
    tax = inputs.tax_financial

    capacity_kw = b.capacity_kw
    total_static = inputs.total_static_investment
    construction_interest = inputs.construction_interest
    total_dynamic = inputs.total_dynamic_investment
    working_capital = inputs.working_capital
    total_invest = inputs.total_investment
    deductible_vat = inputs.deductible_vat
    annual_gen_mwh = b.net_annual_generation_mwh

    # 固定资产原值 = 动态投资（静态 + 建设期利息）
    fixed_asset_value = total_dynamic
    # 可折旧基数 = 固定资产原值（简化处理，部分可研会扣除可抵扣进项税）
    depreciable_base = fixed_asset_value

    annual_depreciation = ops.annual_depreciation(depreciable_base)

    # 贷款金额（基于动态投资）
    loan_amount = fin.debt_for_construction(total_dynamic)

    # 建设期年数（向上取整）
    construction_years = max(1, (b.construction_months + 11) // 12)

    # 总计算期 = 建设期 + 运营期
    total_years = construction_years + ops.operation_years

    # 流动资金贷款
    wc_loan = working_capital * (1.0 - fin.working_capital_equity_ratio)
    wc_equity = working_capital * fin.working_capital_equity_ratio

    # ═══════════════════════════════════════════════════════════
    # 还本付息计划
    # ═══════════════════════════════════════════════════════════
    annual_principal = loan_amount / fin.loan_term_years if fin.loan_term_years > 0 else 0.0
    remaining_loan = loan_amount

    loan_schedule: list[tuple[float, float, float]] = []  # (还本, 付息, 余额)
    for yr in range(total_years):
        if yr < construction_years:
            loan_schedule.append((0.0, 0.0, loan_amount))
            continue

        op_year = yr - construction_years + 1
        if op_year <= fin.loan_term_years and remaining_loan > 0:
            interest = remaining_loan * fin.long_term_loan_rate
            principal = min(annual_principal, remaining_loan)
            remaining_loan -= principal
        else:
            interest = 0.0
            principal = 0.0

        loan_schedule.append((principal, interest, remaining_loan))

    # ═══════════════════════════════════════════════════════════
    # 增值税抵扣计划
    # ═══════════════════════════════════════════════════════════
    remaining_deductible = deductible_vat

    # ═══════════════════════════════════════════════════════════
    # 逐年计算
    # ═══════════════════════════════════════════════════════════
    flows: list[AnnualCashFlow] = []

    for yr in range(total_years):
        is_constr = yr < construction_years
        cf = AnnualCashFlow(year=yr, is_construction=is_constr)

        if is_constr:
            # 建设期投资分配
            schedule = b.investment_schedule
            if schedule and len(schedule) >= construction_years:
                frac = schedule[yr]
            else:
                frac = 1.0 / construction_years
            cf.construction_outflow = total_dynamic * frac

            cf.project_cash_outflow = cf.construction_outflow
            cf.project_net_cf_before_tax = -cf.construction_outflow
            cf.project_net_cf_after_tax = -cf.construction_outflow

            equity_constr = cf.construction_outflow * fin.equity_ratio
            cf.equity_outflow = equity_constr
            cf.equity_cash_outflow = equity_constr
            cf.equity_net_cf = -equity_constr

            cf.remaining_loan = loan_schedule[yr][2]
            flows.append(cf)
            continue

        op_year = yr - construction_years + 1  # 运营年份 (1-based)

        # ---- 流动资金（运营期第一年投入）----
        if op_year == 1:
            cf.wc_outflow = working_capital

        # ---- 收入 ----
        # 考虑限电
        if b.curtailment_years > 0 and op_year <= b.curtailment_years:
            gen_mwh = annual_gen_mwh * (1.0 - b.curtailment_rate)
        else:
            gen_mwh = annual_gen_mwh

        gen_kwh = gen_mwh * 1000.0
        cf.revenue = gen_kwh * tax.tariff_without_tax
        cf.vat_output = gen_kwh * tax.tariff_with_tax - cf.revenue  # 销项税 = 含税收入 - 不含税收入

        # ---- 增值税抵扣 ----
        if remaining_deductible > 0:
            deduction = min(remaining_deductible, cf.vat_output)
            cf.vat_input_deduction = deduction
            remaining_deductible -= deduction
            cf.vat_payable = 0.0
        else:
            cf.vat_payable = cf.vat_output

        # 即征即退
        if cf.vat_payable > 0:
            cf.vat_refund = cf.vat_payable * tax.vat_refund_rate
        else:
            cf.vat_refund = 0.0

        cf.subsidy_income = cf.vat_refund + cf.vat_input_deduction

        # ---- 运营成本 ----
        opex = ops.get_year_opex(op_year, capacity_kw, total_static)
        cf.material = opex["material"]
        cf.repair = opex["repair"]
        cf.other_opex = opex["other"]
        cf.staff_cost = opex["staff"]
        cf.insurance = opex["insurance"]
        cf.offshore_extra = opex["offshore_extra"]

        cf.total_opex = (
            cf.material + cf.repair + cf.other_opex
            + cf.staff_cost + cf.insurance + cf.offshore_extra
        )

        # ---- 折旧 ----
        if op_year <= ops.depreciation_years:
            cf.depreciation = annual_depreciation
        else:
            cf.depreciation = 0.0

        # ---- 财务费用 ----
        principal, interest, remain = loan_schedule[yr]
        cf.loan_principal = principal
        cf.loan_interest = interest
        cf.remaining_loan = remain
        cf.wc_loan_interest = wc_loan * fin.working_capital_loan_rate

        # ---- 总成本费用 ----
        cf.total_cost = cf.total_opex + cf.depreciation + cf.loan_interest + cf.wc_loan_interest

        # ---- 资源税 ----
        cf.resource_tax = cf.revenue * tax.resource_tax_rate

        # ---- 销售税金附加 ----
        if cf.vat_payable > 0:
            cf.surcharge = cf.vat_payable * tax.surcharge_rate
        else:
            cf.surcharge = 0.0

        # ---- 利润 ----
        cf.profit_before_tax = (
            cf.revenue + cf.subsidy_income
            - cf.total_cost - cf.surcharge - cf.resource_tax
        )

        # ---- 所得税 ----
        effective_tax_rate = tax.get_income_tax_rate(op_year)
        cf.taxable_income = max(0.0, cf.profit_before_tax)
        cf.income_tax = cf.taxable_income * effective_tax_rate

        cf.net_profit = cf.profit_before_tax - cf.income_tax

        # ---- 法定盈余公积金 ----
        cf.statutory_reserve = max(0.0, cf.net_profit) * tax.statutory_reserve_rate

        # ---- 回收（最后一年）----
        if op_year == ops.operation_years:
            cf.residual_value = depreciable_base * ops.residual_rate
            cf.wc_recovery = working_capital

        # ═══════════════════════════════════════════════════
        # 全投资现金流
        # ═══════════════════════════════════════════════════
        cf.project_cash_inflow = cf.revenue + cf.subsidy_income + cf.residual_value + cf.wc_recovery
        cf.project_cash_outflow = cf.total_opex + cf.surcharge + cf.resource_tax + cf.wc_outflow

        adjusted_income_tax = (
            cf.revenue - cf.depreciation - cf.total_opex
            - cf.surcharge - cf.resource_tax
        )
        adjusted_income_tax = max(0.0, adjusted_income_tax) * effective_tax_rate

        cf.project_net_cf_before_tax = cf.project_cash_inflow - cf.project_cash_outflow
        cf.project_net_cf_after_tax = cf.project_net_cf_before_tax - adjusted_income_tax

        # ═══════════════════════════════════════════════════
        # 资本金现金流
        # ═══════════════════════════════════════════════════
        cf.equity_cash_inflow = cf.project_cash_inflow

        equity_wc_out = 0.0
        if op_year == 1:
            equity_wc_out = wc_equity

        cf.equity_cash_outflow = (
            cf.total_opex
            + cf.surcharge
            + cf.resource_tax
            + cf.loan_principal
            + cf.loan_interest
            + cf.wc_loan_interest
            + cf.income_tax
            + cf.statutory_reserve
            + equity_wc_out
        )
        cf.equity_net_cf = cf.equity_cash_inflow - cf.equity_cash_outflow

        flows.append(cf)

    # ═══════════════════════════════════════════════════════════
    # 汇总指标计算
    # ═══════════════════════════════════════════════════════════

    project_cf_before = np.array([f.project_net_cf_before_tax for f in flows])
    project_cf_after = np.array([f.project_net_cf_after_tax for f in flows])
    equity_cf = np.array([f.equity_net_cf for f in flows])

    result = CalculationResult(annual_flows=flows)

    # IRR
    result.project_irr_before_tax = _compute_irr(project_cf_before)
    result.project_irr_after_tax = _compute_irr(project_cf_after)
    result.equity_irr = _compute_irr(equity_cf)

    # NPV
    result.project_npv_before_tax = _compute_npv(project_cf_before, tax.discount_rate)
    result.project_npv_after_tax = _compute_npv(project_cf_after, tax.discount_rate)
    result.equity_npv = _compute_npv(equity_cf, tax.discount_rate)

    # 投资回收期
    result.payback_before_tax = _compute_payback(project_cf_before)
    result.payback_after_tax = _compute_payback(project_cf_after)

    # 汇总
    op_flows = [f for f in flows if not f.is_construction]
    result.total_revenue = sum(f.revenue for f in op_flows)
    result.total_cost = sum(f.total_cost for f in op_flows)
    result.total_profit = sum(f.profit_before_tax for f in op_flows)
    result.total_income_tax = sum(f.income_tax for f in op_flows)

    # LCOE = 总成本现值 / 总发电量现值
    result.lcoe = _compute_lcoe(inputs, flows, tax.discount_rate)

    # ROI = 运营期年均利润总额 / 总投资
    avg_profit = result.total_profit / ops.operation_years if ops.operation_years > 0 else 0.0
    result.roi = avg_profit / total_invest if total_invest > 0 else 0.0

    # ROE = 运营期年均净利润 / 资本金
    total_net_profit = sum(f.net_profit for f in op_flows)
    avg_net_profit = total_net_profit / ops.operation_years if ops.operation_years > 0 else 0.0
    equity_total = fin.equity_for_construction(total_dynamic) + wc_equity
    result.roe = avg_net_profit / equity_total if equity_total > 0 else 0.0

    return result


# ════════════════════════════════════════════════════════════════════════════
# 辅助函数
# ════════════════════════════════════════════════════════════════════════════

def _compute_irr(cashflows: np.ndarray) -> float:
    """计算内部收益率 (IRR)，使用二分法求解"""
    try:
        return float(np.irr(cashflows))  # type: ignore[attr-defined]
    except (AttributeError, Exception):
        pass
    return _irr_bisect(cashflows)


def _irr_bisect(cashflows: np.ndarray, lo: float = -0.3, hi: float = 2.0, tol: float = 1e-8) -> float:
    """二分法求 IRR"""
    def npv_at(rate: float) -> float:
        return sum(cf / (1.0 + rate) ** t for t, cf in enumerate(cashflows))

    if npv_at(lo) * npv_at(hi) > 0:
        # 尝试扩大搜索范围
        for h in [5.0, 10.0, 50.0]:
            if npv_at(lo) * npv_at(h) <= 0:
                hi = h
                break
        else:
            return 0.0

    for _ in range(200):
        mid = (lo + hi) / 2.0
        v = npv_at(mid)
        if abs(v) < tol:
            return mid
        if npv_at(lo) * v < 0:
            hi = mid
        else:
            lo = mid
    return (lo + hi) / 2.0


def _compute_npv(cashflows: np.ndarray, rate: float) -> float:
    """计算净现值 (NPV)"""
    return sum(cf / (1.0 + rate) ** t for t, cf in enumerate(cashflows))


def _compute_payback(cashflows: np.ndarray) -> float:
    """计算投资回收期（年）"""
    cumulative = np.cumsum(cashflows)
    for i in range(1, len(cumulative)):
        if cumulative[i] >= 0 and cumulative[i - 1] < 0:
            frac = -cumulative[i - 1] / (cumulative[i] - cumulative[i - 1])
            return i + frac
    return float(len(cashflows))


def _compute_lcoe(
    inputs: WindFarmFinancialInputs,
    flows: list[AnnualCashFlow],
    discount_rate: float,
) -> float:
    """
    度电成本 LCOE (USD/kWh)

    与中国可研报告一致的简单度电成本:
    LCOE = 运营期总成本费用 / 运营期总发电量(kWh)

    总成本费用包含折旧（已摊销投资）、经营成本、利息支出。
    """
    b = inputs.basic
    construction_years = max(1, (b.construction_months + 11) // 12)

    total_cost = 0.0
    total_gen_kwh = 0.0

    for f in flows:
        if f.is_construction:
            continue
        total_cost += f.total_cost
        op_year = f.year - construction_years + 1
        if b.curtailment_years > 0 and op_year <= b.curtailment_years:
            total_gen_kwh += b.net_annual_generation_mwh * (1.0 - b.curtailment_rate) * 1000.0
        else:
            total_gen_kwh += b.net_annual_generation_mwh * 1000.0

    if total_gen_kwh <= 0:
        return 0.0
    return total_cost / total_gen_kwh


def print_summary(inputs: WindFarmFinancialInputs, result: CalculationResult) -> None:
    """打印财务评价结果摘要"""
    USD_TO_CNY = 7.1

    print(f"\n{'='*70}")
    print(f"  财务评价结果 —— {inputs.basic.project_name}")
    print(f"{'='*70}")
    print(f"  全投资 IRR (税前): {result.project_irr_before_tax:.2%}")
    print(f"  全投资 IRR (税后): {result.project_irr_after_tax:.2%}")
    print(f"  全投资 NPV (税后): {result.project_npv_after_tax:,.0f} USD ({result.project_npv_after_tax * USD_TO_CNY / 1e4:,.2f} 万元)")
    print(f"  投资回收期 (税后): {result.payback_after_tax:.2f} 年")
    print(f"{'─'*70}")
    print(f"  资本金 IRR: {result.equity_irr:.2%}")
    print(f"  资本金 NPV: {result.equity_npv:,.0f} USD ({result.equity_npv * USD_TO_CNY / 1e4:,.2f} 万元)")
    print(f"{'─'*70}")
    print(f"  度电成本 (LCOE): {result.lcoe:.6f} USD/kWh ({result.lcoe * USD_TO_CNY:.4f} 元/kWh)")
    print(f"  总投资收益率 (ROI): {result.roi:.2%}")
    print(f"  资本金净利润率 (ROE): {result.roe:.2%}")
    print(f"{'─'*70}")
    print(f"  总营业收入: {result.total_revenue:,.0f} USD ({result.total_revenue * USD_TO_CNY / 1e4:,.2f} 万元)")
    print(f"  总成本费用: {result.total_cost:,.0f} USD ({result.total_cost * USD_TO_CNY / 1e4:,.2f} 万元)")
    print(f"  总所得税: {result.total_income_tax:,.0f} USD ({result.total_income_tax * USD_TO_CNY / 1e4:,.2f} 万元)")
    print(f"{'='*70}")
