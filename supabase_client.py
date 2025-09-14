# supabase_client.py
from typing import List, Dict, Any
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
    Legge dalla view/tabella pubblica (adatta il nome se necessario):
      code, image_url, performance_json, excel_url
    """
    sb = get_client()
    res = (
        sb.table("backtests_manifest")          # <— qui
        .select("code,image_url,performance_json,excel_url")
        .range(offset, offset + limit - 1)
        .execute()
    )
    return res.data or []
