import streamlit as st
import pandas as pd
import pandas_datareader.data as web
import plotly.graph_objects as go
import requests
from datetime import datetime

st.set_page_config(page_title="Diferencial de Juro Real", layout="wide")

st.title("Diferencial de juro real — 10 anos (Brasil – EUA)")

@st.cache_data(ttl=3600)  # Atualiza os dados a cada 1 hora
def load_data():
    end_date = datetime.today()
    start_date = "2005-01-01"
    
    # 1. US 10-Year TIPS Rate via FRED (DFII10)
    df_us = web.DataReader("DFII10", "fred", start_date, end_date)
    df_us.columns = ["TIPS_10A"]

    # 2. NTN-B 10 anos / Juro Real Brasil via API do BCB (SGS)
    url_bcb = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.21619/dados?formato=json"
    response = requests.get(url_bcb, timeout=10)
    data_json = response.json()
    
    # Garante que a resposta é uma lista de dados e não um dicionário de erro
    if isinstance(data_json, list):
        df_br = pd.DataFrame(data_json)
    elif isinstance(data_json, dict):
        df_br = pd.DataFrame([data_json])
    else:
        raise ValueError("Formato de resposta inesperado da API do Banco Central.")

    if "data" not in df_br.columns or "valor" not in df_br.columns:
        raise ValueError("A API do BCB não retornou as colunas esperadas ('data' e 'valor').")

    # Tratar colunas
    df_br["data"] = pd.to_datetime(df_br["data"], format="%d/%m/%Y", errors="coerce")
    df_br["valor"] = pd.to_numeric(df_br["valor"], errors="coerce")
    df_br = df_br.dropna(subset=["data", "valor"])
    df_br.set_index("data", inplace=True)
    df_br.rename(columns={"valor": "NTNB_10A"}, inplace=True)

    # 3. Combinar e calcular diferencial
    df = df_br.join(df_us, how="inner").dropna()
    df["Diferencial"] = df["NTNB_10A"] - df["TIPS_10A"]
    
    return df

try:
    df = load_data()
    
    # Métrica do topo
    ultimo_valor = df["Diferencial"].iloc[-1]
    st.metric(label="Último Diferencial", value=f"{ultimo_valor:.2f} p.p.")

    # Gráfico interativo
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=df.index, 
        y=df["Diferencial"], 
        mode="lines", 
        name="Diferencial",
        line=dict(color="#b8860b", width=1.5)
    ))

    fig.update_layout(
        xaxis_title="Data",
        yaxis_title="Diferencial (p.p.)",
        template="plotly_white",
        hovermode="x unified",
        height=500
    )

    st.plotly_chart(fig, use_container_width=True)

except Exception as e:
    st.error(f"Erro ao carregar os dados: {e}")
