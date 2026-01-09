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

# pares diretos que o Yahoo normalmente suporta
PARES_DIRETOS = {"USD", "EUR", "JPY", "GBP", "CHF", "CAD", "ARS", "CNY"}  # CNY às vezes funciona direto

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

    # se não houver par direto, usa cross via USD: (USD/moeda) e (USD/BRL)
    usd_moeda = yahoo_last_close(f"USD{moeda}=X")  # preço da moeda por USD
    usd_brl = yahoo_last_close("USDBRL=X")         # BRL por USD
    if usd_moeda is not None and usd_brl is not None and usd_brl != 0:
        # moeda/BRL = (moeda/USD) / (BRL/USD)
        return usd_moeda / usd_brl

    return None

def variacao_via_yahoo(moeda):
    # tenta variação do par direto
    direct_ticker = f"{moeda}BRL=X"
    v_direct = yahoo_pct_change_last(direct_ticker)
    if v_direct is not None:
        return v_direct

    # se não houver, usa variação via USD: % (USD/moeda) - % (USD/BRL)
    pct_usd_moeda = yahoo_pct_change_last(f"USD{moeda}=X")
    pct_usd_brl = yahoo_pct_change_last("USDBRL=X")
    if pct_usd_moeda is not None and pct_usd_brl is not None:
        # para razão A/B, aprox var% ≈ varA% - varB%
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
        chave = f"{moeda}BRL"
        if chave in data:
            info = data[chave]
            # usa bid (compra) como valor principal
            valor = float(info.get("bid", "nan"))
            variacao = float(info.get("varBid", 0.0))
        else:
            valor, variacao = float("nan"), 0.0
    except Exception:
        valor, variacao = float("nan"), 0.0

    with cols[i % 5]:
        if not (valor != valor):  # checa se não é NaN
            st.metric(label=f"{nome} ({moeda}/BRL)", value=f"R$ {valor:.3f}", delta=f"{variacao:+.3f}")
        else:
            st.metric(label=f"{nome} ({moeda}/BRL)", value="⚠️ Sem dados", delta="0.0")
            
# ---------------- Índices (mini-charts com Altair e tema escuro) ----------------
st.header("📈 Índices - Visão Rápida")

indices = {
    "Ibovespa": "^BVSP",
    "Nasdaq": "^IXIC",
    "S&P 500": "^GSPC",
    "Dow Jones": "^DJI"
}

cols = st.columns(len(indices))

# Estilo Altair para fundo escuro
import altair as alt
alt.themes.register('dark_theme', lambda: {
    'config': {
        'background': '#121212',
        'view': {'stroke': 'transparent'},
        'axis': {
            'domainColor': '#888888',
            'gridColor': '#2a2a2a',
            'labelColor': '#d9d9d9',
            'titleColor': '#d9d9d9',
            'tickColor': '#888888'
        },
        'legend': {'labelColor': '#d9d9d9', 'titleColor': '#d9d9d9'}
    }
})
alt.themes.enable('dark_theme')

for i, (nome, ticker) in enumerate(indices.items()):
    try:
        df = yf.Ticker(ticker).history(period="1mo")

        # Se não houver dados, mostra aviso
        if df is None or df.empty:
            with cols[i]:
                st.subheader(nome)
                st.write("⚠️ Sem dados disponíveis no momento.")
            continue

        df_view = df.reset_index()
        ultimo = df_view["Close"].iloc[-1]
        variacao = (df_view["Close"].iloc[-1] - df_view["Open"].iloc[-1]) / df_view["Open"].iloc[-1] * 100

        with cols[i]:
            st.subheader(nome)
            st.metric(label="Último valor", value=f"{ultimo:.2f}", delta=f"{variacao:+.2f}%")

            chart = alt.Chart(df_view).mark_line(color="#66b3ff").encode(
                x=alt.X('Date:T', title=''),
                y=alt.Y('Close:Q', title='')
            ).properties(
                width='container',
                height=150,
                title=""  # string vazia para não dar erro
            )

            st.altair_chart(chart, use_container_width=True)

    except Exception as e:
        with cols[i]:
            st.subheader(nome)
            st.write(f"Erro ao carregar dados: {e}")


# ---------------- Ações B3 ----------------
st.header("📊 Top 5 Altas e Baixas (B3)")

tickers_b3 = ["PETR4.SA","VALE3.SA","ITUB4.SA","BBDC4.SA","ABEV3.SA","BBAS3.SA","MGLU3.SA","LREN3.SA","SUZB3.SA","GGBR4.SA"]

dados = {}
for t in tickers_b3:
    df = yf.Ticker(t).history(period="5d")
    if not df.empty:
        ultimo = df.iloc[-1]
        variacao = (ultimo["Close"] - ultimo["Open"]) / ultimo["Open"] * 100
        dados[t] = variacao

ordenado = sorted(dados.items(), key=lambda x: x[1], reverse=True)
altas = ordenado[:5]
baixas = ordenado[-5:]

col1, col2 = st.columns(2)

with col1:
    st.subheader("📈 Maiores Altas")
    df_altas = pd.DataFrame(altas, columns=["Ação", "Variação (%)"])
    st.table(df_altas.style.format({"Variação (%)": "{:+.2f}"}))

with col2:
    st.subheader("📉 Maiores Baixas")
    df_baixas = pd.DataFrame(baixas, columns=["Ação", "Variação (%)"])
    st.table(df_baixas.style.format({"Variação (%)": "{:+.2f}"}))


