"""
core/metrics.py

Responsabilidade: calcular métricas derivadas a partir dos dados
brutos retornados pelo loader.

Não lê arquivos — recebe dicts e retorna dicts.
Todas as funções são puras: mesma entrada → mesma saída.
"""

from __future__ import annotations


# HELPERS
def _safe_div(numerador: float, denominador: float, default: float = 0.0) -> float:
    """Divisão segura — retorna default se denominador for zero."""
    if denominador == 0:
        return default
    return numerador / denominador


def _pct(numerador: float, denominador: float) -> float:
    """Retorna percentual (0–100). Ex: 0.095 → 9.5"""
    return round(_safe_div(numerador, denominador) * 100, 2)


# SAÚDE DA CARTEIRA
def taxa_inadimplencia(dados: dict) -> float:
    """
    Inadimplentes / Carteira bruta (%).

    Usa a carteira bruta (dc_com_aquis.total) como denominador,
    pois é o valor antes da provisão.
    """
    inad   = dados["ativo"]["dc_com_aquis"]["existentes_inadimplentes"]
    bruta  = dados["ativo"]["dc_com_aquis"]["total"]
    return _pct(inad, bruta)


def cobertura_provisao(dados: dict) -> float:
    """
    Provisão constituída / Total inadimplente (%).

    Quanto da inadimplência já está coberta por provisão.
    100% = provisão total; abaixo disso há exposição residual.
    """
    provisao = dados["ativo"]["dc_com_aquis"]["provisao_perda"]
    inad     = dados["ativo"]["dc_com_aquis"]["existentes_inadimplentes"]
    return _pct(provisao, inad)


def exposicao_nao_provisionada(dados: dict) -> float:
    """
    Valor absoluto da inadimplência ainda não coberta por provisão (R$).
    """
    inad     = dados["ativo"]["dc_com_aquis"]["existentes_inadimplentes"]
    provisao = dados["ativo"]["dc_com_aquis"]["provisao_perda"]
    return max(round(inad - provisao, 2), 0.0)


def pct_carteira_curto_prazo(dados: dict) -> float:
    """
    Percentual da carteira adimplente que vence em até 30 dias (%).
    """
    ate_30  = dados["comportamento_carteira"]["com_aquis"]["vencimentos"]["ate_30d"]
    total   = dados["comportamento_carteira"]["com_aquis"]["vencimentos"]["total"]
    return _pct(ate_30, total)


def distribuicao_vencimentos(dados: dict) -> list[dict]:
    """
    Retorna a distribuição de vencimentos como lista ordenada,
    pronta para uso em gráficos de barras.

    Returns:
        [{"faixa": "até 30d", "valor": 1396763.06, "percentual": 63.0}, ...]
    """
    venc  = dados["comportamento_carteira"]["com_aquis"]["vencimentos"]
    total = venc["total"]

    faixas = [
        ("até 30d",    venc["ate_30d"]),
        ("31–60d",     venc["31_60d"]),
        ("61–90d",     venc["61_90d"]),
        ("91–120d",    venc["91_120d"]),
        ("121–150d",   venc["121_150d"]),
        ("151–180d",   venc["151_180d"]),
        ("181–360d",   venc["181_360d"]),
        ("361–720d",   venc["361_720d"]),
        ("721–1080d",  venc["721_1080d"]),
        ("acima 1080d",venc["acima_1080d"]),
    ]

    return [
        {
            "faixa":      label,
            "valor":      valor,
            "percentual": _pct(valor, total),
        }
        for label, valor in faixas
        if valor > 0  # omite faixas zeradas
    ]


def distribuicao_aging(dados: dict) -> list[dict]:
    """
    Retorna o aging da inadimplência como lista ordenada,
    pronta para uso em gráficos.
    """
    inad  = dados["comportamento_carteira"]["com_aquis"]["inadimplentes"]
    total = inad["total"]

    faixas = [
        ("1–30d",      inad["1_30d"]),
        ("31–60d",     inad["31_60d"]),
        ("61–90d",     inad["61_90d"]),
        ("91–120d",    inad["91_120d"]),
        ("121–150d",   inad["121_150d"]),
        ("151–180d",   inad["151_180d"]),
        ("181–360d",   inad["181_360d"]),
        ("361–720d",   inad["361_720d"]),
        ("721–1080d",  inad["721_1080d"]),
        ("acima 1080d",inad["acima_1080d"]),
    ]

    return [
        {
            "faixa":      label,
            "valor":      valor,
            "percentual": _pct(valor, total) if total > 0 else 0.0,
        }
        for label, valor in faixas
    ]



# PATRIMÔNIO
def variacao_pl_vs_media(dados: dict) -> float:
    """
    Variação percentual do PL atual vs PL médio dos últimos 3 meses (%).
    Positivo = PL acima da média; negativo = abaixo.
    """
    pl_atual = dados["patrimonio_liquido"]["pl"]
    pl_medio = dados["patrimonio_liquido"]["pl_medio_3m"]
    if pl_medio == 0:
        return 0.0
    return round(((pl_atual - pl_medio) / pl_medio) * 100, 2)



# COTAS
def pl_por_subclasse(dados: dict) -> list[dict]:
    """
    Calcula o PL de cada subclasse (quantidade × valor da cota).

    Returns:
        [{"tipo": "Mezanino 1", "serie": "Série 1",
          "quantidade_cotas": 827.9, "valor_cota": 1033.9,
          "pl_subclasse": 855966.8, "rentabilidade_pct": 1.89}, ...]
    """
    classes     = dados["outras_informacoes"]["descricao_classes"]
    rentabs     = {
        (r["tipo"], r["serie"]): r["rentabilidade_pct"]
        for r in dados["outras_informacoes"]["rentabilidade"]
    }

    resultado = []
    for c in classes:
        qtd   = c["quantidade_cotas"]
        vl    = c["valor_cota"]
        pl_sc = round(qtd * vl, 2)
        rent  = rentabs.get((c["tipo"], c["serie"]), None)

        resultado.append({
            "tipo":             c["tipo"],
            "serie":            c["serie"],
            "quantidade_cotas": qtd,
            "valor_cota":       vl,
            "pl_subclasse":     pl_sc,
            "rentabilidade_pct": rent,
        })

    return resultado


def variacao_valor_cota(historico: list[dict], tipo: str, serie: str = "") -> float | None:
    """
    Variação percentual do valor da cota entre as duas últimas competências.

    Args:
        historico: lista retornada por carregar_historico() (ordem cronológica)
        tipo:  ex: 'Mezanino 1', 'Subordinada 1', 'Senior'
        serie: ex: 'Série 1' (pode ser vazio para subordinada junior)

    Returns:
        Variação em % ou None se não houver competências suficientes.
    """
    if len(historico) < 2:
        return None

    def _valor_cota(dados):
        for c in dados["outras_informacoes"]["descricao_classes"]:
            if c["tipo"] == tipo and c["serie"] == serie:
                return c["valor_cota"]
        return None

    vl_anterior = _valor_cota(historico[-2])
    vl_atual    = _valor_cota(historico[-1])

    if vl_anterior is None or vl_atual is None or vl_anterior == 0:
        return None

    return round(((vl_atual - vl_anterior) / vl_anterior) * 100, 2)



# CEDENTES
def _nivel_concentracao(pct: float) -> str:
    """Classifica o nível de concentração de um cedente."""
    if pct >= 40:
        return "critico"    # >= 40%
    if pct >= 25:
        return "alto"       # 25–40%
    if pct >= 10:
        return "moderado"   # 10–25%
    return "baixo"          # < 10%


def analise_cedentes(dados: dict) -> dict:
    """
    Analisa a concentração dos cedentes declarados (> 10% do PL).

    Returns:
        {
            "cedentes": [
                {
                    "cpf_cnpj": "02251268189",
                    "participacao_pct": 43.0,
                    "nivel": "critico"
                }
            ],
            "maior_concentracao_pct": 43.0,
            "nivel_geral": "critico",
            "total_declarados": 1,
        }
    """
    cedentes_raw = dados["ativo"]["dc_com_aquis"]["cedentes_mais_10pct_pl"]

    cedentes = [
        {
            "cpf_cnpj":         c["cpf_cnpj"],
            "participacao_pct": c["participacao_pct"],
            "nivel":            _nivel_concentracao(c["participacao_pct"]),
        }
        for c in cedentes_raw
    ]

    maior = max((c["participacao_pct"] for c in cedentes), default=0.0)

    return {
        "cedentes":              cedentes,
        "maior_concentracao_pct": maior,
        "nivel_geral":           _nivel_concentracao(maior),
        "total_declarados":      len(cedentes),
    }



# SCR BACEN
def distribuicao_scr(dados: dict) -> dict:
    """
    Calcula o percentual de cada rating SCR sobre o total da carteira.
    Usa classificação por devedor (principal para análise de risco).

    Returns:
        {
            "por_rating": [
                {"rating": "A", "valor": 1461600.6, "percentual": 59.7},
                {"rating": "C", "valor": 986840.4,  "percentual": 40.3},
                ...
            ],
            "total":            2448441.0,
            "pct_baixo_risco":  59.7,   # AA + A
            "pct_atencao":      40.3,   # B + C
            "pct_alto_risco":   0.0,    # D + E + F + G + H
        }
    """
    scr   = dados["outras_informacoes"]["scr_bacen"]["por_devedor"]
    total = sum(scr.values())

    ratings = ["AA", "A", "B", "C", "D", "E", "F", "G", "H"]

    por_rating = [
        {
            "rating":     r,
            "valor":      scr[r],
            "percentual": _pct(scr[r], total),
        }
        for r in ratings
        if scr[r] > 0  # omite ratings zerados
    ]

    pct_baixo  = _pct(scr["AA"] + scr["A"], total)
    pct_atenc  = _pct(scr["B"]  + scr["C"], total)
    pct_alto   = _pct(sum(scr[r] for r in ["D","E","F","G","H"]), total)

    return {
        "por_rating":      por_rating,
        "total":           round(total, 2),
        "pct_baixo_risco": pct_baixo,
        "pct_atencao":     pct_atenc,
        "pct_alto_risco":  pct_alto,
    }



# FUNÇÃO CONSOLIDADA
def calcular_todas(dados: dict, historico: list[dict] | None = None) -> dict:
    """
    Calcula todas as métricas de uma vez e retorna um dict consolidado.
    É o que o dashboard vai chamar na maioria dos casos.

    Args:
        dados:     dict de uma competência (retorno do loader)
        historico: lista de todas as competências (opcional, para métricas temporais)

    Returns:
        Dict com todas as métricas organizadas por categoria.
    """
    historico = historico or []

    # Métricas de variação de cota por subclasse
    variacoes_cota = {}
    for c in dados["outras_informacoes"]["descricao_classes"]:
        chave = f"{c['tipo']}|{c['serie']}"
        variacoes_cota[chave] = variacao_valor_cota(historico, c["tipo"], c["serie"])

    return {
        "carteira": {
            "taxa_inadimplencia_pct":    taxa_inadimplencia(dados),
            "cobertura_provisao_pct":    cobertura_provisao(dados),
            "exposicao_nao_provisionada": exposicao_nao_provisionada(dados),
            "pct_vencimento_30d":        pct_carteira_curto_prazo(dados),
            "distribuicao_vencimentos":  distribuicao_vencimentos(dados),
            "distribuicao_aging":        distribuicao_aging(dados),
        },
        "patrimonio": {
            "variacao_pl_vs_media_pct":  variacao_pl_vs_media(dados),
        },
        "cotas": {
            "pl_por_subclasse":          pl_por_subclasse(dados),
            "variacao_valor_cota":       variacoes_cota,
        },
        "cedentes":  analise_cedentes(dados),
        "scr":       distribuicao_scr(dados),
    }