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

url = "https://economia.awesomeapi.com.br/json/last/USD-BRL,EUR-BRL,JPY-BRL,GBP-BRL,CHF-BRL,UYU-BRL,CNY-BRL,COP-BRL,ARS-BRL,CLP-BRL"
data = requests.get(url).json()

moedas = {
    "USD": "Dólar Americano",
    "EUR": "Euro",
    "JPY": "Iene Japonês",
    "GBP": "Libra Esterlina",
    "CHF": "Franco Suíço",
    "UYU": "Peso Uruguaio",
    "CNY": "Yuan Chinês",
    "COP": "Peso Colombiano",
    "ARS": "Peso Argentino",
    "CLP": "Peso Chileno"
}

cols = st.columns(5)
for i, (moeda, nome) in enumerate(moedas.items()):
    try:
        valor = float(data[f"{moeda}BRL"]["bid"])
        variacao = float(data[f"{moeda}BRL"]["varBid"])
    except Exception:
        valor, variacao = float("nan"), 0.0
    with cols[i % 5]:
        st.metric(label=f"{nome} ({moeda}/BRL)", value=f"R$ {valor:.3f}", delta=f"{variacao:+.3f}")

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