import streamlit as st
import pandas as pd
import pandas_datareader.data as web
import plotly.graph_objects as go
from bcb import sgs
from datetime import datetime

st.set_page_config(page_title="Diferencial de Juro Real", layout="wide")

st.title("Diferencial de juro real — 10 anos (Brasil – EUA)")

@st.cache_data(ttl=3600)
def fetch_bcb_historico_completo(codigo_serie, start_year=2005):
    """
    Busca os dados do SGS do BCB em blocos de no máximo 10 anos para contornar a restrição da API.
    """
    current_year = datetime.today().year
    df_list = []
    
    for year in range(start_year, current_year + 1, 10):
        start_date = f"{year}-01-01"
        end_year = min(year + 9, current_year)
        
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
        raise ValueError("Não foi possível carregar os dados do Banco Central.")
        
    df_completo = pd.concat(df_list)
    df_completo = df_completo[~df_completo.index.duplicated(keep='first')]
    return df_completo

@st.cache_data(ttl=3600)
def load_data():
    start_date = "2005-01-01"
    end_date = datetime.today().strftime('%Y-%m-%d')
    
    # 1. US 10-Year TIPS Rate via FRED (DFII10)
    df_us = web.DataReader("DFII10", "fred", start_date, end_date)
    df_us.columns = ["TIPS_10A"]

    # 2. NTN-B 10 anos via BCB (em blocos)
    df_br = fetch_bcb_historico_completo(21619, start_year=2005)
    
    # Garantir compatibilidade nos índices
    df_br.index = pd.to_datetime(df_br.index)
    df_us.index = pd.to_datetime(df_us.index)

    # 3. Combinar e calcular o diferencial
    df = df_br.join(df_us, how="inner").dropna()
    df["Diferencial"] = df["NTNB_10A"] - df["TIPS_10A"]
    
    return df

try:
    df = load_data()
    
    # Cálculos Estatísticos para o Visual idêntico ao Brasil Horizonte
    media = df["Diferencial"].mean()
    std = df["Diferencial"].std()
    p25 = df["Diferencial"].quantile(0.25)
    p75 = df["Diferencial"].quantile(0.75)
    ultimo = df["Diferencial"].iloc[-1]

    # Métricas no topo
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Último Diferencial", f"{ultimo:.2f} p.p.")
    col2.metric("Média do Período", f"{media:.2f} p.p.")
    col3.metric("Desvio Padrão (σ)", f"{std:.2f}")
    col4.metric("Faixa 25%-75%", f"{p25:.2f} a {p75:.2f} p.p.")

    # Construção do Gráfico Interativo
    fig = go.Figure()

    # Preparar polígono para a Faixa Sombreada: Média ± Desvio Padrão
    x_banda = df.index.tolist() + df.index[::-1].tolist()
    y_superior = [media + std] * len(df)
    y_inferior = [media - std] * len(df)
    y_banda = y_superior + y_inferior[::-1]

    # Faixa Sombreada usando 'toself'
    fig.add_trace(go.Scatter(
        x=x_banda,
        y=y_banda,
        fill='toself',
        fillcolor='rgba(225, 212, 188, 0.4)',
        line=dict(color='rgba(255,255,255,0)'),
        hoverinfo="skip",
        name="Média ± DP"
    ))

    # Linha Tracejada da Média
    fig.add_hline(
        y=media, 
        line_dash="dash", 
        line_color="#777777", 
        annotation_text=f"Média: {media:.2f} p.p.",
        annotation_position="bottom right"
    )

    # Linha do Diferencial (Cor castanha/dourada original)
    fig.add_trace(go.Scatter(
        x=df.index, 
        y=df["Diferencial"], 
        mode="lines", 
        name="Diferencial",
        line=dict(color="#a86e1e", width=1.6)
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

except Exception as e:
    st.error(f"Erro ao carregar dados: {e}")
