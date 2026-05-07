"""
core/loader.py

Responsabilidade: ler os JSONs do cache/ e entregar dados
organizados para o dashboard consumir.

O dashboard nunca acessa arquivos diretamente — sempre via loader.
"""

import json
import logging
from pathlib import Path

import yaml

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# HELPERS
# ---------------------------------------------------------------------------

def _cache_dir(base_dir: Path, fundo_id: str) -> Path:
    return base_dir / "data" / "funds" / fundo_id / "informes" / "cache"


def _carregar_json(path: Path) -> dict | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        log.error(f"Erro ao ler {path.name}: {e}")
        return None


def _competencia_para_chave(competencia: str) -> str:
    """
    Converte '03/2026' → '2026-03' para ordenação cronológica correta.
    """
    partes = competencia.split("/")
    if len(partes) == 2:
        return f"{partes[1]}-{partes[0].zfill(2)}"
    return competencia


# ---------------------------------------------------------------------------
# FUNÇÕES PÚBLICAS
# ---------------------------------------------------------------------------

def listar_fundos(base_dir: str | Path) -> list[dict]:
    """
    Retorna a lista de fundos configurados em funds.yaml
    com indicação de quantas competências estão disponíveis no cache.

    Returns:
        Lista de dicts:
        [
            {
                "id": "xama",
                "nome": "XAMA! FIDC...",
                "cnpj": "47669160000191",
                "ativo": True,
                "competencias_disponiveis": 3,
            },
            ...
        ]
    """
    base_dir = Path(base_dir)
    config_path = base_dir / "config" / "funds.yaml"

    if not config_path.exists():
        log.warning("funds.yaml não encontrado.")
        return []

    with open(config_path, encoding="utf-8") as f:
        config = yaml.safe_load(f)

    fundos = config.get("funds", [])

    for fundo in fundos:
        fundo_id = fundo.get("id", "")
        cache = _cache_dir(base_dir, fundo_id)
        fundo["competencias_disponiveis"] = len(list(cache.glob("*.json"))) if cache.exists() else 0

    return fundos


def listar_competencias(base_dir: str | Path, fundo_id: str) -> list[str]:
    """
    Retorna as competências disponíveis no cache de um fundo,
    ordenadas da mais recente para a mais antiga.

    Returns:
        Lista de strings no formato original do informe: ['03/2026', '02/2026', ...]
    """
    base_dir = Path(base_dir)
    cache = _cache_dir(base_dir, fundo_id)

    if not cache.exists():
        return []

    competencias = []
    for json_path in cache.glob("*.json"):
        dados = _carregar_json(json_path)
        if dados:
            comp = dados.get("cabecalho", {}).get("competencia", "")
            if comp:
                competencias.append(comp)

    # Ordena da mais recente para a mais antiga
    competencias.sort(key=_competencia_para_chave, reverse=True)
    return competencias


def carregar_competencia(base_dir: str | Path, fundo_id: str, competencia: str) -> dict | None:
    """
    Carrega os dados de uma competência específica de um fundo.

    Args:
        base_dir:    Raiz do projeto
        fundo_id:    ID do fundo (ex: 'xama')
        competencia: Competência no formato '03/2026'

    Returns:
        Dict com todos os dados do informe, ou None se não encontrado.
    """
    base_dir = Path(base_dir)
    cache = _cache_dir(base_dir, fundo_id)

    if not cache.exists():
        log.warning(f"Cache não encontrado para fundo '{fundo_id}'.")
        return None

    for json_path in cache.glob("*.json"):
        dados = _carregar_json(json_path)
        if dados and dados.get("cabecalho", {}).get("competencia") == competencia:
            return dados

    log.warning(f"Competência '{competencia}' não encontrada no cache de '{fundo_id}'.")
    return None


def carregar_historico(base_dir: str | Path, fundo_id: str) -> list[dict]:
    """
    Carrega todas as competências disponíveis de um fundo,
    ordenadas da mais antiga para a mais recente (útil para gráficos de série temporal).

    Returns:
        Lista de dicts, cada um com os dados completos de uma competência.
    """
    base_dir = Path(base_dir)
    cache = _cache_dir(base_dir, fundo_id)

    if not cache.exists():
        return []

    historico = []
    for json_path in cache.glob("*.json"):
        dados = _carregar_json(json_path)
        if dados:
            historico.append(dados)

    # Ordena da mais antiga para a mais recente (para gráficos de evolução)
    historico.sort(
        key=lambda d: _competencia_para_chave(
            d.get("cabecalho", {}).get("competencia", "")
        )
    )
    return historico


def carregar_ultima_competencia(base_dir: str | Path, fundo_id: str) -> dict | None:
    """
    Atalho para carregar a competência mais recente de um fundo.
    Útil para o painel geral do dashboard.

    Returns:
        Dict com os dados da competência mais recente, ou None se vazio.
    """
    competencias = listar_competencias(base_dir, fundo_id)
    if not competencias:
        return None
    return carregar_competencia(base_dir, fundo_id, competencias[0])


# ---------------------------------------------------------------------------
# INSIGHTS
# ---------------------------------------------------------------------------

def carregar_insight(base_dir: str | Path, fundo_id: str, competencia: str) -> str | None:
    """
    Carrega o arquivo de insight (.md) correspondente a um fundo e competência.

    O arquivo deve estar em:
        data/funds/{fundo_id}/insights/{YYYY-MM}.md

    Ex: competencia '03/2026' → arquivo '2026-03.md'

    Returns:
        Conteúdo do markdown como string, ou None se não existir.
    """
    base_dir = Path(base_dir)

    # Converte '03/2026' → '2026-03'
    chave = _competencia_para_chave(competencia)
    insight_path = base_dir / "data" / "funds" / fundo_id / "insights" / f"{chave}.md"

    if not insight_path.exists():
        return None

    try:
        return insight_path.read_text(encoding="utf-8")
    except Exception as e:
        log.error(f"Erro ao ler insight {insight_path}: {e}")
        return None


def listar_insights_disponiveis(base_dir: str | Path, fundo_id: str) -> list[str]:
    """
    Lista as competências que possuem arquivo de insight disponível.

    Returns:
        Lista de competências no formato '03/2026', ordenada da mais recente.
    """
    base_dir     = Path(base_dir)
    insights_dir = base_dir / "data" / "funds" / fundo_id / "insights"

    if not insights_dir.exists():
        return []

    competencias = []
    for md_path in insights_dir.glob("*.md"):
        # '2026-03.md' → '03/2026'
        stem   = md_path.stem          # '2026-03'
        partes = stem.split("-")
        if len(partes) == 2:
            competencias.append(f"{partes[1]}/{partes[0]}")

    competencias.sort(key=_competencia_para_chave, reverse=True)
    return competencias


# ---------------------------------------------------------------------------
# DOCUMENTOS
# ---------------------------------------------------------------------------

# Tipos de documentos suportados e seus labels
TIPOS_DOCUMENTO = {
    "regulamento":  "Regulamento",
    "assembleias":  "Assembleias",
}


def listar_documentos(base_dir: str | Path, fundo_id: str) -> dict[str, list[dict]]:
    """
    Lista todos os documentos disponíveis de um fundo, organizados por tipo.

    Returns:
        Dict com tipo como chave e lista de documentos como valor.
        Ex:
        {
            "regulamento": [
                {"nome": "regulamento.pdf", "path": Path(...), "tem_insight": True}
            ],
            "assembleias": [
                {"nome": "assembleia-2026-03.pdf", "path": Path(...), "tem_insight": False}
            ]
        }
    """
    base_dir  = Path(base_dir)
    docs_root = base_dir / "data" / "funds" / fundo_id / "documentos"
    resultado = {}

    for tipo, label in TIPOS_DOCUMENTO.items():
        tipo_dir = docs_root / tipo
        if not tipo_dir.exists():
            resultado[tipo] = []
            continue

        pdfs = sorted(tipo_dir.glob("*.pdf"), reverse=True)
        resultado[tipo] = [
            {
                "nome":        pdf.name,
                "stem":        pdf.stem,
                "path":        pdf,
                "tipo":        tipo,
                "label":       label,
                "tem_insight": (tipo_dir / f"{pdf.stem}.md").exists(),
                **parsear_nome_arquivo(pdf.stem),
            }
            for pdf in pdfs
        ]

    return resultado


def carregar_documento_insight(base_dir: str | Path, fundo_id: str, tipo: str, stem: str) -> str | None:
    """
    Carrega o insight (.md) de um documento específico.

    Args:
        base_dir:  Raiz do projeto
        fundo_id:  ID do fundo
        tipo:      Tipo do documento ('regulamento', 'assembleias')
        stem:      Nome do arquivo sem extensão (ex: 'regulamento', 'assembleia-2026-03')

    Returns:
        Conteúdo do markdown ou None se não existir.
    """
    base_dir  = Path(base_dir)
    md_path   = base_dir / "data" / "funds" / fundo_id / "documentos" / tipo / f"{stem}.md"

    if not md_path.exists():
        return None

    try:
        return md_path.read_text(encoding="utf-8")
    except Exception as e:
        log.error(f"Erro ao ler insight de documento {md_path}: {e}")
        return None


def carregar_pdf_bytes(pdf_path: Path) -> bytes | None:
    """
    Lê um PDF e retorna seus bytes para renderização no Streamlit.

    Returns:
        Bytes do PDF ou None se não encontrado.
    """
    try:
        return pdf_path.read_bytes()
    except Exception as e:
        log.error(f"Erro ao ler PDF {pdf_path}: {e}")
        return None


# ---------------------------------------------------------------------------
# NOTAS DE DOCUMENTOS
# ---------------------------------------------------------------------------

import re as _re
import uuid as _uuid
from datetime import datetime as _dt


def _notes_path(base_dir: Path, fundo_id: str, tipo: str, stem: str) -> Path:
    return base_dir / "data" / "funds" / fundo_id / "documentos" / tipo / f"{stem}.notes.json"


def carregar_notas(base_dir: str | Path, fundo_id: str, tipo: str, stem: str) -> list[dict]:
    """
    Carrega lista de notas de um documento.
    Cada nota: {id, titulo, conteudo, criado_em, editado_em}
    """
    base_dir = Path(base_dir)
    path     = _notes_path(base_dir, fundo_id, tipo, stem)
    if not path.exists():
        return []
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        log.error(f"Erro ao ler notas {path}: {e}")
        return []


def salvar_notas(base_dir: str | Path, fundo_id: str, tipo: str, stem: str, notas: list[dict]) -> bool:
    """Salva lista de notas em JSON."""
    base_dir = Path(base_dir)
    path     = _notes_path(base_dir, fundo_id, tipo, stem)
    try:
        path.write_text(json.dumps(notas, ensure_ascii=False, indent=2), encoding="utf-8")
        return True
    except Exception as e:
        log.error(f"Erro ao salvar notas {path}: {e}")
        return False


def adicionar_nota(base_dir: str | Path, fundo_id: str, tipo: str, stem: str,
                   titulo: str, conteudo: str) -> bool:
    """Adiciona uma nova nota à lista existente."""
    notas = carregar_notas(base_dir, fundo_id, tipo, stem)
    agora = _dt.now().isoformat()
    notas.append({
        "id":         str(_uuid.uuid4())[:8],
        "titulo":     titulo.strip() or "Nota sem título",
        "conteudo":   conteudo.strip(),
        "criado_em":  agora,
        "editado_em": agora,
    })
    return salvar_notas(base_dir, fundo_id, tipo, stem, notas)


def editar_nota(base_dir: str | Path, fundo_id: str, tipo: str, stem: str,
                nota_id: str, titulo: str, conteudo: str) -> bool:
    """Edita uma nota existente pelo ID."""
    notas = carregar_notas(base_dir, fundo_id, tipo, stem)
    for nota in notas:
        if nota["id"] == nota_id:
            nota["titulo"]     = titulo.strip() or "Nota sem título"
            nota["conteudo"]   = conteudo.strip()
            nota["editado_em"] = _dt.now().isoformat()
            return salvar_notas(base_dir, fundo_id, tipo, stem, notas)
    return False


def apagar_nota(base_dir: str | Path, fundo_id: str, tipo: str, stem: str, nota_id: str) -> bool:
    """Remove uma nota pelo ID."""
    notas = carregar_notas(base_dir, fundo_id, tipo, stem)
    notas = [n for n in notas if n["id"] != nota_id]
    return salvar_notas(base_dir, fundo_id, tipo, stem, notas)


def notas_existem(base_dir: str | Path, fundo_id: str, tipo: str, stem: str) -> bool:
    """Verifica se existem notas para um documento."""
    return len(carregar_notas(base_dir, fundo_id, tipo, stem)) > 0


# ---------------------------------------------------------------------------
# PARSE DE VERSÃO/DATA DO NOME DO ARQUIVO
# ---------------------------------------------------------------------------

def parsear_nome_arquivo(stem: str) -> dict:
    """
    Extrai versão e data do nome do arquivo.
    Padrão: qualquer_nome_V1_01012026 ou qualquer_nome_V2_15032026

    Returns:
        {"nome_base": str, "versao": str|None, "data": str|None}
    """
    # Tenta extrair padrão _V{n}_{DDMMYYYY} no final
    match = _re.search(r"_(V\d+)_(\d{8})$", stem, _re.IGNORECASE)
    if match:
        versao = match.group(1).upper()
        data_raw = match.group(2)
        try:
            data_fmt = f"{data_raw[:2]}/{data_raw[2:4]}/{data_raw[4:]}"
        except Exception:
            data_fmt = data_raw
        nome_base = stem[:match.start()]
        return {"nome_base": nome_base, "versao": versao, "data": data_fmt}

    # Tenta só _V{n} no final
    match2 = _re.search(r"_(V\d+)$", stem, _re.IGNORECASE)
    if match2:
        versao    = match2.group(1).upper()
        nome_base = stem[:match2.start()]
        return {"nome_base": nome_base, "versao": versao, "data": None}

    return {"nome_base": stem, "versao": None, "data": None}