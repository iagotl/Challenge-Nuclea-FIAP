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