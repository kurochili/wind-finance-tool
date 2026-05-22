"""
Automatic tariff data fetching with cache and fallback.

Data source hierarchy:
  1. IRENA Renewable Energy Statistics API (annual LCOE / auction prices)
  2. Static data from country_profiles.py (fallback)
  3. User manual overrides (stored in Supabase)
"""
from __future__ import annotations

import json
import time
import urllib.request
from dataclasses import dataclass, field
from typing import Dict, Optional, Tuple

_CACHE: Dict[str, "_CacheEntry"] = {}
_CACHE_TTL = 86400  # 24 hours


@dataclass
class TariffReference:
    """Tariff reference data for a single country + project type."""
    country: str
    project_type: str  # "onshore" | "offshore"
    low: float = 0.0
    high: float = 0.0
    unit: str = "USD/kWh"
    source: str = ""
    year: int = 0
    mechanism: str = ""
    policy_text: str = ""


@dataclass
class _CacheEntry:
    data: Dict[str, TariffReference]
    ts: float = 0.0


# ── IRENA PxWeb API helpers ──

_IRENA_BASE = "https://pxweb.irena.org/api/v1/en/IRENASTAT"
_IRENA_RE_COSTS = f"{_IRENA_BASE}/RE_Costs/LCOEDATA/LCOEDATA.px"

_COUNTRY_ISO = {
    "china": "CHN", "vietnam": "VNM", "philippines": "PHL",
    "australia": "AUS", "japan": "JPN", "south korea": "KOR",
    "taiwan": "TWN", "thailand": "THA", "indonesia": "IDN",
    "malaysia": "MYS", "cambodia": "KHM",
}

_IRENA_TECH_ONSHORE = "Wind onshore"
_IRENA_TECH_OFFSHORE = "Wind offshore"


def _irena_query_body(iso: str) -> str:
    return json.dumps({
        "query": [
            {"code": "Country/area", "selection": {"filter": "item", "values": [iso]}},
            {"code": "Technology", "selection": {"filter": "item", "values": [_IRENA_TECH_ONSHORE, _IRENA_TECH_OFFSHORE]}},
            {"code": "Indicator", "selection": {"filter": "item", "values": ["Weighted average"]}},
        ],
        "response": {"format": "json"},
    })


def _fetch_irena(country_key: str) -> Optional[Dict[str, TariffReference]]:
    iso = _COUNTRY_ISO.get(country_key)
    if not iso:
        return None
    try:
        req = urllib.request.Request(
            _IRENA_RE_COSTS,
            data=_irena_query_body(iso).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            body = json.loads(resp.read().decode())
        result: Dict[str, TariffReference] = {}
        for entry in body.get("data", []):
            keys = entry.get("key", [])
            val = entry.get("values", [None])[0]
            if val is None or val == "..":
                continue
            try:
                lcoe = float(val) / 1000.0  # IRENA reports in USD/MWh
            except (ValueError, TypeError):
                continue
            tech = keys[1] if len(keys) > 1 else ""
            year_str = keys[-1] if keys else ""
            try:
                year = int(year_str)
            except ValueError:
                year = 0
            ptype = "onshore" if "onshore" in tech.lower() else "offshore"
            existing = result.get(ptype)
            if existing is None or year > existing.year:
                result[ptype] = TariffReference(
                    country=country_key, project_type=ptype,
                    low=lcoe * 0.85, high=lcoe * 1.15,
                    source=f"IRENA LCOE {year}", year=year,
                )
        return result if result else None
    except Exception:
        return None


# ── Static fallback from country_profiles ──

def _get_static_tariffs(country_key: str) -> Dict[str, TariffReference]:
    from wind_finance.country_profiles import get_country_profile
    profile = get_country_profile(country_key)
    if not profile:
        return {}
    result: Dict[str, TariffReference] = {}
    lo_on, hi_on = profile.onshore_tariff_range
    if lo_on > 0 or hi_on > 0:
        result["onshore"] = TariffReference(
            country=country_key, project_type="onshore",
            low=lo_on, high=hi_on,
            source="country_profiles (static)",
            mechanism=profile.tariff_mechanism,
            policy_text=profile.onshore_tariff_policy,
        )
    lo_off, hi_off = profile.offshore_tariff_range
    if lo_off > 0 or hi_off > 0:
        result["offshore"] = TariffReference(
            country=country_key, project_type="offshore",
            low=lo_off, high=hi_off,
            source="country_profiles (static)",
            mechanism=profile.tariff_mechanism,
            policy_text=profile.offshore_tariff_policy,
        )
    return result


# ── Public API ──

def get_tariff_references(country: str, force_refresh: bool = False) -> Dict[str, TariffReference]:
    """Return tariff references for a country (keys: 'onshore', 'offshore').

    Tries IRENA first, then falls back to static data from country_profiles.
    Results are cached for 24 hours.
    """
    key = country.lower().strip()
    now = time.time()

    if not force_refresh and key in _CACHE:
        entry = _CACHE[key]
        if now - entry.ts < _CACHE_TTL:
            return entry.data

    data = _fetch_irena(key)
    if not data:
        data = _get_static_tariffs(key)

    # Merge: ensure policy_text from static is always present
    static = _get_static_tariffs(key)
    for ptype, ref in static.items():
        if ptype in data:
            if not data[ptype].policy_text:
                data[ptype].policy_text = ref.policy_text
            if not data[ptype].mechanism:
                data[ptype].mechanism = ref.mechanism
        else:
            data[ptype] = ref

    _CACHE[key] = _CacheEntry(data=data, ts=now)
    return data


def get_tariff_display(country: str, project_type: str) -> Optional[TariffReference]:
    """Get tariff reference for a specific country + project type."""
    refs = get_tariff_references(country)
    return refs.get(project_type)


def get_all_tariff_summary() -> list[dict]:
    """Return a summary table of tariff references for all supported countries."""
    from wind_finance.country_profiles import list_countries
    rows = []
    for name_en, name_cn in list_countries():
        refs = get_tariff_references(name_en)
        on = refs.get("onshore")
        off = refs.get("offshore")
        rows.append({
            "country": name_en,
            "country_cn": name_cn,
            "onshore_low": on.low if on else 0,
            "onshore_high": on.high if on else 0,
            "offshore_low": off.low if off else 0,
            "offshore_high": off.high if off else 0,
            "onshore_source": on.source if on else "",
            "offshore_source": off.source if off else "",
            "mechanism": on.mechanism if on else (off.mechanism if off else ""),
        })
    return rows
