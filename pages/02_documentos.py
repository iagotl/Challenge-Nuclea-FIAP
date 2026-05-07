"""
pages/02_documentos.py

Repositório de documentos do fundo — FIDC · RAIZ
Permite visualizar PDFs e acessar resumos gerados por IA sob demanda.
"""

from pathlib import Path
import streamlit as st

BASE_DIR = Path(__file__).parent.parent

from core.auth import sessao_ativa, usuario_logado
from core.loader import (
    listar_fundos,
    listar_documentos,
    carregar_documento_insight,
    carregar_pdf_bytes,
    carregar_notas,
    salvar_notas,
    notas_existem,
    TIPOS_DOCUMENTO,
)
from core.auth import fundos_permitidos

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
    html, body, [class*="css"] { font-family: 'DM Sans', sans-serif !important; }
    header[data-testid="stHeader"] { display: none !important; }
    footer { display: none !important; }
    #MainMenu { display: none !important; }
    .block-container { padding-top: 0 !important; padding-bottom: 2rem !important; }
    .stApp { background: linear-gradient(180deg, #0d1415 0%, #1e2e30 100%) !important; }

    /* Selectbox */
    .stSelectbox > div > div {
        background: rgba(255,255,255,0.04) !important;
        border: 1px solid rgba(64,123,110,0.25) !important;
        border-radius: 8px !important;
        color: #fff !important;
    }
    .stSelectbox label p {
        font-size: 11px !important;
        font-family: 'DM Mono', monospace !important;
        letter-spacing: 0.08em !important;
        text-transform: uppercase !important;
        color: rgba(255,255,255,0.4) !important;
    }

    /* Botão primário */
    div[data-testid="stFormSubmitButton"] > button,
    .stButton > button[kind="primary"] {
        background: #407b6e !important;
        border: none !important;
        border-radius: 8px !important;
        color: #fff !important;
        font-weight: 500 !important;
    }
    .stButton > button[kind="primary"]:hover {
        background: #4d9485 !important;
    }

    /* Botão secundário */
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

    /* PDF embed */
    iframe { border-radius: 8px; border: 1px solid rgba(64,123,110,0.2); }

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
    }
    .stTabs [data-baseweb="tab-highlight"] { display: none; }
    .stTabs [data-baseweb="tab-border"]    { display: none; }
    </style>
    """, unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# HELPERS
# ---------------------------------------------------------------------------

def _md_to_html(md: str) -> str:
    """Converte markdown para HTML com cores controladas — mesmo padrão do dashboard."""
    import re

    html  = []
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
        if not table_rows:
            return ""
        out = '<table style="width:100%;border-collapse:collapse;font-size:13px;margin:16px 0;">'
        for ri, row in enumerate(table_rows):
            cells = [c.strip() for c in row.strip("|").split("|")]
            if ri == 0:
                out += "<thead><tr>" + "".join(
                    f'<th style="text-align:left;padding:8px 12px;font-size:10px;'
                    f'letter-spacing:0.08em;text-transform:uppercase;'
                    f'color:rgba(255,255,255,0.35);border-bottom:1px solid rgba(64,123,110,0.25);">{c}</th>'
                    for c in cells
                ) + "</tr></thead><tbody>"
            elif re.match(r'[\s|:-]+$', row.replace("|", "")):
                continue
            else:
                out += "<tr>" + "".join(
                    f'<td style="padding:8px 12px;color:rgba(255,255,255,0.75);'
                    f'border-bottom:1px solid rgba(255,255,255,0.05);">{_inline(c)}</td>'
                    for c in cells
                ) + "</tr>"
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
            in_table = True
            table_rows.append(line)
            i += 1; continue
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

        if re.match(r'^[-*] ', line):
            if not in_list:
                html.append('<ul style="margin:8px 0 12px;padding-left:20px;">')
                in_list = True
            text = _inline(line[2:].strip())
            html.append(f'<li style="color:#ffffff;font-size:14px;line-height:1.8;margin-bottom:4px;">{text}</li>')
            i += 1; continue
        elif in_list:
            html.append("</ul>"); in_list = False

        if not line.strip():
            i += 1; continue

        text = _inline(line.strip())
        html.append(f'<p style="color:#ffffff;font-size:14px;line-height:1.8;margin:0 0 10px;">{text}</p>')
        i += 1

    if in_list:  html.append("</ul>")
    if in_table: html.append(_flush_table())
    return "\n".join(html)



def _badge_notas(tem: bool) -> str:
    if tem:
        return (
            '<span style="font-size:10px;font-family:DM Mono,monospace;padding:2px 8px;'
            'border-radius:10px;background:rgba(74,158,255,0.1);color:#4a9eff;'
            'border:1px solid rgba(74,158,255,0.3);margin-left:4px;">com notas</span>'
        )
    return ""


def _badge_insight(tem: bool) -> str:
    if tem:
        return (
            '<span style="font-size:10px;font-family:DM Mono,monospace;padding:2px 8px;'
            'border-radius:10px;background:rgba(200,245,90,0.1);color:#c8f55a;'
            'border:1px solid rgba(200,245,90,0.3);">resumo disponível</span>'
        )
    return '<span style="font-size:10px;font-family:DM Mono,monospace;color:rgba(255,255,255,0.2);">sem resumo</span>'

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
# MAIN
# ---------------------------------------------------------------------------

def _renderizar_notas(base_dir: Path, fundo_id: str, tipo: str, doc: dict):
    """Renderiza a aba de notas com editor e visualizador."""
    from datetime import datetime

    stem = doc["stem"]

    # Chave de sessão única por documento
    key_modo  = f"notas_modo_{fundo_id}_{tipo}_{stem}"
    key_texto = f"notas_texto_{fundo_id}_{tipo}_{stem}"

    # Inicializa estado
    if key_modo not in st.session_state:
        st.session_state[key_modo] = "visualizar"
    if key_texto not in st.session_state:
        st.session_state[key_texto] = carregar_notas(base_dir, fundo_id, tipo, stem)

    notas_atuais = st.session_state[key_texto]
    modo         = st.session_state[key_modo]

    # ── Header ──
    col_title, col_actions = st.columns([3, 2])
    with col_title:
        st.markdown(f"""
        <div style="padding:8px 0 16px;">
            <div style="font-size:10px;font-family:'DM Mono',monospace;letter-spacing:0.1em;
                        text-transform:uppercase;color:rgba(255,255,255,0.3);margin-bottom:4px;">
                Notas · {doc["nome"]}
            </div>
            <div style="font-size:16px;font-weight:500;color:#fff;">
                Anotações sobre este documento
            </div>
        </div>
        """, unsafe_allow_html=True)

    with col_actions:
        st.markdown("<div style='padding-top:16px;'>", unsafe_allow_html=True)
        if modo == "visualizar":
            if st.button("✏️ Editar notas", use_container_width=True, type="primary"):
                st.session_state[key_modo] = "editar"
                st.rerun()
        else:
            col_s, col_c = st.columns(2)
            with col_s:
                if st.button("💾 Salvar", use_container_width=True, type="primary"):
                    ok = salvar_notas(base_dir, fundo_id, tipo, stem,
                                      st.session_state[key_texto])
                    if ok:
                        st.session_state[key_modo] = "visualizar"
                        st.success("Notas salvas!")
                        st.rerun()
                    else:
                        st.error("Erro ao salvar.")
            with col_c:
                if st.button("✕ Cancelar", use_container_width=True):
                    # Descarta alterações — recarrega do disco
                    st.session_state[key_texto] = carregar_notas(base_dir, fundo_id, tipo, stem)
                    st.session_state[key_modo]  = "visualizar"
                    st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<hr style='border:none;border-top:1px solid rgba(64,123,110,0.15);margin:0 0 16px;'>",
                unsafe_allow_html=True)

    # ── Editor ou visualizador ──
    if modo == "editar":
        st.markdown("""
        <div style="font-size:11px;font-family:'DM Mono',monospace;color:rgba(255,255,255,0.3);
                    margin-bottom:8px;">
            Suporte a Markdown — **negrito**, *itálico*, listas, títulos com ##
        </div>
        """, unsafe_allow_html=True)

        novo_texto = st.text_area(
            label="Notas",
            value=st.session_state[key_texto],
            height=500,
            placeholder="Escreva suas anotações aqui... Suporte a Markdown: ## Título, - Lista, **negrito**, *itálico*",
            label_visibility="collapsed",
            key=f"textarea_{fundo_id}_{tipo}_{stem}",
        )
        st.session_state[key_texto] = novo_texto

    else:
        # Modo visualização
        if not notas_atuais.strip():
            st.markdown("""
            <div style="text-align:center;padding:60px 0;">
                <div style="font-size:28px;margin-bottom:12px;">📝</div>
                <div style="font-size:13px;font-family:'DM Mono',monospace;
                            color:rgba(255,255,255,0.2);margin-bottom:6px;">
                    Nenhuma anotação ainda
                </div>
                <div style="font-size:11px;color:rgba(255,255,255,0.15);">
                    Clique em "Editar notas" para começar
                </div>
            </div>
            """, unsafe_allow_html=True)
        else:
            # Renderiza markdown das notas
            html_notas = _md_to_html(notas_atuais)
            st.markdown(
                f'<div style="background:rgba(255,255,255,0.02);'
                f'border:1px solid rgba(64,123,110,0.15);border-radius:12px;'
                f'padding:24px 28px;">{html_notas}</div>',
                unsafe_allow_html=True
            )

            # Metadata
            notes_path = base_dir / "data" / "funds" / fundo_id / "documentos" / tipo / f"{stem}.notes.md"
            if notes_path.exists():
                import os
                mtime = datetime.fromtimestamp(os.path.getmtime(notes_path))
                st.markdown(f"""
                <div style="font-size:10px;font-family:'DM Mono',monospace;
                            color:rgba(255,255,255,0.2);margin-top:12px;text-align:right;">
                    Última edição: {mtime.strftime("%d/%m/%Y às %H:%M")}
                </div>
                """, unsafe_allow_html=True)



def main():
    _estilo()

    if not sessao_ativa(st):
        st.warning("Sessão expirada. Faça login novamente.")
        st.stop()

    usuario = usuario_logado(st)

    # ── Barra de controles no topo ──
    todos_fundos    = listar_fundos(BASE_DIR)
    fundos_visiveis = fundos_permitidos(usuario, todos_fundos) if usuario else todos_fundos
    fundos_ativos   = [f for f in fundos_visiveis if f.get("ativo", True)]

    col_logo, col_fundo, col_tipo, col_home = st.columns([2, 2, 2, 1])

    with col_logo:
        st.markdown("""
        <div style="padding:8px 0 4px;">
            <div style="font-size:10px;font-family:'DM Mono',monospace;letter-spacing:0.12em;
                        text-transform:uppercase;color:#407b6e;">
                RAIZ · Documentos
            </div>
            <div style="font-size:14px;font-weight:500;color:#fff;">
                Repositório de Documentos
            </div>
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
        tipo_selecionado = st.selectbox(
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

    # ── Lista documentos do tipo selecionado ──
    todos_docs = listar_documentos(BASE_DIR, fundo_id)
    docs       = todos_docs.get(tipo_selecionado, [])

    if not docs:
        _sem_documentos()
        return

    # ── Seletor de documento ──
    col_sel, col_info = st.columns([1, 3])

    with col_sel:
        st.markdown(f"""
        <div style="font-size:10px;font-family:'DM Mono',monospace;letter-spacing:0.1em;
                    text-transform:uppercase;color:rgba(255,255,255,0.35);margin-bottom:6px;">
            {TIPOS_DOCUMENTO[tipo_selecionado]} disponíveis
        </div>
        """, unsafe_allow_html=True)

        # Cards de seleção de documento
        if "doc_selecionado" not in st.session_state:
            st.session_state.doc_selecionado = docs[0]["stem"]

        for doc in docs:
            is_sel = st.session_state.doc_selecionado == doc["stem"]
            cor_borda = "#407b6e" if is_sel else "rgba(64,123,110,0.15)"
            bg        = "rgba(64,123,110,0.1)" if is_sel else "rgba(255,255,255,0.02)"

            st.markdown(f"""
            <div style="background:{bg};border:1px solid {cor_borda};border-radius:8px;
                        padding:12px 14px;margin-bottom:8px;cursor:pointer;">
                <div style="font-size:12px;font-weight:500;color:#fff;margin-bottom:4px;">
                    {doc["nome"]}
                </div>
                <div style="display:flex;align-items:center;gap:8px;">
                    <span style="font-size:10px;font-family:'DM Mono',monospace;
                                 padding:2px 8px;border-radius:10px;
                                 background:rgba(64,123,110,0.15);color:#407b6e;
                                 border:1px solid rgba(64,123,110,0.3);">
                        PDF
                    </span>
                    {_badge_insight(doc["tem_insight"])}
                    {_badge_notas(notas_existem(BASE_DIR, fundo_id, doc["tipo"], doc["stem"]))}
                </div>
            </div>
            """, unsafe_allow_html=True)

            if st.button(f"Abrir", key=f"btn_{doc['stem']}", use_container_width=True):
                st.session_state.doc_selecionado = doc["stem"]
                st.session_state.mostrar_insight = False
                st.rerun()

    with col_info:
        doc_atual = next((d for d in docs if d["stem"] == st.session_state.doc_selecionado), docs[0])

        # ── Tabs: PDF | Resumo ──
        tab_pdf, tab_resumo, tab_notas = st.tabs(["📄 Visualizar documento", "✨ Resumo com IA", "📝 Notas"])

        with tab_pdf:
            st.markdown(f"""
            <div style="font-size:10px;font-family:'DM Mono',monospace;letter-spacing:0.1em;
                        text-transform:uppercase;color:rgba(255,255,255,0.3);margin-bottom:12px;">
                {doc_atual["label"]} · {doc_atual["nome"]}
            </div>
            """, unsafe_allow_html=True)

            pdf_bytes = carregar_pdf_bytes(doc_atual["path"])
            if pdf_bytes:
                st.download_button(
                    label="⬇ Baixar PDF",
                    data=pdf_bytes,
                    file_name=doc_atual["nome"],
                    mime="application/pdf",
                    use_container_width=False,
                )
                # Renderiza PDF embutido via iframe base64
                import base64
                b64 = base64.b64encode(pdf_bytes).decode("utf-8")
                st.markdown(
                    f'<iframe src="data:application/pdf;base64,{b64}" '
                    f'width="100%" height="860px" type="application/pdf"></iframe>',
                    unsafe_allow_html=True,
                )
            else:
                st.error("Não foi possível carregar o PDF.")

        with tab_resumo:
            if "mostrar_insight" not in st.session_state:
                st.session_state.mostrar_insight = False

            if not doc_atual["tem_insight"]:
                st.markdown("""
                <div style="text-align:center;padding:60px 0;">
                    <div style="font-size:13px;font-family:'DM Mono',monospace;
                                color:rgba(255,255,255,0.2);margin-bottom:8px;">
                        Resumo não disponível para este documento
                    </div>
                    <div style="font-size:11px;color:rgba(255,255,255,0.15);">
                        Adicione um arquivo .md com o mesmo nome do PDF para habilitar.
                    </div>
                </div>
                """, unsafe_allow_html=True)

            elif not st.session_state.mostrar_insight:
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

                col_btn = st.columns([1, 2, 1])[1]
                with col_btn:
                    if st.button("✨ Gerar resumo com IA", use_container_width=True, type="primary"):
                        st.session_state.mostrar_insight = True
                        st.rerun()

            else:
                insight_md = carregar_documento_insight(
                    BASE_DIR, fundo_id, tipo_selecionado, doc_atual["stem"]
                )

                if insight_md:
                    # Remove frontmatter YAML
                    linhas = insight_md.split("\n")
                    if linhas[0].strip() == "---":
                        fim = next((i for i, l in enumerate(linhas[1:], 1) if l.strip() == "---"), None)
                        if fim:
                            linhas = linhas[fim + 1:]
                    insight_limpo = "\n".join(linhas).strip()

                    html_insight = _md_to_html(insight_limpo)
                    st.markdown(
                        f'<div style="background:rgba(255,255,255,0.02);'
                        f'border:1px solid rgba(64,123,110,0.2);border-radius:12px;'
                        f'padding:24px 28px;">{html_insight}</div>',
                        unsafe_allow_html=True
                    )

                    # Botão para fechar
                    if st.button("✕ Fechar resumo", use_container_width=False):
                        st.session_state.mostrar_insight = False
                        st.rerun()

        with tab_notas:
            _renderizar_notas(BASE_DIR, fundo_id, tipo_selecionado, doc_atual)


if __name__ == "__main__":
    main()