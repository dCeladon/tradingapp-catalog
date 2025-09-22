# streamlit_app.py
import json
import math
import streamlit as st
from typing import Any, Dict
from supabase_client import fetch_backtests

# Inizializza la pagina se serve
if "page" not in st.session_state:
    st.session_state.page = 1

def render_pagination_controls(total_pages: int, key_prefix: str = "top"):
    """
    Disegna pulsanti Indietro/Avanti sincronizzati usando st.session_state.page.
    Richiama st.rerun() dopo un click per aggiornare subito la pagina.

    Args:
        total_pages: numero totale di pagine (>=1)
        key_prefix: 'top' o 'bottom' per evitare collisioni di chiavi streamlit
    """
    page = int(st.session_state.page)
    page = max(1, min(page, max(1, total_pages)))  # clamp di sicurezza
    st.session_state.page = page

    col_prev, col_info, col_next = st.columns([1, 2, 1])

    with col_prev:
        prev_clicked = st.button("◀ Indietro",
                                 key=f"{key_prefix}_prev",
                                 disabled=(page <= 1),
                                 width="stretch")
    with col_info:
        st.markdown(
            f"<div style='text-align:center; font-weight:600;'>Pagina {page} / {max(1,total_pages)}</div>",
            unsafe_allow_html=True
        )
    with col_next:
        next_clicked = st.button("Avanti ▶",
                                 key=f"{key_prefix}_next",
                                 disabled=(page >= max(1, total_pages)),
                                 width="stretch")

    if prev_clicked:
        st.session_state.page = max(1, page - 1)
        st.rerun()
    if next_clicked:
        st.session_state.page = min(max(1, total_pages), page + 1)
        st.rerun()

def _get_in(d: Dict[str, Any], *keys, default=None):
    """Safe get annidato: _get_in(perf, 'returns','net_profit_eur', default='—')."""
    cur = d
    for k in keys:
        if not isinstance(cur, dict) or k not in cur:
            return default
        cur = cur[k]
    return cur

def parse_all_metrics(perf):
    """
    Estrae: Net Profit (EUR), Profit Factor, Max DD (EUR), Win rate (%), N. trade.
    Supporta:
      - JSON annidato (returns -> net_profit_eur, ecc.)
      - JSON piatto con chiavi "returns.net_profit_eur" dentro perf['metrics']
      - Riepilogo in perf['summary'] (win_rate_pct, profit_factor, ecc.)
    """
    # ---- normalizza a dict
    if perf is None:
        return ("—", "—", "—", "—", "—")
    if isinstance(perf, str):
        try:
            perf = json.loads(perf)
        except Exception:
            return ("—", "—", "—", "—", "—")
    if not isinstance(perf, dict):
        return ("—", "—", "—", "—", "—")

    # helpers
    def flat_get(d, key):
        """Cerca key in d, poi in d.get('metrics'), poi in d.get('summary')."""
        if isinstance(d, dict) and key in d:
            return d[key]
        m = d.get("metrics") if isinstance(d.get("metrics"), dict) else {}
        if key in m:
            return m[key]
        s = d.get("summary") if isinstance(d.get("summary"), dict) else {}
        if key in s:
            return s[key]
        return None

    def fmt_num(x, nd=2):
        if isinstance(x, (int, float)):
            return f"{x:,.{nd}f}".replace(",", " ").replace(".", ",")
        return "—"

    def fmt_int(x):
        if isinstance(x, (int, float)):
            return f"{int(x)}"
        return "—"

    def fmt_pct(x):
        if isinstance(x, (int, float)):
            # se è frazione (0–1) → %; se è già % la lasciamo così
            if 0 <= x <= 1:
                x *= 100.0
            return f"{x:.1f}%"
        return "—"

    # ---- estrazione con tutti i fallback utili
    net_profit = (
        _get_in(perf, "returns", "net_profit_eur")
        or flat_get(perf, "returns.net_profit_eur")
        or flat_get(perf, "net_profit_eur")
    )
    profit_factor = (
        _get_in(perf, "returns", "profit_factor")
        or flat_get(perf, "returns.profit_factor")
        or flat_get(perf, "profit_factor")
    )
    max_dd = (
        _get_in(perf, "risk", "max_drawdown")
        or _get_in(perf, "risk", "max_drawdown_eur")
        or flat_get(perf, "risk.max_drawdown_eur")
        or flat_get(perf, "max_drawdown_eur")
    )
    n_trades = (
        _get_in(perf, "trades", "count")
        or flat_get(perf, "trades.count")
        or flat_get(perf, "count")
    )
    win_rate = (
        _get_in(perf, "trades", "win_rate")
        or _get_in(perf, "trades", "win_rate_pct")
        or flat_get(perf, "trades.win_rate_pct")
        or flat_get(perf, "win_rate_pct")
    )

    # ---- formato finale
    return (
        fmt_num(net_profit, nd=2),    # Net Profit (EUR)
        fmt_num(profit_factor, nd=2), # Profit Factor
        fmt_num(max_dd, nd=2),        # Max DD (EUR)
        fmt_pct(win_rate),            # Win rate (%)
        fmt_int(n_trades)             # N. trade
    )

# ----------------- UI -----------------
st.set_page_config(page_title="TradingApp — Catalogo Equity", layout="wide")
st.title("TradingApp — Catalogo Equity")
st.caption("Visualizza anteprime di backtest pubblicati. (Nessuna promessa di rendimento)")

# ========== NOVITÀ: Banner breve sempre visibile ==========
st.warning(
    "Contenuti informativi/educativi. Non sono consulenza o sollecitazione. "
    "Le performance passate/simulate non garantiscono risultati futuri.",
    icon="⚠️",
)

# ========== NOVITÀ: Expander con disclaimer esteso ==========
with st.expander("Informazioni importanti e disclaimer legale", expanded=False):
    st.markdown("""
**Informazioni importanti e disclaimer legale**  
I contenuti presenti in questa applicazione hanno **finalità esclusivamente informative ed educative**. **Non** costituiscono:
- consulenza in materia di investimenti, raccomandazioni personalizzate o ricerca in materia di investimenti ai sensi della normativa **MiFID II**;
- offerta, invito o **sollecitazione al pubblico risparmio** né promozione di servizi di investimento;
- gestione di portafogli, ricezione/trasmissione ordini o esecuzione di ordini.

I risultati mostrati derivano da **backtest** su dati storici e possono includere assunzioni (costi, slippage, liquidità, esecuzione, qualità e disponibilità dei dati). Le performance **passate o simulate** non sono indicative di performance future.  
L’utente è responsabile delle proprie decisioni finanziarie; valuta la tua situazione personale e, se necessario, **consulta un intermediario abilitato** o un consulente finanziario indipendente.  
L’autore dell’app e TailorCoding **non sono intermediari autorizzati** e **non offrono** servizi o attività di investimento. Nessuna informazione intende eludere i limiti previsti da **CONSOB** e dalla normativa vigente.  
L’uso dell’app implica l’accettazione di questi termini. Per ulteriori dettagli fai riferimento alle sezioni **Termini d’Uso** e **Privacy/Cookie** del sito principale.
""")

# Modalità mobile/desktop (usa nuova API per query params)
try:
    params = st.query_params
    default_mobile = params.get("mobile", "0") == "1"
except Exception:
    params = st.experimental_get_query_params()
    default_mobile = params.get("mobile", ["0"])[0] == "1"

mobile_mode = st.toggle(
    "Modalità smartphone (1 card per riga)",
    value=default_mobile,
    help="Attiva un layout ottimizzato per schermi piccoli."
)

COLS = 1 if mobile_mode else 3
PAGE_SIZE = 6 if mobile_mode else 12

# -------- Paginazione (TOP) --------
page = st.session_state.get("page", 1)
# In alto non conosciamo ancora il totale; mostriamo almeno la pagina corrente
render_pagination_controls(total_pages=max(1, page), key_prefix="top")

# Calcolo offset dopo eventuali click
page = st.session_state.get("page", 1)
offset = (page - 1) * PAGE_SIZE

# -------- Fetch --------
items = fetch_backtests(limit=PAGE_SIZE, offset=offset)

if not items and page > 1:
    st.info("Fine elenco. Torno alla pagina precedente.")
    st.session_state["page"] = page - 1
    st.rerun()

# -------- Stile / CSS --------
st.markdown("""
<style>
/* Nascondi completamente la sidebar (scritte debug “manifest cols…”) */
[data-testid="stSidebar"] { display: none !important; }
[data-testid="stSidebarNav"] { display: none !important; }
/* Nascondi anche il pulsante-hamburger che la riapre */
[data-testid="collapsedControl"] { display: none !important; }

/* Imposta il contenitore principale: un po’ di margine dall’alto */
.main .block-container { padding-top: 1rem; max-width: 100%; }
</style>
""", unsafe_allow_html=True)

# -------- Render griglia --------
rows = math.ceil(len(items) / COLS) if items else 0
for r in range(rows):
    cols = st.columns(COLS)
    for c in range(COLS):
        i = r * COLS + c
        if i >= len(items):
            continue
        bt = items[i]
        with cols[c]:
            st.markdown(f"### {bt.get('code','')}")
            img_url = bt.get("image_url")
            if img_url:
                st.image(img_url, width="stretch")
            else:
                st.info("Anteprima non disponibile per questo backtest.")

            perf = bt.get("performance_json")
            np_eur, pf, mdd, wr, nt = parse_all_metrics(perf)

            st.write(
                f"**Net Profit (EUR):** {np_eur}  \n"
                f"**Profit Factor:** {pf}  \n"
                f"**Max DD:** {mdd}  \n"
                f"**Win rate:** {wr}  \n"
                f"**N. trade:** {nt}"
            )

            # Azioni
            xlsx = bt.get("excel_url")  # già unito via view
            a, b = st.columns(2) if not mobile_mode else (st.container(), st.container())
            with a:
                st.link_button("Apri Excel", xlsx, width="stretch")
            with b:
                st.link_button(
                    "Contattami",
                    "https://www.tailorcoding.com/contatti-tailor-coding",
                    width="stretch"
                )

# -------- Paginazione (BOTTOM) --------
# Se la pagina corrente ha meno item del PAGE_SIZE, siamo all’ultima
page = st.session_state.get("page", 1)
is_last_page = len(items) < PAGE_SIZE
total_pages_bottom = page if is_last_page else page + 1
render_pagination_controls(total_pages_bottom, key_prefix="bottom")

st.divider()
st.caption("© TailorCoding — Le performance passate non garantiscono risultati futuri.")
