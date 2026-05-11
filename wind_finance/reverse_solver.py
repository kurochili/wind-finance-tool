"""
wind_finance.reverse_solver
============================
风电项目经济性评估 -- 反算模块

支持 5 种反算场景:
1. 给定目标 IRR -> 反算上网电价
2. 给定目标 LCOE -> 反算单位千瓦投资
3. 给定目标 IRR -> 反算最低满负荷小时数
4. 给定目标 LCOE -> 反算风机价格（海上EPC明细 或 陆上设备明细）
5. 给定目标 IRR -> 反算风机价格（海上/陆上均支持）

算法基础:
- 使用 scipy.optimize.brentq（Brent法）二分求解，收敛精度 1e-6~1e-8
- IRR 计算基于 DCF（折现现金流），符合 IEC/IEEE/AACE 国际标准
- LCOE 采用简单度电成本法（总成本/总发电量），与 IRENA/BNEF/中国可研一致
- 各国差异体现在输入参数（税率/折现率/融资结构），不影响求解算法本身
"""

from __future__ import annotations

import copy
from typing import Literal, Optional

from scipy.optimize import brentq

from .calculator import CalculationResult, calculate
from .models import WindFarmFinancialInputs


def _get_irr(result: CalculationResult, irr_type: str) -> float:
    if irr_type == "project_before_tax":
        return result.project_irr_before_tax
    elif irr_type == "project_after_tax":
        return result.project_irr_after_tax
    elif irr_type == "equity":
        return result.equity_irr
    raise ValueError(f"Unknown irr_type: {irr_type}")


def _get_npv(result: CalculationResult, npv_type: str) -> float:
    if npv_type == "project_before_tax":
        return result.project_npv_before_tax
    elif npv_type == "project_after_tax":
        return result.project_npv_after_tax
    elif npv_type == "equity":
        return result.equity_npv
    raise ValueError(f"Unknown npv_type: {npv_type}")


def _sync_investment(inp: WindFarmFinancialInputs):
    """同步明细投资到 unit_static_investment，确保运维费联动"""
    if inp.investment.onshore_detail is not None:
        inp.investment.unit_static_investment = inp.investment.onshore_detail.total_per_kw
    elif inp.investment.offshore_detail is not None:
        inp.investment.unit_static_investment = inp.investment.offshore_detail.total_epc_per_kw


# ════════════════════════════════════════════════════════════════════════════
# 1. 给定目标 IRR -> 反算上网电价
# ════════════════════════════════════════════════════════════════════════════

def solve_tariff_for_target_irr(
    inputs: WindFarmFinancialInputs,
    target_irr: float,
    irr_type: Literal["project_before_tax", "project_after_tax", "equity"] = "project_after_tax",
    tariff_range: tuple[float, float] = (0.001, 0.50),
) -> float:
    """
    给定目标 IRR，反算所需的含税上网电价 (USD/kWh)。

    标准依据: DCF-IRR 反求，与 IFC/BNEF/中国可研报告的电价测算方法一致。
    各国差异: 通过输入参数（税率/增值税/所得税优惠/融资）自动体现，无需修改算法。
    """
    def objective(tariff: float) -> float:
        inp = copy.deepcopy(inputs)
        inp.tax_financial.tariff_with_tax = tariff
        result = calculate(inp)
        return _get_irr(result, irr_type) - target_irr

    return brentq(objective, tariff_range[0], tariff_range[1], xtol=1e-8)


# ════════════════════════════════════════════════════════════════════════════
# 2. 给定目标 LCOE -> 反算单位千瓦投资
# ════════════════════════════════════════════════════════════════════════════

def solve_investment_for_target_lcoe(
    inputs: WindFarmFinancialInputs,
    target_lcoe: float,
    investment_range: tuple[float, float] = (100.0, 5000.0),
) -> float:
    """
    给定目标 LCOE，反算所需的单位千瓦静态投资 (USD/kW)。

    注意: 修改总投资会影响折旧、利息、运维费（可研法基于投资百分比），
    因此不能简单线性反推，需要迭代求解。
    """
    def objective(unit_inv: float) -> float:
        inp = copy.deepcopy(inputs)
        inp.investment.unit_static_investment = unit_inv
        if inp.investment.onshore_detail is not None:
            ratio = unit_inv / max(inp.investment.onshore_detail.total_per_kw, 1)
            inp.investment.onshore_detail.equipment_and_installation *= ratio
            inp.investment.onshore_detail.civil_works *= ratio
        if inp.investment.offshore_detail is not None:
            ratio = unit_inv / max(inp.investment.offshore_detail.total_epc_per_kw, 1)
            inp.investment.offshore_detail.oem.turbine_price_per_kw *= ratio
        result = calculate(inp)
        return result.lcoe - target_lcoe

    return brentq(objective, investment_range[0], investment_range[1], xtol=1e-6)


# ════════════════════════════════════════════════════════════════════════════
# 3. 给定目标 IRR -> 反算最低满负荷小时数
# ════════════════════════════════════════════════════════════════════════════

def solve_hours_for_target_irr(
    inputs: WindFarmFinancialInputs,
    target_irr: float,
    irr_type: Literal["project_before_tax", "project_after_tax", "equity"] = "project_after_tax",
    hours_range: tuple[int, int] = (500, 6000),
) -> float:
    """
    给定目标 IRR，反算所需的年等效满负荷小时数 (h)。

    标准依据: 满负荷小时数直接影响年发电量，进而影响年营收和现金流。
    P50/P75/P90 概率对应不同的小时数，反算结果可与风资源评估交叉验证。
    """
    def objective(hours: float) -> float:
        inp = copy.deepcopy(inputs)
        inp.basic.full_load_hours = int(round(hours))
        result = calculate(inp)
        return _get_irr(result, irr_type) - target_irr

    return brentq(objective, float(hours_range[0]), float(hours_range[1]), xtol=1.0)


# ════════════════════════════════════════════════════════════════════════════
# 4. 给定目标 LCOE -> 反算风机价格（海上 + 陆上）
# ════════════════════════════════════════════════════════════════════════════

def solve_turbine_price_for_target_lcoe(
    inputs: WindFarmFinancialInputs,
    target_lcoe: float,
    price_range: tuple[float, float] = (50.0, 3000.0),
) -> Optional[float]:
    """
    给定目标 LCOE，反算风机 OEM 裸机单价 (USD/kW)。

    海上项目: 调整 offshore_detail.oem.turbine_price_per_kw -> 联动 total_epc_per_kw
    陆上项目: 调整 onshore_detail.turbine_price_per_kw -> 联动 equipment_and_installation
    无明细项目: 直接调整 unit_static_investment（等价于总投资反算）

    Returns:
        满足目标 LCOE 的风机裸机单价 (USD/kW)，求解失败返回 None
    """
    if inputs.investment.offshore_detail is not None:
        def objective(turbine_price: float) -> float:
            inp = copy.deepcopy(inputs)
            inp.investment.offshore_detail.oem.turbine_price_per_kw = turbine_price
            inp.investment.unit_static_investment = inp.investment.offshore_detail.total_epc_per_kw
            result = calculate(inp)
            return result.lcoe - target_lcoe
        return brentq(objective, price_range[0], price_range[1], xtol=1e-6)

    elif inputs.investment.onshore_detail is not None:
        onshore = inputs.investment.onshore_detail
        if onshore.turbine_price_per_kw > 0:
            non_turbine = onshore.non_turbine_equip_per_kw
        else:
            non_turbine = onshore.equipment_and_installation * 0.30

        def objective(turbine_price: float) -> float:
            inp = copy.deepcopy(inputs)
            inp.investment.onshore_detail.turbine_price_per_kw = turbine_price
            inp.investment.onshore_detail.equipment_and_installation = turbine_price + non_turbine
            inp.investment.unit_static_investment = inp.investment.onshore_detail.total_per_kw
            result = calculate(inp)
            return result.lcoe - target_lcoe
        return brentq(objective, price_range[0], price_range[1], xtol=1e-6)

    else:
        def objective(turbine_price: float) -> float:
            inp = copy.deepcopy(inputs)
            bop = inp.investment.unit_static_investment * 0.40
            inp.investment.unit_static_investment = turbine_price + bop
            result = calculate(inp)
            return result.lcoe - target_lcoe
        return brentq(objective, price_range[0], price_range[1], xtol=1e-6)


# ════════════════════════════════════════════════════════════════════════════
# 5. 给定目标 IRR -> 反算风机价格（海上 + 陆上）
# ════════════════════════════════════════════════════════════════════════════

def solve_turbine_price_for_target_irr(
    inputs: WindFarmFinancialInputs,
    target_irr: float,
    irr_type: Literal["project_before_tax", "project_after_tax", "equity"] = "project_after_tax",
    price_range: tuple[float, float] = (50.0, 3000.0),
) -> Optional[float]:
    """
    给定目标 IRR，反算风机 OEM 裸机单价 (USD/kW)。

    与 LCOE 版类似，但目标函数改为 IRR。
    适用于投标报价场景：已知目标 IRR，反推可接受的风机采购价。
    """
    if inputs.investment.offshore_detail is not None:
        def objective(turbine_price: float) -> float:
            inp = copy.deepcopy(inputs)
            inp.investment.offshore_detail.oem.turbine_price_per_kw = turbine_price
            inp.investment.unit_static_investment = inp.investment.offshore_detail.total_epc_per_kw
            result = calculate(inp)
            return _get_irr(result, irr_type) - target_irr
        return brentq(objective, price_range[0], price_range[1], xtol=1e-6)

    elif inputs.investment.onshore_detail is not None:
        onshore = inputs.investment.onshore_detail
        if onshore.turbine_price_per_kw > 0:
            non_turbine = onshore.non_turbine_equip_per_kw
        else:
            non_turbine = onshore.equipment_and_installation * 0.30

        def objective(turbine_price: float) -> float:
            inp = copy.deepcopy(inputs)
            inp.investment.onshore_detail.turbine_price_per_kw = turbine_price
            inp.investment.onshore_detail.equipment_and_installation = turbine_price + non_turbine
            inp.investment.unit_static_investment = inp.investment.onshore_detail.total_per_kw
            result = calculate(inp)
            return _get_irr(result, irr_type) - target_irr
        return brentq(objective, price_range[0], price_range[1], xtol=1e-6)

    else:
        def objective(turbine_price: float) -> float:
            inp = copy.deepcopy(inputs)
            bop = inp.investment.unit_static_investment * 0.40
            inp.investment.unit_static_investment = turbine_price + bop
            result = calculate(inp)
            return _get_irr(result, irr_type) - target_irr
        return brentq(objective, price_range[0], price_range[1], xtol=1e-6)


# ════════════════════════════════════════════════════════════════════════════
# 6. NPV=0 -> 反算临界条件
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
