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

def _secao_visao_pool(df_raw: pd.DataFrame):
    """Visão exploratória do pool recebido."""
    _secao("01 · visão do pool", "Composição e características dos boletos")

    # KPIs
    total   = len(df_raw)
    vl_tot  = df_raw["vlr_nominal"].sum()
    vl_med  = df_raw["vlr_nominal"].median()
    prazo_m = df_raw["dias_entre_emissao_vencimento"].median() if "dias_entre_emissao_vencimento" in df_raw.columns else 0
    pags_u  = df_raw["id_pagador"].nunique() if "id_pagador" in df_raw.columns else 0
    ced_u   = df_raw["id_beneficiario"].nunique() if "id_beneficiario" in df_raw.columns else 0

    cols = st.columns(5)
    for col, (label, val, sub, cor) in zip(cols, [
        ("Total de boletos",     f"{total:,}",        "no pool",                   "#fff"),
        ("Valor nominal total",  _fmt_brl(vl_tot),    "soma face value",           "#c8f55a"),
        ("Valor mediano",        _fmt_brl(vl_med),    "mediana por boleto",        "#fff"),
        ("Prazo mediano",        f"{prazo_m:.0f} dias","emissão → vencimento",     "#fff"),
        ("Pagadores únicos",     f"{pags_u:,}",       f"{ced_u} cedentes únicos",  "#4a9eff"),
    ]):
        with col:
            st.markdown(_kpi(label, val, sub, cor), unsafe_allow_html=True)

    st.markdown("<hr style='border:none;border-top:1px solid rgba(64,123,110,0.15);margin:20px 0;'>",
                unsafe_allow_html=True)

    # Gráficos
    col1, col2, col3 = st.columns(3)

    with col1:
        fig = go.Figure(go.Histogram(
            x=df_raw["vlr_nominal"],
            nbinsx=40,
            marker_color="#407b6e",
            hovertemplate="R$ %{x:,.0f}<br>%{y} boletos<extra></extra>",
        ))
        fig.update_layout(title=dict(text="Distribuição de valores", font=dict(size=12, color="rgba(255,255,255,0.5)")))
        st.plotly_chart(_plotly_dark(fig), use_container_width=True, config={"displayModeBar": False})

    with col2:
        if "tipo_especie" in df_raw.columns:
            vc = df_raw["tipo_especie"].value_counts().head(6)
            fig = go.Figure(go.Bar(
                x=vc.values, y=vc.index,
                orientation="h",
                marker_color="#4a9eff",
                hovertemplate="%{y}<br>%{x} boletos<extra></extra>",
            ))
            fig.update_layout(title=dict(text="Tipo de espécie", font=dict(size=12, color="rgba(255,255,255,0.5)")))
            st.plotly_chart(_plotly_dark(fig), use_container_width=True, config={"displayModeBar": False})

    with col3:
        if "dias_entre_emissao_vencimento" in df_raw.columns:
            fig = go.Figure(go.Histogram(
                x=df_raw["dias_entre_emissao_vencimento"].clip(0, 365),
                nbinsx=30,
                marker_color="#c8f55a",
                hovertemplate="%{x} dias<br>%{y} boletos<extra></extra>",
            ))
            fig.update_layout(title=dict(text="Prazo de vencimento (dias)", font=dict(size=12, color="rgba(255,255,255,0.5)")))
            st.plotly_chart(_plotly_dark(fig), use_container_width=True, config={"displayModeBar": False})

    # Concentração por pagador
    if "id_pagador" in df_raw.columns:
        conc = (
            df_raw.groupby("id_pagador")["vlr_nominal"].sum()
            .sort_values(ascending=False)
            .head(10)
        )
        conc_pct = conc / vl_tot * 100
        maior_conc = conc_pct.iloc[0]

        if maior_conc > 30:
            _alerta("amber", f"Concentração de {maior_conc:.1f}% no maior pagador",
                    "Pool com concentração elevada em um único pagador. Avaliar risco de contraparte.")
        elif maior_conc > 15:
            _alerta("blue", f"Concentração de {maior_conc:.1f}% no maior pagador",
                    "Concentração moderada. Top 10 pagadores representam "
                    f"{conc_pct.sum():.1f}% do valor total.")


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
    _secao("03 · detalhamento", "Boleto a boleto com explicabilidade")

    # Formata para exibição
    df_exib = resultado[[
        "id_boleto", "vlr_nominal", "tipo_especie",
        "dias_vencimento", "prob_pagamento",
        "valor_esperado", "valor_em_risco",
        "faixa_risco", "decisao"
    ]].copy()

    df_exib["vlr_nominal"]    = df_exib["vlr_nominal"].apply(lambda x: f"R$ {x:,.2f}")
    df_exib["valor_esperado"] = df_exib["valor_esperado"].apply(lambda x: f"R$ {x:,.2f}")
    df_exib["valor_em_risco"] = df_exib["valor_em_risco"].apply(lambda x: f"R$ {x:,.2f}")
    df_exib["prob_pagamento"] = df_exib["prob_pagamento"].apply(lambda x: f"{x:.1%}")
    df_exib["dias_vencimento"]= df_exib["dias_vencimento"].apply(
        lambda x: f"{x:.0f}d" if pd.notna(x) else "N/D")

    df_exib.columns = [
        "ID Boleto", "Vlr. Nominal", "Espécie",
        "Prazo", "Prob. Pagamento",
        "Valor Esperado", "Valor em Risco",
        "Faixa de Risco", "Decisão"
    ]

    st.dataframe(
        df_exib,
        use_container_width=True,
        hide_index=True,
        height=400,
    )

    # Download
    csv = resultado.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="⬇ Exportar resultados completos (.csv)",
        data=csv,
        file_name="precificacao_pool.csv",
        mime="text/csv",
    )


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

    col_up, col_info = st.columns([2, 3])

    with col_up:
        arquivo = st.file_uploader(
            "Arquivo CSV com os boletos",
            type=["csv"],
            help="Colunas mínimas: id_boleto, id_pagador, id_beneficiario, dt_emissao, dt_vencimento, vlr_nominal, tipo_especie",
        )

    with col_info:
        st.markdown("""
        <div style="background:rgba(255,255,255,0.02);border:1px solid rgba(64,123,110,0.15);
                    border-radius:10px;padding:16px 20px;margin-top:4px;">
            <div style="font-size:10px;font-family:'DM Mono',monospace;letter-spacing:0.1em;
                        text-transform:uppercase;color:rgba(255,255,255,0.3);margin-bottom:10px;">
                Colunas esperadas no CSV
            </div>
            <div style="display:flex;flex-wrap:wrap;gap:6px;">
        """ + "".join([
            f'<span style="font-size:11px;font-family:\'DM Mono\',monospace;padding:3px 10px;'
            f'border-radius:6px;background:rgba(64,123,110,0.1);color:#407b6e;'
            f'border:1px solid rgba(64,123,110,0.25);">{c}</span>'
            for c in ["id_boleto","id_pagador","id_beneficiario",
                      "dt_emissao","dt_vencimento","vlr_nominal","tipo_especie"]
        ]) + """
            </div>
        </div>
        """, unsafe_allow_html=True)

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
    tab_pool, tab_prec = st.tabs(["📊 Visão do pool", "💹 Precificação"])

    with tab_pool:
        _secao_visao_pool(df_proc)

    with tab_prec:
        _secao_precificacao(resultado, metadata)


if __name__ == "__main__":
    main()