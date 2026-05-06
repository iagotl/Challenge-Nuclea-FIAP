"""
manage_users.py

Script utilitário para gerenciar usuários da aplicação.
Rode na raiz do repositório com o ambiente virtual ativo.

Comandos:
    python manage_users.py criar   → cria um novo usuário interativamente
    python manage_users.py listar  → lista os usuários cadastrados
    python manage_users.py resetar → reseta a senha de um usuário
    python manage_users.py init    → cria o users.yaml com o admin padrão (primeiro uso)
"""

import sys
import getpass
from pathlib import Path

import bcrypt
import yaml

CONFIG_PATH = Path("config/users.yaml")


# ---------------------------------------------------------------------------
# HELPERS
# ---------------------------------------------------------------------------

def _hash_senha(senha: str) -> str:
    return bcrypt.hashpw(senha.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def _carregar() -> dict:
    if not CONFIG_PATH.exists():
        return {"users": []}
    with open(CONFIG_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f) or {"users": []}


def _salvar(config: dict) -> None:
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        yaml.dump(config, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
    print(f"✓ Salvo em {CONFIG_PATH}")


def _usuario_existe(config: dict, username: str) -> bool:
    return any(u["username"] == username for u in config.get("users", []))


# ---------------------------------------------------------------------------
# COMANDOS
# ---------------------------------------------------------------------------

def cmd_init():
    """Cria o users.yaml com o usuário admin padrão (admin / admin123)."""
    if CONFIG_PATH.exists():
        resp = input("users.yaml já existe. Sobrescrever? (s/N): ").strip().lower()
        if resp != "s":
            print("Cancelado.")
            return

    config = {
        "users": [
            {
                "username":      "admin",
                "password_hash": _hash_senha("admin123"),
                "nome":          "Administrador",
                "role":          "admin",
                "fundos":        ["*"],
                "ativo":         True,
            }
        ]
    }
    _salvar(config)
    print("✓ Usuário admin criado com senha padrão: admin123")
    print("⚠ Troque a senha em produção usando: python manage_users.py resetar")


def cmd_criar():
    """Cria um novo usuário interativamente."""
    config = _carregar()

    username = input("Username: ").strip()
    if not username:
        print("Username inválido.")
        return

    if _usuario_existe(config, username):
        print(f"Usuário '{username}' já existe.")
        return

    nome     = input("Nome completo: ").strip() or username
    role     = input("Role (admin/viewer) [viewer]: ").strip() or "viewer"
    fundos_i = input("Fundos permitidos (ex: xama,fundo_b) ou * para todos: ").strip()
    fundos   = ["*"] if fundos_i == "*" else [f.strip() for f in fundos_i.split(",")]
    senha    = getpass.getpass("Senha: ")
    confirma = getpass.getpass("Confirme a senha: ")

    if senha != confirma:
        print("As senhas não coincidem.")
        return

    config["users"].append({
        "username":      username,
        "password_hash": _hash_senha(senha),
        "nome":          nome,
        "role":          role,
        "fundos":        fundos,
        "ativo":         True,
    })

    _salvar(config)
    print(f"✓ Usuário '{username}' criado com sucesso.")


def cmd_listar():
    """Lista os usuários cadastrados (sem exibir hashes)."""
    config = _carregar()
    users  = config.get("users", [])

    if not users:
        print("Nenhum usuário cadastrado.")
        return

    print(f"\n{'Username':<15} {'Nome':<25} {'Role':<10} {'Fundos':<20} {'Ativo'}")
    print("-" * 80)
    for u in users:
        fundos = ", ".join(u.get("fundos", []))
        ativo  = "✓" if u.get("ativo", True) else "✗"
        print(f"{u['username']:<15} {u.get('nome',''):<25} {u.get('role',''):<10} {fundos:<20} {ativo}")
    print()


def cmd_resetar():
    """Reseta a senha de um usuário existente."""
    config   = _carregar()
    username = input("Username: ").strip()

    usuario = next((u for u in config["users"] if u["username"] == username), None)
    if not usuario:
        print(f"Usuário '{username}' não encontrado.")
        return

    senha    = getpass.getpass("Nova senha: ")
    confirma = getpass.getpass("Confirme a nova senha: ")

    if senha != confirma:
        print("As senhas não coincidem.")
        return

    usuario["password_hash"] = _hash_senha(senha)
    _salvar(config)
    print(f"✓ Senha de '{username}' atualizada com sucesso.")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

COMANDOS = {
    "init":    cmd_init,
    "criar":   cmd_criar,
    "listar":  cmd_listar,
    "resetar": cmd_resetar,
}

if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] not in COMANDOS:
        print("Uso: python manage_users.py <comando>")
        print("Comandos disponíveis:", ", ".join(COMANDOS.keys()))
        sys.exit(1)

    COMANDOS[sys.argv[1]]()
