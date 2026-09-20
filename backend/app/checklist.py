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
