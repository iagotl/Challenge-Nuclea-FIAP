"""
pages/02_documentos.py
Repositório de documentos — FIDC · RAIZ
"""

from pathlib import Path
from datetime import datetime
import streamlit as st
import pdfplumber
import io

BASE_DIR = Path(__file__).parent.parent

from core.auth import sessao_ativa, usuario_logado, fundos_permitidos
from core.loader import (
    listar_fundos, listar_documentos,
    carregar_documento_insight, carregar_pdf_bytes,
    carregar_notas, salvar_notas,
    adicionar_nota, editar_nota, apagar_nota,
    notas_existem, TIPOS_DOCUMENTO,
)

st.set_page_config(
    page_title="RAIZ · Documentos",
    page_icon="📄",
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
    .block-container{ padding-top:0 !important; padding-bottom:2rem !important; }
    .stApp{ background:linear-gradient(180deg,#0d1415 0%,#1e2e30 100%) !important; }
    .stSelectbox > div > div{
        background:rgba(255,255,255,0.04) !important;
        border:1px solid rgba(64,123,110,0.25) !important;
        border-radius:8px !important; color:#fff !important;
    }
    .stSelectbox label p{
        font-size:11px !important; font-family:'DM Mono',monospace !important;
        letter-spacing:0.08em !important; text-transform:uppercase !important;
        color:rgba(255,255,255,0.4) !important;
    }
    .stTextArea textarea{
        background:#ffffff !important;
        border:1px solid rgba(64,123,110,0.4) !important;
        border-radius:8px !important; color:#0d1415 !important;
        font-family:'DM Sans',sans-serif !important; font-size:14px !important;
    }
    .stTextArea textarea::placeholder{ color:#999 !important; }
    .stTextInput input{
        background:#ffffff !important;
        border:1px solid rgba(64,123,110,0.4) !important;
        border-radius:8px !important; color:#0d1415 !important;
    }
    .stTextInput input::placeholder{ color:#999 !important; }
    .stTextArea label p, .stTextInput label p {
        color:rgba(255,255,255,0.45) !important;
        font-size:11px !important; font-family:'DM Mono',monospace !important;
        text-transform:uppercase !important; letter-spacing:0.08em !important;
    }
    div[data-testid="stFormSubmitButton"] > button,
    .stButton > button[kind="primary"]{
        background:#407b6e !important; border:none !important;
        border-radius:8px !important; color:#fff !important; font-weight:500 !important;
    }
    .stButton > button[kind="primary"]:hover{ background:#4d9485 !important; }
    .stButton > button{
        border:1px solid rgba(64,123,110,0.4) !important;
        background:transparent !important; color:rgba(255,255,255,0.6) !important;
        border-radius:8px !important;
    }
    .stButton > button:hover{
        background:rgba(64,123,110,0.1) !important;
        color:#fff !important; border-color:rgba(64,123,110,0.6) !important;
    }
    /* Botões de ação de nota (editar/apagar) — sem borda, compactos */
    [data-testid="column"] .stButton > button[title="Editar nota"] {
        border:none !important; background:transparent !important;
        color:#4adb8a !important; font-size:14px !important;
        padding:4px 8px !important; min-height:32px !important;
    }
    [data-testid="column"] .stButton > button[title="Apagar nota"] {
        border:none !important; background:transparent !important;
        color:#ff5a4a !important; font-size:14px !important;
        padding:4px 8px !important; min-height:32px !important;
    }
    [data-testid="column"] .stButton > button[title="Editar nota"]:hover {
        background:rgba(74,219,138,0.08) !important; border-radius:6px !important;
    }
    [data-testid="column"] .stButton > button[title="Apagar nota"]:hover {
        background:rgba(255,90,74,0.08) !important; border-radius:6px !important;
    }
    /* Page link — Home */
    [data-testid="stPageLink"] a,
    [data-testid="stPageLink"] span,
    [data-testid="stPageLink"] p {
        color: #ffffff !important;
    }

        iframe{ border-radius:8px; border:1px solid rgba(64,123,110,0.2); }
    /* Chat — força texto branco */
    .stMarkdown p, .stMarkdown li, .stMarkdown h1,
    .stMarkdown h2, .stMarkdown h3, .stMarkdown span,
    .stMarkdown td, .stMarkdown th {
        color: #ffffff !important;
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
# HELPERS
# ---------------------------------------------------------------------------

def _md_to_html(md: str) -> str:
    import re
    html = []
    lines = md.split("\n")
    in_list = False
    in_table = False
    table_rows = []

    def _inline(text):
        text = re.sub(r'\*\*\*(.+?)\*\*\*', r'<strong><em>\1</em></strong>', text)
        text = re.sub(r'\*\*(.+?)\*\*',     r'<strong>\1</strong>', text)
        text = re.sub(r'\*(.+?)\*',          r'<em>\1</em>', text)
        return text

    def _flush_table():
        if not table_rows: return ""
        out = '<table style="width:100%;border-collapse:collapse;font-size:13px;margin:16px 0;">'
        for ri, row in enumerate(table_rows):
            cells = [c.strip() for c in row.strip("|").split("|")]
            if ri == 0:
                out += "<thead><tr>" + "".join(
                    f'<th style="text-align:left;padding:8px 12px;font-size:10px;'
                    f'letter-spacing:0.08em;text-transform:uppercase;'
                    f'color:rgba(255,255,255,0.35);border-bottom:1px solid rgba(64,123,110,0.25);">{c}</th>'
                    for c in cells) + "</tr></thead><tbody>"
            elif re.match(r'[\s|:-]+$', row.replace("|","")):
                continue
            else:
                out += "<tr>" + "".join(
                    f'<td style="padding:8px 12px;color:rgba(255,255,255,0.75);'
                    f'border-bottom:1px solid rgba(255,255,255,0.05);">{_inline(c)}</td>'
                    for c in cells) + "</tr>"
        out += "</tbody></table>"
        return out

    i = 0
    while i < len(lines):
        line = lines[i]
        if re.match(r'^---+$', line.strip()):
            if in_list:  html.append("</ul>"); in_list = False
            if in_table: html.append(_flush_table()); table_rows = []; in_table = False
            html.append('<hr style="border:none;border-top:1px solid rgba(64,123,110,0.2);margin:20px 0;">')
            i += 1; continue
        if line.strip().startswith("|"):
            if in_list: html.append("</ul>"); in_list = False
            in_table = True; table_rows.append(line); i += 1; continue
        elif in_table:
            html.append(_flush_table()); table_rows = []; in_table = False
        if line.startswith("## "):
            if in_list: html.append("</ul>"); in_list = False
            text = _inline(line[3:].strip())
            html.append(f'<h2 style="font-size:20px;font-weight:500;color:#407b6e;'
                        f'margin:28px 0 10px;padding-bottom:8px;'
                        f'border-bottom:1px solid rgba(64,123,110,0.2);">{text}</h2>')
            i += 1; continue
        if line.startswith("### "):
            if in_list: html.append("</ul>"); in_list = False
            text = _inline(line[4:].strip())
            html.append(f'<h3 style="font-size:15px;font-weight:500;color:#407b6e;margin:20px 0 8px;">{text}</h3>')
            i += 1; continue
        if line.startswith("- ") or line.startswith("* "):
            if not in_list: html.append('<ul style="margin:8px 0 12px;padding-left:20px;">'); in_list = True
            text = _inline(line[2:].strip())
            html.append(f'<li style="color:#fff;font-size:14px;line-height:1.8;margin-bottom:4px;">{text}</li>')
            i += 1; continue
        elif in_list:
            html.append("</ul>"); in_list = False
        if not line.strip(): i += 1; continue
        text = _inline(line.strip())
        html.append(f'<p style="color:#fff;font-size:14px;line-height:1.8;margin:0 0 10px;">{text}</p>')
        i += 1

    if in_list:  html.append("</ul>")
    if in_table: html.append(_flush_table())
    return "\n".join(html)


def _fmt_dt(iso: str) -> str:
    try:
        return datetime.fromisoformat(iso).strftime("%d/%m/%Y às %H:%M")
    except Exception:
        return iso


def _sem_documentos():
    st.markdown("""
    <div style="text-align:center;padding:80px 0;color:rgba(255,255,255,0.2);">
        <div style="font-size:32px;margin-bottom:12px;">○</div>
        <div style="font-size:13px;font-family:'DM Mono',monospace;">
            Nenhum documento disponível para este fundo.
        </div>
    </div>
    """, unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# ABA: VISUALIZAR PDF
# ---------------------------------------------------------------------------

def _aba_pdf(doc: dict):
    import base64
    st.markdown(f"""
    <div style="font-size:10px;font-family:'DM Mono',monospace;letter-spacing:0.1em;
                text-transform:uppercase;color:rgba(255,255,255,0.3);margin-bottom:12px;">
        {doc["label"]} · {doc["nome_base"]}
        {f'· <span style="color:#407b6e;">{doc["versao"]}</span>' if doc["versao"] else ""}
        {f'· {doc["data"]}' if doc["data"] else ""}
    </div>
    """, unsafe_allow_html=True)

    pdf_bytes = carregar_pdf_bytes(doc["path"])
    if pdf_bytes:
        st.download_button(
            label="⬇ Baixar PDF",
            data=pdf_bytes,
            file_name=doc["nome"],
            mime="application/pdf",
        )
        b64 = base64.b64encode(pdf_bytes).decode("utf-8")
        st.markdown(
            f'<iframe src="data:application/pdf;base64,{b64}" '
            f'width="100%" height="860px" type="application/pdf"></iframe>',
            unsafe_allow_html=True,
        )
    else:
        st.error("Não foi possível carregar o PDF.")


# ---------------------------------------------------------------------------
# ABA: RESUMO COM IA
# ---------------------------------------------------------------------------

def _aba_resumo(base_dir: Path, fundo_id: str, tipo: str, doc: dict):
    key_show = f"insight_{fundo_id}_{tipo}_{doc['stem']}"
    if key_show not in st.session_state:
        st.session_state[key_show] = False

    if not doc["tem_insight"]:
        st.markdown("""
        <div style="text-align:center;padding:60px 0;">
            <div style="font-size:13px;font-family:'DM Mono',monospace;
                        color:rgba(255,255,255,0.2);margin-bottom:6px;">
                Resumo não disponível para este documento
            </div>
        </div>
        """, unsafe_allow_html=True)
        return

    if not st.session_state[key_show]:
        st.markdown("""
        <div style="text-align:center;padding:60px 0 40px;">
            <div style="font-size:32px;margin-bottom:16px;">✨</div>
            <div style="font-size:16px;font-weight:500;color:#fff;margin-bottom:8px;">
                Resumo com IA disponível
            </div>
            <div style="font-size:13px;color:rgba(255,255,255,0.4);margin-bottom:28px;">
                Clique para gerar o resumo deste documento
            </div>
        </div>
        """, unsafe_allow_html=True)
        _, col_btn, _ = st.columns([1, 2, 1])
        with col_btn:
            if st.button("✨ Gerar resumo com IA", use_container_width=True, type="primary"):
                st.session_state[key_show] = True
                st.rerun()
        return

    insight_md = carregar_documento_insight(base_dir, fundo_id, tipo, doc["stem"])
    if insight_md:
        linhas = insight_md.split("\n")
        if linhas[0].strip() == "---":
            fim = next((i for i, l in enumerate(linhas[1:], 1) if l.strip() == "---"), None)
            if fim: linhas = linhas[fim + 1:]
        html = _md_to_html("\n".join(linhas).strip())
        st.markdown(
            f'<div style="background:rgba(255,255,255,0.02);border:1px solid rgba(64,123,110,0.2);'
            f'border-radius:12px;padding:24px 28px;">{html}</div>',
            unsafe_allow_html=True
        )
    if st.button("✕ Fechar resumo"):
        st.session_state[key_show] = False
        st.rerun()


# ---------------------------------------------------------------------------
# ABA: NOTAS
# ---------------------------------------------------------------------------

def _aba_notas(base_dir: Path, fundo_id: str, tipo: str, doc: dict):
    stem  = doc["stem"]
    notas = carregar_notas(base_dir, fundo_id, tipo, stem)

    # Chaves de estado
    key_nova    = f"nova_nota_{fundo_id}_{tipo}_{stem}"
    key_editing = f"editing_{fundo_id}_{tipo}_{stem}"

    if key_nova    not in st.session_state: st.session_state[key_nova]    = False
    if key_editing not in st.session_state: st.session_state[key_editing] = None

    # ── Header ──
    col_title, col_btn = st.columns([3, 1])
    with col_title:
        st.markdown(f"""
        <div style="padding:8px 0 16px;">
            <div style="font-size:10px;font-family:'DM Mono',monospace;letter-spacing:0.1em;
                        text-transform:uppercase;color:rgba(255,255,255,0.3);margin-bottom:4px;">
                Notas · {doc["nome_base"]}
            </div>
            <div style="font-size:16px;font-weight:500;color:#fff;">
                Anotações: {len(notas)}
            </div>
        </div>
        """, unsafe_allow_html=True)
    with col_btn:
        st.markdown("<div style='padding-top:18px;'>", unsafe_allow_html=True)
        if st.button("＋ Nova nota", use_container_width=True, type="primary"):
            st.session_state[key_nova]    = True
            st.session_state[key_editing] = None
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<hr style='border:none;border-top:1px solid rgba(64,123,110,0.15);margin:0 0 16px;'>",
                unsafe_allow_html=True)

    # ── Formulário nova nota ──
    if st.session_state[key_nova]:
        with st.container():
            st.markdown("""
            <div style="background:rgba(64,123,110,0.06);border:1px solid rgba(64,123,110,0.25);
                        border-radius:10px;padding:16px 16px 4px;margin-bottom:16px;">
            """, unsafe_allow_html=True)
            titulo_novo   = st.text_input("Título da nota", placeholder="Ex: Cláusula importante", key=f"titulo_novo_{stem}")
            conteudo_novo = st.text_area("Conteúdo", placeholder="Escreva sua anotação aqui... Suporte a Markdown.", height=150, key=f"conteudo_novo_{stem}")
            col_s, col_c, _ = st.columns([1, 1, 3])
            with col_s:
                if st.button("💾 Salvar", key=f"salvar_novo_{stem}", type="primary", use_container_width=True):
                    if conteudo_novo.strip():
                        adicionar_nota(base_dir, fundo_id, tipo, stem, titulo_novo, conteudo_novo)
                        st.session_state[key_nova] = False
                        st.rerun()
                    else:
                        st.warning("Escreva algo antes de salvar.")
            with col_c:
                if st.button("✕ Cancelar", key=f"cancelar_novo_{stem}", use_container_width=True):
                    st.session_state[key_nova] = False
                    st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

    # ── Lista de notas ──
    if not notas:
        st.markdown("""
        <div style="text-align:center;padding:60px 0;">
            <div style="font-size:28px;margin-bottom:12px;">📝</div>
            <div style="font-size:13px;font-family:'DM Mono',monospace;
                        color:rgba(255,255,255,0.2);margin-bottom:6px;">
                Nenhuma anotação ainda
            </div>
            <div style="font-size:11px;color:rgba(255,255,255,0.15);">
                Clique em "＋ Nova nota" para começar
            </div>
        </div>
        """, unsafe_allow_html=True)
        return

    for nota in notas:
        is_editing = st.session_state[key_editing] == nota["id"]

        with st.container():
            if is_editing:
                # Modo edição
                st.markdown(f"""
                <div style="background:rgba(64,123,110,0.06);border:1px solid rgba(64,123,110,0.3);
                            border-radius:10px;padding:16px 16px 4px;margin-bottom:12px;">
                """, unsafe_allow_html=True)
                titulo_edit   = st.text_input("Título", value=nota["titulo"], key=f"titulo_edit_{nota['id']}")
                conteudo_edit = st.text_area("Conteúdo", value=nota["conteudo"], height=200, key=f"conteudo_edit_{nota['id']}")
                col_s, col_c, _ = st.columns([1, 1, 3])
                with col_s:
                    if st.button("💾 Salvar", key=f"salvar_{nota['id']}", type="primary", use_container_width=True):
                        editar_nota(base_dir, fundo_id, tipo, stem, nota["id"], titulo_edit, conteudo_edit)
                        st.session_state[key_editing] = None
                        st.rerun()
                with col_c:
                    if st.button("✕ Cancelar", key=f"cancel_{nota['id']}", use_container_width=True):
                        st.session_state[key_editing] = None
                        st.rerun()
                st.markdown("</div>", unsafe_allow_html=True)
            else:
                # Modo visualização
                col_nota, col_acoes = st.columns([5, 1])
                with col_nota:
                    html_nota = _md_to_html(nota["conteudo"])
                    criado    = _fmt_dt(nota["criado_em"])
                    editado   = _fmt_dt(nota["editado_em"])
                    meta      = f"Criado em {criado}"
                    if nota["criado_em"] != nota["editado_em"]:
                        meta += f" · Editado em {editado}"

                    st.markdown(f"""
                    <div style="background:rgba(255,255,255,0.02);border:1px solid rgba(64,123,110,0.15);
                                border-left:3px solid #407b6e;border-radius:0 10px 10px 0;
                                padding:16px 20px;margin-bottom:12px;">
                        <div style="font-size:13px;font-weight:500;color:#fff;margin-bottom:10px;">
                            {nota["titulo"]}
                        </div>
                        <div style="font-size:13px;color:rgba(255,255,255,0.75);line-height:1.7;">
                            {html_nota}
                        </div>
                        <div style="font-size:10px;font-family:'DM Mono',monospace;
                                    color:rgba(255,255,255,0.2);margin-top:10px;">
                            #{nota["id"]} · {meta}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

                with col_acoes:
                    col_e, col_d = st.columns(2)
                    with col_e:
                        if st.button("✏", key=f"edit_{nota['id']}", use_container_width=True, help="Editar nota"):
                            st.session_state[key_editing] = nota["id"]
                            st.session_state[key_nova]    = False
                            st.rerun()
                    with col_d:
                        if st.button("✕", key=f"del_{nota['id']}", use_container_width=True, help="Apagar nota"):
                            apagar_nota(base_dir, fundo_id, tipo, stem, nota["id"])
                            st.rerun()


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# CHAT COM DOCUMENTO
# ---------------------------------------------------------------------------

def _extrair_texto_pdf(pdf_path: Path) -> str:
    """Extrai texto de um PDF usando pdfplumber."""
    try:
        with pdfplumber.open(pdf_path) as pdf:
            paginas = []
            for i, page in enumerate(pdf.pages):
                texto = page.extract_text()
                if texto:
                    paginas.append(f"[Página {i+1}]\n{texto}")
            return "\n\n".join(paginas)
    except Exception as e:
        return ""


def _inicializar_gemini():
    """Carrega a API key e inicializa o cliente Gemini."""
    try:
        import google.generativeai as genai
        api_key = st.secrets.get("GEMINI_API_KEY", "")
        if not api_key:
            return None, "GEMINI_API_KEY não encontrada em .streamlit/secrets.toml"
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-2.5-flash")
        return model, None
    except ImportError:
        return None, "Biblioteca google-generativeai não instalada. Execute: pip install google-generativeai"
    except Exception as e:
        return None, str(e)


def _system_prompt(nome_doc: str, texto_doc: str) -> str:
    return f"""Você é o Assistente RAIZ, um especialista em fundos de investimento em direitos creditórios (FIDCs) da RAIZ Gestão de Ativos.

Você tem acesso ao conteúdo completo do documento: **{nome_doc}**

Conteúdo do documento:
---
{texto_doc[:15000]}
---

Regras que você deve seguir:
1. Responda SOMENTE com base no conteúdo do documento acima
2. Se a pergunta não puder ser respondida com o documento, diga claramente que a informação não está no documento
3. Você PODE responder perguntas gerais sobre mercado financeiro, FIDCs, regulamentação CVM e conceitos financeiros — mas sempre deixe claro quando estiver usando conhecimento geral e não o documento
4. Seja objetivo e preciso. Cite a seção ou cláusula do documento quando relevante
5. Responda sempre em português brasileiro
6. Nunca invente informações que não estejam no documento"""


def _aba_chat(base_dir: Path, fundo_id: str, tipo: str, doc: dict):
    """Aba de chat com o documento usando Gemini."""

    stem     = doc["stem"]
    key_hist = f"chat_hist_{fundo_id}_{tipo}_{stem}"
    key_ctx  = f"chat_ctx_{fundo_id}_{tipo}_{stem}"
    key_ini  = f"chat_ini_{fundo_id}_{tipo}_{stem}"

    # Inicializa histórico
    if key_hist not in st.session_state:
        st.session_state[key_hist] = []
    if key_ini not in st.session_state:
        st.session_state[key_ini] = False

    # ── Header ──
    st.markdown(f"""
    <div style="padding:8px 0 16px;">
        <div style="font-size:10px;font-family:'DM Mono',monospace;letter-spacing:0.1em;
                    text-transform:uppercase;color:rgba(255,255,255,0.3);margin-bottom:4px;">
            Assistente RAIZ · {doc["nome_base"]}
        </div>
        <div style="font-size:16px;font-weight:500;color:#fff;">
            Converse com este documento
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<hr style='border:none;border-top:1px solid rgba(64,123,110,0.15);margin:0 0 16px;'>",
                unsafe_allow_html=True)

    # Inicializa modelo
    model, erro = _inicializar_gemini()
    if erro:
        st.markdown(f"""
        <div style="display:flex;gap:12px;padding:12px 14px;border-radius:8px;
                    background:rgba(255,90,74,0.08);border-left:3px solid #ff5a4a;">
            <span style="color:#ff5a4a;font-size:10px;margin-top:2px;">●</span>
            <div>
                <div style="font-size:13px;font-weight:500;color:#fff;margin-bottom:2px;">
                    Assistente indisponível
                </div>
                <div style="font-size:12px;color:rgba(255,255,255,0.5);">{erro}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        return

    # Extrai texto do PDF (cache por sessão)
    if key_ctx not in st.session_state:
        with st.spinner("Analisando documento..."):
            texto = _extrair_texto_pdf(doc["path"])
            st.session_state[key_ctx] = texto

    texto_doc = st.session_state[key_ctx]

    if not texto_doc:
        st.warning("Não foi possível extrair texto deste PDF. O documento pode estar em formato de imagem.")
        return

    n_chars = len(texto_doc)
    n_pags  = texto_doc.count("[Página")

    st.markdown(f"""
    <div style="display:flex;gap:16px;margin-bottom:16px;">
        <span style="font-size:11px;font-family:'DM Mono',monospace;padding:3px 10px;
                     border-radius:10px;background:rgba(64,123,110,0.1);color:#407b6e;
                     border:1px solid rgba(64,123,110,0.25);">
            {n_pags} páginas indexadas
        </span>
        <span style="font-size:11px;font-family:'DM Mono',monospace;padding:3px 10px;
                     border-radius:10px;background:rgba(64,123,110,0.1);color:#407b6e;
                     border:1px solid rgba(64,123,110,0.25);">
            {n_chars:,} caracteres
        </span>
        <span style="font-size:11px;font-family:'DM Mono',monospace;padding:3px 10px;
                     border-radius:10px;background:rgba(74,219,138,0.1);color:#4adb8a;
                     border:1px solid rgba(74,219,138,0.25);">
            ● Assistente pronto
        </span>
    </div>
    """, unsafe_allow_html=True)

    # Mensagem inicial do assistente
    if not st.session_state[key_ini]:
        msg_inicial = (
            f"Olá! Sou o **Assistente RAIZ** e analisei o documento **{doc['nome_base']}** "
            f"({n_pags} páginas). "
            f"Pode me perguntar sobre qualquer cláusula, condição ou informação presente neste documento. "
            f"Também posso ajudar com dúvidas gerais sobre FIDCs e mercado financeiro."
        )
        st.session_state[key_hist].append({
            "role": "assistant",
            "content": msg_inicial
        })
        st.session_state[key_ini] = True

    # ── Histórico do chat ──
    for msg in st.session_state[key_hist]:
        is_user = msg["role"] == "user"
        prefixo = "Você" if is_user else "Assistente RAIZ"
        cor_pre = "#407b6e" if is_user else "#c8f55a"
        bg      = "rgba(64,123,110,0.1)" if is_user else "rgba(255,255,255,0.02)"
        borda   = "rgba(64,123,110,0.3)" if is_user else "rgba(255,255,255,0.08)"

        st.markdown(f"""
        <div style="background:{bg};border:1px solid {borda};border-radius:12px;
                    padding:4px 16px 4px;margin-bottom:12px;">
            <div style="font-size:10px;font-family:'DM Mono',monospace;color:{cor_pre};
                        margin-top:10px;letter-spacing:0.08em;text-transform:uppercase;">
                {prefixo}
            </div>
        </div>
        """, unsafe_allow_html=True)
        # Renderiza o conteúdo com st.markdown nativo para suportar formatação
        with st.container():
            st.markdown(msg["content"])
        st.markdown("<div style='margin-bottom:4px;'></div>", unsafe_allow_html=True)

    # ── Input do usuário ──
    col_input, col_btn = st.columns([5, 1])

    with col_input:
        st.markdown('<span style="font-size:11px;font-family:DM Mono,monospace;letter-spacing:0.08em;text-transform:uppercase;color:#ffffff;margin-bottom:4px;display:block;">Sua pergunta</span>', unsafe_allow_html=True)
        pergunta = st.text_input(
            "pergunta",
            placeholder="Ex: Qual é a política de concentração de cedentes?",
            label_visibility="collapsed",
            key=f"input_{stem}",
        )

    with col_btn:
        st.markdown("<div style='padding-top:22px;'>", unsafe_allow_html=True)
        enviar = st.button("Enviar →", use_container_width=True, type="primary",
                           key=f"enviar_{stem}")
        st.markdown("</div>", unsafe_allow_html=True)

    if enviar and pergunta.strip():
        # Adiciona pergunta ao histórico
        st.session_state[key_hist].append({
            "role": "user",
            "content": pergunta.strip()
        })

        # Monta histórico para o Gemini
        with st.spinner("Assistente RAIZ está analisando..."):
            try:
                system = _system_prompt(doc["nome_base"], texto_doc)

                # Monta conversa completa
                historico_fmt = []
                for m in st.session_state[key_hist][1:]:  # pula msg inicial
                    role = "user" if m["role"] == "user" else "model"
                    historico_fmt.append({"role": role, "parts": [m["content"]]})

                chat = model.start_chat(history=historico_fmt[:-1])
                resposta = chat.send_message(
                    f"{system}\n\nPergunta do usuário: {pergunta.strip()}"
                )
                texto_resposta = resposta.text

            except Exception as e:
                texto_resposta = f"Ocorreu um erro ao processar sua pergunta: {str(e)}"

        st.session_state[key_hist].append({
            "role": "assistant",
            "content": texto_resposta,
        })
        st.rerun()

    # Botão limpar histórico
    if len(st.session_state[key_hist]) > 1:
        st.markdown("<div style='margin-top:8px;'>", unsafe_allow_html=True)
        if st.button("🗑 Limpar conversa", key=f"limpar_{stem}"):
            st.session_state[key_hist] = []
            st.session_state[key_ini]  = False
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)


def main():
    _estilo()

    if not sessao_ativa(st):
        st.warning("Sessão expirada. Faça login novamente.")
        st.stop()

    usuario = usuario_logado(st)

    # ── Barra de controles ──
    todos_fundos    = listar_fundos(BASE_DIR)
    fundos_visiveis = fundos_permitidos(usuario, todos_fundos) if usuario else todos_fundos
    fundos_ativos   = [f for f in fundos_visiveis if f.get("ativo", True)]

    col_logo, col_fundo, col_tipo, col_home = st.columns([2, 2, 2, 1])

    with col_logo:
        st.markdown("""
        <div style="padding:8px 0 4px;">
            <div style="font-size:10px;font-family:'DM Mono',monospace;letter-spacing:0.12em;
                        text-transform:uppercase;color:#407b6e;">RAIZ · Documentos</div>
            <div style="font-size:14px;font-weight:500;color:#fff;">Repositório de Documentos</div>
        </div>
        """, unsafe_allow_html=True)

    with col_fundo:
        if not fundos_ativos:
            st.warning("Nenhum fundo disponível.")
            return
        opcoes_fundo = {f["nome"]: f["id"] for f in fundos_ativos}
        fundo_nome   = st.selectbox("Fundo", options=list(opcoes_fundo.keys()))
        fundo_id     = opcoes_fundo[fundo_nome]

    with col_tipo:
        tipo_sel = st.selectbox(
            "Tipo de documento",
            options=list(TIPOS_DOCUMENTO.keys()),
            format_func=lambda x: TIPOS_DOCUMENTO[x],
        )

    with col_home:
        st.markdown("<div style='padding-top:24px;'>", unsafe_allow_html=True)
        st.page_link("app.py", label="← Home", use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<hr style='border:none;border-top:1px solid rgba(64,123,110,0.2);margin:8px 0 16px;'>",
                unsafe_allow_html=True)

    # ── Lista documentos ──
    todos_docs = listar_documentos(BASE_DIR, fundo_id)
    docs       = todos_docs.get(tipo_sel, [])

    if not docs:
        _sem_documentos()
        return

    if "doc_selecionado" not in st.session_state:
        st.session_state.doc_selecionado = docs[0]["stem"]

    col_sel, col_info = st.columns([1, 3])

    with col_sel:
        st.markdown(f"""
        <div style="font-size:10px;font-family:'DM Mono',monospace;letter-spacing:0.1em;
                    text-transform:uppercase;color:rgba(255,255,255,0.35);margin-bottom:8px;">
            {TIPOS_DOCUMENTO[tipo_sel]} disponíveis
        </div>
        """, unsafe_allow_html=True)

        for doc in docs:
            is_sel    = st.session_state.doc_selecionado == doc["stem"]
            cor_borda = "#407b6e" if is_sel else "rgba(64,123,110,0.15)"
            bg        = "rgba(64,123,110,0.1)" if is_sel else "rgba(255,255,255,0.02)"
            tem_notas = notas_existem(BASE_DIR, fundo_id, doc["tipo"], doc["stem"])

            # Linha de versão/data ou badges
            if doc["versao"] or doc["data"]:
                versao_html = ""
                if doc["versao"]:
                    versao_html += f'<span style="font-size:10px;font-family:\'DM Mono\',monospace;padding:2px 8px;border-radius:10px;background:rgba(64,123,110,0.15);color:#407b6e;border:1px solid rgba(64,123,110,0.3);margin-right:4px;">{doc["versao"]}</span>'
                if doc["data"]:
                    versao_html += f'<span style="font-size:10px;font-family:\'DM Mono\',monospace;color:rgba(255,255,255,0.35);">{doc["data"]}</span>'
                meta_html = versao_html
            else:
                meta_html = '<span style="font-size:10px;font-family:\'DM Mono\',monospace;padding:2px 6px;border-radius:6px;background:rgba(255,255,255,0.04);color:rgba(255,255,255,0.3);">PDF</span>'

            notas_html = ""
            if tem_notas:
                notas_html = '<span style="font-size:10px;font-family:\'DM Mono\',monospace;padding:2px 8px;border-radius:10px;background:rgba(74,158,255,0.1);color:#4a9eff;border:1px solid rgba(74,158,255,0.3);margin-left:4px;">com notas</span>'
            if doc["tem_insight"]:
                notas_html += '<span style="font-size:10px;font-family:\'DM Mono\',monospace;padding:2px 8px;border-radius:10px;background:rgba(200,245,90,0.1);color:#c8f55a;border:1px solid rgba(200,245,90,0.3);margin-left:4px;">resumo IA</span>'

            st.markdown(f"""
            <div style="background:{bg};border:1px solid {cor_borda};border-radius:8px;
                        padding:12px 14px;margin-bottom:6px;">
                <div style="font-size:12px;font-weight:500;color:#fff;margin-bottom:6px;">
                    {doc["nome_base"]}
                </div>
                <div style="display:flex;align-items:center;flex-wrap:wrap;gap:4px;">
                    {meta_html}
                    {notas_html}
                </div>
            </div>
            """, unsafe_allow_html=True)

            if st.button("Abrir", key=f"btn_{doc['stem']}", use_container_width=True):
                st.session_state.doc_selecionado = doc["stem"]
                st.rerun()

    with col_info:
        doc_atual = next((d for d in docs if d["stem"] == st.session_state.doc_selecionado), docs[0])
        tab_pdf, tab_resumo, tab_notas, tab_chat = st.tabs(["📄 Visualizar documento", "✨ Resumo com IA", "📝 Notas", "💬 Chat"])

        with tab_pdf:
            _aba_pdf(doc_atual)
        with tab_resumo:
            _aba_resumo(BASE_DIR, fundo_id, tipo_sel, doc_atual)
        with tab_notas:
            _aba_notas(BASE_DIR, fundo_id, tipo_sel, doc_atual)
        with tab_chat:
            _aba_chat(BASE_DIR, fundo_id, tipo_sel, doc_atual)


if __name__ == "__main__":
    main()