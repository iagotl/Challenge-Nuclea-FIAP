"""
core/processor.py
 
Responsabilidade: orquestrar o pipeline de ingestão de XMLs.
 
Fluxo por fundo:
    inbox/*.xml  →  extractor.extrair()  →  cache/*.json  →  processed/*.xml
 
Chamado pelo app.py na inicialização da aplicação. Processa apenas
arquivos ainda não processados (presentes em inbox/).
 
Não depende do Streamlit — pode ser executado standalone se necessário.
"""
 
import json
import logging
import shutil
from datetime import datetime
from pathlib import Path
 
import yaml
 
from core.extractor import extrair
 
# ---------------------------------------------------------------------------
# LOGGING
# ---------------------------------------------------------------------------
 
logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    level=logging.INFO,
)
log = logging.getLogger(__name__)
 
 
# ---------------------------------------------------------------------------
# HELPERS
# ---------------------------------------------------------------------------
 
def _carregar_fundos(config_path: Path) -> list[dict]:
    """Lê funds.yaml e retorna a lista de fundos configurados."""
    if not config_path.exists():
        log.warning(f"funds.yaml não encontrado em {config_path}. Nenhum fundo será processado.")
        return []
 
    with open(config_path, encoding="utf-8") as f:
        config = yaml.safe_load(f)
 
    return config.get("funds", [])
 
 
def _nome_cache(xml_path: Path) -> str:
    """
    Gera o nome do arquivo JSON de cache a partir do nome do XML.
    Ex: IFP_032026.xml → IFP_032026.json
    """
    return xml_path.stem + ".json"
 
 
def _processar_xml(xml_path: Path, cache_dir: Path, processed_dir: Path) -> bool:
    """
    Processa um único XML:
    1. Extrai os dados
    2. Salva JSON em cache/
    3. Move XML para processed/
 
    Returns:
        True se processado com sucesso, False em caso de erro.
    """
    cache_file = cache_dir / _nome_cache(xml_path)
 
    try:
        log.info(f"  Processando: {xml_path.name}")
 
        # 1. Extrai
        dados = extrair(xml_path)
 
        # 2. Adiciona metadados de processamento
        dados["_meta"] = {
            "arquivo_origem": xml_path.name,
            "processado_em":  datetime.now().isoformat(),
        }
 
        # 3. Salva JSON no cache
        cache_file.write_text(
            json.dumps(dados, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        log.info(f"  ✓ Cache salvo: {cache_file.name}")
 
        # 4. Move XML para processed/
        destino = processed_dir / xml_path.name
        shutil.move(str(xml_path), str(destino))
        log.info(f"  ✓ Movido para processed/: {xml_path.name}")
 
        return True
 
    except Exception as e:
        log.error(f"  ✗ Erro ao processar {xml_path.name}: {e}")
        # Não move o arquivo — fica em inbox/ para nova tentativa
        # Remove cache parcial se foi criado
        if cache_file.exists():
            cache_file.unlink()
        return False
 
 
def _processar_fundo(fundo_id: str, data_root: Path) -> dict:
    """
    Processa todos os XMLs pendentes de um fundo.
 
    Returns:
        dict com contadores: total, sucesso, erro
    """
    inbox_dir     = data_root / fundo_id / "informes" / "inbox"
    cache_dir     = data_root / fundo_id / "informes" / "cache"
    processed_dir = data_root / fundo_id / "informes" / "processed"
 
    # Garante que os diretórios existem
    for d in [inbox_dir, cache_dir, processed_dir]:
        d.mkdir(parents=True, exist_ok=True)
 
    xmls_pendentes = sorted(inbox_dir.glob("*.xml"))
 
    if not xmls_pendentes:
        log.info(f"[{fundo_id}] Nenhum XML pendente em inbox/.")
        return {"total": 0, "sucesso": 0, "erro": 0}
 
    log.info(f"[{fundo_id}] {len(xmls_pendentes)} XML(s) encontrado(s) em inbox/.")
 
    resultado = {"total": len(xmls_pendentes), "sucesso": 0, "erro": 0}
 
    for xml_path in xmls_pendentes:
        ok = _processar_xml(xml_path, cache_dir, processed_dir)
        if ok:
            resultado["sucesso"] += 1
        else:
            resultado["erro"] += 1
 
    return resultado
 
 
# ---------------------------------------------------------------------------
# FUNÇÃO PÚBLICA
# ---------------------------------------------------------------------------
 
def processar_pendentes(base_dir: str | Path) -> dict:
    """
    Ponto de entrada principal. Varre todos os fundos configurados
    e processa os XMLs pendentes em cada inbox/.
 
    Args:
        base_dir: Raiz do projeto (onde ficam config/ e data/)
 
    Returns:
        dict com resumo do processamento por fundo e totais gerais.
        Ex:
        {
            "xama":    {"total": 2, "sucesso": 2, "erro": 0},
            "fundo_b": {"total": 0, "sucesso": 0, "erro": 0},
            "_totais": {"total": 2, "sucesso": 2, "erro": 0},
        }
    """
    base_dir  = Path(base_dir)
    config_path = base_dir / "config" / "funds.yaml"
    data_root   = base_dir / "data" / "funds"
 
    log.info("=" * 50)
    log.info("Iniciando processamento de XMLs pendentes...")
    log.info("=" * 50)
 
    fundos = _carregar_fundos(config_path)
 
    if not fundos:
        log.warning("Nenhum fundo configurado em funds.yaml.")
        return {"_totais": {"total": 0, "sucesso": 0, "erro": 0}}
 
    resumo = {}
    totais = {"total": 0, "sucesso": 0, "erro": 0}
 
    for fundo in fundos:
        fundo_id = fundo.get("id")
        if not fundo_id:
            log.warning("Fundo sem 'id' em funds.yaml — ignorado.")
            continue
 
        resultado = _processar_fundo(fundo_id, data_root)
        resumo[fundo_id] = resultado
 
        for k in totais:
            totais[k] += resultado[k]
 
    resumo["_totais"] = totais
 
    log.info("=" * 50)
    log.info(f"Processamento concluído.")
    log.info(f"Total: {totais['total']} | Sucesso: {totais['sucesso']} | Erro: {totais['erro']}")
    log.info("=" * 50)
 
    return resumo