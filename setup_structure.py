"""
setup_structure.py
Cria a estrutura de pastas e arquivos vazios do fidc-app.
Execute na raiz do repositório: python setup_structure.py

Seguro para rodar múltiplas vezes — não sobrescreve arquivos existentes.
"""

from pathlib import Path

# ---------------------------------------------------------------------------
# Arquivos a criar (todos vazios)
# ---------------------------------------------------------------------------
FILES = [
    "app.py",

    # --- Configurações ---
    "config/users.yaml",
    "config/funds.yaml",
    "config/settings.yaml",

    # --- Dados: XAMA ---
    # inbox     → arquivos brutos que chegam para processamento
    # processed → arquivos já processados (movidos do inbox)
    # cache     → JSONs/textos extraídos, lidos pelo dashboard
    "data/funds/xama/insights/.gitkeep",
    "data/funds/xama/informes/inbox/.gitkeep",
    "data/funds/xama/informes/processed/.gitkeep",
    "data/funds/xama/informes/cache/.gitkeep",
    "data/funds/xama/documentos/inbox/.gitkeep",
    "data/funds/xama/documentos/processed/.gitkeep",
    "data/funds/xama/documentos/cache/.gitkeep",

    # --- Dados: Fundo B ---
    "data/funds/fundo_b/insights/.gitkeep",
    "data/funds/fundo_b/informes/inbox/.gitkeep",
    "data/funds/fundo_b/informes/processed/.gitkeep",
    "data/funds/fundo_b/informes/cache/.gitkeep",
    "data/funds/fundo_b/documentos/inbox/.gitkeep",
    "data/funds/fundo_b/documentos/processed/.gitkeep",
    "data/funds/fundo_b/documentos/cache/.gitkeep",

    # --- Dados: Fundo C ---
    "data/funds/fundo_c/insights/.gitkeep",
    "data/funds/fundo_c/informes/inbox/.gitkeep",
    "data/funds/fundo_c/informes/processed/.gitkeep",
    "data/funds/fundo_c/informes/cache/.gitkeep",
    "data/funds/fundo_c/documentos/inbox/.gitkeep",
    "data/funds/fundo_c/documentos/processed/.gitkeep",
    "data/funds/fundo_c/documentos/cache/.gitkeep",

    # --- Core (lógica de negócio, independente do Streamlit) ---
    "core/__init__.py",
    "core/extractor.py",    # Extração de XMLs → dict
    "core/processor.py",    # Varre inbox/, processa e move para processed/ + cache/
    "core/loader.py",       # Lê cache/ e entrega dados prontos para o dashboard
    "core/metrics.py",      # Métricas calculadas sobre os dados extraídos
    "core/auth.py",         # Autenticação via users.yaml

    # --- Páginas Streamlit ---
    "pages/00_home.py",
    "pages/01_dashboard.py",
    "pages/02_documentos.py",
    "pages/03_precificacao.py",
    "pages/04_configuracoes.py",

    # --- Componentes reutilizáveis ---
    "components/__init__.py",
    "components/sidebar.py",
    "components/charts.py",
    "components/cards.py",
    "components/filters.py",

    # --- Assets ---
    "assets/style.css",

    # --- Testes ---
    "tests/__init__.py",
    "tests/test_extractor.py",
    "tests/test_processor.py",
    "tests/test_metrics.py",
    "tests/test_auth.py",

    # --- Raiz ---
    "requirements.txt",
    ".gitignore",
    "README.md",
]


# ---------------------------------------------------------------------------
# Criação da estrutura
# ---------------------------------------------------------------------------
def create_structure():
    created_dirs = set()
    created_files = []
    skipped_files = []

    for file_path in FILES:
        path = Path(file_path)

        # Cria diretórios pai se não existirem
        if path.parent != Path("."):
            path.parent.mkdir(parents=True, exist_ok=True)
            created_dirs.add(path.parent)

        # Cria arquivo vazio apenas se não existir
        if not path.exists():
            path.touch()
            created_files.append(str(path))
        else:
            skipped_files.append(str(path))

    print(f"✓ {len(created_dirs)} pastas verificadas/criadas")
    print(f"✓ {len(created_files)} arquivos novos criados")
    if skipped_files:
        print(f"  {len(skipped_files)} arquivos já existentes mantidos intactos")
    print("\nEstrutura gerada com sucesso.")


if __name__ == "__main__":
    create_structure()
