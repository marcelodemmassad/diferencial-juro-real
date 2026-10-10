import streamlit as st
import pandas as pd
import pandas_datareader.data as web
import plotly.graph_objects as go
from bcb import sgs
from datetime import datetime

st.set_page_config(page_title="Diferencial de Juro Real", layout="wide")

st.title("Diferencial de juro real — 10 anos (Brasil – EUA)")

@st.cache_data(ttl=3600)  # Atualiza os dados a cada 1 hora
def fetch_bcb_historico_completo(codigo_serie, start_year=2005):
    """
    Consulta o BCB em blocos de 10 anos para contornar a restrição da API.
    """
    current_year = datetime.today().year
    df_list = []
    
    # Faz consultas em blocos de 10 anos
    for year in range(start_year, current_year + 1, 10):
        start_date = f"{year}-01-01"
        end_year = min(year + 9, current_year)
        
        # Se for o bloco atual, vai até hoje
        if end_year == current_year:
            end_date = datetime.today().strftime('%Y-%m-%d')
        else:
            end_date = f"{end_year}-12-31"
            
        try:
            df_bloco = sgs.get({'NTNB_10A': codigo_serie}, start=start_date, end=end_date)
            if not df_bloco.empty:
                df_list.append(df_bloco)
        except Exception:
            continue
            
    if not df_list:
        raise ValueError("Não foi possível carregar os dados do BCB.")
        
    # Junta todos os blocos e remove duplicadas se houver
    df_completo = pd.concat(df_list)
    df_completo = df_completo[~df_completo.index.duplicated(keep='first')]
    return df_completo

@st.cache_data(ttl=3600)
def load_data():
    start_date = "2005-01-01"
    end_date = datetime.today().strftime('%Y-%m-%d')
    
    # 1. US 10-Year TIPS Rate via FRED (DFII10) - O FRED aceita períodos longos
    df_us = web.DataReader("DFII10", "fred", start_date, end_date)
    df_us.columns = ["TIPS_10A"]

    # 2. NTN-B 10 anos via BCB (busca em blocos para ter todo o histórico)
    df_br = fetch_bcb_historico_completo(21619, start_year=2005)
    
    # Garantir compatibilidade nos índices de data
    df_br.index = pd.to_datetime(df_br.index)
    df_us.index = pd.to_datetime(df_us.index)

    # 3. Combinar e calcular o diferencial
    df = df_br.join(df_us, how="inner").dropna()
    df["Diferencial"] = df["NTNB_10A"] - df["TIPS_10A"]
    
    return df

try:
    df = load_data()
    
    # Métrica do topo
    ultimo_valor = df["Diferencial"].iloc[-1]
    st.metric(label="Último Diferencial", value=f"{ultimo_valor:.2f} p.p.")

    # Gráfico interativo completo
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
