"""
app.py — Entry point da aplicação FIDC · RAIZ
"""

from pathlib import Path
import streamlit as st

st.set_page_config(
    page_title="RAIZ · FIDC",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

from core.auth import (
    inicializar_sessao, sessao_ativa, usuario_logado,
    fazer_login, fazer_logout, verificar_login,
)
from core.processor import processar_pendentes

BASE_DIR = Path(__file__).parent

LOGO_SVG = """<svg width="40" height="40" viewBox="0 0 60 60" fill="none">
  <path d="M30 4 L52 14 L52 34 C52 46 30 56 30 56 C30 56 8 46 8 34 L8 14 Z"
        stroke="rgba(255,255,255,0.2)" stroke-width="1.5" fill="rgba(64,123,110,0.15)"/>
  <line x1="30" y1="14" x2="30" y2="46" stroke="white" stroke-width="1.5"/>
  <line x1="30" y1="22" x2="22" y2="30" stroke="white" stroke-width="1.5"/>
  <line x1="30" y1="22" x2="38" y2="30" stroke="white" stroke-width="1.5"/>
  <line x1="30" y1="30" x2="20" y2="38" stroke="white" stroke-width="1.5"/>
  <line x1="30" y1="30" x2="40" y2="38" stroke="white" stroke-width="1.5"/>
</svg>"""


# ---------------------------------------------------------------------------
# ESTILOS GLOBAIS
# ---------------------------------------------------------------------------

def _aplicar_estilo():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500&family=DM+Mono:wght@400;500&display=swap');

    html, body, [class*="css"] { font-family: 'DM Sans', sans-serif !important; }
    header[data-testid="stHeader"] { display: none !important; }
    footer { display: none !important; }
    #MainMenu { display: none !important; }
    .block-container { padding-top: 0 !important; padding-bottom: 2rem !important; }
    .stApp { background: linear-gradient(180deg, #0d1415 0%, #1e2e30 100%) !important; }

    [data-testid="stSidebar"] {
        background: #0a1012 !important;
        border-right: 1px solid rgba(64,123,110,0.2) !important;
    }
    [data-testid="stSidebar"] p,
    [data-testid="stSidebar"] span,
    [data-testid="stSidebar"] label { color: #fff !important; }

    div[data-testid="stFormSubmitButton"] > button {
        background: #407b6e !important;
        border: none !important;
        border-radius: 8px !important;
        color: #fff !important;
        font-weight: 500 !important;
    }
    div[data-testid="stFormSubmitButton"] > button:hover {
        background: #4d9485 !important;
        border: none !important;
    }

    .stButton > button {
        border: 1px solid rgba(64,123,110,0.4) !important;
        background: transparent !important;
        color: rgba(255,255,255,0.7) !important;
        border-radius: 8px !important;
    }
    .stButton > button:hover {
        background: rgba(64,123,110,0.1) !important;
        color: #fff !important;
        border: 1px solid rgba(64,123,110,0.4) !important;
    }

    input[type="text"], input[type="password"] {
        background: rgba(255,255,255,0.04) !important;
        border: 1px solid rgba(255,255,255,0.12) !important;
        border-radius: 8px !important;
        color: #fff !important;
    }
    input[type="text"]:focus, input[type="password"]:focus {
        border-color: #407b6e !important;
        box-shadow: none !important;
    }
    input::placeholder { color: rgba(255,255,255,0.2) !important; }

    label[data-testid="stWidgetLabel"] p {
        font-size: 11px !important;
        font-family: 'DM Mono', monospace !important;
        letter-spacing: 0.08em !important;
        text-transform: uppercase !important;
        color: rgba(255,255,255,0.45) !important;
    }

    [data-testid="stMetric"] {
        background: rgba(255,255,255,0.03) !important;
        border: 1px solid rgba(64,123,110,0.2) !important;
        border-radius: 10px !important;
        padding: 1rem !important;
    }
    [data-testid="stMetricLabel"] p {
        font-family: 'DM Mono', monospace !important;
        font-size: 11px !important;
        letter-spacing: 0.08em !important;
        text-transform: uppercase !important;
        color: rgba(255,255,255,0.45) !important;
    }
    [data-testid="stMetricValue"] {
        font-family: 'DM Mono', monospace !important;
        color: #fff !important;
    }
    </style>
    """, unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# PROCESSOR
# ---------------------------------------------------------------------------

@st.cache_resource(show_spinner=False)
def _processar_na_inicializacao():
    return processar_pendentes(BASE_DIR)


def _renderizar_log(resumo: dict):
    fundos = {k: v for k, v in resumo.items() if k != "_totais"}
    totais = resumo.get("_totais", {})
    linhas = []
    linhas.append('<div style="background:#080d0e;border:1px solid rgba(64,123,110,0.25);border-radius:10px;padding:14px 18px;font-family:DM Mono,monospace;font-size:13px;line-height:2;margin-bottom:1.5rem;">')
    linhas.append('<span style="color:#2e4446;">── RAIZ · Inicialização ─────────────────────────</span><br>')
    for fundo_id, r in fundos.items():
        if r["total"] == 0:
            linhas.append(f'<span style="color:#2e4446;">  ○  {fundo_id.upper():<18} nenhum arquivo pendente</span><br>')
        elif r["erro"] == 0:
            linhas.append(f'<span style="color:#4adb8a;">  ✓  {fundo_id.upper():<18} {r["sucesso"]} arquivo(s) processado(s)</span><br>')
        else:
            linhas.append(f'<span style="color:#f5a623;">  ⚠  {fundo_id.upper():<18} {r["sucesso"]} ok · {r["erro"]} com erro</span><br>')
    linhas.append('<span style="color:#2e4446;">─────────────────────────────────────────────────</span><br>')
    if totais.get("total", 0) == 0:
        linhas.append('<span style="color:#2e4446;">  ─  Cache atualizado. Nenhum arquivo novo.</span><br>')
    elif totais.get("erro", 0) == 0:
        linhas.append(f'<span style="color:#4adb8a;">  ✓  Sistema pronto · {totais["sucesso"]} arquivo(s) processado(s)</span><br>')
    else:
        linhas.append(f'<span style="color:#f5a623;">  ⚠  {totais["sucesso"]} ok · {totais["erro"]} com erro · verifique inbox/</span><br>')
    linhas.append('</div>')
    st.markdown("".join(linhas), unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# TELA DE LOGIN
# ---------------------------------------------------------------------------

def _tela_login():
    _, col, _ = st.columns([1.2, 1, 1.2])

    with col:
        # 1. Logo e marca — HTML puro, fora do form
        st.markdown(f"""
        <div style="text-align:center; padding:48px 0 28px;">
            {LOGO_SVG}
            <div style="font-size:30px;font-weight:500;letter-spacing:0.14em;
                        color:#fff;margin-top:12px;line-height:1;">
                RA<span style="color:#407b6e;">İ</span>Z
            </div>
            <div style="font-size:10px;font-family:'DM Mono',monospace;
                        letter-spacing:0.15em;text-transform:uppercase;
                        color:rgba(255,255,255,0.3);margin-top:6px;">
                Gestão de Ativos
            </div>
        </div>
        """, unsafe_allow_html=True)

        # 2. Cabeçalho do card — HTML puro, fora do form
        st.markdown("""
        <div style="background:rgba(255,255,255,0.03);border:1px solid rgba(64,123,110,0.2);
                    border-radius:14px;padding:24px 24px 0;">
            <div style="font-size:10px;font-family:'DM Mono',monospace;
                        letter-spacing:0.12em;text-transform:uppercase;
                        color:#407b6e;margin-bottom:6px;">
                Acesso restrito
            </div>
            <div style="font-size:20px;font-weight:500;color:#fff;margin-bottom:4px;">
                Entre na sua conta
            </div>
            <div style="font-size:13px;color:rgba(255,255,255,0.4);margin-bottom:20px;">
                Credenciais fornecidas pelo administrador
            </div>
        </div>
        """, unsafe_allow_html=True)

        # 3. Formulário nativo do Streamlit — separado do HTML acima
        with st.form("form_login", clear_on_submit=False):
            username = st.text_input("Usuário", placeholder="seu.usuario")
            password = st.text_input("Senha", type="password", placeholder="••••••••")
            entrar   = st.form_submit_button("Entrar →", use_container_width=True, type="primary")

        # 4. Rodapé do card — HTML puro, fora do form
        st.markdown("""
        <div style="border-top:1px solid rgba(64,123,110,0.12);margin-top:4px;
                    padding:14px 0 0;text-align:center;">
            <div style="display:flex;gap:8px;justify-content:center;flex-wrap:wrap;">
                <span style="font-size:11px;font-family:'DM Mono',monospace;padding:3px 12px;
                             border-radius:20px;border:1px solid rgba(64,123,110,0.3);
                             color:rgba(255,255,255,0.35);background:rgba(64,123,110,0.08);">
                    Dashboard
                </span>
                <span style="font-size:11px;font-family:'DM Mono',monospace;padding:3px 12px;
                             border-radius:20px;border:1px solid rgba(64,123,110,0.3);
                             color:rgba(255,255,255,0.35);background:rgba(64,123,110,0.08);">
                    Documentos
                </span>
                <span style="font-size:11px;font-family:'DM Mono',monospace;padding:3px 12px;
                             border-radius:20px;border:1px solid rgba(64,123,110,0.3);
                             color:rgba(255,255,255,0.35);background:rgba(64,123,110,0.08);">
                    Precificação
                </span>
            </div>
            <div style="font-size:11px;font-family:'DM Mono',monospace;
                        color:rgba(255,255,255,0.18);margin-top:14px;line-height:1.7;">
                Acesso restrito · Uso interno RAIZ<br>
                Em caso de problemas, contate o administrador
            </div>
        </div>
        """, unsafe_allow_html=True)

        # 5. Feedback de login
        if entrar:
            if not username or not password:
                st.error("Preencha usuário e senha.")
            else:
                usuario = verificar_login(BASE_DIR, username, password)
                if usuario:
                    fazer_login(st, usuario)
                    st.rerun()
                else:
                    st.error("Usuário ou senha incorretos.")


# ---------------------------------------------------------------------------
# SIDEBAR
# ---------------------------------------------------------------------------

def _renderizar_sidebar(usuario: dict):
    with st.sidebar:
        # Widget nativo garante que a sidebar é ativada pelo Streamlit
        st.markdown("&nbsp;", unsafe_allow_html=True)
        st.markdown(f"""
        <div style="padding:16px 0 20px;border-bottom:1px solid rgba(64,123,110,0.2);margin-bottom:16px;">
            <div style="display:flex;align-items:center;gap:10px;">
                {LOGO_SVG}
                <div>
                    <div style="font-size:17px;font-weight:500;letter-spacing:0.1em;color:#fff;">
                        RA<span style="color:#407b6e;">İ</span>Z
                    </div>
                    <div style="font-size:9px;font-family:'DM Mono',monospace;
                                color:rgba(255,255,255,0.3);letter-spacing:0.1em;text-transform:uppercase;">
                        Gestão de Ativos
                    </div>
                </div>
            </div>
        </div>
        <div style="padding-bottom:16px;border-bottom:1px solid rgba(64,123,110,0.12);margin-bottom:16px;">
            <div style="font-size:10px;font-family:'DM Mono',monospace;color:rgba(255,255,255,0.3);
                        text-transform:uppercase;letter-spacing:0.08em;margin-bottom:4px;">
                Usuário
            </div>
            <div style="font-size:14px;color:#fff;font-weight:500;margin-bottom:6px;">
                {usuario['nome']}
            </div>
            <span style="font-size:10px;font-family:'DM Mono',monospace;padding:2px 8px;
                         border-radius:10px;background:rgba(64,123,110,0.18);color:#407b6e;
                         border:1px solid rgba(64,123,110,0.3);">
                {usuario['role']}
            </span>
        </div>
        """, unsafe_allow_html=True)

        if st.button("Sair", use_container_width=True):
            fazer_logout(st)
            st.rerun()


# ---------------------------------------------------------------------------
# HOME
# ---------------------------------------------------------------------------

def _tela_home(usuario: dict):
    st.markdown(f"""
    <div style="padding:40px 0 32px;border-bottom:1px solid rgba(64,123,110,0.15);margin-bottom:32px;">
        <div style="font-size:10px;font-family:'DM Mono',monospace;letter-spacing:0.14em;
                    text-transform:uppercase;color:#407b6e;margin-bottom:10px;">
            FIDC · Painel de Gestão Integrada
        </div>
        <div style="font-size:28px;font-weight:500;color:#fff;margin-bottom:8px;line-height:1.2;">
            Bem-vindo, {usuario['nome']}
        </div>
        <div style="font-size:14px;color:rgba(255,255,255,0.35);max-width:480px;line-height:1.6;">
            Plataforma de monitoramento, análise e precificação de
            fundos de investimento em direitos creditórios.
        </div>
    </div>
    """, unsafe_allow_html=True)

    ICON_DASH = '''<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#407b6e" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
      <rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/>
      <rect x="14" y="14" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/>
    </svg>'''
    ICON_DOC = '''<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#407b6e" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
      <polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/>
    </svg>'''
    ICON_PREC = '''<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#407b6e" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
      <line x1="12" y1="1" x2="12" y2="23"/><path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/>
    </svg>'''

    cards = [
        (ICON_DASH, "Dashboard",    "01", "pages/01_dashboard.py",
         "Monitore indicadores, inadimplência, PL, cotas e SCR em tempo real.",
         ["Inadimplência", "Vencimentos", "SCR Bacen", "Cotas"]),
        (ICON_DOC,  "Documentos",   "02", "pages/02_documentos.py",
         "Acesse regulamentos e relatórios com resumo gerado por inteligência artificial.",
         ["Regulamento", "Lâmina", "Resumo IA", "Histórico"]),
        (ICON_PREC, "Precificação", "03", "pages/03_precificacao.py",
         "Precifique pools de direitos creditórios com modelos quantitativos.",
         ["Modelagem", "Cenários", "Exportação", "Histórico"]),
    ]

    c1, c2, c3 = st.columns(3)
    for col, (icon, titulo, numero, page, desc, tags) in zip([c1, c2, c3], cards):
        tags_html = "".join([
            f'<span style="font-size:10px;font-family:\'DM Mono\',monospace;padding:2px 8px;'
            f'border-radius:10px;border:1px solid rgba(64,123,110,0.25);'
            f'color:rgba(255,255,255,0.3);background:rgba(64,123,110,0.06);'
            f'margin-right:4px;">{t}</span>'
            for t in tags
        ])
        with col:
            st.markdown(f"""
            <div style="background:rgba(255,255,255,0.02);border:1px solid rgba(64,123,110,0.18);
                        border-top:2px solid #407b6e;border-radius:12px;padding:24px 24px 12px;">
                <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:18px;">
                    <div style="width:40px;height:40px;border-radius:10px;
                                background:rgba(64,123,110,0.1);border:1px solid rgba(64,123,110,0.2);
                                display:flex;align-items:center;justify-content:center;">
                        {icon}
                    </div>
                    <div style="font-size:11px;font-family:'DM Mono',monospace;
                                color:rgba(255,255,255,0.15);letter-spacing:0.1em;">
                        {numero}
                    </div>
                </div>
                <div style="font-size:16px;font-weight:500;color:#fff;margin-bottom:8px;">{titulo}</div>
                <div style="font-size:13px;color:rgba(255,255,255,0.4);line-height:1.7;margin-bottom:16px;">{desc}</div>
                <div style="display:flex;flex-wrap:wrap;gap:4px;margin-bottom:16px;">{tags_html}</div>
            </div>
            """, unsafe_allow_html=True)

            # Botão de navegação nativo do Streamlit
            st.page_link(page, label=f"Acessar {titulo} →", use_container_width=True)

    from datetime import datetime
    agora = datetime.now().strftime("%d/%m/%Y às %H:%M")
    st.markdown(f"""
    <div style="margin-top:32px;padding-top:20px;border-top:1px solid rgba(64,123,110,0.12);
                display:flex;align-items:center;justify-content:space-between;
                font-size:11px;font-family:'DM Mono',monospace;color:rgba(255,255,255,0.2);">
        <div style="display:flex;align-items:center;gap:6px;">
            <span style="width:6px;height:6px;border-radius:50%;background:#407b6e;display:inline-block;"></span>
            Todos os sistemas operacionais
        </div>
        <div>Último acesso: {agora}</div>
        <div>RAIZ · Gestão de Ativos · v1.0</div>
    </div>
    """, unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------

def main():
    _aplicar_estilo()
    inicializar_sessao(st)

    with st.spinner("Verificando arquivos pendentes..."):
        resumo = _processar_na_inicializacao()

    totais = resumo.get("_totais", {})
    if totais.get("total", 0) > 0 or totais.get("erro", 0) > 0:
        _renderizar_log(resumo)

    if not sessao_ativa(st):
        _tela_login()
        return

    usuario = usuario_logado(st)
    _renderizar_sidebar(usuario)
    _tela_home(usuario)


if __name__ == "__main__":
    main()