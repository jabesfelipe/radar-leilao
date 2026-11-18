"""Ruleset declarativo de MODALIDADES de aquisição (Onda 2 — F1).

Fonte única da verdade do vocabulário de modalidades e de como as regras variam por
modalidade, no mesmo espírito declarativo de ``workflow_rules.py``/``checklist.py``:
dados + funções puras, sem I/O e sem LLM. A classificação é determinística e só
confirma com evidência; sem evidência permanece ``INDEFINIDO`` (e o hard stop
``MODALIDADE_INDEFINIDA`` do workflow continua ativo).

Preservação: os 27 ``canonical_key`` do Checklist Mestre NÃO são alterados. A
aplicabilidade por modalidade é um METADADO aditivo (nunca renomeia/remove chave).
Compatibilidade com o legado: ``INDEFINIDO`` mantém os 27 itens aplicáveis (idêntico
ao comportamento atual), de modo que oportunidades legadas/sem modalidade não mudam.
"""
from __future__ import annotations

MODALITY_RULESET_VERSION = "modality-v2"

# --- Vocabulário canônico (SPEC/PLAN-WAVE-2 §2) -------------------------------
# LICITACAO é decisão de negócio em aberto (§8 do plano) e NÃO entra nesta onda.
MODALITY_EXTRAJUDICIAL_AF = "EXTRAJUDICIAL_ALIENACAO_FIDUCIARIA"
MODALITY_EXTRAJUDICIAL_OUTRA = "EXTRAJUDICIAL_OUTRA_GARANTIA"
MODALITY_JUDICIAL = "JUDICIAL"
MODALITY_VENDA_DIRETA = "VENDA_DIRETA"
MODALITY_INDEFINIDO = "INDEFINIDO"

MODALITIES: tuple[str, ...] = (
    MODALITY_EXTRAJUDICIAL_AF,
    MODALITY_EXTRAJUDICIAL_OUTRA,
    MODALITY_JUDICIAL,
    MODALITY_VENDA_DIRETA,
    MODALITY_INDEFINIDO,
)

MODALITY_CATALOG: dict[str, dict[str, str]] = {
    MODALITY_EXTRAJUDICIAL_AF: {
        "name": "Extrajudicial — Alienação Fiduciária (Lei 9.514/97)",
        "description": "Execução extrajudicial com consolidação da propriedade e leilão do art. 27. Foco do produto.",
        "track": "EXTRAJUDICIAL",
        "status": "ATIVO",
    },
    MODALITY_EXTRAJUDICIAL_OUTRA: {
        "name": "Extrajudicial — Outra garantia",
        "description": "Outras execuções/vendas extrajudiciais com garantia diversa da alienação fiduciária.",
        "track": "EXTRAJUDICIAL",
        "status": "ATIVO",
    },
    MODALITY_JUDICIAL: {
        "name": "Judicial (CPC)",
        "description": "Arrematação em hasta pública judicial, regida pelo CPC. Rito e riscos próprios.",
        "track": "JUDICIAL",
        "status": "ATIVO",
    },
    MODALITY_VENDA_DIRETA: {
        "name": "Venda direta",
        "description": "Venda direta pelo credor/proprietário, sem leilão.",
        "track": "DIRETA",
        "status": "ATIVO",
    },
    MODALITY_INDEFINIDO: {
        "name": "Indefinida",
        "description": "Modalidade ainda não evidenciada (estado inicial da triagem).",
        "track": "TRIAGEM",
        "status": "ATIVO",
    },
}

# --- Aplicabilidade de checklist por modalidade — SPEC/MATRIZ-CHECKLIST-MODALIDADE
# Estados: APLICAVEL (padrão), CONDICIONAL, NAO_APLICAVEL. Só listamos as EXCEÇÕES;
# qualquer chave não listada para uma modalidade é APLICAVEL. INDEFINIDO = tudo
# aplicável (comportamento legado preservado). Os 27 keys permanecem intactos.
APPLICABILITY_APLICAVEL = "APLICAVEL"
APPLICABILITY_CONDICIONAL = "CONDICIONAL"
APPLICABILITY_NAO_APLICAVEL = "NAO_APLICAVEL"

# Itens específicos do rito EXTRAJUDICIAL de alienação fiduciária (Lei 9.514/97):
# não se aplicam ao judicial nem à venda direta.
_AF_ESPECIFICOS = (
    "INTIMACAO_PESSOAL", "INTIMACAO_EDITAL", "NOTIFICACAO_DOIS_LEILOES",
    "QUITACAO_80", "GARANTIA_DIVIDA_TERCEIRO", "CONSOLIDACAO_REGISTRADA",
    "LEILOES_NEGATIVOS_AVERBADOS", "PENHORA_INDISPONIBILIDADE",
)
# "Preço vil" (<50% da avaliação) é sinal do JUDICIAL; no extrajudicial é só um gatilho
# de atenção, não um piso legal (REVISAO-ANOTACOES-LEILAO §5).
_PRECO_VIL = "LANCE_MENOR_50_AVALIACAO"

# Mapa: modalidade -> {canonical_key -> estado de aplicabilidade} (apenas exceções).
CHECKLIST_APPLICABILITY: dict[str, dict[str, str]] = {
    MODALITY_EXTRAJUDICIAL_AF: {
        _PRECO_VIL: APPLICABILITY_CONDICIONAL,  # atenção, não piso legal
    },
    MODALITY_EXTRAJUDICIAL_OUTRA: {
        **{k: APPLICABILITY_CONDICIONAL for k in ("QUITACAO_80", "NOTIFICACAO_DOIS_LEILOES")},
        _PRECO_VIL: APPLICABILITY_CONDICIONAL,
    },
    MODALITY_JUDICIAL: {
        **{k: APPLICABILITY_NAO_APLICAVEL for k in _AF_ESPECIFICOS},
        _PRECO_VIL: APPLICABILITY_APLICAVEL,  # preço vil é relevante no judicial
    },
    # v2: decidido pela FINALIDADE de cada item (ver VENDA_DIRETA_ITEM_RULES), não por uma lista genérica do rito.
    MODALITY_VENDA_DIRETA: {},   # preenchido abaixo a partir de VENDA_DIRETA_ITEM_RULES
    MODALITY_INDEFINIDO: {},  # tudo aplicável (legado)
}

# --- Finalidade de cada item (v2) ----------------------------------------------------------------------------------
# Grupos: o que o item verifica. Usado pela aplicabilidade por modalidade e pelo veredito (que separa impedimento,
# informação essencial desconhecida, premissa não configurada, risco que reduz confiança e item não aplicável).
GRUPO_PROCEDIMENTO_LEILAO = "PROCEDIMENTO_LEILAO"      # etapa do leilão em curso (edital, lance)
GRUPO_PROCEDIMENTO_ORIGEM = "PROCEDIMENTO_ORIGEM"      # validade da execução fiduciária que originou o título do vendedor
GRUPO_SITUACAO_REGISTRAL = "SITUACAO_REGISTRAL"        # o que consta hoje na matrícula (registros, consolidação, ônus)
GRUPO_CONDICOES_VENDA = "CONDICOES_VENDA"              # responsabilidades do vendedor e do comprador (edital ou condições)
GRUPO_DOCUMENTACAO = "DOCUMENTACAO"                    # documentos e ações sobre o imóvel
GRUPO_OCUPACAO = "OCUPACAO"
GRUPO_MERCADO = "MERCADO"
GRUPO_FINANCEIRO_PREMISSAS = "FINANCEIRO_PREMISSAS"    # depende das premissas financeiras do investidor
GRUPO_PREFERENCIA = "PREFERENCIA_INVESTIDOR"           # decisão pessoal do investidor

ITEM_PURPOSE: dict[str, dict[str, str]] = {
    "INTIMACAO_PESSOAL": {"grupo": GRUPO_PROCEDIMENTO_ORIGEM, "acao": "Solicitar ao vendedor a comprovação da intimação para purgar a mora (art. 26 da Lei 9.514/97)."},
    "INTIMACAO_EDITAL": {"grupo": GRUPO_PROCEDIMENTO_ORIGEM, "acao": "Se a intimação pessoal foi negativa, solicitar a comprovação da intimação por edital."},
    "NOTIFICACAO_DOIS_LEILOES": {"grupo": GRUPO_PROCEDIMENTO_ORIGEM, "acao": "Solicitar a comprovação da notificação ao devedor sobre as datas dos leilões."},
    "QUITACAO_80": {"grupo": GRUPO_PROCEDIMENTO_ORIGEM, "acao": "Verificar o percentual quitado do contrato original (risco de questionamento da execução)."},
    "GARANTIA_DIVIDA_TERCEIRO": {"grupo": GRUPO_PROCEDIMENTO_ORIGEM, "acao": "Verificar no contrato registrado se a garantia era de dívida de terceiro."},
    "LANCE_MENOR_50_AVALIACAO": {"grupo": GRUPO_PROCEDIMENTO_LEILAO, "acao": "Cadastrar avaliação e valor do 2º leilão."},
    "ACAO_QUESTIONAMENTO": {"grupo": GRUPO_DOCUMENTACAO, "acao": "Pesquisar ações judiciais contra o vendedor/ex-devedor sobre o imóvel (certidões dos distribuidores)."},
    "LEILOES_NEGATIVOS_AVERBADOS": {"grupo": GRUPO_SITUACAO_REGISTRAL, "acao": "Conferir na matrícula atualizada a averbação dos leilões negativos e confirmar com o cartório se é exigida para registrar a compra."},
    "CONSOLIDACAO_REGISTRADA": {"grupo": GRUPO_SITUACAO_REGISTRAL, "acao": "Anexar a matrícula atualizada (inteiro teor) para conferir o registro da alienação fiduciária e a averbação da consolidação."},
    "PENHORA_INDISPONIBILIDADE": {"grupo": GRUPO_SITUACAO_REGISTRAL, "acao": "Conferir na matrícula/certidão de ônus atualizada se há penhora ou indisponibilidade averbada."},
    "TERCEIRO_OCUPANTE": {"grupo": GRUPO_OCUPACAO, "acao": "Registrar a verificação de ocupação (vistoria, vizinhos, condomínio)."},
    "LOCACAO_REGISTRADA": {"grupo": GRUPO_OCUPACAO, "acao": "Conferir na matrícula se há contrato de locação registrado/averbado."},
    "EDITAL_LIDO": {"grupo": GRUPO_PROCEDIMENTO_LEILAO, "acao": "Anexar e ler integralmente o edital."},
    "EVICCAO": {"grupo": GRUPO_CONDICOES_VENDA, "acao": "Conferir no edital ou nas condições da venda a cláusula de evicção."},
    "RESPONSABILIDADE_DEBITOS": {"grupo": GRUPO_CONDICOES_VENDA, "acao": "Anexar o edital ou as condições oficiais da venda e informar os limites de responsabilidade nas premissas."},
    "VAGA_MATRICULA": {"grupo": GRUPO_DOCUMENTACAO, "acao": "Conferir na matrícula se a vaga é unidade autônoma ou vinculada."},
    "ILIQUIDEZ": {"grupo": GRUPO_MERCADO, "acao": "Cadastrar comparáveis de venda e avaliar a liquidez."},
    "CONDOMINIO_ALTO": {"grupo": GRUPO_MERCADO, "acao": "Informar o condomínio do imóvel e comparar com os comparáveis."},
    "COMPARAVEIS_SUFFICIENTES": {"grupo": GRUPO_MERCADO, "acao": "Cadastrar ao menos 7 comparáveis de venda e 7 de aluguel."},
    "REGIAO_SERVICOS": {"grupo": GRUPO_MERCADO, "acao": "Registrar a avaliação da região (segurança, serviços, acesso)."},
    "REFORMA_GRANDE": {"grupo": GRUPO_MERCADO, "acao": "Vistoriar o imóvel ou estimar a reforma com fonte."},
    "RETORNO_SELIC": {"grupo": GRUPO_FINANCEIRO_PREMISSAS, "acao": "Configurar as premissas financeiras (meta, venda, prazo) para calcular o retorno."},
    "PRAZO_DOIS_ANOS": {"grupo": GRUPO_FINANCEIRO_PREMISSAS, "acao": "Informar o prazo da operação nas premissas."},
    "DISTANCIA_USUARIO": {"grupo": GRUPO_PREFERENCIA, "acao": "Decisão do investidor."},
    "REFORMA_LIQUIDEZ": {"grupo": GRUPO_MERCADO, "acao": "Vistoriar o imóvel e avaliar a necessidade de obras para revenda."},
    "CONDOMINIO_PORTARIA": {"grupo": GRUPO_PREFERENCIA, "acao": "Registrar se o condomínio tem portaria (relevante para venda sem corretor)."},
    "ETICA_OCUPACAO": {"grupo": GRUPO_PREFERENCIA, "acao": "Decisão do investidor."},
}

# Regras de VENDA_DIRETA por item: (aplicabilidade, justificativa). Itens não listados: APLICAVEL.
_ORIGEM = ("A venda direta dispensa o leilão, mas, quando o título do vendedor decorre de consolidação fiduciária, a validade "
           "dessa execução de origem ainda pode ser questionada pelo ex-devedor. Verificação do procedimento de origem: reduz a "
           "confiança se não comprovada; não é etapa da compra.")
VENDA_DIRETA_ITEM_RULES: dict[str, tuple[str, str]] = {
    "INTIMACAO_PESSOAL": (APPLICABILITY_CONDICIONAL, _ORIGEM),
    "INTIMACAO_EDITAL": (APPLICABILITY_CONDICIONAL, _ORIGEM),
    "NOTIFICACAO_DOIS_LEILOES": (APPLICABILITY_CONDICIONAL, _ORIGEM),
    "QUITACAO_80": (APPLICABILITY_CONDICIONAL, _ORIGEM),
    "GARANTIA_DIVIDA_TERCEIRO": (APPLICABILITY_CONDICIONAL, _ORIGEM),
    _PRECO_VIL: (APPLICABILITY_NAO_APLICAVEL, "Não há segundo leilão nem lance na venda direta: o preço é fixado pelo vendedor e comparado ao mercado na análise financeira."),
    "EDITAL_LIDO": (APPLICABILITY_NAO_APLICAVEL, "Venda direta sem edital: as condições da venda substituem o edital (ver item de responsabilidades por débitos). "
                    "Se um edital for anexado, o item volta a ser aplicável."),
    "LEILOES_NEGATIVOS_AVERBADOS": (APPLICABILITY_CONDICIONAL, "Aplicável quando o título do vendedor decorre de consolidação fiduciária: os leilões "
                                    "negativos fazem parte da situação registral que o comprador precisa conferir para registrar a compra."),
    "CONSOLIDACAO_REGISTRADA": (APPLICABILITY_APLICAVEL, "Situação registral, não etapa do leilão: o registro da alienação fiduciária e a averbação da "
                                "consolidação comprovam que o vendedor é o proprietário."),
    "PENHORA_INDISPONIBILIDADE": (APPLICABILITY_APLICAVEL, "Situação registral: penhora ou indisponibilidade averbada na matrícula pode impedir ou "
                                  "condicionar o registro da compra."),
    "RESPONSABILIDADE_DEBITOS": (APPLICABILITY_APLICAVEL, "Sem edital, as responsabilidades por IPTU e condomínio vêm das condições oficiais da venda."),
    "EVICCAO": (APPLICABILITY_APLICAVEL, "Sem edital, a cláusula de evicção vem das condições da venda."),
}
CHECKLIST_APPLICABILITY[MODALITY_VENDA_DIRETA] = {k: v[0] for k, v in VENDA_DIRETA_ITEM_RULES.items() if v[0] != APPLICABILITY_APLICAVEL}


def item_rule(modality: str, canonical_key: str) -> dict[str, str]:
    """Regra do item na modalidade: aplicabilidade, justificativa, grupo (finalidade), ação sugerida e versão."""
    mod = normalize(modality)
    applicability = checklist_applicability(mod, canonical_key)
    justification = VENDA_DIRETA_ITEM_RULES.get(canonical_key, (None, ""))[1] if mod == MODALITY_VENDA_DIRETA else ""
    purpose = ITEM_PURPOSE.get(canonical_key, {"grupo": GRUPO_DOCUMENTACAO, "acao": ""})
    return {"aplicabilidade": applicability, "justificativa": justification, "grupo": purpose["grupo"], "acao": purpose["acao"],
            "regra": f"{MODALITY_RULESET_VERSION}:{mod}:{canonical_key}"}

# --- Hard stops por modalidade (quais do catálogo do workflow fazem sentido) ---
# Alguns hard stops do workflow só se aplicam ao extrajudicial de AF. Em judicial/
# venda direta eles não devem bloquear (não há consolidação/intimação de mora).
AF_ONLY_HARD_STOPS = ("CONSOLIDACAO_NAO_REGISTRADA", "INTIMACAO_MORA_AUSENTE")

MODALITY_SUPPRESSED_HARD_STOPS: dict[str, tuple[str, ...]] = {
    MODALITY_JUDICIAL: AF_ONLY_HARD_STOPS,
    MODALITY_VENDA_DIRETA: AF_ONLY_HARD_STOPS,
    MODALITY_EXTRAJUDICIAL_OUTRA: (),      # garantia diversa: mantém (depende de evidência)
    MODALITY_EXTRAJUDICIAL_AF: (),
    MODALITY_INDEFINIDO: (),
}

# --- Documentos exigidos por modalidade (declaração; sem automação nesta onda) --
_DOCS_COMUNS = ("EDITAL", "MATRICULA")
MODALITY_REQUIRED_DOCS: dict[str, tuple[str, ...]] = {
    MODALITY_EXTRAJUDICIAL_AF: _DOCS_COMUNS + ("CONTRATO_ALIENACAO_FIDUCIARIA", "CONSOLIDACAO", "INTIMACAO_MORA"),
    MODALITY_EXTRAJUDICIAL_OUTRA: _DOCS_COMUNS + ("CONTRATO_GARANTIA",),
    MODALITY_JUDICIAL: _DOCS_COMUNS + ("AUTO_ARREMATACAO", "PROCESSO_JUDICIAL"),
    MODALITY_VENDA_DIRETA: ("MATRICULA", "PROPOSTA_VENDA"),
    MODALITY_INDEFINIDO: (),
}


# ---------------------------------------------------------------------------
# Helpers puros
# ---------------------------------------------------------------------------

def is_modality(code: str) -> bool:
    return code in MODALITIES


def normalize(code: str | None) -> str:
    c = str(code or "").strip().upper()
    return c if c in MODALITIES else MODALITY_INDEFINIDO


_PROPERTY_MODALITY_SYNONYMS = {
    "VENDA DIRETA": MODALITY_VENDA_DIRETA,
    "VENDA DIRETA ONLINE": MODALITY_VENDA_DIRETA,
    "COMPRA DIRETA": MODALITY_VENDA_DIRETA,
}


def normalize_property_modality(value: str | None) -> str:
    """Modalidade do IMÓVEL (``Property.modality``, texto livre do cadastro) no vocabulário canônico (v1.0.7).

    Aceita o código canônico e sinônimos exatos de venda direta ("Venda direta", "Compra direta"). Qualquer outro
    valor (vazio, "Leilão", "Licitação aberta"...) vira ``INDEFINIDO``: todos os itens continuam aplicáveis, que é o
    comportamento anterior para imóveis de leilão e legados."""
    raw = _strip_accents(str(value or "")).strip().upper()
    if raw in MODALITIES:
        return raw
    spaced = " ".join(raw.replace("_", " ").replace("-", " ").split())
    if spaced.replace(" ", "_") in MODALITIES:
        return spaced.replace(" ", "_")
    return _PROPERTY_MODALITY_SYNONYMS.get(spaced, MODALITY_INDEFINIDO)


def checklist_applicability(modality: str, canonical_key: str) -> str:
    """Estado de aplicabilidade de um canonical_key sob a modalidade. Default APLICAVEL."""
    overrides = CHECKLIST_APPLICABILITY.get(normalize(modality), {})
    return overrides.get(canonical_key, APPLICABILITY_APLICAVEL)


def applicable_checklist_keys(modality: str, all_keys: tuple[str, ...]) -> tuple[str, ...]:
    """Subconjunto de ``all_keys`` cuja aplicabilidade NÃO é NAO_APLICAVEL para a
    modalidade. Preserva o catálogo (não remove chaves; apenas filtra aplicabilidade)."""
    mod = normalize(modality)
    return tuple(k for k in all_keys if checklist_applicability(mod, k) != APPLICABILITY_NAO_APLICAVEL)


def suppressed_hard_stops(modality: str) -> tuple[str, ...]:
    """Hard stops do catálogo do workflow que NÃO se aplicam à modalidade."""
    return MODALITY_SUPPRESSED_HARD_STOPS.get(normalize(modality), ())


def required_docs(modality: str) -> tuple[str, ...]:
    return MODALITY_REQUIRED_DOCS.get(normalize(modality), ())


# ---------------------------------------------------------------------------
# Classificação determinística (evidence-gated)
# ---------------------------------------------------------------------------

# Palavras-chave (normalizadas, sem acento) que indicam cada modalidade. Determinístico.
_SIGNALS: tuple[tuple[str, tuple[str, ...]], ...] = (
    (MODALITY_EXTRAJUDICIAL_AF, ("ALIENACAO FIDUCIARIA", "9.514", "9514", "CONSOLIDACAO DA PROPRIEDADE", "ART. 27", "ARTIGO 27", "LEI 9.514")),
    (MODALITY_JUDICIAL, ("JUDICIAL", "HASTA PUBLICA", "CPC", "EXECUCAO FISCAL", "PENHORA", "PROCESSO N", "VARA ")),
    (MODALITY_VENDA_DIRETA, ("VENDA DIRETA", "VENDA ONLINE", "SEM LEILAO", "PROPOSTA DE COMPRA")),
    (MODALITY_EXTRAJUDICIAL_OUTRA, ("EXTRAJUDICIAL", "GARANTIA")),
)


def _strip_accents(text: str) -> str:
    import unicodedata
    return unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()


def classify_modality(*, signals_text: str | None, origin: str | None = None, has_evidence: bool = False) -> dict:
    """Propõe a modalidade a partir de sinais textuais objetivos (edital/origem).
    Determinístico, sem LLM. **Só confirma com evidência** (``has_evidence``); sem
    evidência, retorna a hipótese mas mantém ``modality=INDEFINIDO`` + necessidade de
    revisão manual. Retorna modalidade, grau de confiança, evidências e justificativa."""
    haystack = _strip_accents(f"{signals_text or ''} {origin or ''}").upper()
    matched: list[tuple[str, list[str]]] = []
    for modality, keywords in _SIGNALS:
        hits = [kw for kw in keywords if _strip_accents(kw).upper() in haystack]
        if hits:
            matched.append((modality, hits))

    if not matched:
        return {
            "modality": MODALITY_INDEFINIDO, "proposed": MODALITY_INDEFINIDO,
            "confidence": "BAIXA", "evidences": [], "needs_manual_review": True,
            "justification": "Nenhum sinal objetivo de modalidade encontrado.",
            "ruleset_version": MODALITY_RULESET_VERSION,
        }

    # Precedência: AF > JUDICIAL > VENDA_DIRETA > EXTRAJUDICIAL_OUTRA (ordem de _SIGNALS).
    proposed, hits = matched[0]
    multiple = len({m for m, _ in matched}) > 1
    confidence = "ALTA" if (has_evidence and not multiple) else ("MEDIA" if has_evidence else "BAIXA")
    confirmed = has_evidence and not multiple
    return {
        "modality": proposed if confirmed else MODALITY_INDEFINIDO,
        "proposed": proposed,
        "confidence": confidence,
        "evidences": hits,
        "needs_manual_review": not confirmed,
        "justification": (
            f"Sinais {hits} indicam {proposed}."
            + ("" if has_evidence else " Sem evidência vinculada: permanece INDEFINIDO até confirmação.")
            + (" Múltiplos sinais divergentes: requer revisão." if multiple else "")
        ),
        "ruleset_version": MODALITY_RULESET_VERSION,
    }
