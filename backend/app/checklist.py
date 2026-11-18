CHECKLIST_MASTER = [
    ("INTIMACAO_PESSOAL", "A intimação para purgar a mora foi pessoal?", "JURIDICO", "Método Radar / referência extrajudicial"),
    ("INTIMACAO_EDITAL", "Se negativa, a intimação foi por edital?", "JURIDICO", "Método Radar / referência extrajudicial"),
    ("NOTIFICACAO_DOIS_LEILOES", "Houve envio de notificação para a data dos dois leilões do art. 27 da Lei 9.514/97?", "JURIDICO", "Método Radar / referência extrajudicial"),
    ("QUITACAO_80", "O contrato de financiamento com alienação fiduciária em garantia está mais de 80% quitado?", "JURIDICO", "Método Radar / referência extrajudicial"),
    ("GARANTIA_DIVIDA_TERCEIRO", "O bem dado em garantia é imóvel residencial de pessoa física que garantiu dívida de terceiro?", "JURIDICO", "Método Radar / referência extrajudicial"),
    ("LANCE_MENOR_50_AVALIACAO", "No segundo leilão, o bem está sendo oferecido por menos de 50% do valor de avaliação?", "JURIDICO", "Método Radar / referência extrajudicial"),
    ("ACAO_QUESTIONAMENTO", "Há alguma ação questionando o leilão ou a execução extrajudicial?", "JURIDICO", "Método Radar / referência extrajudicial"),
    ("LEILOES_NEGATIVOS_AVERBADOS", "Os leilões negativos encontram-se averbados na matrícula?", "DOCUMENTAL", "Método Radar / referência extrajudicial"),
    ("CONSOLIDACAO_REGISTRADA", "Houve registro do contrato e averbação da consolidação na matrícula?", "DOCUMENTAL", "Método Radar / referência extrajudicial"),
    ("PENHORA_INDISPONIBILIDADE", "Os direitos do devedor fiduciante foram penhorados ou indisponibilizados?", "JURIDICO", "Método Radar / referência extrajudicial"),
    ("TERCEIRO_OCUPANTE", "Há terceiro ocupando o imóvel ou cessão de posição contratual?", "DESOCUPACAO", "Método Radar / referência extrajudicial"),
    ("LOCACAO_REGISTRADA", "Há terceiro ocupando com contrato de locação registrado?", "DESOCUPACAO", "Método Radar / referência extrajudicial"),
    ("EDITAL_LIDO", "O edital do leilão foi lido integralmente?", "DOCUMENTAL", "Método Radar / referência extrajudicial"),
    ("EVICCAO", "O banco se responsabiliza pela evicção de direito?", "JURIDICO", "Método Radar / referência extrajudicial"),
    ("RESPONSABILIDADE_DEBITOS", "O edital define responsabilidades por IPTU e condomínio em atraso?", "FINANCEIRO", "Método Radar / referência extrajudicial"),
    ("VAGA_MATRICULA", "A vaga de garagem possui matrícula própria?", "DOCUMENTAL", "Método Radar / referência extrajudicial"),
    ("ILIQUIDEZ", "O imóvel é muito ilíquido mesmo com eventual desconto?", "MERCADO", "Método Radar / referência extrajudicial"),
    ("CONDOMINIO_ALTO", "A taxa de condomínio é superior à de imóveis similares?", "FINANCEIRO", "Método Radar / referência extrajudicial"),
    ("COMPARAVEIS_SUFFICIENTES", "É possível encontrar 7–10 imóveis similares para venda e aluguel?", "MERCADO", "Método Radar / referência extrajudicial"),
    ("REGIAO_SERVICOS", "A região é segura e bem servida de serviços e acesso?", "MERCADO", "Método Radar / referência extrajudicial"),
    ("REFORMA_GRANDE", "O imóvel precisa de grandes obras de reforma?", "FINANCEIRO", "Método Radar / referência extrajudicial"),
    ("RETORNO_SELIC", "A taxa de retorno esperada está acima da Selic + 15% ao ano?", "FINANCEIRO", "Método Radar / referência extrajudicial"),
    ("PRAZO_DOIS_ANOS", "O prazo até o recebimento total da venda é maior ou igual a dois anos?", "FINANCEIRO", "Método Radar / referência extrajudicial"),
    ("DISTANCIA_USUARIO", "O imóvel fica distante do local onde o usuário mora?", "OPERACIONAL", "Método Radar / referência extrajudicial"),
    ("REFORMA_LIQUIDEZ", "O imóvel precisa de grandes obras para se tornar mais líquido?", "MERCADO", "Método Radar / referência extrajudicial"),
    ("CONDOMINIO_PORTARIA", "Venda sem corretor: o condomínio possui portaria?", "MERCADO", "Método Radar / referência extrajudicial"),
    ("ETICA_OCUPACAO", "O usuário se sente à vontade em adquirir imóvel ocupado por uma família?", "DESOCUPACAO", "Método Radar / referência extrajudicial"),
]


def master_items():
    return [{
        "canonical_key": key,
        "question": question,
        "description": question,
        "category": category,
        "domain": [category, "CHECKLIST"],
        "origin": origin,
        "priority": index,
        "required": index <= 15,
        "applicable": True,
        "active": True,
        "version": 1,
        "expected_evidence": [],
        "potential_impact": None,
        "related_rules": [],
        "agents": [],
        "risk_categories": [category],
    } for index, (key, question, category, origin) in enumerate(CHECKLIST_MASTER, 1)]

CHECKLIST_STATES = ("PENDENTE", "EM_ANALISE", "CONFIRMADO", "RISCO_IDENTIFICADO", "ATENCAO", "NAO_IDENTIFICADO", "NAO_APLICAVEL")
CHECKLIST_CONFIDENCES = ("BAIXA", "MEDIA", "ALTA")

# Status padronizado do item (v1.0.7), DERIVADO do estado detalhado acima (que continua sendo o gravado e o
# vocabulário dos agentes). Códigos sem acento, como os demais do sistema; o rótulo de exibição tem acento.
STATUS_RESPONDIDO = "RESPONDIDO"        # avaliado com informação/evidência suficiente (sim, não, risco ou atenção)
STATUS_PENDENTE = "PENDENTE"            # informação ou ação ainda não realizada
STATUS_NAO_APLICAVEL = "NAO_APLICAVEL"  # não exigido pela modalidade: nunca conta como pendência
STATUS_INCONCLUSIVO = "INCONCLUSIVO"    # houve tentativa de análise, sem conclusão confiável
CHECKLIST_STANDARD_STATUSES = (STATUS_RESPONDIDO, STATUS_PENDENTE, STATUS_NAO_APLICAVEL, STATUS_INCONCLUSIVO)
STANDARD_STATUS_LABELS = {STATUS_RESPONDIDO: "Respondido", STATUS_PENDENTE: "Pendente", STATUS_NAO_APLICAVEL: "Não aplicável", STATUS_INCONCLUSIVO: "Inconclusivo"}


def standard_status(state: str | None, applicable: bool | None = True) -> str:
    """Status padronizado a partir do estado gravado e da aplicabilidade do item."""
    normalized = str(state or "").strip().upper()
    if applicable is False or normalized == "NAO_APLICAVEL":
        return STATUS_NAO_APLICAVEL
    if normalized in ("", "PENDENTE"):
        return STATUS_PENDENTE
    if normalized == "EM_ANALISE":
        return STATUS_INCONCLUSIVO
    return STATUS_RESPONDIDO


# Resultado do item para o investidor (v1.0.11, evidencias-v1). Também DERIVADO do estado gravado (nada novo é gravado,
# análises anteriores ganham o mesmo resultado). Separa o que foi comprovado, o risco, o pendente, o analisado sem conclusão,
# o que não se aplica e a ausência de restrição nos documentos examinados (que não é garantia jurídica de inexistência).
RESULTADO_CONFIRMADO = "CONFIRMADO"
RESULTADO_RISCO = "RISCO_IDENTIFICADO"
RESULTADO_PENDENTE = "PENDENTE"
RESULTADO_INCONCLUSIVO = "INCONCLUSIVO"
RESULTADO_NAO_APLICAVEL = "NAO_APLICAVEL"
RESULTADO_SEM_RESTRICAO = "SEM_RESTRICAO_IDENTIFICADA"
CHECKLIST_RESULTS = (RESULTADO_CONFIRMADO, RESULTADO_RISCO, RESULTADO_PENDENTE, RESULTADO_INCONCLUSIVO, RESULTADO_NAO_APLICAVEL, RESULTADO_SEM_RESTRICAO)
RESULT_LABELS = {
    RESULTADO_CONFIRMADO: "Comprovado", RESULTADO_RISCO: "Risco identificado", RESULTADO_PENDENTE: "Pendente",
    RESULTADO_INCONCLUSIVO: "Inconclusivo", RESULTADO_NAO_APLICAVEL: "Não aplicável", RESULTADO_SEM_RESTRICAO: "Sem restrição identificada",
}


def checklist_outcome(state: str | None, applicable: bool | None = True) -> str:
    """Resultado exibido ao investidor a partir do estado gravado (ATENCAO é risco de gravidade moderada)."""
    normalized = str(state or "").strip().upper()
    if applicable is False or normalized == "NAO_APLICAVEL":
        return RESULTADO_NAO_APLICAVEL
    if normalized == "CONFIRMADO":
        return RESULTADO_CONFIRMADO
    if normalized in ("RISCO_IDENTIFICADO", "ATENCAO"):
        return RESULTADO_RISCO
    if normalized == "NAO_IDENTIFICADO":
        return RESULTADO_SEM_RESTRICAO
    if normalized == "EM_ANALISE":
        return RESULTADO_INCONCLUSIVO
    return RESULTADO_PENDENTE


# Tipo da evidência para o investidor (v1.0.11): o que é fato do documento, regra oficial da venda, cálculo, inferência da IA,
# informação do usuário/cadastro ou registro de que a informação não foi localizada no documento examinado.
TIPO_FATO_DOCUMENTAL = "FATO_DOCUMENTAL"
TIPO_REGRA_VENDA = "REGRA_OFICIAL_VENDA"
TIPO_CALCULO = "CALCULO"
TIPO_INFERENCIA_IA = "INFERENCIA_IA"
TIPO_USUARIO = "INFORMACAO_USUARIO"
TIPO_NAO_LOCALIZADA = "INFORMACAO_NAO_LOCALIZADA"
TIPO_PESQUISA_EXTERNA = "PESQUISA_EXTERNA"
TIPO_ORIGEM_NAO_REGISTRADA = "ORIGEM_NAO_REGISTRADA"
EVIDENCE_TYPE_LABELS = {
    TIPO_FATO_DOCUMENTAL: "Fato documental", TIPO_REGRA_VENDA: "Regra oficial da venda", TIPO_CALCULO: "Cálculo",
    TIPO_INFERENCIA_IA: "Inferência da IA", TIPO_USUARIO: "Informação fornecida pelo usuário", TIPO_NAO_LOCALIZADA: "Informação não localizada",
    TIPO_PESQUISA_EXTERNA: "Pesquisa externa", TIPO_ORIGEM_NAO_REGISTRADA: "Origem não registrada",
}


def evidence_type(origin: str | None, category: str | None = None, has_document: bool = False) -> str:
    """Tipo da evidência a partir da origem registrada (``Evidence.origin``) e da categoria."""
    origin_up = str(origin or "").upper()
    if origin_up == "NAO_LOCALIZADA":
        return TIPO_NAO_LOCALIZADA
    if origin_up == "DOCUMENTO" or (not origin_up and has_document):
        return TIPO_REGRA_VENDA if str(category or "").upper() == "CONDICOES_VENDA" else TIPO_FATO_DOCUMENTAL
    if origin_up in ("CALCULO", "REGRA_DETERMINISTICA"):
        return TIPO_CALCULO
    if origin_up in ("CADASTRO", "USUARIO"):
        return TIPO_USUARIO
    if origin_up == "PESQUISA_JUDICIAL":
        return TIPO_PESQUISA_EXTERNA
    if origin_up == "INFERENCIA_IA":
        return TIPO_INFERENCIA_IA
    return TIPO_ORIGEM_NAO_REGISTRADA


def standard_justification(state: str | None, applicable: bool | None, answer: str | None, interpretation: str | None) -> str:
    """Justificativa legível do status (rastreabilidade): resposta/interpretação gravada ou o motivo padrão."""
    status = standard_status(state, applicable)
    text = (interpretation or "").strip() if status == STATUS_INCONCLUSIVO else (answer or interpretation or "").strip()
    if text:
        return text
    return {
        STATUS_NAO_APLICAVEL: "Item não exigido pela modalidade do imóvel.",
        STATUS_PENDENTE: "Informação ou ação ainda não realizada.",
        STATUS_INCONCLUSIVO: "Houve tentativa de análise, sem conclusão confiável.",
        STATUS_RESPONDIDO: "Item avaliado.",
    }[status]
