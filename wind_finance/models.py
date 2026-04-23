"""
wind_finance.models
===================
风电项目经济性评估 —— 核心数据结构定义

所有货币单位统一为 **USD**，比例/费率以小数存储（如 0.13 代表 13%）。
分为 7 大模块，以嵌套 dataclass 组织，同时支持陆上 (onshore) 和海上 (offshore) 风电项目。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Literal, Optional, Tuple


# ════════════════════════════════════════════════════════════════════════════
# 模块 1: 风场基本信息
# ════════════════════════════════════════════════════════════════════════════

@dataclass
class BasicInfo:
    """风场基本信息"""

    project_name: str               # 项目名称，如 "汕尾红海湾五海上风电"
    project_type: Literal["onshore", "offshore"]  # 项目类型：陆上 / 海上
    country: str                    # 所在国家，如 "China", "Vietnam"，用于关联 CountryProfile

    num_turbines: int               # 机组台数（台）
    turbine_capacity_mw: float      # 单机容量（MW）
    full_load_hours: int            # 年等效满负荷小时数（h）

    loss_rate: float = 0.03         # 综合厂用电及线损率（小数，如 0.03 = 3%）
    curtailment_years: int = 0      # 限电年限（年）
    curtailment_rate: float = 0.0   # 限电比例（小数，如 0.05 = 5%）
    construction_months: int = 12   # 建设期（月），陆上 12-18，海上 18-24
    investment_schedule: Optional[Tuple[float, ...]] = None
    # 分年投资比例（如 (0.4, 0.3, 0.3) 表示三年建设期各投40%/30%/30%）
    # None 则按建设年数平均分配

    @property
    def capacity_mw(self) -> float:
        """总装机容量（MW）= 机组台数 × 单机容量"""
        return self.num_turbines * self.turbine_capacity_mw

    @property
    def capacity_kw(self) -> float:
        """总装机容量（kW）"""
        return self.capacity_mw * 1000.0

    @property
    def net_annual_generation_mwh(self) -> float:
        """
        净年上网电量（MWh）
        = 总装机容量(MW) × 满负荷小时数(h) × (1 - 线损率)
        """
        return self.capacity_mw * self.full_load_hours * (1.0 - self.loss_rate)

    @property
    def net_annual_generation_kwh(self) -> float:
        """净年上网电量（kWh）"""
        return self.net_annual_generation_mwh * 1000.0


# ════════════════════════════════════════════════════════════════════════════
# 模块 2: 投资造价
# ════════════════════════════════════════════════════════════════════════════

# ---------- 海上 EPC 分项 ----------

@dataclass
class OEMCost:
    """OEM 成本：风机 + 塔筒"""

    turbine_price_per_kw: float     # 风机单位千瓦售价（USD/kW）
    tower_weight_per_unit: float    # 塔筒重量 + 内附件（t/台）
    tower_unit_price: float         # 塔筒单价（USD/吨）


@dataclass
class InstallationCost:
    """安装与运输成本（USD/台）"""

    installation_per_unit: float    # 风机安装费（USD/台）
    ocean_freight_per_unit: float   # 风机海运费（USD/台）
    inland_transport_per_unit: float  # 风机陆运费（USD/台）


@dataclass
class FoundationCost:
    """基础工程成本"""

    foundation_price_per_ton: float   # 风力机基础造价（USD/吨）
    foundation_tons_per_unit: float   # 风力机基础数量（Ton/台）
    foundation_install_per_unit: float  # 基础安装费（USD/台）


@dataclass
class BOPCost:
    """
    BOP (Balance of Plant) 成本 —— 12 项分项工程（均为 USD/kW）
    包含集电线路、海缆、升压站、集控中心等。
    """

    auxiliary_works: float = 0.0            # 施工辅助工程
    collector_line_equip: float = 0.0       # 集电线路设备及安装工程
    submarine_cable_equip: float = 0.0      # 登陆海缆设备及安装工程
    offshore_substation_equip: float = 0.0  # 海上升压站设备及安装工程
    control_center_equip: float = 0.0       # 集控中心设备及工程
    other_equip: float = 0.0               # 其他设备及安装工程
    collector_line_civil: float = 0.0       # 集电线路工程
    landing_cable_civil: float = 0.0        # 登陆电缆工程
    offshore_substation_civil: float = 0.0  # 海上升压站工程
    control_center_civil: float = 0.0       # 集控中心工程
    transportation_civil: float = 0.0       # 交通工程
    other_civil: float = 0.0               # 其他工程

    @property
    def total_bop_per_kw(self) -> float:
        """BOP 合计（USD/kW）"""
        return (
            self.auxiliary_works
            + self.collector_line_equip
            + self.submarine_cable_equip
            + self.offshore_substation_equip
            + self.control_center_equip
            + self.other_equip
            + self.collector_line_civil
            + self.landing_cable_civil
            + self.offshore_substation_civil
            + self.control_center_civil
            + self.transportation_civil
            + self.other_civil
        )


@dataclass
class OffshoreEPCBreakdown:
    """
    海上风电 EPC 造价明细（对应用户提供的海上项目分项表）
    汇总后得到单位千瓦 EPC 造价。
    """

    oem: OEMCost
    installation: InstallationCost
    foundation: FoundationCost
    bop: BOPCost

    num_turbines: int = 0                # 机组台数（用于将 per-unit 费用折算为 per-kW）
    turbine_capacity_mw: float = 0.0     # 单机容量（MW，用于折算）

    @property
    def _capacity_kw(self) -> float:
        return self.num_turbines * self.turbine_capacity_mw * 1000.0

    @property
    def oem_per_kw(self) -> float:
        """OEM 合计（USD/kW）= 风机售价 + 塔筒折算"""
        if self._capacity_kw <= 0:
            return 0.0
        tower_total = (
            self.oem.tower_weight_per_unit
            * self.oem.tower_unit_price
            * self.num_turbines
        )
        return self.oem.turbine_price_per_kw + tower_total / self._capacity_kw

    @property
    def installation_per_kw(self) -> float:
        """安装与运输合计（USD/kW）"""
        if self._capacity_kw <= 0:
            return 0.0
        total = (
            self.installation.installation_per_unit
            + self.installation.ocean_freight_per_unit
            + self.installation.inland_transport_per_unit
        ) * self.num_turbines
        return total / self._capacity_kw

    @property
    def foundation_per_kw(self) -> float:
        """基础工程合计（USD/kW）"""
        if self._capacity_kw <= 0:
            return 0.0
        total = (
            self.foundation.foundation_price_per_ton
            * self.foundation.foundation_tons_per_unit
            + self.foundation.foundation_install_per_unit
        ) * self.num_turbines
        return total / self._capacity_kw

    @property
    def total_epc_per_kw(self) -> float:
        """EPC 合计（USD/kW）= OEM + Installation + Foundation + BOP"""
        return (
            self.oem_per_kw
            + self.installation_per_kw
            + self.foundation_per_kw
            + self.bop.total_bop_per_kw
        )


# ---------- 陆上投资明细 ----------

@dataclass
class OnshoreInvestment:
    """
    陆上风电投资明细（基于国内可研报告标准格式）
    所有字段均为 USD/kW，汇总后得到单位千瓦静态投资。
    """

    equipment_and_installation: float = 0.0  # 设备及安装工程（USD/kW），含风机+塔筒+箱变+集电线路+升压站
    civil_works: float = 0.0                 # 建筑工程（USD/kW），含基础+升压站土建+道路
    construction_auxiliary: float = 0.0      # 施工辅助工程（USD/kW）
    other_costs: float = 0.0                 # 其他费用（USD/kW），含用地+前期+管理+设计
    contingency_rate: float = 0.02           # 基本预备费率（小数，约 2%）
    storage_cost: float = 0.0                # 储能工程费（USD/kW，如有配套储能）
    grid_connection_cost: float = 0.0        # 送出线路/电网接入费（USD/kW）

    @property
    def subtotal_before_contingency(self) -> float:
        """预备费前小计（USD/kW）"""
        return (
            self.equipment_and_installation
            + self.civil_works
            + self.construction_auxiliary
            + self.other_costs
            + self.storage_cost
            + self.grid_connection_cost
        )

    @property
    def contingency(self) -> float:
        """基本预备费（USD/kW）"""
        return self.subtotal_before_contingency * self.contingency_rate

    @property
    def total_per_kw(self) -> float:
        """陆上静态投资合计（USD/kW）"""
        return self.subtotal_before_contingency + self.contingency


# ---------- 投资数据汇总 ----------

@dataclass
class InvestmentData:
    """
    投资造价汇总模块

    unit_static_investment 可以直接手动填入，也可以由
    OnshoreInvestment.total_per_kw 或 OffshoreEPCBreakdown.total_epc_per_kw 自动计算。
    """

    unit_static_investment: float           # 单位千瓦静态投资（USD/kW）
    working_capital_per_kw: float = 4.2     # 流动资金（USD/kW），中国约 30 元/kW ≈ 4.2 USD/kW
    deductible_vat_ratio: float = 0.086     # 可抵扣进项税占静态投资比例（用于自动计算可抵扣税金）
    special_project_cost: float = 0.0       # 特殊项目费（万 USD），海上可含海洋牧场/码头，陆上为 0

    onshore_detail: Optional[OnshoreInvestment] = None
    offshore_detail: Optional[OffshoreEPCBreakdown] = None

    def resolve_unit_investment(self) -> float:
        """
        优先从明细子结构计算单位千瓦投资；
        如果没有明细，则使用直接填入的 unit_static_investment。
        """
        if self.onshore_detail is not None:
            return self.onshore_detail.total_per_kw
        if self.offshore_detail is not None:
            return self.offshore_detail.total_epc_per_kw
        return self.unit_static_investment

    def total_static_investment(self, capacity_kw: float) -> float:
        """静态总投资（USD）"""
        return capacity_kw * self.resolve_unit_investment()

    def working_capital(self, capacity_kw: float) -> float:
        """流动资金（USD）"""
        return capacity_kw * self.working_capital_per_kw

    def deductible_vat(self, capacity_kw: float) -> float:
        """可抵扣进项税额（USD）"""
        return self.total_static_investment(capacity_kw) * self.deductible_vat_ratio


# ════════════════════════════════════════════════════════════════════════════
# 模块 3: 融资条件
# ════════════════════════════════════════════════════════════════════════════

@dataclass
class FinancingTerms:
    """融资条件"""

    equity_ratio: float                 # 资本金比例（小数，如 0.20 = 20%）
    long_term_loan_rate: float          # 长期贷款年利率（小数，如 0.0325）
    loan_term_years: int = 15           # 贷款年限（年）

    construction_interest_override: Optional[float] = None
    # 手动指定建设期利息（USD），用于精确对齐已有Excel模型。None则自动计算。

    repayment_method: Literal["equal_principal", "equal_payment"] = "equal_principal"
    # 还款方式：equal_principal = 等额本金（利息照付），equal_payment = 等额本息

    working_capital_loan_rate: float = 0.0325  # 流动资金贷款利率（小数）
    working_capital_equity_ratio: float = 0.30  # 流动资金中自有资金比例（小数）

    @property
    def debt_ratio(self) -> float:
        """贷款比例 = 1 - 资本金比例"""
        return 1.0 - self.equity_ratio

    def construction_interest(
        self, total_static_investment: float, construction_months: int,
        investment_schedule: Optional[Tuple[float, ...]] = None,
    ) -> float:
        """
        建设期利息（USD）

        两种模式：
        1. 指定 investment_schedule（如 (0.4, 0.3, 0.3)）→ 分年精确计算
           每年：往年累计贷款本金×全年利率 + 当年新增贷款×半年利率
        2. 无 schedule → 简化公式：贷款×利率×建设期(年)×0.5
        """
        rate = self.long_term_loan_rate
        total_loan = total_static_investment * self.debt_ratio

        if investment_schedule is None or len(investment_schedule) == 0:
            years = construction_months / 12.0
            return total_loan * rate * years * 0.5

        accumulated_principal = 0.0
        total_ci = 0.0
        for frac in investment_schedule:
            new_loan = total_loan * frac
            ci_this_year = accumulated_principal * rate + new_loan * rate * 0.5
            total_ci += ci_this_year
            accumulated_principal += new_loan

        return total_ci

    def equity_for_construction(self, total_dynamic_investment: float) -> float:
        """建设投资中的资本金（USD）"""
        return total_dynamic_investment * self.equity_ratio

    def debt_for_construction(self, total_dynamic_investment: float) -> float:
        """建设投资中的贷款金额（USD）"""
        return total_dynamic_investment * self.debt_ratio


# ════════════════════════════════════════════════════════════════════════════
# 模块 4: 运营成本
# ════════════════════════════════════════════════════════════════════════════

@dataclass
class WarrantyPeriodCost:
    """
    质保期内运维成本

    质保期内风机厂商承担主要维修责任，业主侧费用较低。
    不同项目和机型有不同的报价。
    """

    warranty_years: int = 5                 # 质保期年限（年）
    material_cost_per_kw: float = 0.63      # 材料费（USD/kW·年），约 4.5 元/kW
    repair_cost_per_kw: float = 0.74        # 维修费（USD/kW·年），约 5.24 元/kW
    other_cost_per_kw: float = 3.45         # 其他费用（USD/kW·年），约 24.5 元/kW


@dataclass
class PostWarrantyPeriodCost:
    """
    质保期外运维成本

    质保期外需业主自行承担维修，可选择是否包含大部件维护。
    维修费按静态投资的百分比分阶段递增。
    """

    includes_major_components: bool = True  # 运维合同是否包含大部件更换

    material_cost_per_kw: float = 1.27      # 材料费（USD/kW·年），约 9 元/kW
    other_cost_per_kw: float = 3.45         # 其他费用（USD/kW·年），约 24.5 元/kW

    maintenance_rates: List[Tuple[int, int, float]] = field(default_factory=lambda: [
        # (起始运营年, 结束运营年, 维修费率 — 基于静态投资的年百分比)
        (6, 10, 0.010),    # 第 6-10 年：1.0%
        (11, 15, 0.015),   # 第 11-15 年：1.5%
        (16, 20, 0.020),   # 第 16-20 年：2.0%
        (21, 25, 0.025),   # 第 21-25 年：2.5%（海上项目运营期 25 年）
    ])

    def get_maintenance_rate(self, operation_year: int) -> float:
        """获取指定运营年份的维修费率"""
        for start, end, rate in self.maintenance_rates:
            if start <= operation_year <= end:
                return rate
        if self.maintenance_rates:
            return self.maintenance_rates[-1][2]
        return 0.0


@dataclass
class OffshoreExtraCost:
    """
    海上风电专项运维成本

    海上项目相比陆上额外产生的费用项。
    """

    requires_sov: bool = False              # 是否需要专业运维船 (SOV, Service Operation Vessel)
    sov_annual_cost: float = 0.0            # 运维船年费（万 USD）
    sea_area_usage_fee: float = 0.0         # 海域使用金（万 USD/年）
    storage_rental: float = 0.0             # 储能租赁费（万 USD/年）
    decommissioning_rate: float = 0.0       # 经营期末拆除费率（小数，如 0.02 基于静态投资）


@dataclass
class OperationalCost:
    """
    运营成本汇总模块

    合并质保期内/外成本、人员成本、保险、折旧等。
    """

    # ---- 人员 ----
    staff_count: int = 10                   # 定员人数（陆上 8-10，海上 35）
    salary_per_person: float = 2.54         # 人均年薪（万 USD），中国陆上约 18 万元 ≈ 2.54 万 USD
    welfare_rate: float = 0.60              # 福利系数（小数，含社保公积金等附加工资）

    # ---- 保险 ----
    insurance_rate: float = 0.0025          # 保险费率（小数，基于静态投资。陆上 0.25%，海上 0.35%）

    # ---- 折旧 ----
    depreciation_years: int = 20            # 折旧年限（年）
    residual_rate: float = 0.0              # 残值率（小数，0~0.05）

    # ---- 运营期 ----
    operation_years: int = 20               # 运营期（年，陆上 20，海上 25）
    reserve_fund_rate: float = 0.10         # 法定盈余公积金提取率（小数）

    # ---- 分阶段成本 ----
    warranty: WarrantyPeriodCost = field(default_factory=WarrantyPeriodCost)
    post_warranty: PostWarrantyPeriodCost = field(default_factory=PostWarrantyPeriodCost)
    offshore_extra: Optional[OffshoreExtraCost] = None

    @property
    def annual_staff_cost(self) -> float:
        """年人员工资及福利费（万 USD）= 人数 × 人均年薪 × (1 + 福利系数)"""
        return self.staff_count * self.salary_per_person * (1.0 + self.welfare_rate)

    def annual_insurance(self, total_static_investment: float) -> float:
        """年保险费（USD）= 静态总投资 × 保险费率"""
        return total_static_investment * self.insurance_rate

    def annual_depreciation(self, depreciable_base: float) -> float:
        """
        年折旧费（USD）= 可折旧基数 × (1 - 残值率) / 折旧年限
        可折旧基数 = 固定资产原值（通常 = 静态投资 + 建设期利息 - 可抵扣进项税）
        """
        return depreciable_base * (1.0 - self.residual_rate) / self.depreciation_years

    def get_year_opex(
        self,
        operation_year: int,
        capacity_kw: float,
        total_static_investment: float,
    ) -> dict:
        """
        获取指定运营年份的各项运维成本明细（USD）

        Returns:
            dict 包含: material, repair, other, staff, insurance, offshore_extra
        """
        in_warranty = operation_year <= self.warranty.warranty_years

        if in_warranty:
            material = self.warranty.material_cost_per_kw * capacity_kw
            repair = self.warranty.repair_cost_per_kw * capacity_kw
            other = self.warranty.other_cost_per_kw * capacity_kw
        else:
            material = self.post_warranty.material_cost_per_kw * capacity_kw
            rate = self.post_warranty.get_maintenance_rate(operation_year)
            repair = total_static_investment * rate
            other = self.post_warranty.other_cost_per_kw * capacity_kw

        staff = self.annual_staff_cost * 10_000  # 万USD -> USD
        insurance = self.annual_insurance(total_static_investment)

        offshore = 0.0
        if self.offshore_extra is not None:
            oe = self.offshore_extra
            offshore += oe.sea_area_usage_fee * 10_000
            offshore += oe.storage_rental * 10_000
            if oe.requires_sov:
                offshore += oe.sov_annual_cost * 10_000

        return {
            "material": material,
            "repair": repair,
            "other": other,
            "staff": staff,
            "insurance": insurance,
            "offshore_extra": offshore,
        }


# ════════════════════════════════════════════════════════════════════════════
# 模块 5: 税费与财务假设
# ════════════════════════════════════════════════════════════════════════════

@dataclass
class TaxAndFinancial:
    """税费与财务假设"""

    tariff_with_tax: float                  # 上网电价含税（USD/kWh）
    vat_rate: float = 0.13                  # 增值税率（小数）
    vat_refund_rate: float = 0.50           # 增值税即征即退比例（小数，中国风电 50%）

    income_tax_rate: float = 0.25           # 企业所得税标准税率（小数）

    # 所得税优惠政策：(免征起始年, 免征结束年, 免征期税率, 减半起始年, 减半结束年, 减半期税率)
    # 中国风电典型 "三免三减半"：运营期前 3 年免征，第 4-6 年按 12.5%
    income_tax_holiday: Tuple[int, int, float, int, int, float] = (1, 3, 0.0, 4, 6, 0.125)

    urban_maintenance_tax_rate: float = 0.05  # 城市维护建设税率（陆上 5%，海上 7%）
    education_surcharge_rate: float = 0.05    # 教育费附加率（含地方教育附加，陆上 5%，海上 5%）

    resource_tax_rate: float = 0.0            # 资源税率（基于不含税营收的百分比，如越南1%=0.01）
    statutory_reserve_rate: float = 0.0       # 法定盈余公积金提取率（如越南5%=0.05，从净利润中提取）

    discount_rate: float = 0.08               # 基准折现率（税后）

    @property
    def tariff_without_tax(self) -> float:
        """不含税电价（USD/kWh）= 含税电价 / (1 + 增值税率)"""
        return self.tariff_with_tax / (1.0 + self.vat_rate)

    def get_income_tax_rate(self, operation_year: int) -> float:
        """获取指定运营年份的实际所得税率（考虑优惠政策）"""
        exempt_start, exempt_end, exempt_rate, half_start, half_end, half_rate = (
            self.income_tax_holiday
        )
        if exempt_start <= operation_year <= exempt_end:
            return exempt_rate
        if half_start <= operation_year <= half_end:
            return half_rate
        return self.income_tax_rate

    @property
    def surcharge_rate(self) -> float:
        """销售税金附加合计费率 = 城维税率 + 教育费附加率"""
        return self.urban_maintenance_tax_rate + self.education_surcharge_rate


# ════════════════════════════════════════════════════════════════════════════
# 顶层汇总类
# ════════════════════════════════════════════════════════════════════════════

@dataclass
class WindFarmFinancialInputs:
    """
    风电项目经济性评估 —— 完整输入参数集

    组合所有子模块，作为计算引擎和反算模块的统一输入接口。
    """

    basic: BasicInfo
    investment: InvestmentData
    financing: FinancingTerms
    operational: OperationalCost
    tax_financial: TaxAndFinancial

    # ---- 计算属性快捷访问 ----

    @property
    def capacity_kw(self) -> float:
        return self.basic.capacity_kw

    @property
    def capacity_mw(self) -> float:
        return self.basic.capacity_mw

    @property
    def total_static_investment(self) -> float:
        """静态总投资（USD）"""
        return self.investment.total_static_investment(self.capacity_kw)

    @property
    def construction_interest(self) -> float:
        """建设期利息（USD）"""
        if self.financing.construction_interest_override is not None:
            return self.financing.construction_interest_override
        return self.financing.construction_interest(
            self.total_static_investment, self.basic.construction_months,
            self.basic.investment_schedule,
        )

    @property
    def total_dynamic_investment(self) -> float:
        """动态总投资（USD）= 静态投资 + 建设期利息"""
        return self.total_static_investment + self.construction_interest

    @property
    def working_capital(self) -> float:
        """流动资金（USD）"""
        return self.investment.working_capital(self.capacity_kw)

    @property
    def total_investment(self) -> float:
        """项目总投资（USD）= 动态投资 + 流动资金"""
        return self.total_dynamic_investment + self.working_capital

    @property
    def unit_dynamic_investment(self) -> float:
        """单位千瓦动态投资（USD/kW）"""
        return self.total_dynamic_investment / self.capacity_kw

    @property
    def equity_amount(self) -> float:
        """资本金总额（USD）"""
        return self.financing.equity_for_construction(self.total_dynamic_investment)

    @property
    def debt_amount(self) -> float:
        """贷款总额（USD）"""
        return self.financing.debt_for_construction(self.total_dynamic_investment)

    @property
    def deductible_vat(self) -> float:
        """可抵扣进项税额（USD）"""
        return self.investment.deductible_vat(self.capacity_kw)

    @property
    def net_annual_generation_mwh(self) -> float:
        return self.basic.net_annual_generation_mwh

    def summary(self) -> str:
        """打印项目参数摘要"""
        lines = [
            f"{'='*60}",
            f"  项目名称: {self.basic.project_name}",
            f"  项目类型: {self.basic.project_type}",
            f"  所在国家: {self.basic.country}",
            f"{'='*60}",
            f"  装机容量: {self.capacity_mw:.1f} MW ({self.basic.num_turbines} × {self.basic.turbine_capacity_mw:.2f} MW)",
            f"  满负荷小时数: {self.basic.full_load_hours} h",
            f"  线损率: {self.basic.loss_rate:.2%}",
            f"  净年上网电量: {self.net_annual_generation_mwh:,.1f} MWh",
            f"  建设期: {self.basic.construction_months} 个月",
            f"{'─'*60}",
            f"  单位千瓦静态投资: {self.investment.resolve_unit_investment():,.2f} USD/kW",
            f"  静态总投资: {self.total_static_investment:,.0f} USD ({self.total_static_investment/10000:,.2f} 万USD)",
            f"  建设期利息: {self.construction_interest:,.0f} USD ({self.construction_interest/10000:,.2f} 万USD)",
            f"  动态总投资: {self.total_dynamic_investment:,.0f} USD ({self.total_dynamic_investment/10000:,.2f} 万USD)",
            f"  单位千瓦动态投资: {self.unit_dynamic_investment:,.2f} USD/kW",
            f"  流动资金: {self.working_capital:,.0f} USD",
            f"  项目总投资: {self.total_investment:,.0f} USD ({self.total_investment/10000:,.2f} 万USD)",
            f"  可抵扣进项税: {self.deductible_vat:,.0f} USD",
            f"{'─'*60}",
            f"  资本金比例: {self.financing.equity_ratio:.1%}",
            f"  资本金: {self.equity_amount:,.0f} USD",
            f"  贷款金额: {self.debt_amount:,.0f} USD",
            f"  贷款利率: {self.financing.long_term_loan_rate:.2%}",
            f"  贷款期限: {self.financing.loan_term_years} 年",
            f"{'─'*60}",
            f"  运营期: {self.operational.operation_years} 年",
            f"  上网电价(含税): {self.tax_financial.tariff_with_tax:.4f} USD/kWh",
            f"  上网电价(不含税): {self.tax_financial.tariff_without_tax:.4f} USD/kWh",
            f"  增值税率: {self.tax_financial.vat_rate:.0%}",
            f"  所得税率: {self.tax_financial.income_tax_rate:.0%}",
            f"  折旧年限: {self.operational.depreciation_years} 年",
            f"  残值率: {self.operational.residual_rate:.1%}",
            f"  人员: {self.operational.staff_count} 人, {self.operational.salary_per_person:.2f} 万USD/人·年",
            f"  保险费率: {self.operational.insurance_rate:.3%}",
            f"{'='*60}",
        ]
        return "\n".join(lines)
