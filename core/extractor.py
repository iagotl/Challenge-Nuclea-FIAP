"""
core/extractor.py
 
Responsabilidade única: receber o path de um XML de Informe Mensal FIDC
(layout CVM/B3 versão 6.6) e retornar um dicionário Python estruturado
com todos os dados do informe.
 
Não lê arquivos de disco além do XML recebido.
Não escreve nada — quem persiste é o processor.py.
"""
 
import xml.etree.ElementTree as ET
from pathlib import Path
 
 
# ---------------------------------------------------------------------------
# HELPERS
# ---------------------------------------------------------------------------
 
def _val(node, tag, default=0.0):
    """Retorna float de uma tag filha direta. Trata vírgula como separador decimal."""
    el = node.find(tag)
    if el is None or el.text is None or el.text.strip() == "":
        return default
    return float(el.text.strip().replace(",", "."))
 
 
def _txt(node, tag, default=""):
    """Retorna texto de uma tag filha direta."""
    el = node.find(tag)
    if el is None or el.text is None:
        return default
    return el.text.strip()
 
 
def _taxa(node):
    """Extrai bloco de taxa (TX_MIN, TX_MEDIO, TX_MAXIMO)."""
    if node is None:
        return {"min": 0.0, "medio": 0.0, "max": 0.0}
    return {
        "min":   _val(node, "TX_MIN"),
        "medio": _val(node, "TX_MEDIO"),
        "max":   _val(node, "TX_MAXIMO"),
    }
 
 
# ---------------------------------------------------------------------------
# SEÇÕES
# ---------------------------------------------------------------------------
 
def _extrair_cabecalho(root):
    cab = root.find("CAB_INFORM")
    return {
        "versao":               _txt(cab, "VERSAO"),
        "competencia":          _txt(cab, "DT_COMPT"),
        "monoclasse":           _txt(cab, "CLASS_UNICA"),
        "cnpj_administrador":   _txt(cab, "NR_CNPJ_ADM"),
        "cnpj_fundo":           _txt(cab, "NR_CNPJ_FUNDO"),
        "nome_classe":          _txt(cab, "NM_CLASSE"),
        "cnpj_classe":          _txt(cab, "NR_CNPJ_CLASSE"),
        "tipo_condominio":      _txt(cab, "TP_CONDOMINIO"),
        "fundo_exclusivo":      _txt(cab, "FDO_EXCL"),
        "cotistas_vinculados":  _txt(cab, "COTST_VINCUL"),
    }
 
 
def _extrair_ativo(lista):
    ap = lista.find("APLIC_ATIVO")
    ce = ap.find("CRED_EXISTE")
    di = ap.find("DICRED")
    vm = ap.find("VALORES_MOB")
    md = ap.find("MERC_DERIVATIVO")
    oa = ap.find("OUTROS_ATIVOS")
 
    cedentes = []
    for c in ap.findall("LISTA_CEDENT_CRED_EXISTE/CEDENT_CRED_EXISTE"):
        cedentes.append({
            "cpf_cnpj":         _txt(c, "NR_PF_PJ_CEDENT_CRED_EXISTE"),
            "participacao_pct": _val(c, "PR_CEDENT_CRED_EXISTE"),
        })
 
    return {
        "disponibilidades": _val(ap, "VL_DISPONIB"),
        "carteira_total":   _val(ap, "VL_CARTEIRA"),
 
        "dc_com_aquis": {
            "total":                    _val(ce, "VL_SOM_DICRED_AQUIS"),
            "a_vencer_adimplentes":     _val(ce, "VL_CRED_EXISTE_VENC_ADIMPL"),
            "a_vencer_com_inadimpl":    _val(ce, "VL_CRED_EXISTE_VENC_INAD"),
            "parcelas_inadimplentes":   _val(ce, "VL_CRED_TOTAL_VENC_INAD"),
            "existentes_inadimplentes": _val(ce, "VL_CRED_EXISTE_INAD"),
            "a_performar":              _val(ce, "VL_CRED_REFER_DICRED_PERFO"),
            "vencidos_cessao":          _val(ce, "VL_CRED_VENC_PEND"),
            "recuperacao_judicial":     _val(ce, "VL_CRED_ORIGEM_EMP_PROC_RECUP"),
            "receitas_publicas":        _val(ce, "VL_DECOR_RECEIT_PUBLIC"),
            "acoes_judiciais":          _val(ce, "VL_CRED_ACAO_JUDIC"),
            "risco_juridico":           _val(ce, "VL_CRED_CONST_JUR_FATRISC"),
            "provisao_perda":           _val(ce, "VL_PROVIS_REDUC_RECUP"),
            "cedentes_mais_10pct_pl":   cedentes,
        },
 
        "dc_sem_aquis": {
            "total":                    _val(di, "VL_DICRED"),
            "a_vencer_adimplentes":     _val(di, "VL_DICRED_CEDENT"),
            "a_vencer_com_inadimpl":    _val(di, "VL_DICRED_EXISTE_VENC_INAD"),
            "parcelas_inadimplentes":   _val(di, "VL_DICRED_TOTAL_VENC_INAD"),
            "existentes_inadimplentes": _val(di, "VL_DICRED_EXISTE_INAD"),
            "a_performar":              _val(di, "VL_DICRED_REFER_DICRED_PERFO"),
            "vencidos_cessao":          _val(di, "VL_DICRED_VENC_PEND"),
            "recuperacao_judicial":     _val(di, "VL_DICRED_ORIGEM_EMP_PROC_RECUP"),
            "receitas_publicas":        _val(di, "VL_DICRED_RECEIT_PUBLIC"),
            "acoes_judiciais":          _val(di, "VL_DICRED_ACAO_JUDIC"),
            "risco_juridico":           _val(di, "VL_DICRED_CONST_JUR_FATRISC"),
            "provisao_perda":           _val(di, "VL_DICRED_PROVIS_REDUC_RECUP"),
        },
 
        "valores_mobiliarios": {
            "total":              _val(vm, "VL_SOM_VALORES_MOB"),
            "debentures":         _val(vm, "VL_DEBT"),
            "cri":                _val(vm, "VL_CRI"),
            "notas_promissorias": _val(vm, "VL_NP_COMERC"),
            "letras_financeiras": _val(vm, "VL_LETRA_FINANC"),
            "cotas_fif":          _val(vm, "VL_CLS_COTA_FIF"),
            "outros":             _val(vm, "VL_OUTRO_DICRED"),
        },
 
        "titulos_publicos_federais": _val(ap, "VL_TITPUB_FED"),
        "cdb":                       _val(ap, "VL_CDB"),
        "operacoes_compromissadas":  _val(ap, "VL_APLIC_OPER_COMPSS"),
        "ativos_rf_outros":          _val(ap, "VL_ATIV_FINANC_RF"),
        "cotas_fidc":                _val(ap, "VL_COTA_FIDC"),
        "contratos_entrega_futura":  _val(ap, "VL_CONTR_COMPRA_VENDA_PRESTC_FUTURA"),
 
        "provisoes": {
            "debentures_cri_npc_lf": _val(ap, "VL_PVS_DBT_CRI_NTA_PMS"),
            "cotas_fidc":            _val(ap, "VL_PVS_CTA_FND_INV"),
            "outros_ativos":         _val(ap, "VL_PVS_OTR_ATV"),
        },
 
        "derivativos": {
            "total":             _val(md, "VL_SOM_MERC_DERIVATIVO"),
            "termo_comprado":    _val(md, "VL_MERC_TERMO_POS_COMPRD"),
            "opcoes_titular":    _val(md, "VL_MERC_OP_POS_TITUL"),
            "futuro_ajuste_pos": _val(md, "VL_MERC_FUT_AJUST_POSIT"),
            "swap_a_receber":    _val(md, "VL_DIFER_SWAP_RECEB"),
            "coberturas":        _val(md, "VL_COBERT_PREST"),
            "deposito_margem":   _val(md, "VL_DEPOS_MARGEM"),
        },
 
        "outros_ativos": {
            "total":       _val(oa, "VL_SOM_OUTROS_ATIVOS"),
            "curto_prazo": _val(oa, "VL_OUTRO_VL_RECEB_CURPRZ"),
            "longo_prazo": _val(oa, "VL_OUTRO_VL_RECEB_LPRAZO"),
        },
 
        "ativo_total": _val(ap, "VL_SOM_APLIC_ATIVO"),
    }
 
 
def _extrair_carteira_segmento(lista):
    cs  = lista.find("CART_SEGMT")
    sc  = cs.find("SEGMT_COMERC")
    ss  = cs.find("SEGMT_SERV")
    sf  = cs.find("SEGMT_FINANC")
    sfa = cs.find("SEGMT_FACT")
    sp  = cs.find("SEGMT_SETOR_PUBLIC")
 
    return {
        "total":               _val(cs, "VL_SOM_CART_SEGMT"),
        "industrial":          _val(cs, "VL_IND"),
        "mercado_imobiliario": _val(cs, "VL_MERC_IMOBIL"),
        "comercial": {
            "total":       _val(sc, "VL_SOM_SEGMT_COMERC"),
            "comercial":   _val(sc, "VL_COMERC"),
            "varejo":      _val(sc, "VL_COMERC_VARJ"),
            "arrendamento":_val(sc, "VL_ARREND_MERCNT"),
        },
        "servicos": {
            "total":        _val(ss, "VL_SOM_SEGMT_SERV"),
            "servicos":     _val(ss, "VL_SERV"),
            "publicos":     _val(ss, "VL_SERV_PUBLIC"),
            "educacionais": _val(ss, "VL_SERV_EDUC"),
            "entretenimento":_val(ss, "VL_SERV_ENTRETEN"),
        },
        "agronegocio": _val(cs, "VL_AGRONEG"),
        "financeiro": {
            "total":           _val(sf, "VL_SOM_SEGMT_FINANC"),
            "credito_pessoal": _val(sf, "VL_FINANC_CRED_PESSOA"),
            "consignado":      _val(sf, "VL_FINANC_CRED_PESSOA_CONSIG"),
            "corporativo":     _val(sf, "VL_FINANC_CRED_CORPOR"),
            "middle_market":   _val(sf, "VL_FINANC_MMARKET"),
            "veiculos":        _val(sf, "VL_FINANC_VEICL"),
            "imobiliario_emp": _val(sf, "VL_FINANC_IMOBIL_EMPSRL"),
            "imobiliario_res": _val(sf, "VL_FINANC_IMOBIL_RESID"),
            "outros":          _val(sf, "VL_FINANC_OUTRO"),
        },
        "cartao_credito": _val(cs, "VL_CART_CRED"),
        "factoring": {
            "total":       _val(sfa, "VL_SOM_SEGMT_FACT"),
            "pessoal":     _val(sfa, "VL_FACT_PESSOA"),
            "corporativo": _val(sfa, "VL_FACT_CORPOR"),
        },
        "setor_publico": {
            "total":         _val(sp, "VL_SOM_SEGMT_SETOR_PUBLIC"),
            "precatorios":   _val(sp, "VL_SETOR_PUBLIC_PRECAT"),
            "creditos_trib": _val(sp, "VL_SETOR_PUBLIC_CRED_TRIBUT"),
            "royalties":     _val(sp, "VL_SETOR_PUBLIC_ROYA"),
            "outros":        _val(sp, "VL_SETOR_PUBLIC_OUTRO"),
        },
        "acoes_judiciais":        _val(cs, "VL_ACAO_JUDIC"),
        "propriedade_intelectual":_val(cs, "VL_PROPRD_MARCA_PATENT"),
    }
 
 
def _extrair_passivo(lista):
    pa = lista.find("PASSIV")
    pv = pa.find("PASSIV_VALORES")
    pp = pa.find("PASSIV_POSICOES")
    return {
        "total": _val(pa, "VL_SOM_PASSIV"),
        "valores_a_pagar": {
            "total":       _val(pv, "VL_SOM_PASSIV_VALORES"),
            "curto_prazo": _val(pv, "VL_PGTO_CURPRZ"),
            "longo_prazo": _val(pv, "VL_PGTO_LPRAZO"),
        },
        "derivativos": {
            "total":             _val(pp, "VL_SOM_PASSIV_POSICOES"),
            "termo_vendido":     _val(pp, "VL_POS_MANT_VEND"),
            "opcoes_lancadas":   _val(pp, "VL_POS_MANT_LANC"),
            "futuro_ajuste_neg": _val(pp, "VL_POS_MANT_AJT_FUT"),
            "swap_a_pagar":      _val(pp, "VL_POS_MANT_SWAP_PAGAR"),
        },
    }
 
 
def _extrair_patrimonio_liquido(lista):
    pl = lista.find("PATRLIQ")
    return {
        "pl":          _val(pl, "VL_PATRIM_LIQ"),
        "pl_medio_3m": _val(pl, "VL_PATRIM_LIQ_MEDIO"),
    }
 
 
def _extrair_bloco_comportamento(node):
    return {
        "vencimentos": {
            "total":       _val(node, "VL_SOM_PRAZO_VENC"),
            "ate_30d":     _val(node, "VL_PRAZO_VENC_30"),
            "31_60d":      _val(node, "VL_PRAZO_VENC_31_60"),
            "61_90d":      _val(node, "VL_PRAZO_VENC_61_90"),
            "91_120d":     _val(node, "VL_PRAZO_VENC_91_120"),
            "121_150d":    _val(node, "VL_PRAZO_VENC_121_150"),
            "151_180d":    _val(node, "VL_PRAZO_VENC_151_180"),
            "181_360d":    _val(node, "VL_PRAZO_VENC_181_360"),
            "361_720d":    _val(node, "VL_PRAZO_VENC_361_720"),
            "721_1080d":   _val(node, "VL_PRAZO_VENC_721_1080"),
            "acima_1080d": _val(node, "VL_PRAZO_VENC_1080"),
        },
        "inadimplentes": {
            "total":       _val(node, "VL_SOM_INAD_VENC"),
            "1_30d":       _val(node, "VL_INAD_VENC_30"),
            "31_60d":      _val(node, "VL_INAD_VENC_31_60"),
            "61_90d":      _val(node, "VL_INAD_VENC_61_90"),
            "91_120d":     _val(node, "VL_INAD_VENC_91_120"),
            "121_150d":    _val(node, "VL_INAD_VENC_121_150"),
            "151_180d":    _val(node, "VL_INAD_VENC_151_180"),
            "181_360d":    _val(node, "VL_INAD_VENC_181_360"),
            "361_720d":    _val(node, "VL_INAD_VENC_361_720"),
            "721_1080d":   _val(node, "VL_INAD_VENC_721_1080"),
            "acima_1080d": _val(node, "VL_INAD_VENC_1080"),
        },
        "pagos_antecipadamente": {
            "total":       _val(node, "VL_SOM_PAGO_ANTCP"),
            "ate_30d":     _val(node, "VL_PAGO_ANTCP_30"),
            "31_60d":      _val(node, "VL_PAGO_ANTCP_31_60"),
            "61_90d":      _val(node, "VL_PAGO_ANTCP_61_90"),
            "91_120d":     _val(node, "VL_PAGO_ANTCP_91_120"),
            "121_150d":    _val(node, "VL_PAGO_ANTCP_121_150"),
            "151_180d":    _val(node, "VL_PAGO_ANTCP_151_180"),
            "181_360d":    _val(node, "VL_PAGO_ANTCP_181_360"),
            "361_720d":    _val(node, "VL_PAGO_ANTCP_361_720"),
            "721_1080d":   _val(node, "VL_PAGO_ANTCP_721_1080"),
            "acima_1080d": _val(node, "VL_PAGO_ANTCP_1080"),
        },
    }
 
 
def _extrair_comportamento_carteira(lista):
    return {
        "com_aquis": _extrair_bloco_comportamento(lista.find("COMPMT_DICRED_AQUIS")),
        "sem_aquis": _extrair_bloco_comportamento(lista.find("COMPMT_DICRED_SEM_AQUIS")),
    }
 
 
def _extrair_negocios_mes(lista):
    neg = lista.find("NEGOC_DICRED_MES")
 
    def _aquis(tag):
        n = neg.find(tag)
        return {
            "quantidade": _val(n, "QT_DICRED_AQUIS"),
            "valor":      _val(n, "VL_DICRED_AQUIS"),
        }
 
    def _alien(tag):
        n = neg.find(tag)
        return {
            "quantidade":     _val(n, "QT_DICRED_ALIEN"),
            "valor":          _val(n, "VL_DICRED_ALIEN"),
            "valor_contabil": _val(n, "VL_DICRED_ALIEN_CONTAB"),
        }
 
    return {
        "aquisicoes": {
            "total":           _aquis("AQUISICOES"),
            "com_aquis_subst": _aquis("NEGOC_DICRED_MES_AQUIS"),
            "sem_aquis_subst": _aquis("NEGOC_DICRED_MES_SEM_AQUIS"),
            "a_vencer_adimpl": _aquis("NEGOC_DICRED_MES_VENC_ADIMPL"),
            "a_vencer_inad":   _aquis("NEGOC_DICRED_MES_VENC_INAD"),
            "inadimplentes":   _aquis("NEGOC_DICRED_MES_INAD"),
        },
        "alienacoes": {
            "total":            _alien("DICRED_MES_ALIEN"),
            "para_cedentes":    _alien("DICRED_MES_ALIEN_CEDENT"),
            "para_prestadores": _alien("DICRED_MES_ALIEN_PREST"),
            "para_terceiros":   _alien("DICRED_MES_ALIEN_TERCR"),
        },
        "substituicoes": _alien("DICRED_MES_ALIEN_SUBST"),
        "recompras":     _alien("DICRED_MES_ALIEN_RECOMP"),
    }
 
 
def _extrair_taxas(lista):
    tx = lista.find("TAXA_NEGOC_DICRED_MES")
 
    def _dentro(parent_tag, prefix):
        parent = tx.find(parent_tag)
        _zero = {"min": 0.0, "medio": 0.0, "max": 0.0}
        _vazio = {"desconto_compra": _zero, "desconto_venda": _zero,
                  "juros_compra": _zero, "juros_venda": _zero}
        if parent is None:
            return _vazio
        def _safe(tag):
            node = parent.find(tag)
            return _taxa(node) if node is not None else _zero
        return {
            "desconto_compra": _safe(f"{prefix}_DESC_COMPRA"),
            "desconto_venda":  _safe(f"{prefix}_DESC_VENDA"),
            "juros_compra":    _safe(f"{prefix}_JUROS_COMPRA"),
            "juros_venda":     _safe(f"{prefix}_JUROS_VENDA"),
        }
 
    return {
        "dc_com_aquis": _dentro("TAXA_NEGOC_DICRED_MES_AQUIS",       "TAXA_NEGOC_DICRED_MES_AQUIS"),
        "dc_sem_aquis": _dentro("TAXA_NEGOC_DICRED_MES_SEM_AQUIS",   "TAXA_NEGOC_DICRED_MES_SEM_AQUIS"),
        "valores_mob":  _dentro("TAXA_NEGOC_DICRED_MES_VALOR_MOBILI","TAXA_NEGOC_DICRED_MES_VALOR_MOBILI"),
        "titulos_pub":  _dentro("TAXA_NEGOC_DICRED_MES_TITPUB_FED",  "TAXA_NEGOC_DICRED_MES_TITPUB_FED"),
        "cdb":          _dentro("TAXA_NEGOC_DICRED_MES_CDB",         "TAXA_NEGOC_DICRED_MES_CDB"),
        "ativos_rf":    _dentro("TAXA_NEGOC_DICRED_MES_ATIV_RF",     "TAXA_NEGOC_DICRED_MES_ATIV_RF"),
    }
 
 
def _extrair_outras_informacoes(lista):
    oi  = lista.find("OUTRAS_INFORM")
    nc  = oi.find("NUM_COTISTAS")
    ncd = oi.find("NUM_COTISTAS_DESC")
    dsc = oi.find("DESC_SERIE_CLASSE")
    rm  = oi.find("RENT_MES")
    cra = oi.find("CAPTA_RESGA_AMORTI")
    liq = oi.find("LIQUIDEZ")
    des = oi.find("DESEMP")
    gar = oi.find("GARANTIA")
    scr = oi.find("RES_INF_PRST_SCR")
    rtc = oi.find("REG_TRIB_CED")
 
    # Estrutura de cotas
    estrutura_cotas = {
        "existe_subordinacao":  _txt(nc, "EXISTE_ESTRU_SUBORD") == "SIM",
        "total_cotistas":       int(_val(nc, "QT_TOTAL_COTISTAS")),
        "cotistas_senior":      int(_val(nc, "QT_TOTAL_COTISTAS_SENIOR")),
        "cotistas_subordinado": int(_val(nc, "QT_TOTAL_COTISTAS_SUBORD")),
        "classes": [],
    }
    senior = nc.find("CLASSE_SENIOR")
    if senior is not None:
        estrutura_cotas["classes"].append({
            "tipo": "Senior", "serie": _txt(senior, "SERIE"),
            "id_subclasse": _txt(senior, "ID_SUBCLASSE"),
            "cotistas": int(_val(senior, "QT_COTISTAS")),
        })
    for sub in nc.findall("CLASSE_SUBORD"):
        estrutura_cotas["classes"].append({
            "tipo": _txt(sub, "TIPO"), "serie": _txt(sub, "SERIE"),
            "id_subclasse": _txt(sub, "ID_SUBCLASSE"),
            "cotistas": int(_val(sub, "QT_COTISTAS")),
        })
 
    # Perfil de cotistas
    def _perfil(node):
        if node is None:
            return {}
        return {
            "pessoa_fisica":         int(_val(node, "QNT_PSS_FSC")),
            "pessoa_juridica":       int(_val(node, "QNT_PSS_JRD")),
            "banco_comercial":       int(_val(node, "BNC_CMR")),
            "corretora":             int(_val(node, "CRT_DTR")),
            "outras_pj_financeiras": int(_val(node, "OTR_PSS_JRD")),
            "nao_residentes":        int(_val(node, "INV_RSD")),
            "prev_aberta":           int(_val(node, "ENT_ABR_PRD_CMP")),
            "prev_fechada":          int(_val(node, "ENT_FCH_PRD")),
            "rpps":                  int(_val(node, "RGM_PRP_PRD_SRV_PBL")),
            "seguradora":            int(_val(node, "SCD_SGR_RSG")),
            "capitalizacao":         int(_val(node, "SCD_CPT_ARD_MER")),
            "fundo_fidc":            int(_val(node, "FND_INV_CTS")),
            "fundo_imobiliario":     int(_val(node, "FND_INV_IMB")),
            "outros_fundos":         int(_val(node, "OTR_FND_INV")),
            "clube_investimento":    int(_val(node, "CLB_INV")),
            "outros":                int(_val(node, "CAMOTR")),
        }
 
    # Descrição de classes
    descricao_classes = []
    s = dsc.find("DESC_SERIE_CLASSE_SENIOR")
    if s is not None:
        descricao_classes.append({
            "tipo": "Senior", "serie": _txt(s, "SERIE"),
            "quantidade_cotas": _val(s, "QT_COTAS"),
            "valor_cota":       _val(s, "VL_COTAS"),
        })
    for sub in dsc.findall("DESC_SERIE_CLASSE_SUBORD"):
        descricao_classes.append({
            "tipo": _txt(sub, "TIPO"), "serie": _txt(sub, "SERIE"),
            "quantidade_cotas": _val(sub, "QT_COTAS"),
            "valor_cota":       _val(sub, "VL_COTAS"),
        })
 
    # Rentabilidade
    rentabilidade = []
    rs = rm.find("RENT_CLASSE_SENIOR")
    if rs is not None:
        rentabilidade.append({"tipo": "Senior", "serie": _txt(rs, "SERIE"),
                               "rentabilidade_pct": _val(rs, "PR_APURADA")})
    for sub in rm.findall("RENT_CLASSE_SUBORD"):
        rentabilidade.append({"tipo": _txt(sub, "TIPO"), "serie": _txt(sub, "SERIE"),
                               "rentabilidade_pct": _val(sub, "PR_APURADA")})
 
    # Captações / Resgates
    def _capt_resg(parent_tag, val_tag, qt_tag):
        parent = cra.find(parent_tag)
        result = []
        s = parent.find("CLASSE_SENIOR")
        if s is not None:
            result.append({"tipo": "Senior", "serie": _txt(s, "SERIE"),
                            "valor": _val(s, val_tag), "cotas": _val(s, qt_tag)})
        for sub in parent.findall("CLASSE_SUBORD"):
            result.append({"tipo": _txt(sub, "TIPO"), "serie": _txt(sub, "SERIE"),
                            "valor": _val(sub, val_tag), "cotas": _val(sub, qt_tag)})
        return result
 
    # Amortizações
    def _amort():
        parent = cra.find("AMORT")
        result = []
        s = parent.find("CLASSE_SENIOR")
        if s is not None:
            result.append({"tipo": "Senior", "serie": _txt(s, "SERIE"),
                            "valor_por_cota": _val(s, "VL_COTA"), "valor_total": _val(s, "VL_TOTAL")})
        for sub in parent.findall("CLASSE_SUBORD"):
            result.append({"tipo": _txt(sub, "TIPO"), "serie": _txt(sub, "SERIE"),
                            "valor_por_cota": _val(sub, "VL_COTA"), "valor_total": _val(sub, "VL_TOTAL")})
        return result
 
    # Desempenho esperado vs realizado
    desempenho = []
    ds = des.find("CLASSE_SENIOR")
    if ds is not None:
        desempenho.append({"tipo": "Senior", "serie": _txt(ds, "SERIE"),
                            "esperado_pct": _val(ds, "DESEMP_ESP"), "realizado_pct": _val(ds, "DESEMP_REAL")})
    for sub in des.findall("CLASSE_SUBORD"):
        desempenho.append({"tipo": _txt(sub, "TIPO"), "serie": _txt(sub, "SERIE"),
                            "esperado_pct": _val(sub, "DESEMP_ESP"), "realizado_pct": _val(sub, "DESEMP_REAL")})
 
    # SCR Bacen
    def _scr_bloco(node):
        if node is None:
            return {r: 0.0 for r in ["AA","A","B","C","D","E","F","G","H"]}
        return {r: _val(node, f"VL_{r}") for r in ["AA","A","B","C","D","E","F","G","H"]}
 
    return {
        "estrutura_cotas":   estrutura_cotas,
        "perfil_cotistas": {
            "senior":      _perfil(ncd.find("CLS_SENIOR")),
            "subordinado": _perfil(ncd.find("CLS_SUBORDINADA")),
        },
        "descricao_classes": descricao_classes,
        "rentabilidade":     rentabilidade,
        "captacoes":         _capt_resg("CAPT_MES",    "VL_TOTAL", "QT_COTAS"),
        "resgates":          _capt_resg("RESG_MES",    "VL_TOTAL", "QT_COTAS"),
        "resgates_solicitados": _capt_resg("RESG_SOLIC","VL_PAGO", "QT_COTAS"),
        "amortizacoes":      _amort(),
        "liquidez": {
            "imediata":   _val(liq, "VL_ATIV_LIQDEZ"),
            "ate_30d":    _val(liq, "VL_ATIV_LIQDEZ_30"),
            "ate_60d":    _val(liq, "VL_ATIV_LIQDEZ_60"),
            "ate_90d":    _val(liq, "VL_ATIV_LIQDEZ_90"),
            "ate_180d":   _val(liq, "VL_ATIV_LIQDEZ_180"),
            "ate_360d":   _val(liq, "VL_ATIV_LIQDEZ_360"),
            "acima_360d": _val(liq, "VL_ATIV_LIQDEZ_MAIS_360"),
        },
        "desempenho": desempenho,
        "garantias": {
            "valor_total":    _val(gar, "VLR_GNT_VNC_DRT_CRD"),
            "percentual_pct": _val(gar, "PRC_DRT_CRED_GNT_VNC"),
        },
        "scr_bacen": {
            "por_devedor":  _scr_bloco(scr.find("VLR_TOTAL_DIR_CRD_DEVD")),
            "por_operacao": _scr_bloco(scr.find("VLR_TOTAL_DIR_CRD_OP")),
        },
        "regularidade_fiscal_cedentes": {
            "total_divida_ativa": _val(rtc, "VL_TOTAL"),
        },
    }
 
 
# ---------------------------------------------------------------------------
# FUNÇÃO PÚBLICA
# ---------------------------------------------------------------------------
 
def extrair(xml_path: str | Path) -> dict:
    """
    Recebe o caminho de um XML de Informe Mensal FIDC e retorna
    um dicionário com todos os dados estruturados.
 
    Args:
        xml_path: Caminho para o arquivo .xml (str ou Path)
 
    Returns:
        dict com as seções: cabecalho, ativo, carteira_segmento,
        passivo, patrimonio_liquido, comportamento_carteira,
        negocios_mes, taxas, outras_informacoes.
 
    Raises:
        FileNotFoundError: se o arquivo não existir
        ET.ParseError: se o XML for inválido
    """
    path = Path(xml_path)
    if not path.exists():
        raise FileNotFoundError(f"Arquivo não encontrado: {path}")
 
    tree = ET.parse(path)
    root = tree.getroot()
    lista = root.find("LISTA_INFORM")
 
    return {
        "cabecalho":              _extrair_cabecalho(root),
        "ativo":                  _extrair_ativo(lista),
        "carteira_segmento":      _extrair_carteira_segmento(lista),
        "passivo":                _extrair_passivo(lista),
        "patrimonio_liquido":     _extrair_patrimonio_liquido(lista),
        "comportamento_carteira": _extrair_comportamento_carteira(lista),
        "negocios_mes":           _extrair_negocios_mes(lista),
        "taxas":                  _extrair_taxas(lista),
        "outras_informacoes":     _extrair_outras_informacoes(lista),
    }