"""
Wind Farm Financial Assessment Dashboard
风电项目经济性评估看板 — 多项目管理 + 分项编辑 + 对比

启动方式: streamlit run app.py
"""

import copy
import json
import os
import time
import uuid
from dataclasses import asdict
from typing import Dict, Literal, Optional, Tuple

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from wind_finance.calculator import CalculationResult, calculate
from wind_finance.country_profiles import (
    CountryProfile,
    get_country_profile,
    list_countries,
)
from wind_finance.excel_export import export_to_excel
from wind_finance.models import (
    BOPCost,
    BasicInfo,
    FinancingTerms,
    FoundationCost,
    InstallationCost,
    InvestmentData,
    OEMCost,
    OffshoreEPCBreakdown,
    OffshoreExtraCost,
    OnshoreInvestment,
    OperationalCost,
    PostWarrantyPeriodCost,
    TaxAndFinancial,
    WarrantyPeriodCost,
    WindFarmFinancialInputs,
)
from wind_finance.reverse_solver import (
    solve_hours_for_target_irr,
    solve_investment_for_target_lcoe,
    solve_tariff_for_target_irr,
    solve_tariff_for_zero_npv,
    solve_turbine_price_for_target_lcoe,
)

# ════════════════════════════════════════════════════════════════════════════
# 页面配置 & 全局样式
# ════════════════════════════════════════════════════════════════════════════

st.set_page_config(
    page_title="Wind Farm Assessment",
    page_icon="🌬️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── 密码保护 ──────────────────────────────────────────────────────────────
# 密码来源优先级: HF Secrets > 环境变量 APP_PASSWORD > 不设密码（本地开发）
def _get_secret(key, default=""):
    val = os.environ.get(key, "")
    if not val:
        try:
            val = st.secrets.get(key, default)
        except Exception:
            val = default
    return val

_APP_PASSWORD = _get_secret("APP_PASSWORD")

if _APP_PASSWORD:
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False

    if not st.session_state.authenticated:
        st.markdown(
            "<div style='max-width:400px;margin:120px auto;text-align:center;'>"
            "<h2 style='color:#1F4E79;'>Wind Farm Financial Assessment</h2>"
            "<p style='color:#666;'>Please enter the access password.</p></div>",
            unsafe_allow_html=True,
        )
        col_l, col_m, col_r = st.columns([1, 1, 1])
        with col_m:
            pwd_input = st.text_input("Password", type="password", label_visibility="collapsed",
                                      placeholder="Enter password...")
            if st.button("Login", type="primary", use_container_width=True):
                if pwd_input == _APP_PASSWORD:
                    st.session_state.authenticated = True
                    st.rerun()
                else:
                    st.error("Wrong password. Please try again.")
        st.stop()

# ── 全局样式 ──────────────────────────────────────────────────────────────
st.markdown("""
<style>
    div[data-testid="stSidebar"] { background: #f8f9fb; }
    .block-container { padding-top: 1.5rem; }
    h1 { color: #1F4E79; }
    h2, h3 { color: #2E75B6; }
</style>
""", unsafe_allow_html=True)

COLOR_PALETTE = [
    "#1F4E79", "#2E75B6", "#548235", "#BF8F00",
    "#C00000", "#7030A0", "#ED7D31", "#4472C4",
    "#70AD47", "#FFC000", "#5B9BD5", "#A5A5A5",
]

# ════════════════════════════════════════════════════════════════════════════
# Session State: 多项目存储
# ════════════════════════════════════════════════════════════════════════════

if "projects" not in st.session_state:
    st.session_state.projects: Dict[str, dict] = {}
    # 首次启动：自动加载预置项目
    _preloaders = [
        "wind_finance.preload_philippines",
        "wind_finance.preload_laguna",
        "wind_finance.preload_fsg",
        "wind_finance.preload_vietnam_qh",
    ]
    for _mod_name in _preloaders:
        try:
            import importlib
            _mod = importlib.import_module(_mod_name)
            for entry in _mod.get_all_projects():
                # 支持 5 元组 (name, group, country, inputs, result)
                name, group, country, inputs, result = entry
                pid = str(uuid.uuid4())[:8]
                st.session_state.projects[pid] = {
                    "name": name,
                    "group": group,
                    "country": country,
                    "inputs": copy.deepcopy(inputs),
                    "result": copy.deepcopy(result),
                    "saved_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                }
        except Exception:
            pass

if "compare_ids" not in st.session_state:
    st.session_state.compare_ids: list[str] = []


def save_project(name: str, inputs: WindFarmFinancialInputs, result: CalculationResult,
                  group: str = "", country: str = "") -> str:
    pid = str(uuid.uuid4())[:8]
    _group = group or inputs.basic.project_name.split(" - ")[0].strip()
    _country = country or inputs.basic.country
    st.session_state.projects[pid] = {
        "name": name,
        "group": _group,
        "country": _country,
        "inputs": copy.deepcopy(inputs),
        "result": copy.deepcopy(result),
        "saved_at": time.strftime("%Y-%m-%d %H:%M:%S"),
    }
    return pid


_DELETE_USER = _get_secret("DELETE_USER", "admin")
_DELETE_PWD  = _get_secret("DELETE_PWD")


def delete_project(pid: str):
    st.session_state.projects.pop(pid, None)
    if pid in st.session_state.compare_ids:
        st.session_state.compare_ids.remove(pid)
    st.session_state.pop("confirm_delete", None)


# ════════════════════════════════════════════════════════════════════════════
# 侧边栏：快速模式 (10 个参数即可)
# ════════════════════════════════════════════════════════════════════════════

def sidebar_inputs_quick() -> WindFarmFinancialInputs:
    """快速模式：只需截图级别的数据即可完成评估"""

    st.sidebar.markdown("## Quick Mode")
    st.sidebar.caption("Only 10 params needed. Defaults by country & type.")

    countries = list_countries()
    country_options = {f"{cn} ({en})": en for en, cn in countries}
    selected_display = st.sidebar.selectbox("Country", list(country_options.keys()), index=0, key="q_country")
    country_name = country_options[selected_display]
    profile = get_country_profile(country_name)

    project_type = st.sidebar.radio("Type", ["Onshore", "Offshore"], horizontal=True, key="q_type")
    is_offshore = project_type == "Offshore"

    # 海上/陆上不同的默认值
    _def = {
        "units":     (38,    28),
        "mw":        (9.0,   15.0),
        "p90":       (3429,  3200),
        "tariff":    (0.098, 0.098),
        "tsi":       (617.0, 900.0),
        "bop":       (433.0, 700.0),
        "build_m":   (18,    30),
        "oper_y":    (25,    25),
        "loss":      (0.03,  0.04),
        "staff":     (15,    35),
        "salary":    (1.0,   3.5),
        "insurance": (0.0025, 0.0035),
        "w_mat":     (3.0,   5.0),
        "w_other":   (5.0,   8.0),
        "pw_mat":    (4.0,   6.0),
        "pw_other":  (6.0,   10.0),
    }
    def D(key):
        return _def[key][1 if is_offshore else 0]

    st.sidebar.markdown("---")
    st.sidebar.markdown("### Basic")
    project_name = st.sidebar.text_input("Project Name", value="Quick Project", key="q_name")
    c1, c2 = st.sidebar.columns(2)
    num_turbines = c1.number_input("Units", 1, 500, D("units"), key="q_units")
    turbine_mw = c2.number_input("MW/unit", 1.0, 30.0, D("mw"), step=0.5, key="q_mw")
    full_load_hours = st.sidebar.number_input("P90 Hours (h/yr)", 1000, 5000, D("p90"), step=10, key="q_p90")
    tariff = st.sidebar.number_input("Tariff incl. tax (USD/kWh)", 0.001, 0.500, D("tariff"),
                                     step=0.001, format="%.4f", key="q_tariff")

    st.sidebar.markdown("---")
    st.sidebar.markdown("### Investment")
    tsi_per_kw = st.sidebar.number_input("TSI (USD/kW)", 100.0, 5000.0, D("tsi"), step=10.0, key="q_tsi")
    bop_per_kw = st.sidebar.number_input("BOP (USD/kW)", 50.0, 3000.0, D("bop"), step=10.0, key="q_bop")
    total_per_kw = tsi_per_kw + bop_per_kw
    capacity_mw = num_turbines * turbine_mw
    total_invest_m = total_per_kw * capacity_mw * 1000 / 1e6
    st.sidebar.info(f"**Total: {total_per_kw:,.0f} USD/kW | {total_invest_m:,.0f} M$**")

    st.sidebar.markdown("---")
    st.sidebar.markdown("### Timeline")
    c3, c4 = st.sidebar.columns(2)
    construction_months = c3.number_input("Build (months)", 6, 48, D("build_m"), key="q_build")
    operation_years = c4.number_input("Operate (years)", 15, 30, D("oper_y"), key="q_oper")

    # 从国家配置自动填充
    eq_ratio = profile.typical_equity_ratio if profile else 0.30
    loan_rate = profile.typical_loan_rate if profile else 0.07
    loan_term = profile.typical_loan_term if profile else 15
    vat = profile.vat_rate if profile else 0.12
    cit = profile.corporate_income_tax_rate if profile else 0.25
    urban_tax = profile.urban_maintenance_tax_rate if profile else 0.0
    edu_sur = profile.education_surcharge_rate if profile else 0.0

    if profile and profile.has_wind_tax_incentive:
        tax_holiday = (1, 7, 0.0, 8, 14, cit * 0.4)
    else:
        tax_holiday = (1, 3, 0.0, 4, 6, cit / 2.0)

    # 显示自动填充的默认值
    with st.sidebar.expander("Auto-filled defaults (view only)", expanded=False):
        st.markdown(f"""
- **Equity ratio**: {eq_ratio:.0%}
- **Loan rate**: {loan_rate:.1%} x {loan_term}yr
- **VAT**: {vat:.0%} | **CIT**: {cit:.0%}
- **Loss rate**: {D('loss'):.0%}
- **Staff**: {D('staff')} | **Insurance**: {D('insurance'):.2%}
- **Type**: {'Offshore' if is_offshore else 'Onshore'} defaults
        """)
        st.caption("Switch to Detailed mode to edit these.")

    onshore_detail = None
    offshore_extra = None

    if is_offshore:
        offshore_extra = OffshoreExtraCost(
            requires_sov=False, sov_annual_cost=0.0,
            sea_area_usage_fee=43.0, storage_rental=0.0,
            decommissioning_rate=0.02,
        )
    else:
        onshore_detail = OnshoreInvestment(
            equipment_and_installation=tsi_per_kw,
            civil_works=bop_per_kw * 0.85,
            construction_auxiliary=0.0,
            other_costs=bop_per_kw * 0.15,
            contingency_rate=0.0,
            storage_cost=0.0,
            grid_connection_cost=0.0,
        )

    basic = BasicInfo(
        project_name=project_name,
        project_type="offshore" if is_offshore else "onshore",
        country=country_name,
        num_turbines=num_turbines,
        turbine_capacity_mw=turbine_mw,
        full_load_hours=full_load_hours,
        loss_rate=D("loss"),
        construction_months=construction_months,
    )
    investment = InvestmentData(
        unit_static_investment=total_per_kw,
        working_capital_per_kw=4.0,
        deductible_vat_ratio=0.0,
        onshore_detail=onshore_detail,
        offshore_detail=None,
    )
    financing = FinancingTerms(
        equity_ratio=eq_ratio,
        long_term_loan_rate=loan_rate,
        loan_term_years=loan_term,
        working_capital_loan_rate=loan_rate,
        working_capital_equity_ratio=eq_ratio,
    )
    warranty = WarrantyPeriodCost(
        warranty_years=5, material_cost_per_kw=D("w_mat"),
        repair_cost_per_kw=0.0, other_cost_per_kw=D("w_other"),
    )
    post_warranty = PostWarrantyPeriodCost(
        includes_major_components=True,
        material_cost_per_kw=D("pw_mat"), other_cost_per_kw=D("pw_other"),
        maintenance_rates=[(1,5,0.005),(6,10,0.01),(11,15,0.015),(16,20,0.02),(21,25,0.025)],
    )
    operational = OperationalCost(
        staff_count=D("staff"), salary_per_person=D("salary"), welfare_rate=0.40,
        insurance_rate=D("insurance"), depreciation_years=20, residual_rate=0.0,
        operation_years=operation_years, warranty=warranty,
        post_warranty=post_warranty, offshore_extra=offshore_extra,
    )
    tax_financial = TaxAndFinancial(
        tariff_with_tax=tariff, vat_rate=vat, vat_refund_rate=0.0,
        income_tax_rate=cit, income_tax_holiday=tax_holiday,
        urban_maintenance_tax_rate=urban_tax, education_surcharge_rate=edu_sur,
        discount_rate=0.08,
    )
    return WindFarmFinancialInputs(
        basic=basic, investment=investment, financing=financing,
        operational=operational, tax_financial=tax_financial,
    )


# ════════════════════════════════════════════════════════════════════════════
# 侧边栏：完整分项参数编辑
# ════════════════════════════════════════════════════════════════════════════

def sidebar_inputs() -> WindFarmFinancialInputs:
    """完整的侧边栏参数面板，含所有分项编辑"""

    st.sidebar.markdown("## ⚙️ 项目参数设定")

    # ──── 国家 ────
    countries = list_countries()
    country_options = {f"{cn} ({en})": en for en, cn in countries}
    selected_display = st.sidebar.selectbox(
        "🌏 国家/地区", list(country_options.keys()), index=0
    )
    country_name = country_options[selected_display]
    profile = get_country_profile(country_name)

    # ──── 项目类型 ────
    project_type = st.sidebar.radio(
        "项目类型", ["陆上风电 (Onshore)", "海上风电 (Offshore)"], horizontal=True
    )
    is_offshore = "Offshore" in project_type

    st.sidebar.markdown("---")

    # ═══════════════════ 1. 基本信息 ═══════════════════
    st.sidebar.markdown("### 📋 基本信息")
    project_name = st.sidebar.text_input("项目名称", value="Demo Wind Farm")
    c1, c2 = st.sidebar.columns(2)
    num_turbines = c1.number_input("机组台数", 1, 500, 28 if is_offshore else 16)
    turbine_mw = c2.number_input("单机容量(MW)", 1.0, 30.0, 18.0 if is_offshore else 6.25, step=0.5)
    full_load_hours = st.sidebar.slider("满负荷小时数 (h)", 1000, 5000, 3138 if is_offshore else 2523)
    loss_rate = st.sidebar.slider("综合线损率 (%)", 0.0, 10.0, 3.0, step=0.5) / 100.0
    construction_months = st.sidebar.slider("建设期 (月)", 6, 36, 24 if is_offshore else 12)

    st.sidebar.markdown("---")

    # ═══════════════════ 2. 投资造价分项 ═══════════════════
    st.sidebar.markdown("### 💰 投资造价")

    onshore_detail = None
    offshore_detail = None

    if is_offshore:
        # ---- 海上 EPC 明细 ----
        with st.sidebar.expander("🔩 OEM 成本 (风机+塔筒)", expanded=False):
            oem_turbine_price = st.number_input("风机售价 (USD/kW)", 100.0, 3000.0, 680.0, step=10.0, key="oem_tp")
            oem_tower_weight = st.number_input("塔筒重量+内附件 (t/台)", 50.0, 2000.0, 600.0, step=10.0, key="oem_tw")
            oem_tower_price = st.number_input("塔筒单价 (USD/吨)", 500.0, 5000.0, 1200.0, step=50.0, key="oem_tup")

        with st.sidebar.expander("🚢 安装与运输", expanded=False):
            inst_install = st.number_input("安装费 (USD/台)", 0.0, 5e6, 800_000.0, step=50_000.0, key="inst_i")
            inst_ocean = st.number_input("海运费 (USD/台)", 0.0, 5e6, 400_000.0, step=50_000.0, key="inst_o")
            inst_inland = st.number_input("陆运费 (USD/台)", 0.0, 2e6, 50_000.0, step=10_000.0, key="inst_l")

        with st.sidebar.expander("🏗️ 基础工程", expanded=False):
            fnd_price_per_ton = st.number_input("基础造价 (USD/吨)", 500.0, 10_000.0, 3500.0, step=100.0, key="fnd_p")
            fnd_tons = st.number_input("基础重量 (t/台)", 100.0, 5000.0, 1500.0, step=50.0, key="fnd_t")
            fnd_install = st.number_input("基础安装费 (USD/台)", 0.0, 5e6, 500_000.0, step=50_000.0, key="fnd_i")

        with st.sidebar.expander("⚡ BOP 分项工程 (USD/kW)", expanded=False):
            bop_aux = st.number_input("施工辅助工程", 0.0, 500.0, 20.0, step=1.0, key="bop1")
            bop_coll_eq = st.number_input("集电线路设备", 0.0, 500.0, 40.0, step=1.0, key="bop2")
            bop_subcable = st.number_input("海缆设备", 0.0, 500.0, 80.0, step=1.0, key="bop3")
            bop_offshore_sub = st.number_input("海上升压站设备", 0.0, 500.0, 60.0, step=1.0, key="bop4")
            bop_ctrl = st.number_input("集控中心", 0.0, 200.0, 15.0, step=1.0, key="bop5")
            bop_other_eq = st.number_input("其他设备", 0.0, 200.0, 10.0, step=1.0, key="bop6")
            bop_coll_civ = st.number_input("集电线路工程", 0.0, 200.0, 20.0, step=1.0, key="bop7")
            bop_landing = st.number_input("登陆电缆工程", 0.0, 200.0, 30.0, step=1.0, key="bop8")
            bop_sub_civ = st.number_input("海上升压站工程", 0.0, 200.0, 25.0, step=1.0, key="bop9")
            bop_ctrl_civ = st.number_input("集控中心工程", 0.0, 200.0, 10.0, step=1.0, key="bop10")
            bop_transp = st.number_input("交通工程", 0.0, 200.0, 5.0, step=1.0, key="bop11")
            bop_other_civ = st.number_input("其他工程", 0.0, 200.0, 5.0, step=1.0, key="bop12")

        oem = OEMCost(oem_turbine_price, oem_tower_weight, oem_tower_price)
        installation = InstallationCost(inst_install, inst_ocean, inst_inland)
        foundation = FoundationCost(fnd_price_per_ton, fnd_tons, fnd_install)
        bop = BOPCost(
            bop_aux, bop_coll_eq, bop_subcable, bop_offshore_sub, bop_ctrl, bop_other_eq,
            bop_coll_civ, bop_landing, bop_sub_civ, bop_ctrl_civ, bop_transp, bop_other_civ,
        )
        offshore_detail = OffshoreEPCBreakdown(
            oem=oem, installation=installation, foundation=foundation, bop=bop,
            num_turbines=num_turbines, turbine_capacity_mw=turbine_mw,
        )
        auto_epc = offshore_detail.total_epc_per_kw
        st.sidebar.info(f"EPC 明细合计: **{auto_epc:,.1f} USD/kW**")
        use_detail = st.sidebar.checkbox("使用 EPC 明细计算投资", value=True, key="use_epc")
        if use_detail:
            unit_investment = auto_epc
        else:
            unit_investment = st.sidebar.number_input("手动输入 (USD/kW)", 200.0, 5000.0, 1833.8, step=10.0, key="inv_manual_off")

    else:
        # ---- 陆上投资明细 ----
        with st.sidebar.expander("📦 陆上投资明细 (USD/kW)", expanded=False):
            on_equip = st.number_input("设备及安装工程", 0.0, 3000.0, 550.0, step=10.0, key="on1")
            on_civil = st.number_input("建筑工程", 0.0, 1000.0, 100.0, step=5.0, key="on2")
            on_aux = st.number_input("施工辅助工程", 0.0, 200.0, 15.0, step=1.0, key="on3")
            on_other = st.number_input("其他费用", 0.0, 500.0, 60.0, step=5.0, key="on4")
            on_contingency = st.number_input("基本预备费率 (%)", 0.0, 10.0, 2.0, step=0.5, key="on5") / 100.0
            on_storage = st.number_input("储能工程", 0.0, 500.0, 30.0, step=5.0, key="on6")
            on_grid = st.number_input("送出线路/电网接入", 0.0, 500.0, 50.0, step=5.0, key="on7")

        onshore_detail = OnshoreInvestment(
            on_equip, on_civil, on_aux, on_other, on_contingency, on_storage, on_grid,
        )
        auto_onshore = onshore_detail.total_per_kw
        st.sidebar.info(f"陆上明细合计: **{auto_onshore:,.1f} USD/kW**")
        use_detail = st.sidebar.checkbox("使用陆上明细计算投资", value=True, key="use_on")
        if use_detail:
            unit_investment = auto_onshore
        else:
            unit_investment = st.sidebar.number_input("手动输入 (USD/kW)", 200.0, 5000.0, 816.9, step=10.0, key="inv_manual_on")

    working_capital_per_kw = st.sidebar.number_input("流动资金 (USD/kW)", 0.0, 50.0, 4.2, step=0.5)

    st.sidebar.markdown("---")

    # ═══════════════════ 3. 融资条件 ═══════════════════
    st.sidebar.markdown("### 🏦 融资条件")
    default_eq = profile.typical_equity_ratio * 100 if profile else 25.0
    default_rate = profile.typical_loan_rate * 100 if profile else 3.25
    default_term = profile.typical_loan_term if profile else 15

    equity_ratio = st.sidebar.slider("资本金比例 (%)", 10.0, 50.0, default_eq, step=1.0) / 100.0
    loan_rate = st.sidebar.slider("贷款年利率 (%)", 0.5, 15.0, default_rate, step=0.25) / 100.0
    loan_term = st.sidebar.slider("贷款年限", 5, 25, default_term)

    with st.sidebar.expander("🔄 流动资金贷款", expanded=False):
        wc_loan_rate = st.number_input("流动资金贷款利率 (%)", 0.0, 15.0, 3.25, step=0.25, key="wclr") / 100.0
        wc_equity_ratio = st.number_input("流动资金自有资金比例 (%)", 0.0, 100.0, 30.0, step=5.0, key="wcer") / 100.0

    st.sidebar.markdown("---")

    # ═══════════════════ 4. 税费与电价 ═══════════════════
    st.sidebar.markdown("### 📊 税费与电价")
    default_vat = profile.vat_rate * 100 if profile else 13.0
    default_cit = profile.corporate_income_tax_rate * 100 if profile else 25.0
    default_tariff = 0.0638 if is_offshore else 0.0434

    tariff = st.sidebar.number_input("含税电价 (USD/kWh)", 0.001, 0.500, default_tariff, step=0.001, format="%.4f")
    vat_rate = st.sidebar.slider("增值税率 (%)", 0.0, 20.0, default_vat, step=1.0) / 100.0
    vat_refund = st.sidebar.slider("即征即退比例 (%)", 0.0, 100.0, 50.0, step=5.0) / 100.0
    income_tax_rate = st.sidebar.slider("所得税率 (%)", 0.0, 35.0, default_cit, step=1.0) / 100.0
    discount_rate = st.sidebar.slider("基准折现率 (%)", 3.0, 15.0, 8.0, step=0.5) / 100.0

    with st.sidebar.expander("📑 税费附加 & 所得税优惠", expanded=False):
        urban_tax = st.number_input("城市维护建设税率 (%)", 0.0, 10.0,
                                     (profile.urban_maintenance_tax_rate if profile else 0.05) * 100,
                                     step=1.0, key="utax") / 100.0
        edu_surcharge = st.number_input("教育费附加率 (%)", 0.0, 10.0,
                                         (profile.education_surcharge_rate if profile else 0.05) * 100,
                                         step=1.0, key="edu") / 100.0

        st.markdown("**所得税优惠政策**")
        if profile and profile.has_wind_tax_incentive:
            st.caption(f"当前国家优惠: {profile.tax_incentive_description}")
        c1, c2, c3 = st.columns(3)
        exempt_start = c1.number_input("免征起始年", 1, 25, 1, key="exs")
        exempt_end = c2.number_input("免征结束年", 1, 25, 3, key="exe")
        exempt_rate = c3.number_input("免征期税率", 0.0, 0.5, 0.0, step=0.01, key="exr")
        c4, c5, c6 = st.columns(3)
        half_start = c4.number_input("减半起始年", 1, 25, 4, key="hfs")
        half_end = c5.number_input("减半结束年", 1, 25, 6, key="hfe")
        half_rate = c6.number_input("减半期税率", 0.0, 0.5, income_tax_rate / 2.0, step=0.01, key="hfr")
        tax_holiday = (exempt_start, exempt_end, exempt_rate, half_start, half_end, half_rate)

    st.sidebar.markdown("---")

    # ═══════════════════ 5. 运营成本分项 ═══════════════════
    st.sidebar.markdown("### 🔧 运营成本")
    operation_years = st.sidebar.slider("运营期 (年)", 15, 30, 25 if is_offshore else 20)
    depreciation_years = st.sidebar.slider("折旧年限 (年)", 10, 25, 20)
    residual_rate = st.sidebar.slider("残值率 (%)", 0.0, 10.0, 0.0 if is_offshore else 5.0, step=0.5) / 100.0

    with st.sidebar.expander("👷 人员与保险", expanded=False):
        staff_count = st.number_input("定员人数", 1, 200, 35 if is_offshore else 18, key="staff")
        salary_per_person = st.number_input("人均年薪 (万USD)", 0.5, 20.0, 3.52 if is_offshore else 1.11, step=0.1, key="sal")
        welfare_rate = st.number_input("福利系数", 0.0, 2.0, 0.60, step=0.05, key="welf")
        insurance_rate = st.number_input("保险费率 (%)", 0.0, 1.0, 0.35 if is_offshore else 0.25, step=0.05, key="ins") / 100.0

    with st.sidebar.expander("🛡️ 质保期内运维 (USD/kW·年)", expanded=False):
        warranty_years = st.number_input("质保期 (年)", 0, 10, 5, key="wy")
        w_material = st.number_input("材料费", 0.0, 20.0, 4.23 if is_offshore else 2.82, step=0.1, key="wm")
        w_repair = st.number_input("维修费", 0.0, 20.0, 0.0, step=0.1, key="wr")
        w_other = st.number_input("其他费用", 0.0, 20.0, 4.23 if is_offshore else 2.82, step=0.1, key="wo")

    with st.sidebar.expander("🔧 质保期外运维", expanded=False):
        pw_major = st.checkbox("含大部件更换", value=True, key="pw_major")
        pw_material = st.number_input("材料费 (USD/kW·年)", 0.0, 20.0, 4.23 if is_offshore else 2.82, step=0.1, key="pwm")
        pw_other = st.number_input("其他费用 (USD/kW·年)", 0.0, 20.0, 4.23 if is_offshore else 2.82, step=0.1, key="pwo")
        st.markdown("**维修费率 (基于静态投资)**")
        st.caption("格式: 起始年-结束年: 费率%")
        rate_6_10 = st.number_input("6-10年 (%)", 0.0, 5.0, 1.0, step=0.1, key="mr1") / 100.0
        rate_11_15 = st.number_input("11-15年 (%)", 0.0, 5.0, 1.5, step=0.1, key="mr2") / 100.0
        rate_16_20 = st.number_input("16-20年 (%)", 0.0, 5.0, 2.0, step=0.1, key="mr3") / 100.0
        rate_21_25 = st.number_input("21-25年 (%)", 0.0, 5.0, 2.5, step=0.1, key="mr4") / 100.0
        maint_rates = [
            (1, 5, 0.005),
            (6, 10, rate_6_10),
            (11, 15, rate_11_15),
            (16, 20, rate_16_20),
            (21, 25, rate_21_25),
        ]

    # ──── 海上专项 ────
    offshore_extra = None
    if is_offshore:
        with st.sidebar.expander("🚢 海上专项费用", expanded=False):
            requires_sov = st.checkbox("需要 SOV 运维船", value=False, key="sov")
            sov_cost = st.number_input("SOV 年费 (万USD)", 0.0, 500.0, 0.0, key="sov_c") if requires_sov else 0.0
            sea_area_fee = st.number_input("海域使用金 (万USD/年)", 0.0, 500.0, 43.2, step=1.0, key="sea")
            storage_rental = st.number_input("储能租赁费 (万USD/年)", 0.0, 500.0, 0.0, step=1.0, key="stor_r")
            decomm_rate = st.number_input("拆除费率 (%)", 0.0, 10.0, 2.0, step=0.5, key="decomm") / 100.0
            offshore_extra = OffshoreExtraCost(
                requires_sov=requires_sov,
                sov_annual_cost=sov_cost,
                sea_area_usage_fee=sea_area_fee,
                storage_rental=storage_rental,
                decommissioning_rate=decomm_rate,
            )

    # ═══════════════════ 组装 ═══════════════════
    basic = BasicInfo(
        project_name=project_name,
        project_type="offshore" if is_offshore else "onshore",
        country=country_name,
        num_turbines=num_turbines,
        turbine_capacity_mw=turbine_mw,
        full_load_hours=full_load_hours,
        loss_rate=loss_rate,
        construction_months=construction_months,
    )

    investment = InvestmentData(
        unit_static_investment=unit_investment,
        working_capital_per_kw=working_capital_per_kw,
        onshore_detail=onshore_detail,
        offshore_detail=offshore_detail,
    )

    financing = FinancingTerms(
        equity_ratio=equity_ratio,
        long_term_loan_rate=loan_rate,
        loan_term_years=loan_term,
        working_capital_loan_rate=wc_loan_rate,
        working_capital_equity_ratio=wc_equity_ratio,
    )

    warranty_cost = WarrantyPeriodCost(
        warranty_years=warranty_years,
        material_cost_per_kw=w_material,
        repair_cost_per_kw=w_repair,
        other_cost_per_kw=w_other,
    )
    post_warranty_cost = PostWarrantyPeriodCost(
        includes_major_components=pw_major,
        material_cost_per_kw=pw_material,
        other_cost_per_kw=pw_other,
        maintenance_rates=maint_rates,
    )

    operational = OperationalCost(
        staff_count=staff_count,
        salary_per_person=salary_per_person,
        welfare_rate=welfare_rate,
        insurance_rate=insurance_rate,
        depreciation_years=depreciation_years,
        residual_rate=residual_rate,
        operation_years=operation_years,
        warranty=warranty_cost,
        post_warranty=post_warranty_cost,
        offshore_extra=offshore_extra,
    )

    tax_financial = TaxAndFinancial(
        tariff_with_tax=tariff,
        vat_rate=vat_rate,
        vat_refund_rate=vat_refund,
        income_tax_rate=income_tax_rate,
        income_tax_holiday=tax_holiday,
        urban_maintenance_tax_rate=urban_tax,
        education_surcharge_rate=edu_surcharge,
        discount_rate=discount_rate,
    )

    return WindFarmFinancialInputs(
        basic=basic,
        investment=investment,
        financing=financing,
        operational=operational,
        tax_financial=tax_financial,
    )


# ════════════════════════════════════════════════════════════════════════════
# 图表函数（复用）
# ════════════════════════════════════════════════════════════════════════════

def plot_kpi_cards(result: CalculationResult):
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("全投资IRR(税后)", f"{result.project_irr_after_tax:.2%}")
    c2.metric("资本金IRR", f"{result.equity_irr:.2%}")
    c3.metric("LCOE", f"{result.lcoe:.5f} $/kWh")
    c4.metric("回收期(税后)", f"{result.payback_after_tax:.1f} 年")
    c5.metric("NPV(税后)", f"{result.project_npv_after_tax / 1e6:,.1f} M$")


def plot_investment_breakdown(inputs: WindFarmFinancialInputs):
    items = {"静态投资": inputs.total_static_investment,
             "建设期利息": inputs.construction_interest,
             "流动资金": inputs.working_capital}

    if inputs.investment.onshore_detail:
        od = inputs.investment.onshore_detail
        items = {
            "设备及安装": od.equipment_and_installation * inputs.capacity_kw,
            "建筑工程": od.civil_works * inputs.capacity_kw,
            "施工辅助": od.construction_auxiliary * inputs.capacity_kw,
            "其他费用": od.other_costs * inputs.capacity_kw,
            "储能": od.storage_cost * inputs.capacity_kw,
            "送出线路": od.grid_connection_cost * inputs.capacity_kw,
            "预备费": od.contingency * inputs.capacity_kw,
            "建设期利息": inputs.construction_interest,
        }
    elif inputs.investment.offshore_detail:
        od = inputs.investment.offshore_detail
        items = {
            "OEM(风机+塔筒)": od.oem_per_kw * inputs.capacity_kw,
            "安装与运输": od.installation_per_kw * inputs.capacity_kw,
            "基础工程": od.foundation_per_kw * inputs.capacity_kw,
            "BOP 合计": od.bop.total_bop_per_kw * inputs.capacity_kw,
            "建设期利息": inputs.construction_interest,
        }

    items = {k: v for k, v in items.items() if v > 0}
    fig = px.pie(
        pd.DataFrame({"项目": list(items.keys()), "金额": list(items.values())}),
        values="金额", names="项目",
        color_discrete_sequence=COLOR_PALETTE, hole=0.45,
    )
    fig.update_layout(title="投资构成", height=380, margin=dict(t=40, b=20))
    st.plotly_chart(fig, use_container_width=True)


def plot_cashflow_chart(result: CalculationResult):
    years, cf_after, cum = [], [], []
    running = 0.0
    for f in result.annual_flows:
        years.append(f"Y{f.year}")
        cf_after.append(f.project_net_cf_after_tax)
        running += f.project_net_cf_after_tax
        cum.append(running)

    fig = go.Figure()
    fig.add_trace(go.Bar(x=years, y=cf_after, name="税后净现金流", marker_color="#2E75B6", opacity=0.85))
    fig.add_trace(go.Scatter(x=years, y=cum, name="累计", line=dict(color="#C00000", width=2.5), yaxis="y2"))
    fig.update_layout(
        title="逐年全投资现金流", xaxis_title="年份",
        yaxis_title="净现金流 (USD)",
        yaxis2=dict(title="累计 (USD)", overlaying="y", side="right"),
        legend=dict(x=0.01, y=0.99), height=400, margin=dict(t=40, b=40),
    )
    st.plotly_chart(fig, use_container_width=True)


def plot_profit_chart(result: CalculationResult):
    op = [f for f in result.annual_flows if not f.is_construction]
    yrs = [f"Y{f.year}" for f in op]
    fig = go.Figure()
    fig.add_trace(go.Bar(x=yrs, y=[f.revenue for f in op], name="营业收入", marker_color="#548235"))
    fig.add_trace(go.Bar(x=yrs, y=[-f.total_opex for f in op], name="经营成本", marker_color="#BF8F00"))
    fig.add_trace(go.Bar(x=yrs, y=[-f.depreciation for f in op], name="折旧", marker_color="#7030A0"))
    fig.add_trace(go.Bar(x=yrs, y=[-(f.loan_interest + f.wc_loan_interest) for f in op], name="利息", marker_color="#C00000"))
    fig.add_trace(go.Scatter(x=yrs, y=[f.net_profit for f in op], name="净利润", line=dict(color="#1F4E79", width=2.5)))
    fig.update_layout(barmode="relative", title="利润结构", height=400, margin=dict(t=40, b=40))
    st.plotly_chart(fig, use_container_width=True)


def plot_sensitivity(inputs: WindFarmFinancialInputs):
    factors = {
        "电价": ("tariff_with_tax", inputs.tax_financial.tariff_with_tax),
        "投资": ("unit_static_investment", inputs.investment.unit_static_investment),
        "小时数": ("full_load_hours", inputs.basic.full_load_hours),
        "贷款利率": ("long_term_loan_rate", inputs.financing.long_term_loan_rate),
    }
    pct_range = [-20, -10, -5, 0, 5, 10, 20]
    heatmap, labels = [], []
    for name, (attr, base_val) in factors.items():
        labels.append(name)
        row = []
        for pct in pct_range:
            inp = copy.deepcopy(inputs)
            nv = base_val * (1.0 + pct / 100.0)
            if attr == "tariff_with_tax": inp.tax_financial.tariff_with_tax = nv
            elif attr == "unit_static_investment": inp.investment.unit_static_investment = nv
            elif attr == "full_load_hours": inp.basic.full_load_hours = max(500, int(round(nv)))
            elif attr == "long_term_loan_rate": inp.financing.long_term_loan_rate = max(0.001, nv)
            try:
                row.append(calculate(inp).project_irr_after_tax * 100)
            except Exception:
                row.append(0.0)
        heatmap.append(row)

    fig = go.Figure(data=go.Heatmap(
        z=heatmap, x=[f"{p:+d}%" for p in pct_range], y=labels,
        colorscale="RdYlGn",
        text=[[f"{v:.2f}%" for v in r] for r in heatmap],
        texttemplate="%{text}", textfont=dict(size=12),
        colorbar=dict(title="IRR(%)"),
    ))
    fig.update_layout(title="敏感性分析 — 全投资税后 IRR", height=350, margin=dict(t=40, b=40))
    st.plotly_chart(fig, use_container_width=True)


def render_full_assessment(inputs: WindFarmFinancialInputs, result: CalculationResult, key_prefix: str = "main"):
    """
    渲染完整的项目评估视图（KPI + 参数 + 图表 + 明细表）。
    key_prefix 用于防止多次调用时 widget key 冲突。
    """
    # KPI
    plot_kpi_cards(result)
    st.markdown("---")

    # 国家参考
    profile = get_country_profile(inputs.basic.country)
    if profile:
        with st.expander(f"🌏 {profile.country_name_cn} 国别参数参考", expanded=False):
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("企业所得税", f"{profile.corporate_income_tax_rate:.0%}")
            c2.metric("增值税", f"{profile.vat_rate:.0%}")
            c3.metric("典型贷款利率", f"{profile.typical_loan_rate:.2%}")
            c4.metric("典型资本金比例", f"{profile.typical_equity_ratio:.0%}")
            st.info(f"**优惠政策**: {profile.tax_incentive_description}")

    # 完整参数表
    with st.expander("📋 全部输入参数", expanded=False):
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.markdown("**基本信息**")
            st.write(f"- 项目名称: {inputs.basic.project_name}")
            st.write(f"- 类型: {'海上' if inputs.basic.project_type == 'offshore' else '陆上'}")
            st.write(f"- 国家: {inputs.basic.country}")
            st.write(f"- 装机: {inputs.capacity_mw:.0f} MW ({inputs.basic.num_turbines}×{inputs.basic.turbine_capacity_mw} MW)")
            st.write(f"- 满负荷小时数: {inputs.basic.full_load_hours} h")
            st.write(f"- 线损率: {inputs.basic.loss_rate:.2%}")
            st.write(f"- 年上网电量: {inputs.net_annual_generation_mwh:,.0f} MWh")
            st.write(f"- 建设期: {inputs.basic.construction_months} 月")
        with c2:
            st.markdown("**投资造价**")
            st.write(f"- 单位千瓦投资: {inputs.investment.resolve_unit_investment():,.1f} USD/kW")
            st.write(f"- 静态总投资: {inputs.total_static_investment / 1e6:,.1f} M$")
            st.write(f"- 建设期利息: {inputs.construction_interest / 1e6:,.2f} M$")
            st.write(f"- 动态总投资: {inputs.total_dynamic_investment / 1e6:,.1f} M$")
            st.write(f"- 流动资金: {inputs.working_capital / 1e6:,.2f} M$")
            st.write(f"- 项目总投资: {inputs.total_investment / 1e6:,.1f} M$")
        with c3:
            st.markdown("**融资条件**")
            st.write(f"- 资本金: {inputs.equity_amount / 1e6:,.1f} M$ ({inputs.financing.equity_ratio:.0%})")
            st.write(f"- 贷款: {inputs.debt_amount / 1e6:,.1f} M$")
            st.write(f"- 利率: {inputs.financing.long_term_loan_rate:.2%}")
            st.write(f"- 贷款期限: {inputs.financing.loan_term_years} 年")
            st.write(f"- 电价(含税): {inputs.tax_financial.tariff_with_tax:.4f} USD/kWh")
            st.write(f"- 电价(不含税): {inputs.tax_financial.tariff_without_tax:.4f} USD/kWh")
        with c4:
            st.markdown("**运营与税费**")
            st.write(f"- 运营期: {inputs.operational.operation_years} 年")
            st.write(f"- 折旧年限: {inputs.operational.depreciation_years} 年")
            st.write(f"- 残值率: {inputs.operational.residual_rate:.1%}")
            st.write(f"- 质保期: {inputs.operational.warranty.warranty_years} 年")
            st.write(f"- 保险费率: {inputs.operational.insurance_rate:.3%}")
            st.write(f"- 人员: {inputs.operational.staff_count} 人")
            st.write(f"- 增值税率: {inputs.tax_financial.vat_rate:.0%}")
            st.write(f"- 所得税率: {inputs.tax_financial.income_tax_rate:.0%}")
            st.write(f"- 折现率: {inputs.tax_financial.discount_rate:.1%}")

    # 投资造价分项明细
    with st.expander("💰 投资造价明细", expanded=False):
        if inputs.investment.onshore_detail:
            od = inputs.investment.onshore_detail
            inv_items = {
                "设备及安装工程": od.equipment_and_installation,
                "建筑工程": od.civil_works,
                "施工辅助工程": od.construction_auxiliary,
                "其他费用": od.other_costs,
                "储能工程": od.storage_cost,
                "送出线路": od.grid_connection_cost,
                "基本预备费": od.contingency,
                "**合计**": od.total_per_kw,
            }
            df_inv = pd.DataFrame([
                {"分项": k, "USD/kW": v, "总额(M$)": v * inputs.capacity_kw / 1e6}
                for k, v in inv_items.items() if v > 0 or k == "**合计**"
            ])
            st.dataframe(df_inv.style.format({"USD/kW": "{:,.1f}", "总额(M$)": "{:,.2f}"}),
                         use_container_width=True, hide_index=True)
        elif inputs.investment.offshore_detail:
            od = inputs.investment.offshore_detail
            inv_items = {
                "OEM (风机+塔筒)": od.oem_per_kw,
                "安装与运输": od.installation_per_kw,
                "基础工程": od.foundation_per_kw,
                "BOP 合计": od.bop.total_bop_per_kw,
                "**EPC 合计**": od.total_epc_per_kw,
            }
            df_inv = pd.DataFrame([
                {"分项": k, "USD/kW": v, "总额(M$)": v * inputs.capacity_kw / 1e6}
                for k, v in inv_items.items()
            ])
            st.dataframe(df_inv.style.format({"USD/kW": "{:,.1f}", "总额(M$)": "{:,.2f}"}),
                         use_container_width=True, hide_index=True)
        else:
            st.write(f"单位千瓦投资: {inputs.investment.resolve_unit_investment():,.1f} USD/kW")
            st.write(f"总投资: {inputs.total_investment / 1e6:,.1f} M$")

    # 运维成本逐年预览
    with st.expander("🔧 运维成本逐年预览", expanded=False):
        opex_rows = []
        sample_years = list(range(1, inputs.operational.operation_years + 1, max(1, inputs.operational.operation_years // 10)))
        if inputs.operational.operation_years not in sample_years:
            sample_years.append(inputs.operational.operation_years)
        for yr in sample_years:
            opex = inputs.operational.get_year_opex(yr, inputs.capacity_kw, inputs.total_static_investment)
            opex_rows.append({
                "运营年": yr,
                "材料费": opex["material"],
                "维修费": opex["repair"],
                "其他费用": opex["other"],
                "人员": opex["staff"],
                "保险": opex["insurance"],
                "海上专项": opex["offshore_extra"],
                "合计": sum(opex.values()),
            })
        df_opex = pd.DataFrame(opex_rows)
        st.dataframe(df_opex.style.format({c: "{:,.0f}" for c in df_opex.columns if c != "运营年"}),
                     use_container_width=True, hide_index=True)

    # 图表
    col_l, col_r = st.columns([2, 1])
    with col_l:
        plot_cashflow_chart(result)
    with col_r:
        plot_investment_breakdown(inputs)

    plot_profit_chart(result)

    st.markdown("---")
    plot_sensitivity(inputs)

    # 逐年明细
    st.markdown("---")
    st.markdown("### 📊 逐年现金流明细")
    df_data = []
    for f in result.annual_flows:
        df_data.append({
            "年份": f"建设-{f.year + 1}" if f.is_construction else f"运营-{f.year}",
            "营业收入": f.revenue, "经营成本": f.total_opex,
            "折旧": f.depreciation,
            "利息支出": f.loan_interest + f.wc_loan_interest,
            "总成本": f.total_cost, "利润总额": f.profit_before_tax,
            "所得税": f.income_tax, "净利润": f.net_profit,
            "全投资税后CF": f.project_net_cf_after_tax,
            "资本金CF": f.equity_net_cf,
        })
    df = pd.DataFrame(df_data)
    st.dataframe(
        df.style.format({c: "{:,.0f}" for c in df.columns if c != "年份"}),
        use_container_width=True, height=400,
    )

    # Excel 导出
    st.markdown("---")
    excel_bytes = export_to_excel(inputs, result)
    st.download_button(
        "📥 下载 Excel 报告", data=excel_bytes,
        file_name=f"{inputs.basic.project_name}_财务评价.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        key=f"{key_prefix}_dl_excel",
    )


def reverse_calc_panel(inputs: WindFarmFinancialInputs):
    tab1, tab2, tab3, tab4 = st.tabs([
        "目标IRR→电价", "目标LCOE→投资", "目标IRR→小时数", "目标LCOE→风机价格",
    ])
    irr_labels = {"project_before_tax": "全投资税前", "project_after_tax": "全投资税后", "equity": "资本金"}

    with tab1:
        c1, c2 = st.columns(2)
        t_irr = c1.number_input("目标IRR(%)", 1.0, 30.0, 8.0, step=0.5, key="rv1_irr") / 100.0
        t_type = c2.selectbox("IRR类型", list(irr_labels.keys()), 1, format_func=irr_labels.get, key="rv1_type")
        if st.button("计算电价", key="rv1_btn"):
            with st.spinner("求解中..."):
                try:
                    t = solve_tariff_for_target_irr(inputs, t_irr, t_type)
                    st.success(f"含税电价: **{t:.5f} USD/kWh** ({t * 7.1:.4f} 元/kWh)")
                except Exception as e:
                    st.error(f"求解失败: {e}")

    with tab2:
        t_lcoe = st.number_input("目标LCOE (USD/kWh)", 0.001, 0.200, 0.030, step=0.001, format="%.4f", key="rv2_lcoe")
        if st.button("计算投资", key="rv2_btn"):
            with st.spinner("求解中..."):
                try:
                    inv = solve_investment_for_target_lcoe(inputs, t_lcoe)
                    st.success(f"单位千瓦投资: **{inv:.1f} USD/kW** ({inv * 7.1:.0f} 元/kW)")
                except Exception as e:
                    st.error(f"求解失败: {e}")

    with tab3:
        c1, c2 = st.columns(2)
        t_irr2 = c1.number_input("目标IRR(%)", 1.0, 30.0, 8.0, step=0.5, key="rv3_irr") / 100.0
        t_type2 = c2.selectbox("IRR类型", list(irr_labels.keys()), 1, format_func=irr_labels.get, key="rv3_type")
        if st.button("计算小时数", key="rv3_btn"):
            with st.spinner("求解中..."):
                try:
                    h = solve_hours_for_target_irr(inputs, t_irr2, t_type2)
                    st.success(f"最低满负荷小时数: **{h:.0f} h**")
                except Exception as e:
                    st.error(f"求解失败: {e}")

    with tab4:
        has_epc = inputs.investment.offshore_detail is not None
        if not has_epc:
            st.info("此功能需要海上项目且启用了 EPC 明细。请在侧边栏选择「海上风电」并勾选「使用 EPC 明细计算投资」。")
        else:
            current_price = inputs.investment.offshore_detail.oem.turbine_price_per_kw
            st.caption(f"当前风机 OEM 售价: **{current_price:,.1f} USD/kW**")
            t_lcoe4 = st.number_input(
                "目标 LCOE (USD/kWh)", 0.001, 0.200, 0.040, step=0.001, format="%.4f", key="rv4_lcoe",
            )
            if st.button("反算风机价格", key="rv4_btn"):
                with st.spinner("求解中..."):
                    try:
                        price = solve_turbine_price_for_target_lcoe(inputs, t_lcoe4)
                        if price is not None:
                            delta = price - current_price
                            sign = "+" if delta >= 0 else ""
                            st.success(
                                f"满足 LCOE={t_lcoe4:.4f} USD/kWh 的风机 OEM 售价: "
                                f"**{price:,.1f} USD/kW** ({price * 7.1:,.0f} 元/kW)\n\n"
                                f"相比当前 {current_price:,.1f} USD/kW 变化: {sign}{delta:,.1f} USD/kW ({sign}{delta/current_price:.1%})"
                            )
                        else:
                            st.error("无法求解，请检查是否已配置海上 EPC 明细。")
                    except Exception as e:
                        st.error(f"求解失败: {e}")


# ════════════════════════════════════════════════════════════════════════════
# 项目对比面板
# ════════════════════════════════════════════════════════════════════════════

def comparison_page():
    """多项目对比页面"""
    st.header("📊 项目对比")

    projects = st.session_state.projects
    if len(projects) < 2:
        st.warning("至少需要保存 **2 个项目** 才能进行对比。请在「项目评估」页面保存项目后再来。")
        return

    options = {pid: f"{p['name']} ({p['saved_at']})" for pid, p in projects.items()}
    selected = st.multiselect(
        "选择要对比的项目 (至少选 2 个)",
        options=list(options.keys()),
        format_func=lambda x: options[x],
        default=list(options.keys())[:min(4, len(options))],
    )

    if len(selected) < 2:
        st.info("请至少选择 2 个项目。")
        return

    # ──── KPI 对比表 ────
    st.markdown("### 关键指标对比")
    rows = []
    for pid in selected:
        p = projects[pid]
        r: CalculationResult = p["result"]
        inp: WindFarmFinancialInputs = p["inputs"]
        rows.append({
            "项目": p["name"],
            "类型": "海上" if inp.basic.project_type == "offshore" else "陆上",
            "容量(MW)": inp.capacity_mw,
            "小时数(h)": inp.basic.full_load_hours,
            "投资(USD/kW)": inp.investment.resolve_unit_investment(),
            "电价(USD/kWh)": inp.tax_financial.tariff_with_tax,
            "全投资IRR(税后)": r.project_irr_after_tax,
            "资本金IRR": r.equity_irr,
            "LCOE(USD/kWh)": r.lcoe,
            "回收期(年)": r.payback_after_tax,
            "NPV(M$)": r.project_npv_after_tax / 1e6,
            "ROI": r.roi,
            "ROE": r.roe,
        })

    df = pd.DataFrame(rows)
    fmt_map = {
        "投资(USD/kW)": "{:,.1f}",
        "电价(USD/kWh)": "{:.4f}",
        "全投资IRR(税后)": "{:.2%}",
        "资本金IRR": "{:.2%}",
        "LCOE(USD/kWh)": "{:.5f}",
        "回收期(年)": "{:.1f}",
        "NPV(M$)": "{:,.1f}",
        "ROI": "{:.2%}",
        "ROE": "{:.2%}",
    }
    st.dataframe(df.style.format(fmt_map), use_container_width=True, hide_index=True)

    # ──── 柱状图对比 ────
    st.markdown("### 核心指标并列对比")

    col1, col2 = st.columns(2)

    with col1:
        fig = go.Figure()
        names = [projects[pid]["name"] for pid in selected]
        irr_vals = [projects[pid]["result"].project_irr_after_tax * 100 for pid in selected]
        eq_irr_vals = [projects[pid]["result"].equity_irr * 100 for pid in selected]
        fig.add_trace(go.Bar(x=names, y=irr_vals, name="全投资IRR(税后)", marker_color="#2E75B6"))
        fig.add_trace(go.Bar(x=names, y=eq_irr_vals, name="资本金IRR", marker_color="#548235"))
        fig.update_layout(title="IRR 对比 (%)", barmode="group", height=380, yaxis_title="%")
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        fig = go.Figure()
        lcoe_vals = [projects[pid]["result"].lcoe * 1000 for pid in selected]
        fig.add_trace(go.Bar(x=names, y=lcoe_vals, name="LCOE", marker_color="#BF8F00"))
        fig.update_layout(title="LCOE 对比 (USD/MWh)", height=380, yaxis_title="USD/MWh")
        st.plotly_chart(fig, use_container_width=True)

    # ──── 雷达图 ────
    st.markdown("### 综合能力雷达图")

    categories = ["IRR", "ROI", "ROE", "回收期(短优)", "LCOE(低优)"]
    fig = go.Figure()

    all_irr = [projects[pid]["result"].project_irr_after_tax for pid in selected]
    all_roi = [projects[pid]["result"].roi for pid in selected]
    all_roe = [projects[pid]["result"].roe for pid in selected]
    all_payback = [projects[pid]["result"].payback_after_tax for pid in selected]
    all_lcoe = [projects[pid]["result"].lcoe for pid in selected]

    def normalize(vals, invert=False):
        mn, mx = min(vals), max(vals)
        if mx == mn:
            return [0.5] * len(vals)
        if invert:
            return [(mx - v) / (mx - mn) for v in vals]
        return [(v - mn) / (mx - mn) for v in vals]

    n_irr = normalize(all_irr)
    n_roi = normalize(all_roi)
    n_roe = normalize(all_roe)
    n_pay = normalize(all_payback, invert=True)
    n_lcoe = normalize(all_lcoe, invert=True)

    for i, pid in enumerate(selected):
        vals = [n_irr[i], n_roi[i], n_roe[i], n_pay[i], n_lcoe[i]]
        vals.append(vals[0])
        fig.add_trace(go.Scatterpolar(
            r=vals,
            theta=categories + [categories[0]],
            name=projects[pid]["name"],
            fill="toself",
            opacity=0.6,
            line_color=COLOR_PALETTE[i % len(COLOR_PALETTE)],
        ))

    fig.update_layout(
        polar=dict(radialaxis=dict(visible=True, range=[0, 1])),
        title="项目综合能力雷达图 (归一化)",
        height=500,
    )
    st.plotly_chart(fig, use_container_width=True)

    # ──── 现金流对比 ────
    st.markdown("### 累计现金流对比")
    fig = go.Figure()
    for i, pid in enumerate(selected):
        p = projects[pid]
        cum, running = [], 0.0
        for f in p["result"].annual_flows:
            running += f.project_net_cf_after_tax
            cum.append(running)
        fig.add_trace(go.Scatter(
            y=cum, name=p["name"],
            line=dict(color=COLOR_PALETTE[i % len(COLOR_PALETTE)], width=2.5),
        ))
    fig.update_layout(title="累计净现金流", xaxis_title="年份", yaxis_title="USD", height=400)
    st.plotly_chart(fig, use_container_width=True)


# ════════════════════════════════════════════════════════════════════════════
# 项目管理 — 按国家 → 项目分组展示 (卡片式 UI)
# ════════════════════════════════════════════════════════════════════════════

_PM_CSS = """
<style>
.pm-country-banner {
    background: linear-gradient(135deg, #1F4E79 0%, #2E75B6 100%);
    color: white; padding: 14px 24px; border-radius: 10px;
    margin: 20px 0 14px 0;
}
.pm-country-banner .pm-title { font-size: 1.35rem; font-weight: 700; margin: 0; }
.pm-country-banner .pm-sub { opacity: 0.85; font-size: 0.88rem; margin-top: 2px; }
.pm-group-bar {
    background: #f0f4f8; border-left: 4px solid #2E75B6;
    padding: 10px 18px; border-radius: 0 8px 8px 0;
    margin: 14px 0 10px 0; display: flex; align-items: center; gap: 12px;
}
.pm-group-bar .pm-gname { font-weight: 700; font-size: 1.05rem; color: #1F4E79; }
.pm-tag {
    display: inline-block; padding: 2px 10px; border-radius: 10px;
    font-size: 0.75rem; font-weight: 600; color: #fff;
}
.pm-tag-onshore { background: #548235; }
.pm-tag-offshore { background: #1F4E79; }
.pm-tag-count { background: #aab; color: #fff; }
.pm-summary {
    background: #fafbfc; border: 1px solid #e8ecf0; border-radius: 8px;
    padding: 8px 16px; margin: 4px 0 14px 0; display: flex;
    gap: 24px; flex-wrap: wrap; font-size: 0.85rem; color: #555;
}
.pm-summary b { color: #1F4E79; }
.pm-best-tag {
    display: inline-block; font-size: 0.68rem; font-weight: 800;
    padding: 1px 8px; border-radius: 8px; margin-left: 6px; vertical-align: middle;
}
.pm-best-irr { background: linear-gradient(135deg, #FFD700, #FFA500); color: #333; }
.pm-best-lcoe { background: linear-gradient(135deg, #90EE90, #2E8B57); color: #fff; }
</style>
"""


def _irr_color(v: float) -> str:
    if v >= 0.10:
        return "#548235"
    elif v >= 0.06:
        return "#BF8F00"
    return "#C00000"


def _render_project_card(pid: str, proj: dict, best_irr: bool, best_lcoe: bool):
    """Render one project card inside a st.container with border."""
    inp: WindFarmFinancialInputs = proj["inputs"]
    res: CalculationResult = proj["result"]
    irr_c = _irr_color(res.project_irr_after_tax)

    with st.container(border=True):
        # 标题行
        title_md = f"**{proj['name']}**"
        if best_irr:
            title_md += ' <span class="pm-best-tag pm-best-irr">Best IRR</span>'
        elif best_lcoe:
            title_md += ' <span class="pm-best-tag pm-best-lcoe">Best LCOE</span>'
        st.markdown(title_md, unsafe_allow_html=True)

        # KPI 指标
        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Capacity", f"{inp.capacity_mw:.0f} MW")
        k2.metric("Investment", f"{inp.investment.resolve_unit_investment():,.0f} $/kW")
        k3.metric("P90", f"{inp.basic.full_load_hours:.0f} h")
        k4.metric("Tariff", f"{inp.tax_financial.tariff_with_tax:.4f} $/kWh")

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("IRR (after tax)", f"{res.project_irr_after_tax:.2%}")
        m2.metric("Equity IRR", f"{res.equity_irr:.2%}")
        m3.metric("LCOE", f"{res.lcoe:.5f} $/kWh")
        m4.metric("NPV", f"{res.project_npv_after_tax / 1e6:,.1f} M$")

        r1, r2 = st.columns([1, 1])
        r1.metric("Payback", f"{res.payback_after_tax:.1f} yr")
        r2.metric("IRR (before tax)", f"{res.project_irr_before_tax:.2%}")

        # 操作按钮
        b1, b2, b3, _pad = st.columns([1, 1, 1, 3])
        with b1:
            if st.button("View Details", key=f"view_{pid}", type="primary", use_container_width=True):
                st.session_state.detail_pid = pid
                st.rerun()
        with b2:
            excel_b = export_to_excel(inp, res)
            st.download_button(
                "Download Excel", data=excel_b,
                file_name=f"{proj['name']}_report.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key=f"dl_{pid}", use_container_width=True,
            )
        with b3:
            confirming = st.session_state.get("confirm_delete") == pid
            if confirming:
                st.warning(f"Delete **{proj['name']}**? Enter credentials:")
                del_u = st.text_input("Username", key=f"delu_{pid}",
                                      placeholder="Username")
                del_p = st.text_input("Password", key=f"delp_{pid}",
                                      type="password", placeholder="Password")
                c_yes, c_no = st.columns(2)
                with c_yes:
                    if st.button("Confirm", key=f"cdel_y_{pid}",
                                 type="primary", use_container_width=True):
                        if del_u == _DELETE_USER and del_p == _DELETE_PWD:
                            delete_project(pid)
                            st.rerun()
                        else:
                            st.error("Wrong credentials")
                with c_no:
                    if st.button("Cancel", key=f"cdel_n_{pid}",
                                 use_container_width=True):
                        st.session_state.pop("confirm_delete", None)
                        st.rerun()
            else:
                if st.button("Delete", key=f"del_{pid}", use_container_width=True):
                    st.session_state["confirm_delete"] = pid
                    st.rerun()


def _render_project_list():
    """按 国家 -> 项目组 -> 方案 三级结构展示"""
    st.markdown(_PM_CSS, unsafe_allow_html=True)

    projects = st.session_state.projects

    from collections import defaultdict
    tree: dict[str, dict[str, list]] = defaultdict(lambda: defaultdict(list))
    for pid, proj in projects.items():
        country = proj.get("country", proj["inputs"].basic.country)
        group = proj.get("group", proj["name"].split(" - ")[0].strip() if " - " in proj["name"] else "Other")
        tree[country][group].append((pid, proj))

    total_variants = len(projects)
    total_groups = sum(len(g) for g in tree.values())
    st.markdown(
        f'<div class="pm-summary">'
        f'<span><b>{total_variants}</b> variants</span>'
        f'<span><b>{len(tree)}</b> countries</span>'
        f'<span><b>{total_groups}</b> project groups</span></div>',
        unsafe_allow_html=True,
    )

    for country in sorted(tree.keys()):
        groups = tree[country]
        country_count = sum(len(v) for v in groups.values())
        st.markdown(
            f'<div class="pm-country-banner">'
            f'<div class="pm-title">{country}</div>'
            f'<div class="pm-sub">{country_count} variants / {len(groups)} project groups</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

        for group_name in sorted(groups.keys()):
            items = groups[group_name]
            items.sort(key=lambda x: x[1]["name"])

            ptype = items[0][1]["inputs"].basic.project_type
            tag_cls = "pm-tag-onshore" if ptype == "onshore" else "pm-tag-offshore"
            type_label = "Onshore" if ptype == "onshore" else "Offshore"

            best_irr_pid = max(items, key=lambda x: x[1]["result"].project_irr_after_tax)[0]
            best_lcoe_pid = min(items, key=lambda x: x[1]["result"].lcoe)[0]

            st.markdown(
                f'<div class="pm-group-bar">'
                f'<span class="pm-gname">{group_name}</span>'
                f'<span class="pm-tag {tag_cls}">{type_label}</span>'
                f'<span class="pm-tag pm-tag-count">{len(items)} variants</span>'
                f'</div>',
                unsafe_allow_html=True,
            )

            # 汇总对比表
            rows = []
            for pid, proj in items:
                inp = proj["inputs"]
                res = proj["result"]
                rows.append({
                    "Variant": proj["name"],
                    "MW": f"{inp.capacity_mw:.0f}",
                    "USD/kW": f"{inp.investment.resolve_unit_investment():,.0f}",
                    "P90 (h)": f"{inp.basic.full_load_hours:.0f}",
                    "Tariff": f"{inp.tax_financial.tariff_with_tax:.4f}",
                    "IRR pre-tax": f"{res.project_irr_before_tax:.2%}",
                    "IRR post-tax": f"{res.project_irr_after_tax:.2%}",
                    "Equity IRR": f"{res.equity_irr:.2%}",
                    "LCOE": f"{res.lcoe:.5f}",
                    "NPV (M$)": f"{res.project_npv_after_tax / 1e6:,.1f}",
                    "Payback (yr)": f"{res.payback_after_tax:.1f}",
                })
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

            # 对比图表 (方案 >= 2)
            if len(items) >= 2:
                names = [p[1]["name"].replace("Laguna-", "").replace("Laguna ", "") for p in items]
                irrs = [p[1]["result"].project_irr_after_tax * 100 for p in items]
                lcoes = [p[1]["result"].lcoe for p in items]
                invests = [p[1]["inputs"].investment.resolve_unit_investment() for p in items]

                col_c1, col_c2 = st.columns(2)
                with col_c1:
                    fig = go.Figure()
                    colors = [("#548235" if v >= 10 else "#BF8F00" if v >= 6 else "#C00000") for v in irrs]
                    fig.add_trace(go.Bar(
                        x=names, y=irrs, marker_color=colors,
                        text=[f"{v:.1f}%" for v in irrs], textposition="outside",
                    ))
                    fig.update_layout(
                        title="IRR post-tax (%)", height=300,
                        margin=dict(t=40, b=60, l=40, r=20),
                        yaxis_title="%", xaxis_tickangle=-35, font=dict(size=11),
                    )
                    st.plotly_chart(fig, use_container_width=True)
                with col_c2:
                    fig = go.Figure()
                    fig.add_trace(go.Bar(
                        x=names, y=invests, marker_color="#2E75B6", name="Investment",
                        text=[f"{v:,.0f}" for v in invests], textposition="outside",
                    ))
                    fig.add_trace(go.Scatter(
                        x=names, y=[l * 1e6 for l in lcoes], yaxis="y2",
                        name="LCOE", line=dict(color="#BF8F00", width=2.5),
                        marker=dict(size=8), mode="lines+markers+text",
                        text=[f"{l:.4f}" for l in lcoes], textposition="top center",
                    ))
                    fig.update_layout(
                        title="Investment & LCOE", height=300,
                        margin=dict(t=40, b=60, l=40, r=60),
                        yaxis=dict(title="USD/kW"),
                        yaxis2=dict(title="LCOE", overlaying="y", side="right", showgrid=False),
                        xaxis_tickangle=-35, font=dict(size=11), showlegend=False,
                    )
                    st.plotly_chart(fig, use_container_width=True)

            # 每个方案一张卡片 (2列布局)
            COLS_PER_ROW = 2
            for row_start in range(0, len(items), COLS_PER_ROW):
                row_items = items[row_start:row_start + COLS_PER_ROW]
                cols = st.columns(COLS_PER_ROW)
                for col_idx, (pid, proj) in enumerate(row_items):
                    with cols[col_idx]:
                        _render_project_card(
                            pid, proj,
                            best_irr=(pid == best_irr_pid and len(items) > 1),
                            best_lcoe=(pid == best_lcoe_pid and pid != best_irr_pid and len(items) > 1),
                        )

            st.markdown("")


# ════════════════════════════════════════════════════════════════════════════
# 主入口
# ════════════════════════════════════════════════════════════════════════════

def main():
    st.title("🌬️ 风电项目经济性评估")
    st.caption("Wind Farm Financial Assessment Dashboard | 多项目管理 & 对比 | 货币: USD")

    page = st.tabs(["📈 项目评估", "📊 项目对比", "🗂️ 项目管理"])

    # ═══════════════════════════════════════════════════════
    # Tab 1: 项目评估（含侧边栏全分项编辑）
    # ═══════════════════════════════════════════════════════
    with page[0]:
        # 模式切换
        input_mode = st.sidebar.radio(
            "Input Mode", ["Quick (10 params)", "Detailed (full)"],
            horizontal=True, key="input_mode",
            help="Quick: only TSI/BOP/P90/tariff needed. Detailed: edit all sub-items.",
        )
        st.sidebar.markdown("---")

        if input_mode.startswith("Quick"):
            inputs = sidebar_inputs_quick()
        else:
            inputs = sidebar_inputs()
        result = calculate(inputs)

        # 保存按钮
        col_save, col_info = st.columns([1, 3])
        with col_save:
            if st.button("💾 保存当前项目", type="primary"):
                pid = save_project(inputs.basic.project_name, inputs, result)
                st.success(f"项目已保存! (ID: {pid})")
        with col_info:
            st.caption(f"当前已保存 {len(st.session_state.projects)} 个项目")

        st.markdown("---")
        render_full_assessment(inputs, result, key_prefix="main")

        st.markdown("---")
        st.markdown("### 🔄 反算工具")
        reverse_calc_panel(inputs)

    # ═══════════════════════════════════════════════════════
    # Tab 2: 项目对比
    # ═══════════════════════════════════════════════════════
    with page[1]:
        comparison_page()

    # ═══════════════════════════════════════════════════════
    # Tab 3: 项目管理
    # ═══════════════════════════════════════════════════════
    with page[2]:
        st.header("🗂️ 已保存的项目")

        if not st.session_state.projects:
            st.info("暂无已保存的项目。请在「项目评估」页面编辑参数后点击「保存当前项目」。")
        elif "detail_pid" in st.session_state and st.session_state.detail_pid in st.session_state.projects:
            dpid = st.session_state.detail_pid
            dproj = st.session_state.projects[dpid]
            dinp = dproj["inputs"]
            dres = dproj["result"]

            if st.button("⬅️ 返回项目列表", key="back_to_list"):
                del st.session_state.detail_pid
                st.rerun()

            st.markdown(f"## 📄 {dproj['name']}")
            st.caption(f"保存于 {dproj['saved_at']}")
            render_full_assessment(dinp, dres, key_prefix=f"detail_{dpid}")
        else:
            _render_project_list()


if __name__ == "__main__":
    main()
