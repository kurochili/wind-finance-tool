"""
wind_finance.reverse_solver
============================
风电项目经济性评估 —— 反算模块

支持 4 种反算场景：
1. 给定目标全投资 IRR → 反算上网电价
2. 给定目标 LCOE → 反算单位千瓦投资（或风机定价）
3. 给定目标 IRR → 反算最低满负荷小时数
4. 给定 NPV=0 → 反算临界条件（电价/投资/小时数任选）

使用 scipy.optimize.brentq 二分法求解。
"""

from __future__ import annotations

import copy
from typing import Literal, Optional

from scipy.optimize import brentq

from .calculator import CalculationResult, calculate
from .models import WindFarmFinancialInputs


def _get_irr(
    result: CalculationResult,
    irr_type: str,
) -> float:
    if irr_type == "project_before_tax":
        return result.project_irr_before_tax
    elif irr_type == "project_after_tax":
        return result.project_irr_after_tax
    elif irr_type == "equity":
        return result.equity_irr
    raise ValueError(f"Unknown irr_type: {irr_type}")


def _get_npv(
    result: CalculationResult,
    npv_type: str,
) -> float:
    if npv_type == "project_before_tax":
        return result.project_npv_before_tax
    elif npv_type == "project_after_tax":
        return result.project_npv_after_tax
    elif npv_type == "equity":
        return result.equity_npv
    raise ValueError(f"Unknown npv_type: {npv_type}")


# ════════════════════════════════════════════════════════════════════════════
# 1. 给定目标 IRR → 反算上网电价
# ════════════════════════════════════════════════════════════════════════════

def solve_tariff_for_target_irr(
    inputs: WindFarmFinancialInputs,
    target_irr: float,
    irr_type: Literal["project_before_tax", "project_after_tax", "equity"] = "project_after_tax",
    tariff_range: tuple[float, float] = (0.001, 0.50),
) -> float:
    """
    给定目标 IRR，反算所需的上网电价（含税，USD/kWh）

    Args:
        inputs: 项目参数（tariff_with_tax 将被替换）
        target_irr: 目标 IRR（小数，如 0.08 = 8%）
        irr_type: IRR 类型
        tariff_range: 搜索范围 (USD/kWh)

    Returns:
        满足目标 IRR 的含税电价 (USD/kWh)
    """
    def objective(tariff: float) -> float:
        inp = copy.deepcopy(inputs)
        inp.tax_financial.tariff_with_tax = tariff
        result = calculate(inp)
        return _get_irr(result, irr_type) - target_irr

    return brentq(objective, tariff_range[0], tariff_range[1], xtol=1e-8)


# ════════════════════════════════════════════════════════════════════════════
# 2. 给定目标 LCOE → 反算单位千瓦投资
# ════════════════════════════════════════════════════════════════════════════

def solve_investment_for_target_lcoe(
    inputs: WindFarmFinancialInputs,
    target_lcoe: float,
    investment_range: tuple[float, float] = (100.0, 5000.0),
) -> float:
    """
    给定目标 LCOE，反算所需的单位千瓦静态投资 (USD/kW)

    Args:
        inputs: 项目参数（unit_static_investment 将被替换）
        target_lcoe: 目标度电成本 (USD/kWh)
        investment_range: 搜索范围 (USD/kW)

    Returns:
        满足目标 LCOE 的单位千瓦投资 (USD/kW)
    """
    def objective(unit_inv: float) -> float:
        inp = copy.deepcopy(inputs)
        inp.investment.unit_static_investment = unit_inv
        result = calculate(inp)
        return result.lcoe - target_lcoe

    return brentq(objective, investment_range[0], investment_range[1], xtol=1e-6)


def solve_turbine_price_for_target_lcoe(
    inputs: WindFarmFinancialInputs,
    target_lcoe: float,
    price_range: tuple[float, float] = (100.0, 3000.0),
) -> Optional[float]:
    """
    给定目标 LCOE，反算风机 OEM 单价 (USD/kW)

    仅适用于有海上 EPC 明细的项目。通过调整 OEM turbine_price_per_kw，
    联动 total_epc_per_kw → unit_static_investment。

    Returns:
        满足目标 LCOE 的风机 OEM 单价 (USD/kW)，如果无 EPC 明细则返回 None
    """
    if inputs.investment.offshore_detail is None:
        return None

    def objective(turbine_price: float) -> float:
        inp = copy.deepcopy(inputs)
        inp.investment.offshore_detail.oem.turbine_price_per_kw = turbine_price
        inp.investment.unit_static_investment = inp.investment.offshore_detail.total_epc_per_kw
        result = calculate(inp)
        return result.lcoe - target_lcoe

    return brentq(objective, price_range[0], price_range[1], xtol=1e-6)


# ════════════════════════════════════════════════════════════════════════════
# 3. 给定目标 IRR → 反算最低满负荷小时数
# ════════════════════════════════════════════════════════════════════════════

def solve_hours_for_target_irr(
    inputs: WindFarmFinancialInputs,
    target_irr: float,
    irr_type: Literal["project_before_tax", "project_after_tax", "equity"] = "project_after_tax",
    hours_range: tuple[int, int] = (500, 6000),
) -> float:
    """
    给定目标 IRR，反算所需的最低年等效满负荷小时数

    Args:
        inputs: 项目参数（full_load_hours 将被替换）
        target_irr: 目标 IRR（小数）
        hours_range: 搜索范围（小时）

    Returns:
        满足目标 IRR 的满负荷小时数 (h)
    """
    def objective(hours: float) -> float:
        inp = copy.deepcopy(inputs)
        inp.basic.full_load_hours = int(round(hours))
        result = calculate(inp)
        return _get_irr(result, irr_type) - target_irr

    return brentq(objective, float(hours_range[0]), float(hours_range[1]), xtol=1.0)


# ════════════════════════════════════════════════════════════════════════════
# 4. NPV=0 → 反算临界条件
# ════════════════════════════════════════════════════════════════════════════

def solve_tariff_for_zero_npv(
    inputs: WindFarmFinancialInputs,
    npv_type: Literal["project_before_tax", "project_after_tax", "equity"] = "project_after_tax",
    tariff_range: tuple[float, float] = (0.001, 0.50),
) -> float:
    """给定 NPV=0，反算临界电价 (含税 USD/kWh)"""
    def objective(tariff: float) -> float:
        inp = copy.deepcopy(inputs)
        inp.tax_financial.tariff_with_tax = tariff
        result = calculate(inp)
        return _get_npv(result, npv_type)

    return brentq(objective, tariff_range[0], tariff_range[1], xtol=1e-8)


def solve_investment_for_zero_npv(
    inputs: WindFarmFinancialInputs,
    npv_type: Literal["project_before_tax", "project_after_tax", "equity"] = "project_after_tax",
    investment_range: tuple[float, float] = (100.0, 5000.0),
) -> float:
    """给定 NPV=0，反算临界单位千瓦投资 (USD/kW)"""
    def objective(unit_inv: float) -> float:
        inp = copy.deepcopy(inputs)
        inp.investment.unit_static_investment = unit_inv
        result = calculate(inp)
        return _get_npv(result, npv_type)

    return brentq(objective, investment_range[0], investment_range[1], xtol=1e-6)


def solve_hours_for_zero_npv(
    inputs: WindFarmFinancialInputs,
    npv_type: Literal["project_before_tax", "project_after_tax", "equity"] = "project_after_tax",
    hours_range: tuple[int, int] = (500, 6000),
) -> float:
    """给定 NPV=0，反算临界发电小时数"""
    def objective(hours: float) -> float:
        inp = copy.deepcopy(inputs)
        inp.basic.full_load_hours = int(round(hours))
        result = calculate(inp)
        return _get_npv(result, npv_type)

    return brentq(objective, float(hours_range[0]), float(hours_range[1]), xtol=1.0)
