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
    Busca os dados do SGS do BCB em blocos de 10 anos.
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

    # 2. NTN-B 10 anos via BCB
    df_br = fetch_bcb_historico_completo(21619, start_year=2005)
    
    df_br.index = pd.to_datetime(df_br.index)
    df_us.index = pd.to_datetime(df_us.index)

    # 3. Combinar e calcular o diferencial
    df = df_br.join(df_us, how="inner").dropna()
    df["Diferencial"] = df["NTNB_10A"] - df["TIPS_10A"]
    
    return df

try:
    df = load_data()
    
    # Métrica do topo e Estatísticas idênticas ao cabeçalho da imagem
    ultimo = df["Diferencial"].iloc[-1]
    media = df["Diferencial"].mean()
    std = df["Diferencial"].std()
    p25 = df["Diferencial"].quantile(0.25)
    p75 = df["Diferencial"].quantile(0.75)

    st.markdown(
        f"**Em {df.index[-1].strftime('%d/%m/%Y')}:** **{ultimo:.2f} p.p.** "
        f"• média do período **{media:.2f} p.p.** (σ {std:.2f}) "
        f"• faixa **{p25:.2f}** a **{p75:.2f}** • percentil 25 do período"
    )

    # Construção do Gráfico
    fig = go.Figure()

    # Dates x-axis
    x_dates = df.index.tolist()
    x_banda = x_dates + x_dates[::-1]

    # --- BANDA 1 (Externa / Mais Clara): Média ± 1 Desvio Padrão ---
    y_std_sup = [media + std] * len(df)
    y_std_inf = [media - std] * len(df)
    y_banda_std = y_std_sup + y_std_inf[::-1]

    fig.add_trace(go.Scatter(
        x=x_banda,
        y=y_banda_std,
        fill='toself',
        fillcolor='rgba(235, 225, 205, 0.35)', # Bege bem claro
        line=dict(color='rgba(255,255,255,0)'),
        hoverinfo="skip",
        name="Média ± 1 DP"
    ))

    # --- BANDA 2 (Interna / Mais Escura): Percentil 25 ao Percentil 75 ---
    y_p75 = [p75] * len(df)
    y_p25 = [p25] * len(df)
    y_banda_p = y_p75 + y_p25[::-1]

    fig.add_trace(go.Scatter(
        x=x_banda,
        y=y_banda_p,
        fill='toself',
        fillcolor='rgba(215, 195, 160, 0.50)', # Bege mais escuro
        line=dict(color='rgba(255,255,255,0)'),
        hoverinfo="skip",
        name="Faixa P25 - P75"
    ))

    # Linha tracejada da Média
    fig.add_hline(
        y=media, 
        line_dash="dot", 
        line_color="#a09080", 
        line_width=1,
        annotation_text=f"Média: {media:.2f} p.p.",
        annotation_position="bottom right"
    )

    # Linha principal do Diferencial
    fig.add_trace(go.Scatter(
        x=df.index, 
        y=df["Diferencial"], 
        mode="lines", 
        name="Diferencial (Brasil - EUA)",
        line=dict(color="#a86e1e", width=1.8)
    ))

    fig.update_layout(
        xaxis_title="",
        yaxis_title="Percentagem (p.p.)",
        template="plotly_white",
        hovermode="x unified",
        height=550,
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )

    st.plotly_chart(fig, use_container_width=True)

except Exception as e:
    st.error(f"Erro ao carregar dados: {e}")
