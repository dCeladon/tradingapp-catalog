# -*- coding: utf-8 -*-
"""
Created on Mon Aug 25 16:22:34 2025

@author: dinoc
"""

# supabase_client.py
from supabase import create_client, Client
import os

def get_client() -> Client:
    # prova prima dai secrets di Streamlit
    try:
        import streamlit as st
        url = st.secrets["SUPABASE_URL"]
        key = st.secrets["SUPABASE_ANON_KEY"]
    except Exception:
        # fallback su variabili d'ambiente
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_ANON_KEY")

    if not url or not key:
        raise RuntimeError("Mancano SUPABASE_URL / SUPABASE_ANON_KEY nei secrets.toml o env var.")
    return create_client(url, key)

def count_published_backtests() -> int:
    sb = get_client()
    resp = (
        sb.table("backtests")
        .select("id", count="exact")   # prende solo il conteggio
        .eq("published", True)
        .limit(1)
        .execute()
    )
    return int(resp.count or 0)

def fetch_backtests(limit: int = 12, offset: int = 0):
    sb = get_client()
    resp = (
        sb.table("v_backtests_catalog")
        .select("code, symbol, image_url, excel_url, performance_json, created_at")
        .order("created_at", desc=True)
        .range(offset, offset + limit - 1)
        .execute()
    )
    return resp.data or []
