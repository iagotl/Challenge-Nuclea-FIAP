"""
components/sidebar.py

Sidebar reutilizável com seletor de fundo e competência.
Retorna o fundo e competência selecionados para a página usar.
"""

import streamlit as st
from core.loader import listar_fundos, listar_competencias
from core.auth import usuario_logado, fazer_logout, fundos_permitidos

LOGO_SVG = """<svg width="36" height="36" viewBox="0 0 60 60" fill="none">
  <path d="M30 4 L52 14 L52 34 C52 46 30 56 30 56 C30 56 8 46 8 34 L8 14 Z"
        stroke="rgba(255,255,255,0.2)" stroke-width="1.5" fill="rgba(64,123,110,0.15)"/>
  <line x1="30" y1="14" x2="30" y2="46" stroke="white" stroke-width="1.5"/>
  <line x1="30" y1="22" x2="22" y2="30" stroke="white" stroke-width="1.5"/>
  <line x1="30" y1="22" x2="38" y2="30" stroke="white" stroke-width="1.5"/>
  <line x1="30" y1="30" x2="20" y2="38" stroke="white" stroke-width="1.5"/>
  <line x1="30" y1="30" x2="40" y2="38" stroke="white" stroke-width="1.5"/>
</svg>"""


def render(base_dir) -> tuple[str | None, str | None]:
    """
    Renderiza a sidebar completa e retorna (fundo_id, competencia).
    Retorna (None, None) se não houver dados disponíveis.
    """
    usuario = usuario_logado(st)

    with st.sidebar:

        # ── Logo e marca ──
        st.markdown(f"""
        <div style="padding:16px 0 20px;border-bottom:1px solid rgba(64,123,110,0.2);
                    margin-bottom:20px;">
            <div style="display:flex;align-items:center;gap:10px;">
                {LOGO_SVG}
                <div>
                    <div style="font-size:16px;font-weight:500;letter-spacing:0.1em;color:#fff;">
                        RA<span style="color:#407b6e;">İ</span>Z
                    </div>
                    <div style="font-size:9px;font-family:'DM Mono',monospace;
                                color:rgba(255,255,255,0.3);letter-spacing:0.1em;
                                text-transform:uppercase;">
                        Gestão de Ativos
                    </div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # ── Seletor de fundo ──
        st.markdown("""
        <div style="font-size:10px;font-family:'DM Mono',monospace;letter-spacing:0.1em;
                    text-transform:uppercase;color:rgba(255,255,255,0.35);margin-bottom:6px;">
            Fundo
        </div>
        """, unsafe_allow_html=True)

        todos_fundos   = listar_fundos(base_dir)
        fundos_visiveis = fundos_permitidos(usuario, todos_fundos) if usuario else todos_fundos
        fundos_ativos  = [f for f in fundos_visiveis if f.get("ativo", True)
                          and f.get("competencias_disponiveis", 0) > 0]

        if not fundos_ativos:
            st.warning("Nenhum fundo disponível.")
            _render_footer(usuario)
            return None, None

        opcoes_fundo = {f["nome"]: f["id"] for f in fundos_ativos}
        fundo_nome   = st.selectbox(
            "Fundo",
            options=list(opcoes_fundo.keys()),
            label_visibility="collapsed",
        )
        fundo_id = opcoes_fundo[fundo_nome]

        # ── Seletor de competência ──
        st.markdown("""
        <div style="font-size:10px;font-family:'DM Mono',monospace;letter-spacing:0.1em;
                    text-transform:uppercase;color:rgba(255,255,255,0.35);
                    margin-top:14px;margin-bottom:6px;">
            Competência
        </div>
        """, unsafe_allow_html=True)

        competencias = listar_competencias(base_dir, fundo_id)

        if not competencias:
            st.warning("Nenhuma competência disponível.")
            _render_footer(usuario)
            return fundo_id, None

        competencia = st.selectbox(
            "Competência",
            options=competencias,
            label_visibility="collapsed",
        )

        # ── Info do fundo selecionado ──
        fundo_info = next((f for f in fundos_ativos if f["id"] == fundo_id), {})
        st.markdown(f"""
        <div style="margin-top:16px;padding:12px;background:rgba(64,123,110,0.06);
                    border:1px solid rgba(64,123,110,0.15);border-radius:8px;">
            <div style="font-size:10px;font-family:'DM Mono',monospace;
                        color:rgba(255,255,255,0.25);margin-bottom:4px;">
                CNPJ
            </div>
            <div style="font-size:11px;font-family:'DM Mono',monospace;color:rgba(255,255,255,0.5);">
                {fundo_info.get('cnpj', '—')}
            </div>
            <div style="font-size:10px;font-family:'DM Mono',monospace;
                        color:rgba(255,255,255,0.25);margin-top:8px;margin-bottom:4px;">
                Competências disponíveis
            </div>
            <div style="font-size:11px;font-family:'DM Mono',monospace;color:rgba(255,255,255,0.5);">
                {fundo_info.get('competencias_disponiveis', 0)}
            </div>
        </div>
        """, unsafe_allow_html=True)

        _render_footer(usuario)

    return fundo_id, competencia


def _render_footer(usuario):
    """Rodapé da sidebar com usuário e botão de logout."""
    st.markdown("<div style='flex:1;'></div>", unsafe_allow_html=True)

    if usuario:
        st.markdown(f"""
        <div style="margin-top:24px;padding-top:16px;border-top:1px solid rgba(64,123,110,0.15);">
            <div style="font-size:10px;font-family:'DM Mono',monospace;
                        color:rgba(255,255,255,0.25);text-transform:uppercase;
                        letter-spacing:0.08em;margin-bottom:4px;">
                Usuário
            </div>
            <div style="font-size:13px;color:#fff;font-weight:500;margin-bottom:4px;">
                {usuario['nome']}
            </div>
            <span style="font-size:10px;font-family:'DM Mono',monospace;padding:2px 8px;
                         border-radius:10px;background:rgba(64,123,110,0.18);color:#407b6e;
                         border:1px solid rgba(64,123,110,0.3);">
                {usuario['role']}
            </span>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<div style='margin-top:12px;'></div>", unsafe_allow_html=True)
    if st.button("Sair", use_container_width=True):
        fazer_logout(st)
        st.rerun()