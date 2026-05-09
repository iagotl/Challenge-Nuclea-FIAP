"""
pages/03_precificacao.py
Precificação de pools de direitos creditórios — FIDC · RAIZ
"""

from pathlib import Path
import streamlit as st
import pandas as pd
import numpy as np
import joblib
import plotly.graph_objects as go
import plotly.express as px

BASE_DIR   = Path(__file__).parent.parent
MODEL_PATH = BASE_DIR / "data" / "models" / "modelo_fidc_v2.pkl"
META_PATH  = BASE_DIR / "data" / "models" / "metadata_fidc_v2.pkl"
AUX_PATH   = BASE_DIR / "data" / "auxiliar" / "base_auxiliar.csv"

st.set_page_config(
    page_title="RAIZ · Precificação",
    page_icon="💹",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ---------------------------------------------------------------------------
# ESTILO
# ---------------------------------------------------------------------------

def _estilo():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500&family=DM+Mono:wght@400;500&display=swap');
    html,body,[class*="css"]{ font-family:'DM Sans',sans-serif !important; }
    header[data-testid="stHeader"]{ display:none !important; }
    footer{ display:none !important; }
    #MainMenu{ display:none !important; }
    .block-container{ padding-top:0 !important; }
    .stApp{ background:linear-gradient(180deg,#0d1415 0%,#1e2e30 100%) !important; }
    div[data-testid="stFormSubmitButton"] > button,
    .stButton > button[kind="primary"]{
        background:#407b6e !important; border:none !important;
        border-radius:8px !important; color:#fff !important; font-weight:500 !important;
    }
    .stButton > button{
        border:1px solid rgba(64,123,110,0.4) !important;
        background:transparent !important; color:rgba(255,255,255,0.6) !important;
        border-radius:8px !important;
    }
    .stButton > button:hover{
        background:rgba(64,123,110,0.1) !important; color:#fff !important;
    }
    .stDataFrame{ border-radius:8px !important; }
    /* File uploader */
    [data-testid="stFileUploader"] {
        background: rgba(64,123,110,0.06) !important;
        border: 1px dashed rgba(64,123,110,0.4) !important;
        border-radius: 10px !important;
        padding: 8px !important;
    }
    [data-testid="stFileUploader"] label {
        color: rgba(255,255,255,0.6) !important;
    }
    [data-testid="stFileUploaderDropzone"] {
        background: transparent !important;
    }
    [data-testid="stFileUploaderDropzoneInstructions"] p {
        color: rgba(255,255,255,0.5) !important;
    }
    .stTabs [data-baseweb="tab-list"]{
        gap:4px; background:rgba(255,255,255,0.02); border-radius:10px;
        padding:4px; border:1px solid rgba(64,123,110,0.15);
    }
    .stTabs [data-baseweb="tab"]{
        border-radius:8px; padding:6px 16px;
        font-family:'DM Mono',monospace !important; font-size:12px !important;
        color:rgba(255,255,255,0.4) !important; background:transparent !important;
    }
    .stTabs [aria-selected="true"]{
        background:rgba(64,123,110,0.2) !important; color:#fff !important;
    }
    .stTabs [data-baseweb="tab-highlight"]{ display:none; }
    .stTabs [data-baseweb="tab-border"]{ display:none; }
    </style>
    """, unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# HELPERS VISUAIS
# ---------------------------------------------------------------------------

def _kpi(label, valor, sub="", cor="#fff"):
    return f"""
    <div style="background:rgba(255,255,255,0.02);border:1px solid rgba(64,123,110,0.18);
                border-radius:10px;padding:16px 18px;">
        <div style="font-size:10px;font-family:'DM Mono',monospace;letter-spacing:0.08em;
                    text-transform:uppercase;color:rgba(255,255,255,0.35);margin-bottom:8px;">
            {label}
        </div>
        <div style="font-size:22px;font-weight:500;font-family:'DM Mono',monospace;
                    color:{cor};line-height:1;margin-bottom:6px;">
            {valor}
        </div>
        <div style="font-size:11px;color:rgba(255,255,255,0.3);">{sub}</div>
    </div>"""


def _fmt_brl(v):
    if abs(v) >= 1_000_000: return f"R$ {v/1_000_000:.2f}M"
    if abs(v) >= 1_000:     return f"R$ {v/1_000:.1f}K"
    return f"R$ {v:,.2f}"


def _alerta(tipo, titulo, desc):
    cores = {
        "red":   ("#ff5a4a", "rgba(255,90,74,0.08)"),
        "amber": ("#f5a623", "rgba(245,166,35,0.08)"),
        "green": ("#4adb8a", "rgba(74,219,138,0.08)"),
        "blue":  ("#4a9eff", "rgba(74,158,255,0.08)"),
    }
    cor, bg = cores.get(tipo, cores["blue"])
    st.markdown(f"""
    <div style="display:flex;gap:12px;padding:12px 14px;border-radius:8px;
                background:{bg};border-left:3px solid {cor};margin-bottom:8px;">
        <span style="color:{cor};font-size:10px;margin-top:2px;flex-shrink:0;">●</span>
        <div>
            <div style="font-size:13px;font-weight:500;color:#fff;margin-bottom:2px;">{titulo}</div>
            <div style="font-size:12px;color:rgba(255,255,255,0.5);line-height:1.5;">{desc}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)


def _secao(eyebrow, titulo):
    st.markdown(f"""
    <div style="margin:24px 0 16px;">
        <div style="font-size:10px;font-family:'DM Mono',monospace;letter-spacing:0.12em;
                    text-transform:uppercase;color:#407b6e;margin-bottom:4px;">{eyebrow}</div>
        <div style="font-size:18px;font-weight:500;color:#fff;">{titulo}</div>
    </div>
    """, unsafe_allow_html=True)


def _plotly_dark(fig, height=280):
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(t=20, b=10, l=0, r=0),
        height=height,
        font=dict(family="DM Mono", color="rgba(255,255,255,0.5)", size=11),
        legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(color="rgba(255,255,255,0.5)")),
    )
    fig.update_xaxes(gridcolor="rgba(255,255,255,0.04)", linecolor="rgba(255,255,255,0.06)")
    fig.update_yaxes(gridcolor="rgba(255,255,255,0.04)")
    return fig


# ---------------------------------------------------------------------------
# CORE: FEATURE ENGINEERING E PRECIFICAÇÃO
# ---------------------------------------------------------------------------

@st.cache_resource
def _carregar_modelo():
    if not MODEL_PATH.exists() or not META_PATH.exists():
        return None, None
    return joblib.load(MODEL_PATH), joblib.load(META_PATH)


@st.cache_data
def _carregar_auxiliar():
    if not AUX_PATH.exists():
        return None
    return pd.read_csv(AUX_PATH)


def _feature_engineering(df: pd.DataFrame, aux: pd.DataFrame) -> pd.DataFrame:
    """Aplica todas as transformações necessárias para o modelo."""
    df = df.copy()

    # Log do valor nominal
    df["log_vlr_nominal"] = np.log1p(df["vlr_nominal"])

    # Dias entre emissão e vencimento
    df["dt_emissao"]    = pd.to_datetime(df["dt_emissao"],    errors="coerce")
    df["dt_vencimento"] = pd.to_datetime(df["dt_vencimento"], errors="coerce")
    df["dias_entre_emissao_vencimento"] = (df["dt_vencimento"] - df["dt_emissao"]).dt.days

    # Join pagador
    df = df.merge(
        aux.add_prefix("pagador_"),
        left_on="id_pagador", right_on="pagador_id_cnpj",
        how="left"
    )

    # Join cedente
    df = df.merge(
        aux.add_prefix("cedente_"),
        left_on="id_beneficiario", right_on="cedente_id_cnpj",
        how="left"
    )

    return df


def _faixa_risco(prob: float) -> tuple[str, str]:
    """Retorna (label, cor_hex) com base na probabilidade de pagamento."""
    if prob >= 0.90: return "Baixo risco",   "#4adb8a"
    if prob >= 0.76: return "Atenção",        "#f5a623"
    return               "Alto risco",        "#ff5a4a"


def _calcular_precificacao(df: pd.DataFrame, modelo, metadata: dict) -> pd.DataFrame:
    """Calcula probabilidades e valor esperado para o pool."""
    features = [f for f in metadata["selected_features"] if f in df.columns]
    X = df[features].copy()

    for col in metadata.get("categorical_features", []):
        if col in X.columns:
            X[col] = X[col].astype("object")

    proba = modelo.predict_proba(X)[:, 1]

    resultado = pd.DataFrame({
        "id_boleto":               df["id_boleto"].values if "id_boleto" in df.columns else range(len(df)),
        "vlr_nominal":             df["vlr_nominal"].values,
        "tipo_especie":            df["tipo_especie"].values if "tipo_especie" in df.columns else "N/D",
        "dias_vencimento":         df["dias_entre_emissao_vencimento"].values if "dias_entre_emissao_vencimento" in df.columns else np.nan,
        "prob_pagamento":          proba,
        "prob_nao_pagamento":      1 - proba,
        "valor_esperado":          df["vlr_nominal"].values * proba,
        "valor_em_risco":          df["vlr_nominal"].values * (1 - proba),
    })

    resultado["faixa_risco"]  = resultado["prob_pagamento"].apply(lambda p: _faixa_risco(p)[0])
    resultado["cor_risco"]    = resultado["prob_pagamento"].apply(lambda p: _faixa_risco(p)[1])
    resultado["decisao"]      = resultado["prob_pagamento"].apply(
        lambda p: "✅ Comprar" if p >= metadata.get("best_threshold", 0.76) else "⚠️ Revisar"
    )

    return resultado


# ---------------------------------------------------------------------------
# SEÇÕES DA PÁGINA
# ---------------------------------------------------------------------------

def _faixa_valor(v):
    if v <= 1_000:    return "até R$ 1K"
    if v <= 5_000:    return "R$ 1K – 5K"
    if v <= 50_000:   return "R$ 5K – 50K"
    if v <= 500_000:  return "R$ 50K – 500K"
    return "acima R$ 500K"

ORDEM_VALOR = ["até R$ 1K","R$ 1K – 5K","R$ 5K – 50K","R$ 50K – 500K","acima R$ 500K"]
CORES_VALOR = ["#4adb8a","#c8f55a","#407b6e","#f5a623","#ff5a4a"]

def _faixa_prazo(d):
    if pd.isna(d) or d < 0: return "Sem info"
    if d <= 30:   return "até 30d"
    if d <= 60:   return "31–60d"
    if d <= 90:   return "61–90d"
    if d <= 180:  return "91–180d"
    return "acima 180d"

ORDEM_PRAZO  = ["até 30d","31–60d","61–90d","91–180d","acima 180d","Sem info"]
CORES_PRAZO  = ["#ff5a4a","#f5a623","#c8f55a","#407b6e","#4a9eff","#555550"]


def _secao_visao_pool(df_raw: pd.DataFrame):
    """Visão exploratória do pool recebido."""
    _secao("01 · visão do pool", "Composição e características dos boletos")

    total   = len(df_raw)
    vl_tot  = df_raw["vlr_nominal"].sum()
    vl_med  = df_raw["vlr_nominal"].median()
    prazo_m = df_raw["dias_entre_emissao_vencimento"].median() if "dias_entre_emissao_vencimento" in df_raw.columns else 0
    pags_u  = df_raw["id_pagador"].nunique() if "id_pagador" in df_raw.columns else 0
    ced_u   = df_raw["id_beneficiario"].nunique() if "id_beneficiario" in df_raw.columns else 0

    # Validação de duplicatas
    col_dup = "id_boleto" if "id_boleto" in df_raw.columns else None
    n_dup   = df_raw[col_dup].duplicated().sum() if col_dup else 0

    cols = st.columns(5)
    for col, (label, val, sub, cor) in zip(cols, [
        ("Total de boletos",    f"{total:,}",         "no pool",                  "#fff"),
        ("Valor nominal total", _fmt_brl(vl_tot),     "soma face value",          "#c8f55a"),
        ("Valor mediano",       _fmt_brl(vl_med),     "mediana por boleto",       "#fff"),
        ("Prazo mediano",       f"{prazo_m:.0f} dias","emissão → vencimento",     "#fff"),
        ("Pagadores únicos",    f"{pags_u:,}",        f"{ced_u} cedentes únicos", "#4a9eff"),
    ]):
        with col:
            st.markdown(_kpi(label, val, sub, cor), unsafe_allow_html=True)

    # Alerta de duplicatas
    if n_dup > 0:
        _alerta("red", f"⚠️ {n_dup} boleto(s) duplicado(s) detectado(s)",
                f"Encontrados {n_dup} id_boleto repetidos no pool — possível indício de fraude ou erro operacional. "
                f"Verifique antes de prosseguir com a precificação.")
    else:
        _alerta("green", "Nenhum boleto duplicado encontrado",
                "Todos os id_boleto são únicos no pool.")

    st.markdown("<hr style='border:none;border-top:1px solid rgba(64,123,110,0.15);margin:20px 0;'>",
                unsafe_allow_html=True)

    # ── Linha 1: Valor + Espécie ──
    col1, col_sep1, col2 = st.columns([5, 0.2, 4])

    with col1:
        df_raw["_faixa_valor"] = df_raw["vlr_nominal"].apply(_faixa_valor)
        vc_val = (
            df_raw.groupby("_faixa_valor")["vlr_nominal"]
            .agg(qtd="count", total="sum")
            .reindex(ORDEM_VALOR)
            .dropna()
            .reset_index()
        )
        fig = go.Figure(go.Bar(
            x=vc_val["_faixa_valor"],
            y=vc_val["qtd"],
            marker=dict(color=CORES_VALOR[:len(vc_val)], line=dict(color="#0d1415", width=1)),
            text=vc_val["qtd"],
            textposition="outside",
            textfont=dict(color="rgba(255,255,255,0.6)", size=11),
            hovertemplate="<b>%{x}</b><br>%{y} boletos<extra></extra>",
        ))
        fig.update_layout(
            title=dict(text="Distribuição por faixa de valor", font=dict(size=12, color="rgba(255,255,255,0.5)")),
            xaxis=dict(categoryorder="array", categoryarray=ORDEM_VALOR),
            bargap=0.25,
        )
        st.plotly_chart(_plotly_dark(fig, height=300), use_container_width=True, config={"displayModeBar": False})

    with col_sep1:
        st.markdown("<div style='border-left:1px solid rgba(64,123,110,0.2);height:300px;margin-top:40px;'></div>",
                    unsafe_allow_html=True)

    with col2:
        if "tipo_especie" in df_raw.columns:
            vc = df_raw["tipo_especie"].value_counts().head(6).reset_index()
            vc.columns = ["especie", "qtd"]
            # Abrevia nomes longos
            vc["especie_curta"] = vc["especie"].str.split(" ").str[:3].str.join(" ")
            fig = go.Figure(go.Bar(
                x=vc["qtd"], y=vc["especie_curta"],
                orientation="h",
                marker=dict(color="#4a9eff", line=dict(color="#0d1415", width=1)),
                text=vc["qtd"],
                textposition="outside",
                textfont=dict(color="rgba(255,255,255,0.6)", size=11),
                hovertemplate="<b>%{y}</b><br>%{x} boletos<extra></extra>",
            ))
            fig.update_layout(
                title=dict(text="Tipo de espécie", font=dict(size=12, color="rgba(255,255,255,0.5)")),
                bargap=0.3,
            )
            st.plotly_chart(_plotly_dark(fig, height=300), use_container_width=True, config={"displayModeBar": False})

    st.markdown("<hr style='border:none;border-top:1px solid rgba(64,123,110,0.15);margin:8px 0 16px;'>",
                unsafe_allow_html=True)

    # ── Linha 2: Prazo ──
    if "dias_entre_emissao_vencimento" in df_raw.columns:
        col3, col_sep2, col4 = st.columns([4, 0.2, 5])

        with col3:
            df_raw["_faixa_prazo"] = df_raw["dias_entre_emissao_vencimento"].apply(_faixa_prazo)
            vc_prazo = (
                df_raw["_faixa_prazo"].value_counts()
                .reindex(ORDEM_PRAZO)
                .dropna()
                .reset_index()
            )
            vc_prazo.columns = ["faixa", "qtd"]
            cores_prazo_filtradas = [CORES_PRAZO[ORDEM_PRAZO.index(f)] for f in vc_prazo["faixa"]]

            fig = go.Figure(go.Bar(
                x=vc_prazo["faixa"],
                y=vc_prazo["qtd"],
                marker=dict(color=cores_prazo_filtradas, line=dict(color="#0d1415", width=1)),
                text=vc_prazo["qtd"],
                textposition="outside",
                textfont=dict(color="rgba(255,255,255,0.6)", size=11),
                hovertemplate="<b>%{x}</b><br>%{y} boletos<extra></extra>",
            ))
            fig.update_layout(
                title=dict(text="Prazo até vencimento", font=dict(size=12, color="rgba(255,255,255,0.5)")),
                xaxis=dict(categoryorder="array", categoryarray=ORDEM_PRAZO),
                bargap=0.3,
            )
            st.plotly_chart(_plotly_dark(fig, height=280), use_container_width=True, config={"displayModeBar": False})

        with col_sep2:
            st.markdown("<div style='border-left:1px solid rgba(64,123,110,0.2);height:280px;margin-top:40px;'></div>",
                        unsafe_allow_html=True)

        with col4:
            # Top 8 pagadores por valor
            if "id_pagador" in df_raw.columns:
                top_pag = (
                    df_raw.groupby("id_pagador")["vlr_nominal"].sum()
                    .sort_values(ascending=True)
                    .tail(8)
                    .reset_index()
                )
                top_pag["id_curto"] = top_pag["id_pagador"].str[:12] + "..."
                top_pag["pct"]      = top_pag["vlr_nominal"] / vl_tot * 100

                fig = go.Figure(go.Bar(
                    x=top_pag["vlr_nominal"], y=top_pag["id_curto"],
                    orientation="h",
                    marker=dict(color="#407b6e", line=dict(color="#0d1415", width=1)),
                    text=top_pag["pct"].apply(lambda x: f"{x:.1f}%"),
                    textposition="outside",
                    textfont=dict(color="rgba(255,255,255,0.6)", size=11),
                    hovertemplate="<b>%{y}</b><br>R$ %{x:,.0f}<extra></extra>",
                ))
                fig.update_layout(
                    title=dict(text="Top 8 pagadores por valor", font=dict(size=12, color="rgba(255,255,255,0.5)")),
                    xaxis=dict(tickformat=",.0f"),
                    bargap=0.3,
                )
                st.plotly_chart(_plotly_dark(fig, height=280), use_container_width=True, config={"displayModeBar": False})

    # Alerta concentração
    if "id_pagador" in df_raw.columns:
        conc     = df_raw.groupby("id_pagador")["vlr_nominal"].sum().sort_values(ascending=False)
        conc_pct = conc / vl_tot * 100
        maior    = conc_pct.iloc[0]
        if maior > 30:
            _alerta("amber", f"Concentração de {maior:.1f}% no maior pagador",
                    "Pool com concentração elevada. Avaliar risco de contraparte.")
        elif maior > 15:
            _alerta("blue", f"Concentração de {maior:.1f}% no maior pagador",
                    f"Concentração moderada. Top 10 representam {conc_pct.head(10).sum():.1f}% do valor total.")


def _secao_precificacao(resultado: pd.DataFrame, metadata: dict):
    """Resultados da precificação com explicabilidade."""
    _secao("02 · precificação", "Probabilidades e valor esperado do pool")

    threshold = metadata.get("best_threshold", 0.76)
    vl_nom    = resultado["vlr_nominal"].sum()
    vl_esp    = resultado["valor_esperado"].sum()
    vl_risco  = resultado["valor_em_risco"].sum()
    prob_med  = resultado["prob_pagamento"].mean()
    n_comprar = (resultado["decisao"] == "✅ Comprar").sum()
    n_revisar = (resultado["decisao"] == "⚠️ Revisar").sum()

    # KPIs de precificação
    cols = st.columns(5)
    for col, (label, val, sub, cor) in zip(cols, [
        ("Valor nominal total",    _fmt_brl(vl_nom),         "face value do pool",         "#fff"),
        ("Valor esperado",         _fmt_brl(vl_esp),         "Σ nominal × prob. pagamento","#c8f55a"),
        ("Valor em risco",         _fmt_brl(vl_risco),       "Σ nominal × prob. não pagar","#ff5a4a"),
        ("Prob. média pagamento",  f"{prob_med:.1%}",         f"threshold: {threshold:.0%}","#4a9eff"),
        ("Recomendação compra",    f"{n_comprar}/{len(resultado)}",
                                                              f"{n_revisar} para revisão",  "#4adb8a"),
    ]):
        with col:
            st.markdown(_kpi(label, val, sub, cor), unsafe_allow_html=True)

    st.markdown("<hr style='border:none;border-top:1px solid rgba(64,123,110,0.15);margin:20px 0;'>",
                unsafe_allow_html=True)

    # Gráficos de probabilidade
    col1, col2 = st.columns(2)

    with col1:
        fig = go.Figure(go.Histogram(
            x=resultado["prob_pagamento"],
            nbinsx=30,
            marker_color="#407b6e",
            hovertemplate="Prob: %{x:.2f}<br>%{y} boletos<extra></extra>",
        ))
        # Linha do threshold
        fig.add_vline(x=threshold, line_dash="dash", line_color="#ff5a4a",
                      annotation_text=f"Threshold {threshold:.0%}",
                      annotation_font_color="#ff5a4a")
        fig.update_layout(title=dict(text="Distribuição das probabilidades", font=dict(size=12, color="rgba(255,255,255,0.5)")))
        st.plotly_chart(_plotly_dark(fig), use_container_width=True, config={"displayModeBar": False})

    with col2:
        # Donut por faixa de risco
        faixas = resultado["faixa_risco"].value_counts()
        cores_faixas = {"Baixo risco": "#4adb8a", "Atenção": "#f5a623", "Alto risco": "#ff5a4a"}
        fig = go.Figure(go.Pie(
            labels=faixas.index, values=faixas.values,
            hole=0.6,
            marker=dict(
                colors=[cores_faixas.get(f, "#407b6e") for f in faixas.index],
                line=dict(color="#0d1415", width=2),
            ),
            textinfo="percent+label",
            textfont=dict(family="DM Mono", size=11, color="#fff"),
            hovertemplate="<b>%{label}</b><br>%{value} boletos (%{percent})<extra></extra>",
        ))
        fig.update_layout(
            title=dict(text="Distribuição por faixa de risco", font=dict(size=12, color="rgba(255,255,255,0.5)")),
            showlegend=False,
        )
        st.plotly_chart(_plotly_dark(fig, height=280), use_container_width=True, config={"displayModeBar": False})

    # Alertas automáticos
    pct_alto_risco = (resultado["faixa_risco"] == "Alto risco").mean()
    if pct_alto_risco > 0.20:
        _alerta("red", f"{pct_alto_risco:.1%} do pool em faixa de alto risco",
                "Volume elevado de boletos com baixa probabilidade de pagamento. Revisar antes de adquirir.")
    elif pct_alto_risco > 0.10:
        _alerta("amber", f"{pct_alto_risco:.1%} do pool em faixa de alto risco",
                "Presença relevante de boletos de risco. Considerar deságio adicional.")

    pct_revisao = n_revisar / len(resultado)
    if pct_revisao > 0:
        _alerta("blue", f"{n_revisar} boleto(s) recomendado(s) para revisão ({pct_revisao:.1%})",
                f"Probabilidade de pagamento abaixo do threshold de {threshold:.0%}. "
                f"Valor nominal envolvido: {_fmt_brl(resultado[resultado['decisao']=='⚠️ Revisar']['vlr_nominal'].sum())}")

    st.markdown("<hr style='border:none;border-top:1px solid rgba(64,123,110,0.15);margin:20px 0;'>",
                unsafe_allow_html=True)

    # Tabela detalhada
    col_sec, col_dl = st.columns([4, 1])
    with col_sec:
        _secao("03 · detalhamento", "Boleto a boleto com explicabilidade")
    with col_dl:
        csv = resultado.to_csv(index=False).encode("utf-8")
        st.markdown("<div style='padding-top:24px;'>", unsafe_allow_html=True)
        st.download_button(
            label="⬇ Exportar CSV",
            data=csv,
            file_name="precificacao_pool.csv",
            mime="text/csv",
            use_container_width=True,
        )
        st.markdown("</div>", unsafe_allow_html=True)

    CORES_FAIXA = {"Baixo risco": "#4adb8a", "Atenção": "#f5a623", "Alto risco": "#ff5a4a"}
    CORES_DEC   = {"✅ Comprar": "#4adb8a", "⚠️ Revisar": "#f5a623"}

    linhas_html = ""
    for _, row in resultado.iterrows():
        cor_faixa = CORES_FAIXA.get(row["faixa_risco"], "#fff")
        cor_dec   = CORES_DEC.get(row["decisao"], "#fff")
        id_curto  = str(row["id_boleto"])[:20] + "..." if len(str(row["id_boleto"])) > 20 else str(row["id_boleto"])
        prazo_str = f"{row['dias_vencimento']:.0f}d" if pd.notna(row["dias_vencimento"]) else "N/D"
        especie   = str(row["tipo_especie"])[:25] + "..." if len(str(row["tipo_especie"])) > 25 else str(row["tipo_especie"])

        linhas_html += f"""
        <tr>
            <td style="font-family:'DM Mono',monospace;font-size:11px;color:rgba(255,255,255,0.4);"
                title="{row['id_boleto']}">{id_curto}</td>
            <td style="font-family:'DM Mono',monospace;color:#fff;text-align:right;">
                R$ {row['vlr_nominal']:,.2f}</td>
            <td style="color:rgba(255,255,255,0.6);font-size:12px;">{especie}</td>
            <td style="font-family:'DM Mono',monospace;color:rgba(255,255,255,0.5);text-align:center;">
                {prazo_str}</td>
            <td style="font-family:'DM Mono',monospace;color:{cor_faixa};font-weight:500;text-align:center;">
                {row['prob_pagamento']:.1%}</td>
            <td style="font-family:'DM Mono',monospace;color:#c8f55a;text-align:right;">
                R$ {row['valor_esperado']:,.2f}</td>
            <td style="font-family:'DM Mono',monospace;color:#ff5a4a;text-align:right;">
                R$ {row['valor_em_risco']:,.2f}</td>
            <td style="text-align:center;">
                <span style="font-size:11px;font-family:'DM Mono',monospace;padding:2px 10px;
                             border-radius:10px;background:{cor_faixa}22;color:{cor_faixa};
                             border:1px solid {cor_faixa}44;">
                    {row["faixa_risco"]}
                </span>
            </td>
            <td style="text-align:center;color:{cor_dec};font-size:13px;">{row["decisao"]}</td>
        </tr>"""

    th = ("padding:8px 12px;font-size:10px;font-family:'DM Mono',monospace;"
          "letter-spacing:0.08em;text-transform:uppercase;color:rgba(255,255,255,0.3);"
          "border-bottom:1px solid rgba(64,123,110,0.25);background:#0d1415;")

    st.markdown(f"""
    <div style="overflow-x:auto;overflow-y:auto;max-height:420px;
                background:rgba(255,255,255,0.02);border:1px solid rgba(64,123,110,0.2);
                border-radius:10px;">
        <table style="width:100%;border-collapse:collapse;">
            <thead>
                <tr>
                    <th style="{th}text-align:left;">ID Boleto</th>
                    <th style="{th}text-align:right;">Vlr. Nominal</th>
                    <th style="{th}text-align:left;">Espécie</th>
                    <th style="{th}text-align:center;">Prazo</th>
                    <th style="{th}text-align:center;">Prob. Pag.</th>
                    <th style="{th}text-align:right;">Vlr. Esperado</th>
                    <th style="{th}text-align:right;">Vlr. em Risco</th>
                    <th style="{th}text-align:center;">Faixa de Risco</th>
                    <th style="{th}text-align:center;">Decisão</th>
                </tr>
            </thead>
            <tbody>{linhas_html}</tbody>
        </table>
    </div>
    """, unsafe_allow_html=True)




# ---------------------------------------------------------------------------
# SEÇÃO: INTERPRETABILIDADE
# ---------------------------------------------------------------------------

def _secao_interpretabilidade(modelo, metadata: dict):
    """Exibe coeficientes do modelo e interpretação das features."""

    _secao("modelo · interpretabilidade", "Critérios e pesos usados na precificação")

    threshold = metadata.get("best_threshold", 0.76)

    # Extrai coeficientes
    try:
        lr        = modelo.named_steps["model"]
        pre       = modelo.named_steps["preprocessor"]
        num_names = metadata.get("numeric_features", [])
        cat_names = []
        if "cat" in pre.named_transformers_:
            cat_enc   = pre.named_transformers_["cat"].named_steps["onehot"]
            cat_feats = metadata.get("categorical_features", [])
            cat_names = cat_enc.get_feature_names_out(cat_feats).tolist()

        all_names = num_names + cat_names
        coefs     = lr.coef_[0]
        coef_dict = dict(zip(all_names, coefs))
    except Exception as e:
        st.warning(f"Não foi possível extrair coeficientes: {e}")
        return

    # Descrições das features numéricas
    DESCRICOES = {
        "log_vlr_nominal":                       ("Valor do boleto (log)",          "Boletos de maior valor têm relação com perfil de pagamento"),
        "dias_entre_emissao_vencimento":          ("Prazo de vencimento (dias)",     "Prazos maiores tendem a ter mais incerteza de pagamento"),
        "pagador_score_materialidade_v2":         ("Score de materialidade — pagador","Score de relevância financeira do pagador"),
        "pagador_sacado_indice_liquidez_1m":      ("Índice de liquidez — pagador",   "Capacidade de pagamento no curto prazo do pagador"),
        "pagador_media_atraso_dias":              ("Média de atraso — pagador",      "Histórico de atrasos do pagador. Maior atraso = maior risco"),
        "cedente_indicador_liquidez_quantitativo_3m": ("Liquidez quantitativa — cedente","Saúde financeira do cedente nos últimos 3 meses"),
        "cedente_score_materialidade_v2":         ("Score de materialidade — cedente","Score de relevância financeira do cedente"),
    }

    # Filtra só as features numéricas principais
    features_principais = [f for f in num_names if f in coef_dict]
    dados_coef = []
    for feat in features_principais:
        coef  = coef_dict[feat]
        desc  = DESCRICOES.get(feat, (feat, ""))
        dados_coef.append({
            "feature":     feat,
            "label":       desc[0],
            "descricao":   desc[1],
            "coeficiente": coef,
            "impacto":     "↑ Aumenta prob. pagamento" if coef > 0 else "↓ Reduz prob. pagamento",
            "cor":         "#4adb8a" if coef > 0 else "#ff5a4a",
        })

    dados_coef.sort(key=lambda x: abs(x["coeficiente"]), reverse=True)

    # KPIs do modelo
    col1, col2, col3, col4 = st.columns(4)
    for col, (label, val, sub, cor) in zip([col1,col2,col3,col4], [
        ("Threshold de decisão",  f"{threshold:.0%}",             "prob. mínima para comprar",      "#c8f55a"),
        ("Features no modelo",    str(len(features_principais)),  "variáveis numéricas",            "#fff"),
        ("Tipo de modelo",        "Regressão Logística",          "interpretável por coeficientes", "#4a9eff"),
        ("Calibração",            "Brier Score 0.072",            "erro quadrático médio",          "#4adb8a"),
    ]):
        with col:
            st.markdown(_kpi(label, val, sub, cor), unsafe_allow_html=True)

    st.markdown("<hr style='border:none;border-top:1px solid rgba(64,123,110,0.15);margin:20px 0;'>",
                unsafe_allow_html=True)

    # Gráfico de coeficientes
    col_chart, col_tab = st.columns([1, 1])

    with col_chart:
        labels = [d["label"] for d in dados_coef]
        valores = [d["coeficiente"] for d in dados_coef]
        cores   = [d["cor"] for d in dados_coef]

        fig = go.Figure(go.Bar(
            x=valores,
            y=labels,
            orientation="h",
            marker=dict(color=cores, line=dict(color="#0d1415", width=1)),
            text=[f"{v:+.3f}" for v in valores],
            textposition="outside",
            textfont=dict(color="rgba(255,255,255,0.6)", size=11),
            hovertemplate="<b>%{y}</b><br>Coeficiente: %{x:+.4f}<extra></extra>",
        ))
        fig.add_vline(x=0, line_color="rgba(255,255,255,0.2)", line_width=1)
        fig.update_layout(
            title=dict(text="Peso de cada variável no modelo",
                       font=dict(size=12, color="rgba(255,255,255,0.5)")),
            bargap=0.3,
            xaxis=dict(title=dict(text="Coeficiente (positivo = favorece pagamento)",
                                  font=dict(size=10, color="rgba(255,255,255,0.3)"))),
        )
        st.plotly_chart(_plotly_dark(fig, height=340), use_container_width=True,
                        config={"displayModeBar": False})

    with col_tab:
        st.markdown("""
        <div style="font-size:10px;font-family:'DM Mono',monospace;letter-spacing:0.1em;
                    text-transform:uppercase;color:rgba(255,255,255,0.3);margin-bottom:12px;">
            Interpretação das variáveis
        </div>
        """, unsafe_allow_html=True)

        for d in dados_coef:
            barra_w = min(abs(d["coeficiente"]) / max(abs(v) for v in valores) * 100, 100)
            st.markdown(f"""
            <div style="background:rgba(255,255,255,0.02);border:1px solid rgba(64,123,110,0.12);
                        border-left:3px solid {d['cor']};border-radius:0 8px 8px 0;
                        padding:10px 14px;margin-bottom:8px;">
                <div style="display:flex;justify-content:space-between;margin-bottom:4px;">
                    <span style="font-size:12px;font-weight:500;color:#fff;">{d['label']}</span>
                    <span style="font-size:11px;font-family:'DM Mono',monospace;
                                 color:{d['cor']};font-weight:500;">{d['coeficiente']:+.3f}</span>
                </div>
                <div style="height:4px;background:rgba(255,255,255,0.06);border-radius:2px;
                            overflow:hidden;margin-bottom:6px;">
                    <div style="height:100%;width:{barra_w:.0f}%;background:{d['cor']};
                                border-radius:2px;"></div>
                </div>
                <div style="font-size:11px;color:rgba(255,255,255,0.4);">{d['descricao']}</div>
                <div style="font-size:10px;font-family:'DM Mono',monospace;
                            color:{d['cor']};margin-top:4px;">{d['impacto']}</div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("<hr style='border:none;border-top:1px solid rgba(64,123,110,0.15);margin:20px 0;'>",
                unsafe_allow_html=True)

    # Como ler o resultado
    _secao("como interpretar", "Guia de leitura da precificação")
    col_a, col_b, col_c = st.columns(3)

    for col, (cor, titulo, desc) in zip([col_a, col_b, col_c], [
        ("#4adb8a", "Baixo risco — prob. ≥ 90%",
         "Alta probabilidade de pagamento. O valor esperado é próximo do valor nominal. Recomendado para aquisição."),
        ("#f5a623", f"Atenção — prob. entre {threshold:.0%} e 90%",
         "Probabilidade razoável, mas com desconto relevante. Avaliar custo de aquisição vs valor esperado."),
        ("#ff5a4a", f"Alto risco — prob. < {threshold:.0%}",
         "Probabilidade baixa de pagamento. Valor em risco elevado. Recomenda-se revisão individual antes de adquirir."),
    ]):
        with col:
            st.markdown(f"""
            <div style="background:rgba(255,255,255,0.02);border:1px solid {cor}44;
                        border-top:2px solid {cor};border-radius:10px;padding:16px;height:100%;">
                <div style="font-size:12px;font-weight:500;color:{cor};margin-bottom:8px;">{titulo}</div>
                <div style="font-size:13px;color:rgba(255,255,255,0.55);line-height:1.7;">{desc}</div>
            </div>
            """, unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------

def main():
    _estilo()

    from core.auth import sessao_ativa
    if not sessao_ativa(st):
        st.warning("Sessão expirada. Faça login novamente.")
        st.stop()

    # ── Barra superior ──
    col_logo, _, col_home = st.columns([3, 4, 1])
    with col_logo:
        st.markdown("""
        <div style="padding:8px 0 4px;">
            <div style="font-size:10px;font-family:'DM Mono',monospace;letter-spacing:0.12em;
                        text-transform:uppercase;color:#407b6e;">RAIZ · Precificação</div>
            <div style="font-size:14px;font-weight:500;color:#fff;">
                Precificação de Pools de Direitos Creditórios
            </div>
        </div>
        """, unsafe_allow_html=True)
    with col_home:
        st.markdown("<div style='padding-top:16px;'>", unsafe_allow_html=True)
        st.page_link("app.py", label="← Home", use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<hr style='border:none;border-top:1px solid rgba(64,123,110,0.2);margin:4px 0 20px;'>",
                unsafe_allow_html=True)

    # ── Verifica modelo e auxiliar ──
    modelo, metadata = _carregar_modelo()
    auxiliar         = _carregar_auxiliar()

    if modelo is None:
        _alerta("red", "Modelo não encontrado",
                f"Coloque modelo_fidc_v2.pkl e metadata_fidc_v2.pkl em {MODEL_PATH.parent}")
        return
    if auxiliar is None:
        _alerta("red", "Base auxiliar não encontrada",
                f"Coloque base_auxiliar.csv em {AUX_PATH.parent}")
        return

    # ── Upload ──
    _secao("upload", "Envie a base de boletos do pool")

    col_info, col_up = st.columns([3, 2])

    with col_info:
        st.markdown("""
        <div style="background:rgba(255,255,255,0.02);border:1px solid rgba(64,123,110,0.15);
                    border-radius:10px;padding:16px 20px;margin-top:4px;">
            <div style="font-size:10px;font-family:'DM Mono',monospace;letter-spacing:0.1em;
                        text-transform:uppercase;color:rgba(255,255,255,0.3);margin-bottom:10px;">
                Colunas esperadas no CSV
            </div>
            <div style="display:flex;flex-wrap:wrap;gap:6px;margin-bottom:12px;">
        """ + "".join([
            f'<span style="font-size:11px;font-family:\'DM Mono\',monospace;padding:3px 10px;'
            f'border-radius:6px;background:rgba(64,123,110,0.1);color:#407b6e;'
            f'border:1px solid rgba(64,123,110,0.25);">{c}</span>'
            for c in ["id_boleto","id_pagador","id_beneficiario",
                      "dt_emissao","dt_vencimento","vlr_nominal","tipo_especie"]
        ]) + """
            </div>
            <div style="font-size:11px;color:rgba(255,255,255,0.3);line-height:1.6;">
                A base auxiliar com scores de pagador e cedente é gerenciada internamente.<br>
                O modelo usa <strong style="color:rgba(255,255,255,0.6);">8 variáveis</strong>
                para estimar a probabilidade de pagamento de cada boleto.
            </div>
        </div>
        """, unsafe_allow_html=True)

    with col_up:
        arquivo = st.file_uploader(
            "Arquivo CSV com os boletos",
            type=["csv"],
            help="Colunas mínimas: id_boleto, id_pagador, id_beneficiario, dt_emissao, dt_vencimento, vlr_nominal, tipo_especie",
        )

    if arquivo is None:
        st.markdown("""
        <div style="text-align:center;padding:80px 0;color:rgba(255,255,255,0.2);">
            <div style="font-size:32px;margin-bottom:12px;">💹</div>
            <div style="font-size:13px;font-family:'DM Mono',monospace;">
                Faça o upload de um CSV para precificar o pool
            </div>
        </div>
        """, unsafe_allow_html=True)
        return

    # ── Processa ──
    try:
        df_raw = pd.read_csv(arquivo)
    except Exception as e:
        _alerta("red", "Erro ao ler o arquivo", str(e))
        return

    # Valida colunas mínimas
    COLS_MIN = ["id_pagador", "id_beneficiario", "dt_emissao", "dt_vencimento", "vlr_nominal"]
    faltando = [c for c in COLS_MIN if c not in df_raw.columns]
    if faltando:
        _alerta("red", "Colunas obrigatórias ausentes", f"Faltando: {', '.join(faltando)}")
        return

    # Feature engineering
    with st.spinner("Calculando features e aplicando modelo..."):
        df_proc = _feature_engineering(df_raw, auxiliar)
        resultado = _calcular_precificacao(df_proc, modelo, metadata)

    st.markdown("<hr style='border:none;border-top:1px solid rgba(64,123,110,0.2);margin:8px 0 4px;'>",
                unsafe_allow_html=True)

    # ── Tabs ──
    tab_pool, tab_prec, tab_interp = st.tabs([
        "📊 Visão do pool", "💹 Precificação", "🧠 Como o modelo decide"
    ])

    with tab_pool:
        _secao_visao_pool(df_proc)

    with tab_prec:
        _secao_precificacao(resultado, metadata)

    with tab_interp:
        _secao_interpretabilidade(modelo, metadata)


if __name__ == "__main__":
    main()