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
# ABA: INADIMPLÊNCIA
# ---------------------------------------------------------------------------

def _aba_inadimplencia(dados: dict, metricas: dict):

    at   = dados["ativo"]
    cart = metricas["carteira"]
    dc   = at["dc_com_aquis"]

    inad        = dc["existentes_inadimplentes"]
    prov        = dc["provisao_perda"]
    cobertura   = cart["cobertura_provisao_pct"]
    exposta     = cart["exposicao_nao_provisionada"]
    inad_pct    = cart["taxa_inadimplencia_pct"]

    cor_inad    = "#ff5a4a" if inad_pct > 8 else "#f5a623" if inad_pct > 4 else "#4adb8a"
    cor_cob     = "#ff5a4a" if cobertura < 30 else "#f5a623" if cobertura < 60 else "#4adb8a"
    cor_exp     = "#ff5a4a" if exposta > 100_000 else "#f5a623" if exposta > 0 else "#4adb8a"

    # ── Header + Home ──
    col_t, col_h = st.columns([5, 1])
    with col_t:
        st.markdown("""
        <div style="padding:20px 0 24px;">
            <div style="font-size:10px;font-family:'DM Mono',monospace;letter-spacing:0.12em;
                        text-transform:uppercase;color:#407b6e;margin-bottom:6px;">
                Inadimplência · Análise de Atrasos e Provisões
            </div>
            <div style="font-size:22px;font-weight:500;color:#fff;">
                Aging, cobertura e exposição não provisionada
            </div>
        </div>
        """, unsafe_allow_html=True)
    with col_h:
        st.markdown("<div style='padding-top:24px;'>", unsafe_allow_html=True)
        st.page_link("app.py", label="← Home", use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<hr style='border:none;border-top:1px solid rgba(64,123,110,0.2);margin:0 0 24px;'>",
                unsafe_allow_html=True)

    # ── KPIs ──
    kpis = [
        ("Total Inadimplente",       _fmt_brl(inad),    f"{inad_pct:.1f}% da carteira bruta",           cor_inad),
        ("Provisão Constituída",     _fmt_brl(prov),    f"Cobertura de {cobertura:.0f}% do inadimplente", cor_cob),
        ("Exposição Não Provisionada", _fmt_brl(exposta), "Valor sem cobertura de provisão",             cor_exp),
        ("Aging Predominante",       "1–30 dias",       "100% da inadimplência recente",                 "#f5a623"),
    ]
    cols = st.columns(4)
    for col, (label, valor, sub, cor) in zip(cols, kpis):
        with col:
            st.markdown(_kpi(label, valor, sub, cor), unsafe_allow_html=True)

    # ── Separador ──
    st.markdown("<div style='margin:28px 0 0;padding-top:28px;border-top:1px solid rgba(64,123,110,0.15);'></div>",
                unsafe_allow_html=True)

    # ── Aging + Cobertura ──
    _secao("aging da inadimplência", "Distribuição por faixa de atraso")
    col_aging, col_cob = st.columns([2, 1])

    with col_aging:
        aging = cart["distribuicao_aging"]
        faixas  = [d["faixa"] for d in aging]
        valores = [d["valor"] for d in aging]
        pcts    = [d["percentual"] for d in aging]

        def _cor_aging(v):
            return "#ff5a4a" if v > 0 else "rgba(255,255,255,0.08)"

        fig = go.Figure(go.Bar(
            x=faixas,
            y=valores,
            marker=dict(
                color=[_cor_aging(v) for v in valores],
                line=dict(color="#0d1415", width=1),
            ),
            text=[f"{p:.0f}%" if v > 0 else "" for v, p in zip(valores, pcts)],
            textposition="outside",
            textfont=dict(family="DM Mono", size=11, color="rgba(255,255,255,0.6)"),
            hovertemplate="<b>%{x}</b><br>R$ %{y:,.2f}<extra></extra>",
        ))
        fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            margin=dict(t=30, b=10, l=0, r=0),
            height=280,
            showlegend=False,
            xaxis=dict(
                tickfont=dict(family="DM Mono", size=11, color="rgba(255,255,255,0.5)"),
                gridcolor="rgba(255,255,255,0.04)",
                linecolor="rgba(255,255,255,0.06)",
            ),
            yaxis=dict(
                tickfont=dict(family="DM Mono", size=10, color="rgba(255,255,255,0.3)"),
                gridcolor="rgba(255,255,255,0.04)",
                tickformat=",.0f",
                title=dict(text="R$", font=dict(color="rgba(255,255,255,0.2)", size=10)),
            ),
            bargap=0.3,
        )
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

        st.markdown("""
        <div style="font-size:11px;font-family:'DM Mono',monospace;
                    color:rgba(255,255,255,0.3);margin-top:-8px;font-style:italic;">
            Barras em destaque indicam faixas com saldo inadimplente.
            Faixas zeradas aparecem em cinza.
        </div>
        """, unsafe_allow_html=True)

    with col_cob:
        st.markdown("""
        <div style="font-size:10px;font-family:'DM Mono',monospace;letter-spacing:0.1em;
                    text-transform:uppercase;color:rgba(255,255,255,0.3);margin-bottom:16px;">
            Cobertura de provisão
        </div>
        """, unsafe_allow_html=True)

        # Barra de cobertura
        cor_barra = "#ff5a4a" if cobertura < 30 else "#f5a623" if cobertura < 60 else "#4adb8a"
        st.markdown(f"""
        <div style="margin-bottom:20px;">
            <div style="display:flex;justify-content:space-between;margin-bottom:6px;
                        font-size:12px;font-family:'DM Mono',monospace;">
                <span style="color:rgba(255,255,255,0.5);">Inadimplente</span>
                <span style="color:#fff;">{_fmt_brl(inad)}</span>
            </div>
            <div style="height:10px;background:rgba(255,255,255,0.06);border-radius:5px;
                        overflow:hidden;margin-bottom:8px;">
                <div style="height:100%;width:{min(cobertura, 100):.0f}%;
                            background:{cor_barra};border-radius:5px;
                            transition:width 0.6s ease;"></div>
            </div>
            <div style="display:flex;justify-content:space-between;
                        font-size:12px;font-family:'DM Mono',monospace;">
                <span style="color:rgba(255,255,255,0.5);">Provisionado</span>
                <span style="color:{cor_barra};">{_fmt_brl(prov)} ({cobertura:.0f}%)</span>
            </div>
        </div>

        <div style="background:rgba(255,255,255,0.02);border:1px solid rgba(64,123,110,0.15);
                    border-radius:8px;padding:14px;margin-bottom:12px;">
            <div style="font-size:10px;font-family:'DM Mono',monospace;
                        color:rgba(255,255,255,0.3);margin-bottom:6px;">
                Exposição residual
            </div>
            <div style="font-size:20px;font-weight:500;font-family:'DM Mono',monospace;
                        color:{cor_exp};">
                {_fmt_brl(exposta)}
            </div>
            <div style="font-size:11px;color:rgba(255,255,255,0.3);margin-top:4px;">
                Sem cobertura de provisão
            </div>
        </div>
        """, unsafe_allow_html=True)

        # Tabela de aging detalhada
        st.markdown("""
        <table style="width:100%;border-collapse:collapse;font-size:11px;font-family:'DM Mono',monospace;">
            <thead><tr>
                <th style="text-align:left;padding:6px 8px;font-size:10px;letter-spacing:0.08em;
                           text-transform:uppercase;color:rgba(255,255,255,0.25);
                           border-bottom:1px solid rgba(64,123,110,0.2);">Faixa</th>
                <th style="text-align:right;padding:6px 8px;font-size:10px;letter-spacing:0.08em;
                           text-transform:uppercase;color:rgba(255,255,255,0.25);
                           border-bottom:1px solid rgba(64,123,110,0.2);">Valor</th>
                <th style="text-align:right;padding:6px 8px;font-size:10px;letter-spacing:0.08em;
                           text-transform:uppercase;color:rgba(255,255,255,0.25);
                           border-bottom:1px solid rgba(64,123,110,0.2);">%</th>
            </tr></thead>
            <tbody>
        """ + "".join([
            f"""<tr style="background:{'rgba(255,90,74,0.06)' if d['valor'] > 0 else 'transparent'};">
                <td style="padding:6px 8px;color:{'#ff5a4a' if d['valor'] > 0 else 'rgba(255,255,255,0.2)'};
                           border-bottom:1px solid rgba(255,255,255,0.03);">{d['faixa']}</td>
                <td style="padding:6px 8px;text-align:right;font-weight:{'500' if d['valor'] > 0 else '400'};
                           color:{'#ff5a4a' if d['valor'] > 0 else 'rgba(255,255,255,0.15)'};
                           border-bottom:1px solid rgba(255,255,255,0.03);">
                    {_fmt_brl(d['valor']) if d['valor'] > 0 else '—'}</td>
                <td style="padding:6px 8px;text-align:right;
                           color:{'#ff5a4a' if d['valor'] > 0 else 'rgba(255,255,255,0.15)'};
                           border-bottom:1px solid rgba(255,255,255,0.03);">
                    {f"{d['percentual']:.0f}%" if d['valor'] > 0 else '—'}</td>
            </tr>"""
            for d in aging
        ]) + """
            </tbody>
        </table>
        """, unsafe_allow_html=True)

    # ── Separador ──
    st.markdown("<div style='margin:28px 0 0;padding-top:28px;border-top:1px solid rgba(64,123,110,0.15);'></div>",
                unsafe_allow_html=True)

    # ── Análise de cenários ──
    _secao("análise de cenários", "Interpretação da inadimplência atual")

    col_c1, col_c2 = st.columns(2)

    with col_c1:
        st.markdown(f"""
        <div style="background:rgba(74,219,138,0.05);border:1px solid rgba(74,219,138,0.2);
                    border-top:2px solid #4adb8a;border-radius:10px;padding:20px;height:100%;">
            <div style="font-size:10px;font-family:'DM Mono',monospace;letter-spacing:0.1em;
                        text-transform:uppercase;color:#4adb8a;margin-bottom:10px;">
                Cenário positivo
            </div>
            <div style="font-size:15px;font-weight:500;color:#fff;margin-bottom:10px;">
                Atraso pontual com recuperação
            </div>
            <div style="font-size:13px;color:rgba(255,255,255,0.5);line-height:1.7;">
                100% da inadimplência está na faixa de 1–30 dias, sem acúmulo em faixas mais longas.
                Isso pode indicar atraso operacional ou pontual, com chance de regularização
                no próximo ciclo sem impacto permanente na carteira.
            </div>
            <div style="margin-top:14px;font-size:11px;font-family:'DM Mono',monospace;
                        color:rgba(255,255,255,0.3);">
                Confirmação: inadimplência zerada ou reduzida em abril
            </div>
        </div>
        """, unsafe_allow_html=True)

    with col_c2:
        st.markdown(f"""
        <div style="background:rgba(255,90,74,0.05);border:1px solid rgba(255,90,74,0.2);
                    border-top:2px solid #ff5a4a;border-radius:10px;padding:20px;height:100%;">
            <div style="font-size:10px;font-family:'DM Mono',monospace;letter-spacing:0.1em;
                        text-transform:uppercase;color:#ff5a4a;margin-bottom:10px;">
                Cenário de atenção
            </div>
            <div style="font-size:15px;font-weight:500;color:#fff;margin-bottom:10px;">
                Início de ciclo de deterioração
            </div>
            <div style="font-size:13px;color:rgba(255,255,255,0.5);line-height:1.7;">
                Se os créditos em atraso migrarem para faixas maiores (31–60d, 61–90d),
                o fundo precisará ampliar provisões, impactando novamente a cota junior.
                A ausência de novas aquisições agrava o risco de concentração de perdas.
            </div>
            <div style="margin-top:14px;font-size:11px;font-family:'DM Mono',monospace;
                        color:rgba(255,255,255,0.3);">
                Sinal de alerta: migração de aging em abril
            </div>
        </div>
        """, unsafe_allow_html=True)

    # ── Alerta de provisão ──
    if cobertura < 50:
        st.markdown(f"""
        <div style="display:flex;gap:12px;padding:12px 14px;border-radius:8px;margin-top:16px;
                    background:rgba(245,166,35,0.08);border-left:3px solid #f5a623;">
            <span style="color:#f5a623;font-size:10px;margin-top:2px;flex-shrink:0;">●</span>
            <div>
                <div style="font-size:13px;font-weight:500;color:#fff;margin-bottom:2px;">
                    Provisão cobre apenas {cobertura:.0f}% do inadimplente
                </div>
                <div style="font-size:12px;color:rgba(255,255,255,0.5);line-height:1.5;">
                    {_fmt_brl(exposta)} sem cobertura. Caso os créditos não sejam recuperados,
                    novas provisões serão necessárias, impactando a rentabilidade da cota junior.
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# ABA: CARTEIRA
# ---------------------------------------------------------------------------

def _aba_carteira(dados: dict, metricas: dict):

    at  = dados["ativo"]
    neg = dados["negocios_mes"]
    cart= metricas["carteira"]

    # ── Botão Home ──
    col_t, col_h = st.columns([5, 1])
    with col_t:
        st.markdown("""
        <div style="padding:20px 0 24px;">
            <div style="font-size:10px;font-family:'DM Mono',monospace;letter-spacing:0.12em;
                        text-transform:uppercase;color:#407b6e;margin-bottom:6px;">
                Carteira · Composição e Originação
            </div>
            <div style="font-size:22px;font-weight:500;color:#fff;">
                Perfil de vencimentos e movimentações do mês
            </div>
        </div>
        """, unsafe_allow_html=True)
    with col_h:
        st.markdown("<div style='padding-top:24px;'>", unsafe_allow_html=True)
        st.page_link("app.py", label="← Home", use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<hr style='border:none;border-top:1px solid rgba(64,123,110,0.2);margin:0 0 24px;'>",
                unsafe_allow_html=True)

    # ── KPIs ──
    inad    = at["dc_com_aquis"]["existentes_inadimplentes"]
    prov    = at["dc_com_aquis"]["provisao_perda"]
    bruta   = at["dc_com_aquis"]["total"]
    adimpl  = at["dc_com_aquis"]["a_vencer_adimplentes"]
    exp_nao_prov = cart["exposicao_nao_provisionada"]

    cor_inad = "#ff5a4a" if cart["taxa_inadimplencia_pct"] > 8 else                "#f5a623" if cart["taxa_inadimplencia_pct"] > 4 else "#4adb8a"
    cor_prov = "#f5a623" if cart["cobertura_provisao_pct"] < 50 else "#4adb8a"

    kpis = [
        ("Carteira Bruta",        _fmt_brl(bruta),   "Total com aquisição substancial",              "#fff"),
        ("Créditos Adimplentes",  _fmt_brl(adimpl),  "A vencer e em dia",                            "#4adb8a"),
        ("Créditos Inadimplentes",_fmt_brl(inad),    f"{cart['taxa_inadimplencia_pct']:.1f}% da carteira bruta", cor_inad),
        ("Provisão para Perdas",  _fmt_brl(prov),    f"Cobertura: {cart['cobertura_provisao_pct']:.0f}% · Exposto: {_fmt_brl(exp_nao_prov)}", cor_prov),
    ]
    cols = st.columns(4)
    for col, (label, valor, sub, cor) in zip(cols, kpis):
        with col:
            st.markdown(_kpi(label, valor, sub, cor), unsafe_allow_html=True)

    # ── Separador ──
    st.markdown("<div style='margin:28px 0 0;padding-top:28px;border-top:1px solid rgba(64,123,110,0.15);'></div>",
                unsafe_allow_html=True)

    # ── Vencimentos + Segmento ──
    _secao("perfil de vencimentos", "Distribuição por prazo — créditos adimplentes")
    col_bar, col_seg = st.columns([2, 1])

    with col_bar:
        dist = cart["distribuicao_vencimentos"]
        faixas  = [d["faixa"] for d in dist]
        valores = [d["valor"] for d in dist]
        pcts    = [d["percentual"] for d in dist]

        # Cor por urgência
        def _cor_faixa(f):
            if f == "até 30d":   return "#ff5a4a"
            if f in ("31–60d", "61–90d", "91–120d", "121–150d", "151–180d"): return "#f5a623"
            return "#4adb8a"

        cores_bar = [_cor_faixa(f) for f in faixas]

        fig = go.Figure(go.Bar(
            x=faixas,
            y=valores,
            marker=dict(
                color=cores_bar,
                line=dict(color="#0d1415", width=1),
            ),
            text=[f"{p:.1f}%" for p in pcts],
            textposition="outside",
            textfont=dict(family="DM Mono", size=11, color="rgba(255,255,255,0.6)"),
            hovertemplate="<b>%{x}</b><br>R$ %{y:,.2f}<extra></extra>",
        ))
        fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            margin=dict(t=30, b=10, l=0, r=0),
            height=280,
            showlegend=False,
            xaxis=dict(
                tickfont=dict(family="DM Mono", size=11, color="rgba(255,255,255,0.5)"),
                gridcolor="rgba(255,255,255,0.04)",
                linecolor="rgba(255,255,255,0.06)",
            ),
            yaxis=dict(
                tickfont=dict(family="DM Mono", size=10, color="rgba(255,255,255,0.3)"),
                gridcolor="rgba(255,255,255,0.04)",
                tickformat=",.0f",
                title=dict(text="R$", font=dict(color="rgba(255,255,255,0.2)", size=10)),
            ),
            bargap=0.3,
        )
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

        # Legenda de cores
        st.markdown("""
        <div style="display:flex;gap:16px;font-size:11px;font-family:'DM Mono',monospace;
                    color:rgba(255,255,255,0.4);margin-top:-8px;">
            <span style="display:flex;align-items:center;gap:5px;">
                <span style="width:10px;height:10px;border-radius:2px;background:#ff5a4a;display:inline-block;"></span>
                Até 30 dias — crítico
            </span>
            <span style="display:flex;align-items:center;gap:5px;">
                <span style="width:10px;height:10px;border-radius:2px;background:#f5a623;display:inline-block;"></span>
                31–180 dias — atenção
            </span>
            <span style="display:flex;align-items:center;gap:5px;">
                <span style="width:10px;height:10px;border-radius:2px;background:#4adb8a;display:inline-block;"></span>
                Acima de 180 dias — ok
            </span>
        </div>
        """, unsafe_allow_html=True)

    with col_seg:
        cs = dados["carteira_segmento"]
        total_seg = cs["total"] or 1

        segmentos = [
            ("Financeiro",          cs["financeiro"]["total"],    "#407b6e"),
            ("Comercial",           cs["comercial"]["total"],     "#4a9eff"),
            ("Industrial",          cs["industrial"],             "#c8f55a"),
            ("Serviços",            cs["servicos"]["total"],      "#f5a623"),
            ("Agronegócio",         cs["agronegocio"],            "#4adb8a"),
            ("Cartão de Crédito",   cs["cartao_credito"],         "#ff5a4a"),
            ("Setor Público",       cs["setor_publico"]["total"], "#a78bfa"),
            ("Factoring",           cs["factoring"]["total"],     "#fb923c"),
        ]
        segmentos = [(n, v, c) for n, v, c in segmentos if v > 0]

        st.markdown("""
        <div style="font-size:10px;font-family:'DM Mono',monospace;letter-spacing:0.1em;
                    text-transform:uppercase;color:rgba(255,255,255,0.3);margin-bottom:12px;">
            Segmento da carteira
        </div>
        """, unsafe_allow_html=True)

        for nome, valor, cor in segmentos:
            pct = round(valor / total_seg * 100, 1)
            st.markdown(f"""
            <div style="margin-bottom:10px;">
                <div style="display:flex;justify-content:space-between;
                            font-size:11px;font-family:'DM Mono',monospace;margin-bottom:4px;">
                    <span style="color:rgba(255,255,255,0.6);">{nome}</span>
                    <span style="color:{cor};font-weight:500;">{pct}%</span>
                </div>
                <div style="height:6px;background:rgba(255,255,255,0.06);border-radius:3px;overflow:hidden;">
                    <div style="height:100%;width:{pct}%;background:{cor};border-radius:3px;"></div>
                </div>
            </div>
            """, unsafe_allow_html=True)

        if not segmentos:
            st.markdown("""
            <div style="font-size:12px;font-family:'DM Mono',monospace;
                        color:rgba(255,255,255,0.2);padding:20px 0;">
                Nenhum segmento declarado.
            </div>
            """, unsafe_allow_html=True)

    # ── Separador ──
    st.markdown("<div style='margin:28px 0 0;padding-top:28px;border-top:1px solid rgba(64,123,110,0.15);'></div>",
                unsafe_allow_html=True)

    # ── Negócios do mês ──
    _secao("negócios realizados", "Movimentações do mês")

    col_n1, col_n2, col_n3, col_n4 = st.columns(4)
    negocios = [
        (col_n1, "Aquisições",    neg["aquisicoes"]["total"]["valor"],      neg["aquisicoes"]["total"]["quantidade"],      "#4adb8a"),
        (col_n2, "Alienações",    neg["alienacoes"]["total"]["valor"],       neg["alienacoes"]["total"]["quantidade"],       "#4a9eff"),
        (col_n3, "Substituições", neg["substituicoes"]["valor"],             neg["substituicoes"]["quantidade"],             "#f5a623"),
        (col_n4, "Recompras",     neg["recompras"]["valor"],                 neg["recompras"]["quantidade"],                 "#c8f55a"),
    ]

    for col, label, valor, qtd, cor in negocios:
        cor_val = cor if valor > 0 else "rgba(255,255,255,0.2)"
        with col:
            st.markdown(f"""
            <div style="background:rgba(255,255,255,0.02);border:1px solid rgba(64,123,110,0.18);
                        border-top:2px solid {cor_val};border-radius:10px;padding:16px 18px;">
                <div style="font-size:10px;font-family:'DM Mono',monospace;letter-spacing:0.08em;
                            text-transform:uppercase;color:rgba(255,255,255,0.35);margin-bottom:8px;">
                    {label}
                </div>
                <div style="font-size:22px;font-weight:500;font-family:'DM Mono',monospace;
                            color:{cor_val};line-height:1;margin-bottom:6px;">
                    {_fmt_brl(valor) if valor > 0 else "—"}
                </div>
                <div style="font-size:11px;color:rgba(255,255,255,0.3);">
                    {int(qtd)} operação(ões)
                </div>
            </div>
            """, unsafe_allow_html=True)

    # ── Alerta de originação zerada ──
    if neg["aquisicoes"]["total"]["valor"] == 0:
        st.markdown("""
        <div style="display:flex;gap:12px;padding:12px 14px;border-radius:8px;margin-top:16px;
                    background:rgba(255,90,74,0.08);border-left:3px solid #ff5a4a;">
            <span style="color:#ff5a4a;font-size:10px;margin-top:2px;">●</span>
            <div>
                <div style="font-size:13px;font-weight:500;color:#fff;margin-bottom:2px;">
                    Originação zerada no mês
                </div>
                <div style="font-size:12px;color:rgba(255,255,255,0.5);line-height:1.5;">
                    Nenhuma aquisição realizada. Com concentração de vencimentos no curto prazo,
                    o fundo tende a encolher caso não haja novas operações em abril.
                </div>
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
        # Cores com alto contraste entre si
        cores = ["#407b6e", "#c8f55a", "#4a9eff", "#f5a623"]

        fig = go.Figure(go.Pie(
            labels=labels, values=values,
            hole=0.68,
            marker=dict(colors=cores, line=dict(color="#0d1415", width=3)),
            textinfo="percent",
            textfont=dict(family="DM Mono", size=12, color="#fff"),
            hovertemplate="<b>%{label}</b><br>R$ %{value:,.2f}<br>%{percent}<extra></extra>",
            pull=[0.03, 0, 0, 0],
        ))
        fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            margin=dict(t=10, b=10, l=10, r=10),
            height=280,
            showlegend=True,
            legend=dict(
                font=dict(family="DM Mono", size=11, color="rgba(255,255,255,0.6)"),
                bgcolor="rgba(0,0,0,0)",
                orientation="v", x=1.02, y=0.5,
                itemsizing="constant",
            ),
            annotations=[dict(
                text=f"<b>{_fmt_brl(at['ativo_total'])}</b><br><span style='font-size:10px'>Ativo Total</span>",
                x=0.5, y=0.5,
                font=dict(size=14, color="#fff", family="DM Mono"),
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
            for i, (n, v, c, bg) in enumerate([
                ("Disponibilidades",     _fmt_brl(at["disponibilidades"]),          "#c8f55a", "rgba(200,245,90,0.04)"),
                ("Direitos Creditórios", _fmt_brl(at["dc_com_aquis"]["total"]),     "#407b6e", "rgba(64,123,110,0.06)"),
                ("Títulos Públicos",     _fmt_brl(at["titulos_publicos_federais"]), "#4a9eff", "rgba(74,158,255,0.04)"),
                ("Outros Ativos",        _fmt_brl(at["outros_ativos"]["total"]),    "#f5a623", "rgba(245,166,35,0.04)"),
                ("Ativo Total",          _fmt_brl(at["ativo_total"]),               "#4adb8a", "rgba(74,219,138,0.08)"),
                ("Passivo (a pagar)",    f"({_fmt_brl(passivo)})",                 "#ff5a4a", "rgba(255,90,74,0.06)"),
                ("Patrimônio Líquido",   _fmt_brl(pl["pl"]),                        "#c8f55a", "rgba(200,245,90,0.08)"),
            ])
        ]) + """
            </tbody>
        </table>
        """, unsafe_allow_html=True)

        # Legenda de cores
        st.markdown("""
        <div style="display:flex;flex-wrap:wrap;gap:12px;margin-top:16px;
                    font-size:11px;font-family:'DM Mono',monospace;">
            <span style="display:flex;align-items:center;gap:6px;color:rgba(255,255,255,0.4);">
                <span style="width:10px;height:10px;border-radius:2px;background:#407b6e;display:inline-block;"></span>
                Direitos Creditórios
            </span>
            <span style="display:flex;align-items:center;gap:6px;color:rgba(255,255,255,0.4);">
                <span style="width:10px;height:10px;border-radius:2px;background:#c8f55a;display:inline-block;"></span>
                Disponibilidades
            </span>
            <span style="display:flex;align-items:center;gap:6px;color:rgba(255,255,255,0.4);">
                <span style="width:10px;height:10px;border-radius:2px;background:#4a9eff;display:inline-block;"></span>
                Títulos Públicos
            </span>
            <span style="display:flex;align-items:center;gap:6px;color:rgba(255,255,255,0.4);">
                <span style="width:10px;height:10px;border-radius:2px;background:#f5a623;display:inline-block;"></span>
                Outros
            </span>
        </div>
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

    with abas[1]:
        _aba_carteira(dados, metricas)

    with abas[2]:
        _aba_inadimplencia(dados, metricas)

    for i, nome in enumerate(["Cotas",
                               "Risco de Crédito", "Cedentes", "Relatórios"], start=3):
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