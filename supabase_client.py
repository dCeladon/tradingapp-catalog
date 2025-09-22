from typing import List, Dict, Any, Tuple
import os
import streamlit as st
from supabase import create_client, Client


def _read_creds() -> tuple[str, str]:
    """
    Legge le credenziali da:
    1) st.secrets["SUPABASE_URL"] / st.secrets["SUPABASE_ANON_KEY"]
    2) st.secrets["supabase"]["url"] / st.secrets["supabase"]["anon_key"]
    3) variabili d'ambiente SUPABASE_URL / SUPABASE_ANON_KEY
    """
    url = None
    key = None

    # 1) flat in secrets.toml
    try:
        url = st.secrets.get("SUPABASE_URL")
        key = st.secrets.get("SUPABASE_ANON_KEY")
    except Exception:
        pass

    # 2) sezione [supabase] in secrets.toml
    if not url or not key:
        try:
            sub = st.secrets.get("supabase", {})
            if isinstance(sub, dict):
                url = url or sub.get("url")
                key = key or sub.get("anon_key")
        except Exception:
            pass

    # 3) variabili d’ambiente (fallback)
    url = url or os.environ.get("SUPABASE_URL")
    key = key or os.environ.get("SUPABASE_ANON_KEY")

    if not url or not key:
        raise RuntimeError("Mancano SUPABASE_URL / SUPABASE_ANON_KEY nei secrets.toml o env var.")

    return url, key


@st.cache_resource
def get_client() -> Client:
    url, key = _read_creds()
    return create_client(url, key)


def fetch_backtests(limit: int = 12, offset: int = 0) -> List[Dict[str, Any]]:
    """
    Legge SOLO i pubblicati da `backtests_manifest` (code, png_url, xlsx_url)
    e arricchisce con `performance_json` leggendo da `backtests` tramite code.
    """
    sb = get_client()

    # 1) Manifest = elenco pubblicati + asset pubblici
    mres = (
        sb.table("backtests_manifest")
        .select("code,png_url,xlsx_url")
        .range(offset, offset + limit - 1)
        .execute()
    )
    manifest = mres.data or []

    if not manifest:
        return []

    # 2) Completa con performance_json dalla tabella backtests, via code
    codes = [row["code"] for row in manifest if "code" in row and row["code"]]
    pres = (
        sb.table("backtests")
        .select("code,performance_json")
        .in_("code", codes)
        .execute()
    )
    perf_rows = pres.data or []
    perf_map = {r["code"]: r.get("performance_json") for r in perf_rows}

    # 3) Merge finale nel formato atteso dalla UI
    items: List[Dict[str, Any]] = []
    for r in manifest:
        code = r.get("code")
        items.append({
            "code": code,
            "image_url": r.get("png_url"),
            "excel_url": r.get("xlsx_url"),
            "performance_json": perf_map.get(code),  # può essere None se mancante
        })

    return items


def fetch_backtests_and_count(limit: int = 12, offset: int = 0) -> Tuple[List[Dict[str, Any]], int]:
    """
    Variante di fetch_backtests che restituisce anche il conteggio totale.
    Usa count="exact" su backtests_manifest.
    """
    sb = get_client()

    # 1) Manifest con count
    mres = (
        sb.table("backtests_manifest")
        .select("code,png_url,xlsx_url", count="exact")
        .range(offset, offset + limit - 1)
        .execute()
    )
    manifest = mres.data or []
    total = mres.count or 0

    if not manifest:
        return [], total

    # 2) Performance_json
    codes = [row["code"] for row in manifest if "code" in row and row["code"]]
    pres = (
        sb.table("backtests")
        .select("code,performance_json")
        .in_("code", codes)
        .execute()
    )
    perf_rows = pres.data or []
    perf_map = {r["code"]: r.get("performance_json") for r in perf_rows}

    # 3) Merge finale
    items: List[Dict[str, Any]] = []
    for r in manifest:
        code = r.get("code")
        items.append({
            "code": code,
            "image_url": r.get("png_url"),
            "excel_url": r.get("xlsx_url"),
            "performance_json": perf_map.get(code),
        })

    return items, total
