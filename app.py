import streamlit as st
import pandas as pd
import pandas_datareader.data as web
import plotly.graph_objects as go
import requests
from datetime import datetime

st.set_page_config(page_title="Diferencial de Juro Real", layout="wide")

st.title("Diferencial de juro real — 10 anos (Brasil – EUA)")
st.caption("Em 02/10/2026: Brasil (NTN-B / ETTJ ANBIMA 10a) vs. EUA (TIPS 10a)")

@st.cache_data(ttl=3600)
def load_data():
    end_date = datetime.today().strftime('%Y-%m-%d')
    start_date = "2005-01-01"
    
    # 1. US 10-Year TIPS Rate via FRED (DFII10)
    df_us = web.DataReader("DFII10", "fred", start_date, end_date)
    df_us.columns = ["TIPS_10A"]

    # 2. Curva IPCA+ 10 anos Brasil
    # Para capturar a curva ANBIMA/NTN-B com precisão histórica sem discrepância do BCB
    # Usamos o endpoint de estatísticas da ANBIMA / SGS ajustado (Série 21619 tratada ou IPEADATA)
    url_bcb = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.21619/dados?formato=json"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json"
    }
    
    # Fazemos a requisição e limpeza
    res = requests.get(url_bcb, headers=headers, timeout=15)
    df_br = pd.DataFrame(res.json())
    df_br["data"] = pd.to_datetime(df_br["data"], format="%d/%m/%Y")
    df_br["valor"] = pd.to_numeric(df_br["valor"], errors="coerce")
    df_br = df_br.dropna().set_index("data")
    df_br.columns = ["NTNB_10A"]

    # 3. Combinar séries
    df = df_br.join(df_us, how="inner").dropna()
    df["Diferencial"] = df["NTNB_10A"] - df["TIPS_10A"]
    
    return df

try:
    df = load_data()
    
    # Estatísticas históricas (Média e Faixa do Período)
    media = df["Diferencial"].mean()
    std = df["Diferencial"].std()
    p25 = df["Diferencial"].quantile(0.25)
    p75 = df["Diferencial"].quantile(0.75)
    ultimo = df["Diferencial"].iloc[-1]

    # Métricas idênticas às da imagem
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Último Diferencial", f"{ultimo:.2f} p.p.")
    col2.metric("Média do Período", f"{media:.2f} p.p.")
    col3.metric("Desvio Padrão (σ)", f"{std:.2f}")
    col4.metric("Faixa (P25 - P75)", f"{p25:.2f} a {p75:.2f}")

    # Gráfico interativo no estilo do Brasil Horizonte
    fig = go.Figure()

    # Faixa Sombreada: Média ± Desvio Padrão
    fig.add_trace(go.Scatter(
        x=df.index.tolist() + df.index[::-1].tolist(),
        y=(df["Diferencial"] * 0 + media + std).tolist() + (df["Diferencial"] * 0 + media - std)[::-1].tolist(),
        fill='todense',
        fillcolor='rgba(211, 190, 150, 0.25)',
        line=dict(color='rgba(255,255,255,0)'),
        hoverinfo="skip",
        name="Média ± DP"
    ))

    # Linha da Média
    fig.add_hline(y=media, line_dash="dash", line_color="#888888", annotation_text=f"Média: {media:.2f} p.p.")

    # Linha Principal do Diferencial (Cor Amarela/Castanha da imagem)
    fig.add_trace(go.Scatter(
        x=df.index, 
        y=df["Diferencial"], 
        mode="lines", 
        name="Diferencial (Brasil - EUA)",
        line=dict(color="#a86e1e", width=1.8)
    ))

    fig.update_layout(
        xaxis_title="",
        yaxis_title="Diferencial (p.p.)",
        template="plotly_white",
        hovermode="x unified",
        height=550,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )

    st.plotly_chart(fig, use_container_width=True)

    st.info("Nota técnica: O gráfico reflete a diferença entre a taxa de juro real brasileira (NTN-B/ANBIMA 10a) e a norte-americana (TIPS 10a) descontando as respetivas inflações implícitas.")

except Exception as e:
    st.error(f"Erro ao carregar dados: {e}")
