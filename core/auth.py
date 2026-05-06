"""
core/auth.py

Responsabilidade: autenticação e controle de acesso.

- Lê usuários de config/users.yaml
- Verifica senha com bcrypt
- Controla acesso por fundo via role e lista de fundos
- Gerencia sessão via st.session_state

Funções públicas:
    verificar_login(base_dir, username, password) → dict | None
    usuario_tem_acesso(usuario, fundo_id) → bool
    hash_senha(senha) → str
    inicializar_sessao(st) → None
    fazer_logout(st) → None
    sessao_ativa(st) → bool
    usuario_logado(st) → dict | None
"""

import logging
from pathlib import Path

import bcrypt
import yaml

log = logging.getLogger(__name__)

# Chave usada no st.session_state
_SESSION_KEY = "fidc_usuario"


# ---------------------------------------------------------------------------
# HELPERS
# ---------------------------------------------------------------------------

def _carregar_usuarios(base_dir: Path) -> list[dict]:
    """Lê e retorna a lista de usuários do users.yaml."""
    config_path = base_dir / "config" / "users.yaml"

    if not config_path.exists():
        log.error(f"users.yaml não encontrado em {config_path}.")
        return []

    with open(config_path, encoding="utf-8") as f:
        config = yaml.safe_load(f)

    return config.get("users", [])


def _usuario_por_username(base_dir: Path, username: str) -> dict | None:
    """Busca um usuário pelo username. Retorna None se não encontrado."""
    for user in _carregar_usuarios(base_dir):
        if user.get("username") == username:
            return user
    return None


# ---------------------------------------------------------------------------
# SENHA
# ---------------------------------------------------------------------------

def hash_senha(senha: str) -> str:
    """
    Gera o hash bcrypt de uma senha.
    Use este utilitário para criar entradas no users.yaml.

    Args:
        senha: senha em texto plano

    Returns:
        Hash bcrypt como string (para salvar no users.yaml)
    """
    return bcrypt.hashpw(senha.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def _verificar_senha(senha: str, password_hash: str) -> bool:
    """Verifica se a senha corresponde ao hash bcrypt."""
    try:
        return bcrypt.checkpw(senha.encode("utf-8"), password_hash.encode("utf-8"))
    except Exception as e:
        log.error(f"Erro ao verificar senha: {e}")
        return False


# ---------------------------------------------------------------------------
# LOGIN
# ---------------------------------------------------------------------------

def verificar_login(base_dir: str | Path, username: str, password: str) -> dict | None:
    """
    Verifica as credenciais do usuário.

    Args:
        base_dir: Raiz do projeto
        username: Nome de usuário
        password: Senha em texto plano

    Returns:
        Dict com dados do usuário se as credenciais forem válidas, None caso contrário.
        Ex:
        {
            "username": "admin",
            "nome":     "Administrador",
            "role":     "admin",
            "fundos":   ["*"],
        }
    """
    base_dir = Path(base_dir)
    usuario = _usuario_por_username(base_dir, username)

    if usuario is None:
        log.warning(f"Tentativa de login com usuário inexistente: '{username}'")
        return None

    if not usuario.get("ativo", True):
        log.warning(f"Tentativa de login com usuário inativo: '{username}'")
        return None

    password_hash = usuario.get("password_hash", "")
    if not _verificar_senha(password, password_hash):
        log.warning(f"Senha incorreta para usuário: '{username}'")
        return None

    log.info(f"Login bem-sucedido: '{username}'")

    # Retorna apenas os campos seguros (sem o hash)
    return {
        "username": usuario["username"],
        "nome":     usuario.get("nome", username),
        "role":     usuario.get("role", "viewer"),
        "fundos":   usuario.get("fundos", []),
    }


# ---------------------------------------------------------------------------
# CONTROLE DE ACESSO
# ---------------------------------------------------------------------------

def usuario_tem_acesso(usuario: dict, fundo_id: str) -> bool:
    """
    Verifica se o usuário tem acesso a um fundo específico.

    Regras:
    - role 'admin' → acesso a tudo
    - fundos: ["*"] → acesso a tudo
    - fundos: ["xama", "fundo_b"] → acesso apenas aos fundos listados

    Args:
        usuario:  Dict retornado por verificar_login()
        fundo_id: ID do fundo (ex: 'xama')

    Returns:
        True se tiver acesso, False caso contrário.
    """
    if usuario.get("role") == "admin":
        return True

    fundos_permitidos = usuario.get("fundos", [])

    if "*" in fundos_permitidos:
        return True

    return fundo_id in fundos_permitidos


def fundos_permitidos(usuario: dict, todos_os_fundos: list[dict]) -> list[dict]:
    """
    Filtra a lista de fundos retornando apenas os que o usuário pode acessar.

    Args:
        usuario:        Dict retornado por verificar_login()
        todos_os_fundos: Lista retornada por loader.listar_fundos()

    Returns:
        Lista filtrada de fundos acessíveis pelo usuário.
    """
    return [
        f for f in todos_os_fundos
        if usuario_tem_acesso(usuario, f["id"])
    ]


# ---------------------------------------------------------------------------
# SESSÃO (Streamlit)
# ---------------------------------------------------------------------------

def inicializar_sessao(st) -> None:
    """
    Garante que a chave de sessão existe no st.session_state.
    Chamar no topo do app.py.
    """
    if _SESSION_KEY not in st.session_state:
        st.session_state[_SESSION_KEY] = None


def sessao_ativa(st) -> bool:
    """Retorna True se houver um usuário logado na sessão."""
    return st.session_state.get(_SESSION_KEY) is not None


def usuario_logado(st) -> dict | None:
    """Retorna o dict do usuário logado, ou None se não houver sessão."""
    return st.session_state.get(_SESSION_KEY)


def fazer_login(st, usuario: dict) -> None:
    """Salva o usuário na sessão após login bem-sucedido."""
    st.session_state[_SESSION_KEY] = usuario


def fazer_logout(st) -> None:
    """Encerra a sessão do usuário."""
    st.session_state[_SESSION_KEY] = None
    log.info(f"Logout realizado.")