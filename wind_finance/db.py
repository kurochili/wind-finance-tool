"""
wind_finance.db
===============
Supabase 数据库持久化模块 — 通过 REST API 读写项目数据，
所有用户共享同一份项目库。
"""

from __future__ import annotations

import json
import logging
import urllib.request
import urllib.error
from dataclasses import asdict
from typing import Any, Dict, List, Optional, Tuple

from .models import (
    BasicInfo,
    BOPCost,
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

log = logging.getLogger(__name__)

_SUPABASE_URL: str = ""
_SUPABASE_KEY: str = ""


def init(url: str, key: str):
    global _SUPABASE_URL, _SUPABASE_KEY
    _SUPABASE_URL = url.rstrip("/")
    _SUPABASE_KEY = key


def _request(method: str, path: str, data: Any = None,
             params: Optional[Dict[str, str]] = None) -> Any:
    """Low-level Supabase REST API call."""
    url = f"{_SUPABASE_URL}/rest/v1/{path}"
    if params:
        qs = "&".join(f"{k}={v}" for k, v in params.items())
        url = f"{url}?{qs}"

    headers = {
        "apikey": _SUPABASE_KEY,
        "Authorization": f"Bearer {_SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=representation",
    }

    body = json.dumps(data).encode("utf-8") if data is not None else None
    req = urllib.request.Request(url, data=body, headers=headers, method=method)

    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            raw = resp.read().decode("utf-8")
            return json.loads(raw) if raw else []
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8", errors="replace")[:500]
        log.error("Supabase %s %s → HTTP %s: %s", method, path, e.code, err_body)
        raise
    except Exception as e:
        log.error("Supabase request failed: %s", e)
        raise


# ── 序列化 / 反序列化 ─────────────────────────────────────────────────────

def inputs_to_dict(inputs: WindFarmFinancialInputs) -> dict:
    """将 WindFarmFinancialInputs 转为可 JSON 序列化的 dict。"""
    d = asdict(inputs)
    return d


def dict_to_inputs(d: dict) -> WindFarmFinancialInputs:
    """从 dict 还原 WindFarmFinancialInputs（处理 Tuple / 嵌套 dataclass）。"""

    # --- BasicInfo ---
    bd = dict(d["basic"])
    if bd.get("investment_schedule") is not None:
        bd["investment_schedule"] = tuple(bd["investment_schedule"])
    basic = BasicInfo(**bd)

    # --- InvestmentData ---
    inv = dict(d["investment"])
    onshore_d = inv.pop("onshore_detail", None)
    offshore_d = inv.pop("offshore_detail", None)

    onshore_obj = OnshoreInvestment(**onshore_d) if onshore_d else None

    offshore_obj = None
    if offshore_d:
        offshore_obj = OffshoreEPCBreakdown(
            oem=OEMCost(**offshore_d["oem"]),
            installation=InstallationCost(**offshore_d["installation"]),
            foundation=FoundationCost(**offshore_d["foundation"]),
            bop=BOPCost(**offshore_d["bop"]),
            num_turbines=offshore_d.get("num_turbines", 0),
            turbine_capacity_mw=offshore_d.get("turbine_capacity_mw", 0.0),
        )
    investment = InvestmentData(**inv, onshore_detail=onshore_obj, offshore_detail=offshore_obj)

    # --- FinancingTerms ---
    fin = dict(d["financing"])
    financing = FinancingTerms(**fin)

    # --- OperationalCost ---
    op = dict(d["operational"])
    w_d = op.pop("warranty", {})
    pw_d = op.pop("post_warranty", {})
    oe_d = op.pop("offshore_extra", None)

    if pw_d.get("maintenance_rates"):
        pw_d["maintenance_rates"] = [tuple(r) for r in pw_d["maintenance_rates"]]

    warranty = WarrantyPeriodCost(**w_d)
    post_warranty = PostWarrantyPeriodCost(**pw_d)
    offshore_extra = OffshoreExtraCost(**oe_d) if oe_d else None

    operational = OperationalCost(
        **op, warranty=warranty, post_warranty=post_warranty, offshore_extra=offshore_extra,
    )

    # --- TaxAndFinancial ---
    tf = dict(d["tax_financial"])
    if tf.get("income_tax_holiday") is not None:
        tf["income_tax_holiday"] = tuple(tf["income_tax_holiday"])
    tax_financial = TaxAndFinancial(**tf)

    return WindFarmFinancialInputs(
        basic=basic,
        investment=investment,
        financing=financing,
        operational=operational,
        tax_financial=tax_financial,
    )


# ── CRUD ──────────────────────────────────────────────────────────────────

def db_load_all() -> Dict[str, dict]:
    """从 Supabase 加载所有项目，返回 {pid: {...}} 格式。"""
    from .calculator import calculate

    rows = _request("GET", "projects", params={"order": "saved_at.asc"})
    projects: Dict[str, dict] = {}
    for row in rows:
        try:
            inputs = dict_to_inputs(row["inputs_json"])
            result = calculate(inputs)
            projects[row["id"]] = {
                "name": row["name"],
                "group": row.get("group_name", ""),
                "country": row.get("country", ""),
                "inputs": inputs,
                "result": result,
                "saved_at": row.get("saved_at", ""),
            }
        except Exception as e:
            log.warning("Failed to load project %s: %s", row["id"], e)
    return projects


def db_save(pid: str, name: str, group: str, country: str,
            inputs: WindFarmFinancialInputs, saved_at: str) -> None:
    """保存或更新一个项目到 Supabase。"""
    payload = {
        "id": pid,
        "name": name,
        "group_name": group,
        "country": country,
        "inputs_json": inputs_to_dict(inputs),
        "saved_at": saved_at,
    }
    headers_extra = "resolution=merge-duplicates"
    url = f"{_SUPABASE_URL}/rest/v1/projects"
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=body, method="POST", headers={
        "apikey": _SUPABASE_KEY,
        "Authorization": f"Bearer {_SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": f"return=representation,{headers_extra}",
    })
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            resp.read()
    except urllib.error.HTTPError as e:
        log.error("db_save failed: HTTP %s %s", e.code, e.read().decode()[:300])
        raise


def db_delete(pid: str) -> None:
    """从 Supabase 删除一个项目。"""
    _request("DELETE", f"projects?id=eq.{pid}")


def db_available() -> bool:
    """检查 Supabase 是否已配置且可用。"""
    if not _SUPABASE_URL or not _SUPABASE_KEY:
        return False
    try:
        _request("GET", "projects", params={"limit": "1"})
        return True
    except Exception:
        return False
