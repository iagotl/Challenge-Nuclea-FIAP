"""
pages/01_dashboard.py

Dashboard principal — FIDC · RAIZ
Abas: Painel Geral | Carteira | Inadimplência | Cotas | Risco | Cedentes | Relatórios
"""

from pathlib import Path
import streamlit as st
import plotly.graph_objects as go

BASE_DIR = Path(__file__).parent.parent

from core.auth import sessao_ativa, usuario_logado
from core.loader import carregar_ultima_competencia, carregar_competencia, carregar_historico
from core.metrics import calcular_todas
from components.sidebar import render as render_sidebar

st.set_page_config(
    page_title="RAIZ · Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ---------------------------------------------------------------------------
# HELPERS VISUAIS
# ---------------------------------------------------------------------------

def _estilo():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500&family=DM+Mono:wght@400;500&display=swap');
    html, body, [class*="css"] { font-family: 'DM Sans', sans-serif !important; }
    header[data-testid="stHeader"] { display: none !important; }
    footer { display: none !important; }
    #MainMenu { display: none !important; }
    .block-container { padding-top: 1.5rem !important; }
    .stApp { background: linear-gradient(180deg, #0d1415 0%, #1e2e30 100%) !important; }

    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {
        gap: 4px;
        background: rgba(255,255,255,0.02);
        border-radius: 10px;
        padding: 4px;
        border: 1px solid rgba(64,123,110,0.15);
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 8px;
        padding: 6px 16px;
        font-family: 'DM Mono', monospace !important;
        font-size: 12px !important;
        color: rgba(255,255,255,0.4) !important;
        background: transparent !important;
    }
    .stTabs [aria-selected="true"] {
        background: rgba(64,123,110,0.2) !important;
        color: #fff !important;
        border-bottom: none !important;
    }
    .stTabs [data-baseweb="tab-highlight"] { display: none; }
    .stTabs [data-baseweb="tab-border"]    { display: none; }

    /* Sidebar */
    [data-testid="stSidebar"] {
        background: #0a1012 !important;
        border-right: 1px solid rgba(64,123,110,0.2) !important;
    }
    [data-testid="stSidebar"] p,
    [data-testid="stSidebar"] span,
    [data-testid="stSidebar"] label { color: #fff !important; }
    [data-testid="stSidebar"] .stSelectbox > div > div {
        background: rgba(255,255,255,0.04) !important;
        border: 1px solid rgba(64,123,110,0.25) !important;
        border-radius: 8px !important;
        color: #fff !important;
    }

    /* Botão Sair */
    .stButton > button {
        border: 1px solid rgba(64,123,110,0.4) !important;
        background: transparent !important;
        color: rgba(255,255,255,0.6) !important;
        border-radius: 8px !important;
    }
    .stButton > button:hover {
        background: rgba(64,123,110,0.1) !important;
        color: #fff !important;
        border-color: rgba(64,123,110,0.6) !important;
    }
    </style>
    """, unsafe_allow_html=True)


def _fmt_brl(valor: float) -> str:
    """Formata valor em reais de forma legível. Ex: 2305454.92 → R$ 2,31M"""
    if abs(valor) >= 1_000_000:
        return f"R$ {valor/1_000_000:.2f}M"
    if abs(valor) >= 1_000:
        return f"R$ {valor/1_000:.1f}K"
    return f"R$ {valor:,.2f}"


def _badge(texto: str, tipo: str) -> str:
    """Gera HTML de badge colorido."""
    cores = {
        "red":   ("rgba(255,90,74,0.12)",  "#ff5a4a", "rgba(255,90,74,0.3)"),
        "amber": ("rgba(245,166,35,0.12)", "#f5a623", "rgba(245,166,35,0.3)"),
        "green": ("rgba(74,219,138,0.12)", "#4adb8a", "rgba(74,219,138,0.3)"),
        "teal":  ("rgba(64,123,110,0.12)", "#407b6e", "rgba(64,123,110,0.3)"),
    }
    bg, color, border = cores.get(tipo, cores["teal"])
    return (f'<span style="font-size:10px;font-family:\'DM Mono\',monospace;'
            f'padding:2px 10px;border-radius:10px;background:{bg};color:{color};'
            f'border:1px solid {border};white-space:nowrap;">{texto}</span>')


def _kpi(label: str, valor: str, sub: str = "", cor: str = "#fff") -> str:
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
        <div style="font-size:11px;color:rgba(255,255,255,0.3);line-height:1.4;">{sub}</div>
    </div>"""


def _secao(eyebrow: str, titulo: str):
    st.markdown(f"""
    <div style="margin:28px 0 16px;">
        <div style="font-size:10px;font-family:'DM Mono',monospace;letter-spacing:0.12em;
                    text-transform:uppercase;color:#407b6e;margin-bottom:4px;">{eyebrow}</div>
        <div style="font-size:18px;font-weight:500;color:#fff;">{titulo}</div>
    </div>
    """, unsafe_allow_html=True)


def _sem_dados():
    st.markdown("""
    <div style="text-align:center;padding:60px 0;color:rgba(255,255,255,0.2);">
        <div style="font-size:32px;margin-bottom:12px;">○</div>
        <div style="font-size:13px;font-family:'DM Mono',monospace;">
            Nenhum dado disponível para este período.
        </div>
    </div>
    """, unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# ABA: PAINEL GERAL
# ---------------------------------------------------------------------------

def _aba_painel_geral(dados: dict, metricas: dict):

    cab = dados["cabecalho"]
    at  = dados["ativo"]
    pl  = dados["patrimonio_liquido"]

    # ── Header ──
    col_header, col_home = st.columns([5, 1])
    with col_header:
        st.markdown(f"""
        <div style="padding:20px 0 24px;">
            <div style="font-size:10px;font-family:'DM Mono',monospace;letter-spacing:0.12em;
                        text-transform:uppercase;color:#407b6e;margin-bottom:6px;">
                {cab.get('nome_classe') or 'FIDC'} · Informe Mensal
            </div>
            <div style="font-size:22px;font-weight:500;color:#fff;margin-bottom:4px;">
                Posição consolidada — {cab['competencia']}
            </div>
            <div style="font-size:11px;font-family:'DM Mono',monospace;
                        color:rgba(255,255,255,0.2);">
                CNPJ {cab['cnpj_fundo']} · Adm: {cab['cnpj_administrador']}
            </div>
        </div>
        """, unsafe_allow_html=True)
    with col_home:
        st.markdown("<div style='padding-top:24px;'>", unsafe_allow_html=True)
        st.page_link("app.py", label="← Home", use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<hr style='border:none;border-top:1px solid rgba(64,123,110,0.2);margin:0 0 24px;'>",
                unsafe_allow_html=True)

    # ── KPIs ──
    var_pl   = metricas["patrimonio"]["variacao_pl_vs_media_pct"]
    cor_var  = "#4adb8a" if var_pl >= 0 else "#ff5a4a"
    sinal    = "↑" if var_pl >= 0 else "↓"
    inad_pct = metricas["carteira"]["taxa_inadimplencia_pct"]
    cor_inad = "#ff5a4a" if inad_pct > 8 else "#f5a623" if inad_pct > 4 else "#4adb8a"
    passivo  = dados["passivo"]["total"]
    pct_pass = round(passivo / pl["pl"] * 100, 1) if pl["pl"] > 0 else 0

    kpis = [
        ("Patrimônio Líquido",   _fmt_brl(pl["pl"]),
         f"{sinal} {abs(var_pl):.1f}% vs média 3m", cor_var),
        ("Ativo Total",          _fmt_brl(at["ativo_total"]),
         "Carteira + disponível + outros", "#fff"),
        ("Carteira de Créditos", _fmt_brl(at["dc_com_aquis"]["total"]),
         "Com aquisição substancial", "#fff"),
        ("Inadimplência",        f"{inad_pct:.1f}%",
         f"{_fmt_brl(at['dc_com_aquis']['existentes_inadimplentes'])}", cor_inad),
        ("Passivo Total",        _fmt_brl(passivo),
         f"~{pct_pass}% do PL", "#f5a623"),
        ("Liquidez Imediata",    _fmt_brl(at["disponibilidades"] + at["titulos_publicos_federais"]),
         "Disponível + TPF", "#fff"),
    ]
    cols = st.columns(6)
    for col, (label, valor, sub, cor) in zip(cols, kpis):
        with col:
            st.markdown(_kpi(label, valor, sub, cor), unsafe_allow_html=True)

    # ── Separador ──
    st.markdown("""
    <div style="margin:28px 0 0;padding-top:28px;border-top:1px solid rgba(64,123,110,0.15);">
    </div>
    """, unsafe_allow_html=True)

    # ── Composição do ativo + Balanço ──
    _secao("composição", "Estrutura do ativo")
    col_chart, col_tabela = st.columns([1, 1])

    with col_chart:
        labels = ["Direitos Creditórios", "Disponibilidades", "Títulos Públicos", "Outros"]
        values = [
            at["dc_com_aquis"]["total"],
            at["disponibilidades"],
            at["titulos_publicos_federais"],
            at["outros_ativos"]["total"],
        ]
        cores = ["#407b6e", "#4adb8a", "#002775", "#2e4446"]
        fig = go.Figure(go.Pie(
            labels=labels, values=values,
            hole=0.65,
            marker=dict(colors=cores, line=dict(color="#0d1415", width=2)),
            textinfo="percent",
            textfont=dict(family="DM Mono", size=11, color="#fff"),
            hovertemplate="<b>%{label}</b><br>R$ %{value:,.2f}<br>%{percent}<extra></extra>",
        ))
        fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            margin=dict(t=10, b=10, l=10, r=10),
            height=260,
            showlegend=True,
            legend=dict(
                font=dict(family="DM Mono", size=10, color="rgba(255,255,255,0.5)"),
                bgcolor="rgba(0,0,0,0)",
                orientation="v", x=1, y=0.5,
            ),
            annotations=[dict(
                text=f"<b>{_fmt_brl(at['ativo_total'])}</b>",
                x=0.5, y=0.5,
                font=dict(size=13, color="#fff", family="DM Mono"),
                showarrow=False,
            )],
        )
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    with col_tabela:
        st.markdown("""
        <table style="width:100%;border-collapse:collapse;font-size:12px;font-family:'DM Mono',monospace;">
            <thead><tr>
                <th style="text-align:left;padding:8px 12px;font-size:10px;letter-spacing:0.08em;
                           text-transform:uppercase;color:rgba(255,255,255,0.3);
                           border-bottom:1px solid rgba(64,123,110,0.2);">Item</th>
                <th style="text-align:right;padding:8px 12px;font-size:10px;letter-spacing:0.08em;
                           text-transform:uppercase;color:rgba(255,255,255,0.3);
                           border-bottom:1px solid rgba(64,123,110,0.2);">Valor</th>
            </tr></thead>
            <tbody>
        """ + "".join([
            f'''<tr>
                <td style="padding:8px 12px;color:{c};border-bottom:1px solid rgba(255,255,255,0.04);">{n}</td>
                <td style="padding:8px 12px;text-align:right;color:{c};border-bottom:1px solid rgba(255,255,255,0.04);">{v}</td>
            </tr>'''
            for n, v, c in [
                ("Disponibilidades",     _fmt_brl(at["disponibilidades"]),            "rgba(255,255,255,0.6)"),
                ("Direitos Creditórios", _fmt_brl(at["dc_com_aquis"]["total"]),       "rgba(255,255,255,0.6)"),
                ("Títulos Públicos",     _fmt_brl(at["titulos_publicos_federais"]),   "rgba(255,255,255,0.6)"),
                ("Outros Ativos",        _fmt_brl(at["outros_ativos"]["total"]),      "rgba(255,255,255,0.6)"),
                ("Ativo Total",          _fmt_brl(at["ativo_total"]),                 "#4adb8a"),
                ("Passivo (a pagar)",    f"({_fmt_brl(passivo)})",                   "#f5a623"),
                ("Patrimônio Líquido",   _fmt_brl(pl["pl"]),                          "#407b6e"),
            ]
        ]) + """
            </tbody>
        </table>
        """, unsafe_allow_html=True)

    # ── Separador ──
    st.markdown("""
    <div style="margin:28px 0 0;padding-top:28px;border-top:1px solid rgba(64,123,110,0.15);">
    </div>
    """, unsafe_allow_html=True)

    # ── Alertas ──
    _secao("resumo", "Pontos de atenção do mês")

    alertas = []
    if metricas["negocios"]["aquisicoes_total"] == 0:
        alertas.append(("red", "Originação zerada no mês",
                        "Nenhuma aquisição realizada. Com 63% da carteira vencendo em 30 dias, o PL tende a encolher."))
    if inad_pct > 8:
        alertas.append(("red", f"Inadimplência em {inad_pct:.1f}%",
                        f"{_fmt_brl(at['dc_com_aquis']['existentes_inadimplentes'])} em atraso. "
                        f"Provisão cobre {metricas['carteira']['cobertura_provisao_pct']:.0f}%."))
    for c in metricas["cedentes"]["cedentes"]:
        if c["nivel"] in ("critico", "alto"):
            alertas.append(("amber", f"Concentração de cedente: {c['participacao_pct']:.0f}% ({c['nivel'].upper()})",
                             f"CPF/CNPJ {c['cpf_cnpj']} representa {c['participacao_pct']:.0f}% da carteira."))
    if metricas["scr"]["pct_atencao"] > 30:
        alertas.append(("amber", f"{metricas['scr']['pct_atencao']:.0f}% da carteira em rating C (SCR/Bacen)",
                        "Faixa de risco moderado/atenção. Monitorar migração para faixa D."))
    if var_pl > 10:
        alertas.append(("green", f"PL {var_pl:.0f}% acima da média trimestral",
                        "Crescimento recente do fundo. Captações positivas no período."))
    for rent in dados["outras_informacoes"]["rentabilidade"]:
        if rent["rentabilidade_pct"] > 0:
            alertas.append(("green", f"Cota {rent['tipo']} rendeu +{rent['rentabilidade_pct']:.2f}% no mês",
                            "Retorno positivo na competência."))
    if not alertas:
        alertas.append(("green", "Nenhum alerta crítico identificado",
                        "Todos os indicadores dentro dos parâmetros esperados."))

    col_a, col_b = st.columns(2)
    for i, (tipo, titulo, desc) in enumerate(alertas):
        cores_alert = {
            "red":   ("#ff5a4a", "rgba(255,90,74,0.08)",   "rgba(255,90,74,0.3)"),
            "amber": ("#f5a623", "rgba(245,166,35,0.08)",  "rgba(245,166,35,0.3)"),
            "green": ("#4adb8a", "rgba(74,219,138,0.08)",  "rgba(74,219,138,0.3)"),
        }
        cor, bg, border = cores_alert[tipo]
        html = f"""
        <div style="display:flex;gap:12px;padding:12px 14px;border-radius:8px;
                    background:{bg};border-left:3px solid {cor};margin-bottom:8px;">
            <span style="color:{cor};font-size:10px;margin-top:2px;flex-shrink:0;">●</span>
            <div>
                <div style="font-size:13px;font-weight:500;color:#fff;margin-bottom:2px;">{titulo}</div>
                <div style="font-size:12px;color:rgba(255,255,255,0.5);line-height:1.5;">{desc}</div>
            </div>
        </div>"""
        with (col_a if i % 2 == 0 else col_b):
            st.markdown(html, unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------

def main():
    _estilo()

    # Verifica autenticação
    if not sessao_ativa(st):
        st.warning("Sessão expirada. Faça login novamente.")
        st.stop()

    # Sidebar — retorna fundo e competência selecionados
    fundo_id, competencia = render_sidebar(BASE_DIR)

    if not fundo_id or not competencia:
        _sem_dados()
        return

    # Carrega dados
    dados    = carregar_competencia(BASE_DIR, fundo_id, competencia)
    historico= carregar_historico(BASE_DIR, fundo_id)

    if not dados:
        _sem_dados()
        return

    metricas = calcular_todas(dados, historico)

    # Adiciona negócios ao dict de métricas para os alertas
    neg = dados["negocios_mes"]
    metricas["negocios"] = {
        "aquisicoes_total": neg["aquisicoes"]["total"]["valor"],
    }

    # ── Abas ──
    abas = st.tabs([
        "Painel Geral",
        "Carteira",
        "Inadimplência",
        "Cotas",
        "Risco de Crédito",
        "Cedentes",
        "Relatórios",
    ])

    with abas[0]:
        _aba_painel_geral(dados, metricas)

    for i, nome in enumerate(["Carteira", "Inadimplência", "Cotas",
                               "Risco de Crédito", "Cedentes", "Relatórios"], start=1):
        with abas[i]:
            st.markdown(f"""
            <div style="text-align:center;padding:60px 0;color:rgba(255,255,255,0.2);">
                <div style="font-size:13px;font-family:'DM Mono',monospace;">
                    Aba <b style="color:#407b6e;">{nome}</b> — em construção
                </div>
            </div>
            """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()