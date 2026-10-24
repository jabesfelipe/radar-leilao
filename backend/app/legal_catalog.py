"""Catálogo jurídico curado da Central Jurídica (conteúdo real e verificável).

Este módulo é a FONTE declarativa da base legal do Método Radar. Não há mágica:
cada fonte/dispositivo/regra é um dado estático, versionado em código e revisável
por qualquer pessoa. O seed (``legal_service.seed_legal_catalog``) materializa este
catálogo de forma IDEMPOTENTE (upsert por ``slug``), sem jamais sobrescrever edições
humanas verificadas.

Princípios (iguais ao resto do projeto):
- NUNCA fabricar norma. ``official_text`` guarda o texto oficial (verbatim) do
  dispositivo vigente; ``practical_note`` guarda paráfrase/orientação prática e é
  SEMPRE apresentada separada do texto legal.
- ``verification_status`` deixa explícito o que já foi conferido na fonte oficial
  (VERIFICADO) e o que ainda é pendência de curadoria (PENDENTE).
- Os vínculos com o checklist referenciam os 27 ``canonical_key`` EXISTENTES, sem
  alterá-los.

Sobre o histórico "136 + 27 → 45 regras": a base canônica IMPLEMENTADA do produto
é o Checklist Mestre com 27 ``canonical_key`` (ver ``checklist.py``). O conjunto
histórico de 136/163 itens brutos e 45 regras canônicas descrito na documentação é
MATERIAL DE ORIGEM e permanece registrado como pendência de curadoria
(``docs/TODO-CENTRAL-JURIDICA.md``): não é reinventado aqui para não fabricar
conteúdo inexistente no código.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ProvisionSeed:
    slug: str
    reference: str
    heading: str | None = None
    official_text: str | None = None
    practical_note: str | None = None
    contexts: tuple[str, ...] = ()
    tags: tuple[str, ...] = ()
    verification_status: str = "PENDENTE"


@dataclass(frozen=True)
class SourceSeed:
    slug: str
    source_type: str
    label: str
    title: str
    authority: str | None = None
    official_url: str | None = None
    year: int | None = None
    in_force: bool = True
    verification_status: str = "PENDENTE"
    summary: str | None = None
    provisions: tuple[ProvisionSeed, ...] = ()


@dataclass(frozen=True)
class RuleLink:
    canonical_key: str
    relevance: str = "PRINCIPAL"
    note: str | None = None


@dataclass(frozen=True)
class RuleSeed:
    slug: str
    rule_kind: str
    title: str
    statement: str
    contexts: tuple[str, ...] = ()
    severity: str | None = None
    provision_slug: str | None = None
    links: tuple[RuleLink, ...] = ()


# ---------------------------------------------------------------------------
# FONTES E DISPOSITIVOS
# ---------------------------------------------------------------------------
# Textos oficiais transcritos dos dispositivos vigentes das normas citadas. Mantidos
# curtos e fiéis; a curadoria humana confirma/estende depois (verification_status).

SOURCES: tuple[SourceSeed, ...] = (
    SourceSeed(
        slug="lei-9514-1997",
        source_type="LEI",
        label="Lei 9.514/1997",
        title="Lei 9.514/1997 — Sistema de Financiamento Imobiliário e alienação fiduciária de coisa imóvel",
        authority="Federal",
        official_url="https://www.planalto.gov.br/ccivil_03/leis/l9514.htm",
        year=1997,
        in_force=True,
        verification_status="VERIFICADO",
        summary=(
            "Disciplina a alienação fiduciária de bem imóvel e a execução extrajudicial "
            "da garantia: intimação para purgação da mora, consolidação da propriedade "
            "em nome do credor fiduciário e os dois leilões públicos."
        ),
        provisions=(
            ProvisionSeed(
                slug="lei-9514-1997-art26",
                reference="Art. 26",
                heading="Consolidação da propriedade após a mora",
                official_text=(
                    "Vencida e não paga, no todo ou em parte, a dívida e constituído em mora "
                    "o fiduciante, consolidar-se-á, nos termos deste artigo, a propriedade do "
                    "imóvel em nome do fiduciário."
                ),
                practical_note=(
                    "A consolidação só é regular se o fiduciante foi efetivamente constituído "
                    "em mora e intimado para purgá-la. Confirmar a intimação (pessoal ou, "
                    "esgotada, por edital) e a averbação da consolidação na matrícula."
                ),
                contexts=("CONSOLIDACAO", "MATRICULA", "LEILAO"),
                tags=("intimacao", "mora", "consolidacao"),
                verification_status="VERIFICADO",
            ),
            ProvisionSeed(
                slug="lei-9514-1997-art27",
                reference="Art. 27",
                heading="Leilões públicos após a consolidação",
                official_text=(
                    "Uma vez consolidada a propriedade em seu nome, o fiduciário, no prazo de "
                    "trinta dias, contados da data do registro de que trata o § 7º do art. 26, "
                    "promoverá público leilão para a alienação do imóvel."
                ),
                practical_note=(
                    "São dois leilões. No primeiro, o lance mínimo é o valor do imóvel; não "
                    "havendo arrematação, realiza-se o segundo leilão, cujo lance mínimo passa "
                    "a ser o valor da dívida e encargos (art. 27, §§). Verificar datas, "
                    "notificações e se os leilões negativos estão averbados."
                ),
                contexts=("LEILAO", "ARREMATACAO"),
                tags=("leilao", "lance-minimo", "notificacao"),
                verification_status="VERIFICADO",
            ),
            ProvisionSeed(
                slug="lei-9514-1997-art37a",
                reference="Art. 37-A",
                heading="Taxa de ocupação do imóvel",
                official_text=(
                    "O fiduciante pagará ao fiduciário, ou a quem vier a sucedê-lo, a título de "
                    "taxa de ocupação do imóvel, por mês ou fração, valor correspondente a 1% "
                    "(um por cento) do valor a que se refere o inciso VI do art. 24, computado e "
                    "exigível desde a data da alienação em leilão até a data em que o fiduciário, "
                    "ou seus sucessores, vier a ser imitido na posse do imóvel."
                ),
                practical_note=(
                    "Enquanto o imóvel permanece ocupado após o leilão, há previsão de taxa de "
                    "ocupação devida pelo antigo fiduciante. É um dado relevante para a conta de "
                    "desocupação, mas não substitui a avaliação do custo/prazo de imissão na posse."
                ),
                contexts=("DESOCUPACAO", "POSSE", "ARREMATACAO"),
                tags=("taxa-ocupacao", "posse", "desocupacao"),
                verification_status="VERIFICADO",
            ),
        ),
    ),
    SourceSeed(
        slug="cc-2002",
        source_type="CODIGO",
        label="Código Civil (Lei 10.406/2002)",
        title="Lei 10.406/2002 — Código Civil",
        authority="Federal",
        official_url="https://www.planalto.gov.br/ccivil_03/leis/2002/l10406compilada.htm",
        year=2002,
        in_force=True,
        verification_status="VERIFICADO",
        summary="Regras gerais de propriedade, posse e responsabilidade por evicção.",
        provisions=(
            ProvisionSeed(
                slug="cc-2002-art1228",
                reference="Art. 1.228",
                heading="Faculdades do proprietário",
                official_text=(
                    "O proprietário tem a faculdade de usar, gozar e dispor da coisa, e o direito "
                    "de reavê-la do poder de quem quer que injustamente a possua ou detenha."
                ),
                practical_note=(
                    "Fundamento do direito do arrematante de reaver o imóvel de quem o ocupe "
                    "injustamente — base da ação de imissão na posse após a arrematação."
                ),
                contexts=("POSSE", "DESOCUPACAO"),
                tags=("propriedade", "posse"),
                verification_status="VERIFICADO",
            ),
            ProvisionSeed(
                slug="cc-2002-art447",
                reference="Art. 447",
                heading="Responsabilidade pela evicção",
                official_text=(
                    "Nos contratos onerosos, o alienante responde pela evicção. Subsiste esta "
                    "garantia ainda que a aquisição se tenha realizado em hasta pública."
                ),
                practical_note=(
                    "A garantia da evicção subsiste mesmo em hasta pública, mas editais podem "
                    "prever cláusulas específicas. Conferir no edital se o vendedor/credor se "
                    "responsabiliza pela evicção de direito."
                ),
                contexts=("ARREMATACAO", "LEILAO"),
                tags=("eviccao", "garantia"),
                verification_status="VERIFICADO",
            ),
        ),
    ),
    SourceSeed(
        slug="cpc-2015",
        source_type="CODIGO",
        label="CPC (Lei 13.105/2015)",
        title="Lei 13.105/2015 — Código de Processo Civil",
        authority="Federal",
        official_url="https://www.planalto.gov.br/ccivil_03/_ato2015-2018/2015/lei/l13105.htm",
        year=2015,
        in_force=True,
        verification_status="VERIFICADO",
        summary="Procedimento da arrematação judicial e imissão na posse do arrematante.",
        provisions=(
            ProvisionSeed(
                slug="cpc-2015-art903",
                reference="Art. 903",
                heading="Perfeição e eficácia da arrematação",
                official_text=(
                    "Qualquer que seja a modalidade de leilão, assinado o auto pelo juiz, pelo "
                    "arrematante e pelo leiloeiro, a arrematação será considerada perfeita, "
                    "acabada e irretratável, ainda que venham a ser julgados procedentes os "
                    "embargos do executado ou a ação autônoma de que trata o § 4º deste artigo."
                ),
                practical_note=(
                    "Na arrematação judicial, assinado o auto, a arrematação é, em regra, perfeita "
                    "e irretratável — ressalvadas as hipóteses de invalidação previstas no próprio "
                    "artigo. Distinguir arrematação judicial do leilão extrajudicial da Lei 9.514/97."
                ),
                contexts=("ARREMATACAO", "LEILAO"),
                tags=("arrematacao", "auto", "irretratavel"),
                verification_status="VERIFICADO",
            ),
        ),
    ),
    SourceSeed(
        slug="lei-8245-1991",
        source_type="LEI",
        label="Lei 8.245/1991",
        title="Lei 8.245/1991 — Lei do Inquilinato (locações de imóveis urbanos)",
        authority="Federal",
        official_url="https://www.planalto.gov.br/ccivil_03/leis/l8245.htm",
        year=1991,
        in_force=True,
        verification_status="VERIFICADO",
        summary="Efeitos da locação perante o adquirente do imóvel locado.",
        provisions=(
            ProvisionSeed(
                slug="lei-8245-1991-art8",
                reference="Art. 8º",
                heading="Locação perante o adquirente",
                official_text=(
                    "Se o imóvel for alienado durante a locação, o adquirente poderá denunciar o "
                    "contrato, com o prazo de noventa dias para a desocupação, salvo se a locação "
                    "for por tempo determinado e o contrato contiver cláusula de vigência em caso "
                    "de alienação e estiver averbado junto à matrícula do imóvel."
                ),
                practical_note=(
                    "Locação com cláusula de vigência AVERBADA na matrícula pode obrigar o "
                    "arrematante a respeitar o contrato. Sem averbação, em regra cabe denúncia "
                    "com prazo de 90 dias. Verificar locação registrada na matrícula."
                ),
                contexts=("LOCACAO", "DESOCUPACAO", "MATRICULA"),
                tags=("locacao", "denuncia", "averbacao"),
                verification_status="VERIFICADO",
            ),
        ),
    ),
    SourceSeed(
        slug="ctn-1966",
        source_type="CODIGO",
        label="CTN (Lei 5.172/1966)",
        title="Lei 5.172/1966 — Código Tributário Nacional",
        authority="Federal",
        official_url="https://www.planalto.gov.br/ccivil_03/leis/l5172compilado.htm",
        year=1966,
        in_force=True,
        verification_status="VERIFICADO",
        summary="Responsabilidade por tributos do imóvel e sub-rogação no preço da arrematação.",
        provisions=(
            ProvisionSeed(
                slug="ctn-1966-art130",
                reference="Art. 130",
                heading="Sub-rogação de tributos do imóvel",
                official_text=(
                    "Os créditos tributários relativos a impostos cujo fato gerador seja a "
                    "propriedade, o domínio útil ou a posse de bens imóveis, e bem assim os "
                    "relativos a taxas pela prestação de serviços referentes a tais bens, ou a "
                    "contribuições de melhoria, subrogam-se na pessoa dos respectivos adquirentes, "
                    "salvo quando conste do título a prova de sua quitação. Parágrafo único. No "
                    "caso de arrematação em hasta pública, a sub-rogação ocorre sobre o respectivo preço."
                ),
                practical_note=(
                    "Regra importante: na arrematação em hasta pública, os tributos do imóvel "
                    "(IPTU, taxas) sub-rogam-se no PREÇO, não no arrematante — isso depende dos "
                    "termos do edital. Ler o edital para saber se há transferência de débitos."
                ),
                contexts=("TRIBUTARIO", "ARREMATACAO"),
                tags=("iptu", "sub-rogacao", "debitos"),
                verification_status="VERIFICADO",
            ),
            ProvisionSeed(
                slug="ctn-1966-art131",
                reference="Art. 131, I",
                heading="Responsabilidade pessoal do adquirente",
                official_text=(
                    "São pessoalmente responsáveis: I - o adquirente ou remitente, pelos tributos "
                    "relativos aos bens adquiridos ou remidos;"
                ),
                practical_note=(
                    "Fora da hipótese de sub-rogação no preço (art. 130, parágrafo único), o "
                    "adquirente pode responder pelos tributos do bem. Débitos de condomínio não "
                    "são tributos e seguem regra própria (obrigação propter rem)."
                ),
                contexts=("TRIBUTARIO", "ARREMATACAO"),
                tags=("responsabilidade", "tributos"),
                verification_status="VERIFICADO",
            ),
        ),
    ),
)


# ---------------------------------------------------------------------------
# REGRAS PRÁTICAS (ancoradas nos dispositivos) + VÍNCULOS COM O CHECKLIST
# ---------------------------------------------------------------------------
# Cada regra referencia um dispositivo (provision_slug) e um ou mais canonical_key
# EXISTENTES do Checklist Mestre — enriquecendo o item sem alterá-lo.

RULES: tuple[RuleSeed, ...] = (
    RuleSeed(
        slug="regra-intimacao-mora",
        rule_kind="REQUISITO",
        title="Intimação para purgar a mora antes da consolidação",
        statement=(
            "A consolidação da propriedade pressupõe que o fiduciante tenha sido intimado "
            "para purgar a mora. Verificar se a intimação foi pessoal e, se frustrada, se "
            "houve intimação por edital. Falha na intimação é causa recorrente de "
            "questionamento do leilão extrajudicial."
        ),
        contexts=("CONSOLIDACAO", "LEILAO"),
        provision_slug="lei-9514-1997-art26",
        links=(
            RuleLink("INTIMACAO_PESSOAL", "PRINCIPAL"),
            RuleLink("INTIMACAO_EDITAL", "PRINCIPAL"),
            RuleLink("CONSOLIDACAO_REGISTRADA", "COMPLEMENTAR"),
        ),
    ),
    RuleSeed(
        slug="regra-dois-leiloes",
        rule_kind="REQUISITO",
        title="Dois leilões e lance mínimo do art. 27",
        statement=(
            "Após a consolidação, o imóvel vai a dois leilões. No primeiro, o lance mínimo é "
            "o valor do imóvel; no segundo, passa a ser o valor da dívida e encargos. "
            "Confirmar as datas dos dois leilões e a regularidade das notificações."
        ),
        contexts=("LEILAO", "ARREMATACAO"),
        provision_slug="lei-9514-1997-art27",
        links=(
            RuleLink("NOTIFICACAO_DOIS_LEILOES", "PRINCIPAL"),
            RuleLink("LEILOES_NEGATIVOS_AVERBADOS", "COMPLEMENTAR"),
            RuleLink("LANCE_MENOR_50_AVALIACAO", "COMPLEMENTAR"),
        ),
    ),
    RuleSeed(
        slug="regra-taxa-ocupacao",
        rule_kind="ORIENTACAO",
        title="Taxa de ocupação e custo de desocupação",
        statement=(
            "Enquanto o imóvel estiver ocupado após o leilão, há previsão legal de taxa de "
            "ocupação devida pelo antigo fiduciante (1% ao mês sobre o valor de referência). "
            "Considerar na conta de desocupação, sem presumir recebimento."
        ),
        contexts=("DESOCUPACAO", "POSSE"),
        provision_slug="lei-9514-1997-art37a",
        links=(
            RuleLink("TERCEIRO_OCUPANTE", "PRINCIPAL"),
            RuleLink("ETICA_OCUPACAO", "COMPLEMENTAR"),
        ),
    ),
    RuleSeed(
        slug="regra-imissao-posse",
        rule_kind="ORIENTACAO",
        title="Direito de reaver o imóvel (imissão na posse)",
        statement=(
            "O proprietário tem o direito de reaver o imóvel de quem injustamente o possua. "
            "Após o registro da aquisição, a via usual é a ação de imissão na posse quando "
            "não há desocupação amigável."
        ),
        contexts=("POSSE", "DESOCUPACAO"),
        provision_slug="cc-2002-art1228",
        links=(
            RuleLink("TERCEIRO_OCUPANTE", "COMPLEMENTAR"),
        ),
    ),
    RuleSeed(
        slug="regra-eviccao",
        rule_kind="RISCO",
        title="Garantia da evicção na arrematação",
        statement=(
            "A garantia da evicção subsiste mesmo em hasta pública, mas o edital pode trazer "
            "cláusulas específicas. Verificar no edital se há responsabilização pela evicção "
            "de direito e sinalizar o risco quando houver exclusão."
        ),
        contexts=("ARREMATACAO", "LEILAO"),
        severity="MEDIA",
        provision_slug="cc-2002-art447",
        links=(
            RuleLink("EVICCAO", "PRINCIPAL"),
            RuleLink("EDITAL_LIDO", "COMPLEMENTAR"),
        ),
    ),
    RuleSeed(
        slug="regra-locacao-averbada",
        rule_kind="RISCO",
        title="Locação averbada com cláusula de vigência",
        statement=(
            "Locação por prazo determinado, com cláusula de vigência em caso de alienação e "
            "averbada na matrícula, pode obrigar o arrematante a respeitar o contrato. Sem "
            "averbação, cabe em regra denúncia com prazo de 90 dias."
        ),
        contexts=("LOCACAO", "DESOCUPACAO", "MATRICULA"),
        severity="MEDIA",
        provision_slug="lei-8245-1991-art8",
        links=(
            RuleLink("LOCACAO_REGISTRADA", "PRINCIPAL"),
        ),
    ),
    RuleSeed(
        slug="regra-tributos-sub-rogacao",
        rule_kind="RESPONSABILIDADE",
        title="Tributos do imóvel e sub-rogação no preço",
        statement=(
            "Na arrematação em hasta pública, os tributos do imóvel (IPTU/taxas) sub-rogam-se "
            "no preço, salvo disposição do edital. Débitos de condomínio não são tributos e "
            "seguem regra própria (propter rem). Ler o edital para saber o que é transferido."
        ),
        contexts=("TRIBUTARIO", "ARREMATACAO"),
        provision_slug="ctn-1966-art130",
        links=(
            RuleLink("RESPONSABILIDADE_DEBITOS", "PRINCIPAL"),
            RuleLink("EDITAL_LIDO", "COMPLEMENTAR"),
        ),
    ),
    RuleSeed(
        slug="regra-arrematacao-perfeita",
        rule_kind="ORIENTACAO",
        title="Perfeição da arrematação judicial",
        statement=(
            "Na arrematação judicial, assinado o auto, a arrematação é em regra perfeita e "
            "irretratável, ressalvadas as hipóteses de invalidação previstas em lei. Não "
            "confundir com o leilão extrajudicial da Lei 9.514/97."
        ),
        contexts=("ARREMATACAO",),
        provision_slug="cpc-2015-art903",
        links=(
            RuleLink("ACAO_QUESTIONAMENTO", "COMPLEMENTAR"),
        ),
    ),
)
