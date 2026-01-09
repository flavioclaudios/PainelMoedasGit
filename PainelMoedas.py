import streamlit as st
import requests
import yfinance as yf
import pandas as pd
from streamlit_autorefresh import st_autorefresh
import altair as alt

# Configuração da página
st.set_page_config(page_title="Painel Financeiro", layout="wide")
st.title("📊 Painel Financeiro Interativo")

# Atualização automática a cada 60 segundos
st_autorefresh(interval=60 * 1000, key="refresh")

# Tema escuro via CSS inline (fonte clara e containers escuros)
st.markdown(
    """
    <style>
    /* Fundo geral */
    .stApp, body {
        background-color: #000000 !important;
        color: #e0e0e0 !important;
    }

    /* Títulos */
    h1, h2, h3, h4 {
        color: #f2f2f2 !important;
    }

    /* Métricas (cards) */
    div[data-testid="stMetric"] {
        background-color: #1a1a1a !important;
        border-radius: 10px !important;
        padding: 10px !important;
        border: 1px solid #2a2a2a !important;
    }

    /* Label da métrica (nome da moeda e "Último valor") */
    div[data-testid="stMetric"] label {
        color: #e0e0e0 !important;   /* força tom claro */
    }

    /* Valor principal */
    div[data-testid="stMetricValue"] {
        color: #f2f2f2 !important;
    }

    /* Delta (variação) */
    div[data-testid="stMetricDelta"] {
        color: #f2f2f2 !important;
    }

    /* Tabelas */
    table {
        color: #e0e0e0 !important;
        background-color: #1a1a1a !important;
    }
    table th {
        color: #ffffff !important;
        background-color: #2a2a2a !important;
    }
    table td {
        color: #e0e0e0 !important;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# ---------------- Moedas ----------------
st.header("💱 Moedas")

moedas = {
    "USD": "Dólar Americano",
    "EUR": "Euro",
    "JPY": "Iene Japonês",
    "GBP": "Libra Esterlina",
    "CHF": "Franco Suíço",
    "CAD": "Dólar Canadense",
    "CNY": "Yuan Chinês",
    "COP": "Peso Colombiano",
    "ARS": "Peso Argentino",
    "CLP": "Peso Chileno"
}

@st.cache_data(ttl=300)
def yahoo_last_close(ticker):
    try:
        hist = yf.download(tickers=ticker, period="5d", interval="1d", progress=False)
        closes = hist["Close"].dropna()
        if len(closes) >= 1:
            return float(closes.iloc[-1])
    except Exception:
        pass
    return None

@st.cache_data(ttl=300)
def yahoo_pct_change_last(ticker):
    try:
        hist = yf.download(tickers=ticker, period="7d", interval="1d", progress=False)
        closes = hist["Close"].dropna()
        if len(closes) >= 2:
            prev, last = closes.iloc[-2], closes.iloc[-1]
            return float((last - prev) / prev * 100)
    except Exception:
        pass
    return None

def valor_via_yahoo(moeda):
    # tenta par direto moeda/BRL
    direct_ticker = f"{moeda}BRL=X"
    v_direct = yahoo_last_close(direct_ticker)
    if v_direct is not None:
        return v_direct

    # se não houver par direto, usa cross via USD
    usd_moeda = yahoo_last_close(f"USD{moeda}=X")
    usd_brl = yahoo_last_close("USDBRL=X")
    if usd_moeda is not None and usd_brl is not None and usd_brl != 0:
        return usd_moeda / usd_brl

    return None

def variacao_via_yahoo(moeda):
    # tenta variação do par direto
    direct_ticker = f"{moeda}BRL=X"
    v_direct = yahoo_pct_change_last(direct_ticker)
    if v_direct is not None:
        return v_direct

    # se não houver, usa variação via USD
    pct_usd_moeda = yahoo_pct_change_last(f"USD{moeda}=X")
    pct_usd_brl = yahoo_pct_change_last("USDBRL=X")
    if pct_usd_moeda is not None and pct_usd_brl is not None:
        return pct_usd_moeda - pct_usd_brl

    return None

@st.cache_data(ttl=120)
def awesome_data():
    url = "https://economia.awesomeapi.com.br/json/last/" + ",".join(
        [f"{m}-BRL" for m in moedas.keys()]
    )
    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        return r.json()
    except Exception:
        return {}

data = awesome_data()
cols = st.columns(5)

for i, (moeda, nome) in enumerate(moedas.items()):
    # valor: tenta AwesomeAPI, senão Yahoo
    chave = f"{moeda}BRL"
    valor = None
    info = data.get(chave)
    if isinstance(info, dict):
        try:
            valor = float(info.get("bid", "nan"))
            if pd.isna(valor):
                valor = None
        except Exception:
            valor = None
    if valor is None:
        valor = valor_via_yahoo(moeda)

    # variação: sempre tenta via Yahoo; se falhar e houver varBid na Awesome, usa
    variacao = variacao_via_yahoo(moeda)
    if variacao is None and isinstance(info, dict):
        try:
            vb = info.get("varBid")
            variacao = float(vb) if vb not in (None, "", "nan") else None
        except Exception:
            variacao = None

    with cols[i % 5]:
        if valor is not None:
            delta_str = f"{variacao:+.2f}%" if variacao is not None else "0.00%"
            st.metric(label=f"{nome} ({moeda}/BRL)", value=f"R$ {valor:.3f}", delta=delta_str)
        else:
            st.metric(label=f"{nome} ({moeda}/BRL)", value="❌ Não disponível", delta="0.00%")


