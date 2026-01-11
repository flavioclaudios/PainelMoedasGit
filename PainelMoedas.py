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

# Tema escuro via CSS inline
st.markdown(
    """
    <style>
    .stApp, body { background-color: #000000 !important; color: #e0e0e0 !important; }
    h1, h2, h3, h4 { color: #f2f2f2 !important; }
    div[data-testid="stMetric"] {
        background-color: #1a1a1a !important;
        border-radius: 10px !important;
        padding: 10px !important;
        border: 1px solid #2a2a2a !important;
    }
    div[data-testid="stMetric"] label { color: #e0e0e0 !important; }
    div[data-testid="stMetricValue"] { color: #f2f2f2 !important; }
    div[data-testid="stMetricDelta"] { color: #f2f2f2 !important; }
    table { color: #e0e0e0 !important; background-color: #1a1a1a !important; }
    table th { color: #ffffff !important; background-color: #2a2a2a !important; }
    table td { color: #e0e0e0 !important; }
    </style>
    """,
    unsafe_allow_html=True
)

# ---------------- Moedas ----------------
st.header("💱 Moedas")

# Dicionário com código da moeda, código da bandeira e nome
moedas = {
    "USD": ("us", "Dólar Americano"),
    "EUR": ("eu", "Euro"),
    "JPY": ("jp", "Iene Japonês"),
    "GBP": ("gb", "Libra Esterlina"),
    "CHF": ("ch", "Franco Suíço"),
    "CAD": ("ca", "Dólar Canadense"),
    "CNY": ("cn", "Yuan Chinês"),
    "COP": ("co", "Peso Colombiano"),
    "ARS": ("ar", "Peso Argentino"),
    "CLP": ("cl", "Peso Chileno")
}

# Último fechamento via Yahoo
@st.cache_data(ttl=300)
def yahoo_last_close(ticker: str) -> float | None:
    try:
        hist = yf.download(tickers=ticker, period="5d", interval="1d", progress=False)
        closes = hist["Close"].dropna()
        if not closes.empty:
            return float(closes.iloc[-1])
    except Exception:
        return None
    return None

# Variação percentual via Yahoo
@st.cache_data(ttl=300)
def yahoo_pct_change_last(ticker: str) -> float | None:
    try:
        hist = yf.download(tickers=ticker, period="7d", interval="1d", progress=False)
        closes = hist["Close"].dropna()
        if len(closes) >= 2:
            prev, last = closes.iloc[-2], closes.iloc[-1]
            return float((last - prev) / prev * 100)
    except Exception:
        return None
    return None

# Valor da moeda em BRL
def valor_via_yahoo(moeda: str) -> float | None:
    if moeda == "USD":
        return yahoo_last_close("USDBRL=X")

    direct_ticker = f"{moeda}BRL=X"
    v_direct = yahoo_last_close(direct_ticker)
    if v_direct is not None:
        return v_direct

    usd_moeda = yahoo_last_close(f"USD{moeda}=X")
    usd_brl = yahoo_last_close("USDBRL=X")
    if usd_moeda is not None and usd_brl not in (None, 0):
        return usd_moeda / usd_brl

    return None

# Variação percentual da moeda em BRL
def variacao_via_yahoo(moeda: str) -> float | None:
    if moeda == "USD":
        return yahoo_pct_change_last("USDBRL=X")

    direct_ticker = f"{moeda}BRL=X"
    v_direct = yahoo_pct_change_last(direct_ticker)
    if v_direct is not None:
        return v_direct

    pct_usd_moeda = yahoo_pct_change_last(f"USD{moeda}=X")
    pct_usd_brl = yahoo_pct_change_last("USDBRL=X")
    if pct_usd_moeda is not None and pct_usd_brl is not None:
        return pct_usd_moeda - pct_usd_brl

    return None

# Dados da AwesomeAPI
@st.cache_data(ttl=120)
def awesome_data() -> dict:
    url = "https://economia.awesomeapi.com.br/json/last/" + ",".join(
        [f"{m}-BRL" for m in moedas.keys()]
    )
    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        return r.json()
    except Exception:
        return {}

# Histórico via Yahoo para gráficos
@st.cache_data(ttl=300)
def yahoo_history(ticker: str, days: int = 30) -> pd.DataFrame:
    try:
        hist = yf.download(
            tickers=ticker,
            period=f"{days}d",
            interval="1d",
            progress=False
        )
        closes = hist["Close"].dropna().reset_index()
        closes.rename(columns={"Date": "Data", "Close": "Fechamento"}, inplace=True)

        # garante tipos corretos
        closes["Data"] = pd.to_datetime(closes["Data"], errors="coerce")
        closes["Fechamento"] = pd.to_numeric(closes["Fechamento"], errors="coerce")

        return closes.dropna()
    except Exception:
        return pd.DataFrame()

# Inicializa dados da AwesomeAPI
data = awesome_data()

# Cria colunas para métricas e gráficos
cols = st.columns(5)

# Loop moedas
for i, (moeda, (codigo_pais, nome)) in enumerate(moedas.items()):
    chave = f"{moeda}BRL"
    valor = None
    info = data.get(chave)

    # tenta pegar valor da AwesomeAPI
    if isinstance(info, dict):
        try:
            valor = float(info.get("bid", "nan"))
            if pd.isna(valor):
                valor = None
        except Exception:
            valor = None

    # se não veio da AwesomeAPI, tenta Yahoo
    if valor is None:
        valor = valor_via_yahoo(moeda)

    # variação: tenta Yahoo primeiro
    variacao = variacao_via_yahoo(moeda)
    if variacao is None and isinstance(info, dict):
        try:
            vb = info.get("varBid")
            variacao = float(vb) if vb not in (None, "", "nan") else None
        except Exception:
            variacao = None

    # renderização da métrica + gráfico
    with cols[i % 5]:
        # bandeira
        st.markdown(
    f"""
    <img src="https://flagcdn.com/w40/{codigo_pais}.png"
         style="width:40px;height:25px;object-fit:cover;">
    """,
    unsafe_allow_html=True
)


        if valor is not None:
            casas = f"{valor:.3f}"
            parte_decimal = casas.split(".")[1]
            if parte_decimal.startswith("00"):
                valor_str = f"R$ {valor:.4f}"
            else:
                valor_str = f"R$ {valor:.3f}"

            delta_str = f"{variacao:+.2f}%" if variacao is not None else "0.00%"
            st.metric(label=f"{nome} ({moeda}/BRL)", value=valor_str, delta=delta_str)

            # gráfico histórico
            hist_data = yahoo_history(f"{moeda}BRL=X")
            if not hist_data.empty:
                chart = alt.Chart(hist_data).mark_line(color="steelblue").encode(
                    x=alt.X("Data:T", title="Data"),
                    y=alt.Y("Fechamento:Q", title="Fechamento (R$)"),
                    tooltip=["Data", "Fechamento"]
                ).properties(
                    width=250,
                    height=150,
                    title=f"{nome} ({moeda}/BRL)"
                )
                st.altair_chart(chart, use_container_width=True)
        else:
            st.metric(label=f"{nome} ({moeda}/BRL)", value="❌ Não disponível", delta="0.00%")

# ---------------- Índices ----------------
st.header("📈 Índices - Visão Rápida")

indices = {
    "Ibovespa": "^BVSP",
    "Nasdaq": "^IXIC",
    "S&P 500": "^GSPC",
    "Dow Jones": "^DJI"
}

cols = st.columns(len(indices))

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
            ).properties(width='container', height=150, title="")
            st.altair_chart(chart, use_container_width=True)
    except Exception as e:
        with cols[i]:
            st.subheader(nome)
            st.write(f"Erro ao carregar dados: {e}")

# ---------------- Ações B3 ----------------
st.header("📊 Top 5 Altas e Baixas (B3)")

tickers_b3 = ["PETR4.SA","VALE3.SA","ITUB4.SA","BBDC4.SA","ABEV3.SA",
              "BBAS3.SA","MGLU3.SA","LREN3.SA","SUZB3.SA","GGBR4.SA"]

dados = {}
for t in tickers_b3:
    df = yf.Ticker(t).history(period="5d")
    if not df.empty:
        ultimo = df.iloc[-1]
        variacao = (ultimo["Close"] - ultimo["Open"]) / ultimo["Open"] * 100
        preco = ultimo["Close"]
        volume = ultimo["Volume"]
        dados[t] = {"variacao": variacao, "preco": preco, "volume": volume}

ordenado = sorted(dados.items(), key=lambda x: x[1]["variacao"], reverse=True)
altas = ordenado[:5]
baixas = ordenado[-5:]

col1, col2 = st.columns(2)

with col1:
    st.subheader("📈 Maiores Altas")
    df_altas = pd.DataFrame(
        [(t, d["variacao"], d["preco"], d["volume"]) for t, d in altas],
        columns=["Ação", "Variação (%)", "Preço (R$)", "Volume"]
    )
    st.table(df_altas.style.format({"Variação (%)": "{:+.2f}", "Preço (R$)": "{:.2f}"}))

with col2:
    st.subheader("📉 Maiores Baixas")
    df_baixas = pd.DataFrame(
        [(t, d["variacao"], d["preco"], d["volume"]) for t, d in baixas],
        columns=["Ação", "Variação (%)", "Preço (R$)", "Volume"]
    )
    st.table(df_baixas.style.format({"Variação (%)": "{:+.2f}", "Preço (R$)": "{:.2f}"}))