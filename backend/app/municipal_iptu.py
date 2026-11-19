"""IPTU dos quatro municípios de cobertura inicial (v1.0.12, Fase F): levantamento dos portais e consulta manual assistida.

Levantamento feito em páginas públicas oficiais (sem login, sem automação, sem contornar CAPTCHA ou bloqueio). Nenhum dos
portais oferece API pública documentada nem termos que autorizem consulta automatizada; todos exigem dado pessoal do
proprietário (CPF/CNPJ), cadastro com senha ou verificação de navegador. Por isso NENHUM provider automático é registrado:
a consulta continua MANUAL ASSISTIDA (``debt_providers.ManualAssistedProvider``), com o portal e o passo a passo exibidos ao
operador. A cobertura e as fontes vivem como DADO (``MunicipalityCoverage`` / ``DebtSource``), administráveis no Admin.

Reclassificação: as linhas de cobertura de IPTU semeadas antes como AUTOMATIZAVEL passam a MANUAL **apenas** se ainda estão
exatamente como o seed original as criou (edição do operador nunca é sobrescrita).
"""
from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from . import models

LEVANTAMENTO = "Levantamento v1.0.12 (19/11/2026) em páginas públicas oficiais (sem login e sem automação)."

# Observações do seed original (v1.0.x) — usadas só para reconhecer linha de cobertura nunca editada.
_SEED_ORIGINAL_OBS = {
    ("Curitiba", "PR"): "Portal IPTU-DAM (iptu-dam.curitiba.pr.gov.br). Viabilidade de automação depende de termos de uso.",
    ("São José dos Pinhais", "PR"): "Portal de Finanças (financas.sjp.pr.gov.br / Semfi). Viabilidade de automação não confirmada.",
    ("Fazenda Rio Grande", "PR"): "Divisão de Arrecadação (fazendariogrande.pr.gov.br). Possível plataforma atende.net; não confirmado.",
    ("Assis", "SP"): "Sistema de Arrecadação (tributacao.assis.sp.gov.br). NÃO confundir com a capital de SP.",
}

IPTU_PORTALS: dict[tuple[str, str], dict[str, Any]] = {
    ("Curitiba", "PR"): {
        "fonte": "Prefeitura de Curitiba — IPTU-DAM e Certidão de débitos do imóvel",
        "orgao": "Secretaria Municipal de Planejamento, Finanças e Orçamento",
        "urls": ["https://iptu-dam.curitiba.pr.gov.br/", "https://cnd-cidadao.curitiba.pr.gov.br/Certidao/Solicitar",
                 "https://financas.curitiba.pr.gov.br/"],
        "identificador": "Inscrição Imobiliária + Sublote, ou Indicação Fiscal",
        "exigencias": ["CPF/CNPJ do proprietário cadastrado para consultar débitos e emitir a certidão",
                       "Finalidade da certidão (na emissão da certidão)"],
        "api_publica": False, "captcha_ou_bloqueio": "Acesso automatizado recusado (HTTP 403) no levantamento.",
        "login": False, "termos_uso": "Não localizados termos que autorizem consulta automatizada.",
        "estabilidade": "Portal oficial ativo; acesso por robô bloqueado.",
        "nivel": "MANUAL", "situacao": "DISPONIVEL", "metodo": "PORTAL_PUBLICO",
        "motivo_manual": "Exige CPF/CNPJ do proprietário e bloqueia acesso automatizado.",
        "passos": ["Abrir o portal IPTU-DAM ou o de certidão da Prefeitura de Curitiba.",
                   "Informar a Inscrição Imobiliária e o Sublote (ou a Indicação Fiscal) do imóvel.",
                   "Informar o CPF/CNPJ do proprietário que consta no cadastro municipal (após a consolidação, em geral o vendedor).",
                   "Registrar os débitos encontrados (ou a ausência) na Central de Débitos, anexando a certidão ou o extrato."],
    },
    ("São José dos Pinhais", "PR"): {
        "fonte": "Prefeitura de São José dos Pinhais — Portal de Serviços da Secretaria de Finanças (Semfi)",
        "orgao": "Secretaria Municipal de Finanças — Departamento de Tributos Imobiliários",
        "urls": ["https://financas.sjp.pr.gov.br/", "https://www.sjp.pr.gov.br/secretarias/secretaria-financas/iptu/"],
        "identificador": "Cadastro/inscrição imobiliária do imóvel",
        "exigencias": ["Cadastro de usuário e senha no portal de Finanças para os serviços do contribuinte"],
        "api_publica": False, "captcha_ou_bloqueio": "Aplicação web que depende de JavaScript e autenticação.",
        "login": True, "termos_uso": "Não localizados termos que autorizem consulta automatizada.",
        "estabilidade": "Portal oficial ativo.",
        "nivel": "MANUAL", "situacao": "DEPENDE_AUTENTICACAO", "metodo": "PORTAL_PUBLICO",
        "motivo_manual": "Serviços do contribuinte exigem login (usuário e senha).",
        "passos": ["Acessar o Portal de Serviços da Secretaria de Finanças com usuário e senha.",
                   "Localizar o imóvel pelo cadastro imobiliário e consultar os débitos ou solicitar a certidão.",
                   "Sem acesso: protocolo digital (e-Sic) ou atendimento do Departamento de Tributos Imobiliários.",
                   "Registrar o resultado na Central de Débitos, anexando o documento obtido."],
    },
    ("Fazenda Rio Grande", "PR"): {
        "fonte": "Prefeitura de Fazenda Rio Grande — Divisão de Arrecadação / Portal do Cidadão Web",
        "orgao": "Secretaria Municipal de Finanças — Divisão de Arrecadação",
        "urls": ["https://www.fazendariogrande.pr.gov.br/divisao-de-arrecadacao"],
        "identificador": "CPF ou CNPJ do proprietário",
        "exigencias": ["CPF ou CNPJ do proprietário para consultar débitos e emitir boletos"],
        "api_publica": False, "captcha_ou_bloqueio": "Não verificado: a consulta exige dado pessoal do proprietário.",
        "login": False, "termos_uso": "Não localizados termos que autorizem consulta automatizada.",
        "estabilidade": "Página oficial ativa (IPTU 2026 publicado).",
        "nivel": "MANUAL", "situacao": "DISPONIVEL", "metodo": "PORTAL_PUBLICO",
        "motivo_manual": "Consulta feita pelo CPF/CNPJ do proprietário (dado pessoal); sem API pública.",
        "passos": ["Abrir a página da Divisão de Arrecadação e o link de consulta do IPTU (Portal do Cidadão Web).",
                   "Informar o CPF/CNPJ do proprietário cadastrado (após a consolidação, em geral o vendedor).",
                   "Conferir as parcelas e exercícios em aberto do imóvel (pela inscrição imobiliária).",
                   "Registrar o resultado na Central de Débitos; para o ITBI, a certidão exige o imóvel sem dívidas."],
    },
    ("Assis", "SP"): {
        "fonte": "Prefeitura de Assis — Sistema de Arrecadação e Via Fácil",
        "orgao": "Secretaria Municipal da Fazenda — Tributação",
        "urls": ["https://tributacao.assis.sp.gov.br/", "https://www.assis.sp.gov.br/portal/servicos/1019/via-facil/"],
        "identificador": "Cadastro do imóvel",
        "exigencias": ["Atendimento Via Fácil (presencial ou WhatsApp da Prefeitura) para levantamento de débitos e certidão"],
        "api_publica": False, "captcha_ou_bloqueio": "Portal com verificação de navegador (página de espera) no levantamento.",
        "login": False, "termos_uso": "Não localizados termos que autorizem consulta automatizada.",
        "estabilidade": "Portal oficial ativo, com verificação de navegador.",
        "nivel": "MANUAL", "situacao": "DISPONIVEL", "metodo": "PORTAL_PUBLICO",
        "motivo_manual": "Verificação de navegador no portal; levantamento de débitos pelo Via Fácil.",
        "passos": ["Acessar o Sistema de Arrecadação de Assis/SP (não confundir com a capital) ou o Via Fácil.",
                   "Informar o cadastro do imóvel ou pedir o levantamento de débitos e a certidão ao Via Fácil.",
                   "Registrar o resultado na Central de Débitos, anexando o documento obtido."],
    },
}


def _municipality(db: Session, name: str, state: str):
    return db.scalar(select(models.Municipality).where(models.Municipality.name == name, models.Municipality.state == state))


def seed_iptu_sources(db: Session) -> dict[str, int]:
    """Fontes de IPTU (DebtSource) dos 4 municípios e reclassificação da cobertura nunca editada. Idempotente."""
    created = reclassified = 0
    for (name, state), info in IPTU_PORTALS.items():
        muni = _municipality(db, name, state)
        if muni is None:
            continue
        exists = db.scalar(select(models.DebtSource).where(models.DebtSource.municipality_id == muni.id, models.DebtSource.debt_category == "IPTU",
                                                           models.DebtSource.name == info["fonte"]))
        if exists is None:
            db.add(models.DebtSource(
                municipality_id=muni.id, debt_category="IPTU", name=info["fonte"], authority=info["orgao"], official_url=info["urls"][0],
                source_type="PORTAL_PUBLICO", method="Consulta manual assistida no portal oficial", situation=info["situacao"],
                access_requirements="; ".join(info["exigencias"] + ([] if not info["login"] else ["login"])),
                limitations=f"{info['motivo_manual']} {info['captcha_ou_bloqueio']} {info['termos_uso']}",
                observations=f"{LEVANTAMENTO} Identificador: {info['identificador']}. Outras páginas: {', '.join(info['urls'][1:]) or '—'}.",
                active=True))
            created += 1
        cov = db.scalar(select(models.MunicipalityCoverage).where(models.MunicipalityCoverage.municipality_id == muni.id,
                                                                  models.MunicipalityCoverage.debt_type_code == "IPTU"))
        if cov is not None and cov.level == "AUTOMATIZAVEL" and cov.observations == _SEED_ORIGINAL_OBS.get((name, state)):
            cov.level, cov.situation, cov.method = info["nivel"], info["situacao"], info["metodo"]
            cov.identifier_required = info["identificador"]
            cov.observations = f"{info['motivo_manual']} {LEVANTAMENTO}"
            reclassified += 1
    db.flush()
    return {"fontes_iptu": created, "cobertura_reclassificada": reclassified}


def guidance(db: Session, municipality_id: int | None) -> dict[str, Any] | None:
    """Orientação da consulta manual assistida do IPTU para o município (portal, identificador, exigências, passos)."""
    if municipality_id is None:
        return None
    muni = db.get(models.Municipality, municipality_id)
    if muni is None:
        return None
    info = IPTU_PORTALS.get((muni.name, muni.state))
    if info is None:
        return {"municipio": f"{muni.name}/{muni.state}", "automatizado": False, "modo": "MANUAL_ASSISTIDA",
                "motivo": "Município sem levantamento de portal: consulte a prefeitura e registre o resultado.", "passos": [], "urls": []}
    return {"municipio": f"{muni.name}/{muni.state}", "automatizado": False, "modo": "MANUAL_ASSISTIDA", "motivo": info["motivo_manual"],
            "fonte": info["fonte"], "orgao": info["orgao"], "urls": info["urls"], "identificador": info["identificador"],
            "exigencias": info["exigencias"], "login": info["login"], "api_publica": info["api_publica"],
            "captcha_ou_bloqueio": info["captcha_ou_bloqueio"], "termos_uso": info["termos_uso"], "passos": info["passos"],
            "aviso": "Consulta sem resultado ou indisponível não significa ausência de débito. Registre o que for encontrado, com o documento."}
