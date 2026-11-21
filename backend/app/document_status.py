"""Situação documental do imóvel (v1.0.14). Leitura pura.

Diz em poucos segundos: o que foi recebido, o que foi analisado, o que é obrigatório e falta, o que está incompleto (sem
texto, OCR com falha, indexação parcial), quantas evidências e páginas cada documento sustenta e a próxima ação.
"""
from __future__ import annotations

from collections import Counter
from typing import Any

from .registry_chain import fold

ANALISADOS = {"INDEXADO", "PRONTO_SEM_EMBEDDING"}
INCOMPLETOS = {"INDEXADO_PARCIAL", "SEM_TEXTO", "OCR_NECESSARIO", "OCR_FALHOU", "ERRO"}
EM_PROCESSAMENTO = {"RECEBIDO", "PROCESSANDO"}
SITUACAO_LABELS = {"ANALISADO": "Analisado", "INCOMPLETO": "Incompleto", "EM_PROCESSAMENTO": "Recebido, em processamento", "RECEBIDO": "Recebido"}

# Documentos esperados. ``tipos``: document_type aceito; ``nome``: trecho do nome do arquivo aceito; ``obrigatorio``: sem ele não há
# decisão segura (P0); ``alternativa``: outra forma de cumprir (ex.: consulta registrada do IPTU).
ESPERADOS = (
    {"chave": "MATRICULA", "nome_exibicao": "Matrícula atualizada", "tipos": {"MATRICULA"}, "nome": ("MATRICULA",), "obrigatorio": True,
     "por_que": "Mostra quem é o dono, ônus, penhoras e a consolidação.", "acao": "Pedir a certidão de inteiro teor ao cartório de registro de imóveis."},
    {"chave": "EDITAL", "nome_exibicao": "Edital ou condições da venda", "tipos": {"EDITAL", "CONDICOES_VENDA"}, "nome": ("EDITAL", "CONDICOES", "CONDICOES DA VENDA"),
     "obrigatorio": True, "por_que": "Define pagamento, débitos, desocupação e responsabilidades.", "acao": "Baixar o edital ou as condições da venda no site do leiloeiro ou do banco."},
    {"chave": "IPTU", "nome_exibicao": "Certidão ou consulta do IPTU", "tipos": set(), "nome": ("IPTU", "CERTIDAO NEGATIVA DE DEBITOS MUNICIPAIS"),
     "obrigatorio": False, "alternativa": "consulta de IPTU registrada", "por_que": "Débito de IPTU pode passar para o comprador.",
     "acao": "Consultar no portal da prefeitura e registrar em Débitos."},
    {"chave": "CONDOMINIO", "nome_exibicao": "Declaração de débitos do condomínio", "tipos": set(), "nome": ("CONDOMINIO", "DECLARACAO DE DEBITOS"),
     "obrigatorio": False, "por_que": "Mostra a taxa mensal e atrasos.", "acao": "Pedir à administradora a declaração de débitos e o valor da taxa."},
    {"chave": "LAUDO", "nome_exibicao": "Laudo de avaliação ou fotos", "tipos": set(), "nome": ("LAUDO", "AVALIACAO", "FOTO"),
     "obrigatorio": False, "por_que": "Ajuda a estimar o estado de conservação e a reforma.", "acao": "Baixar o laudo ou as fotos do anúncio do leilão."},
)


def _v(obj: Any, key: str, default: Any = None) -> Any:
    return obj.get(key, default) if isinstance(obj, dict) else getattr(obj, key, default)


def _latest(document: Any) -> Any:
    versions = list(_v(document, "versions", []) or [])
    return max(versions, key=lambda v: _v(v, "version", 0)) if versions else None


def summarize(documents: list[Any], *, evidences: list[Any] = (), iptu_consulted: bool = False, condo_debt_known: bool = False) -> dict[str, Any]:
    by_version: dict[int, list[Any]] = {}
    for ev in evidences:
        if _v(ev, "document_version_id") is not None:
            by_version.setdefault(int(_v(ev, "document_version_id")), []).append(ev)
    rows = []
    for doc in documents:
        latest = _latest(doc)
        status = str(_v(latest, "status") or _v(doc, "status") or "RECEBIDO").upper() if latest is not None else str(_v(doc, "status") or "RECEBIDO").upper()
        situacao = "ANALISADO" if status in ANALISADOS else "INCOMPLETO" if status in INCOMPLETOS else "EM_PROCESSAMENTO" if status in EM_PROCESSAMENTO else "RECEBIDO"
        evs = by_version.get(int(_v(latest, "id"))) if latest is not None and _v(latest, "id") is not None else []
        evs = evs or []
        meta = (_v(latest, "extraction_metadata") or {}) if latest is not None else {}
        pages = meta.get("pages") or meta.get("page_count") or meta.get("paginas")
        cited_pages = sorted({int(_v(e, "page")) for e in evs if _v(e, "page") is not None})
        conf = Counter(str(_v(e, "confidence") or "MEDIA").upper() for e in evs)
        pend = []
        if situacao == "INCOMPLETO":
            pend.append("Texto não extraído por completo: reenviar o PDF com melhor qualidade ou ativar OCR.")
        if situacao == "ANALISADO" and not evs:
            pend.append("Analisado, mas nenhuma evidência foi tirada dele ainda: rodar a análise do imóvel.")
        rows.append({"id": _v(doc, "id"), "nome": _v(doc, "name"), "tipo": _v(doc, "document_type"), "versao": _v(latest, "version") if latest is not None else None,
                     "status_tecnico": status, "situacao": situacao, "situacao_label": SITUACAO_LABELS[situacao],
                     "paginas": pages, "paginas_citadas": cited_pages, "evidencias": len(evs),
                     "confianca": {"alta": conf.get("ALTA", 0), "media": conf.get("MEDIA", 0), "baixa": conf.get("BAIXA", 0)},
                     "metodo_extracao": meta.get("method") or meta.get("metodo") or meta.get("extractor"), "pendencias": pend})
    expected = []
    for spec in ESPERADOS:
        match = [r for r in rows if str(r["tipo"] or "").upper() in spec["tipos"] or any(n in fold(str(r["nome"] or "")) for n in spec["nome"])]
        alt = (spec["chave"] == "IPTU" and iptu_consulted) or (spec["chave"] == "CONDOMINIO" and condo_debt_known)
        if match:
            best = next((m for m in match if m["situacao"] == "ANALISADO"), match[0])
            state = "ANALISADO" if best["situacao"] == "ANALISADO" else "INCOMPLETO" if best["situacao"] == "INCOMPLETO" else "RECEBIDO"
        elif alt:
            state = "ATENDIDO_POR_CONSULTA"
        else:
            state = "PENDENTE"
        expected.append({"chave": spec["chave"], "nome": spec["nome_exibicao"], "obrigatorio": spec["obrigatorio"], "situacao": state,
                         "documentos": [m["id"] for m in match], "por_que": spec["por_que"],
                         "proxima_acao": None if state in ("ANALISADO", "ATENDIDO_POR_CONSULTA") else spec["acao"]})
    missing_required = [e["nome"] for e in expected if e["obrigatorio"] and e["situacao"] == "PENDENTE"]
    actions = [f"{e['nome']}: {e['proxima_acao']}" for e in expected if e["proxima_acao"] and (e["obrigatorio"] or e["situacao"] == "PENDENTE")]
    actions += [f"{r['nome']}: {p}" for r in rows for p in r["pendencias"]]
    counts = Counter(r["situacao"] for r in rows)
    texto = (f"{len(rows)} documento(s) recebido(s), {counts.get('ANALISADO', 0)} analisado(s)"
             + (f", {counts.get('INCOMPLETO', 0)} incompleto(s)" if counts.get("INCOMPLETO") else "")
             + (f". Falta(m) obrigatório(s): {', '.join(missing_required)}." if missing_required else ". Documentos obrigatórios recebidos."))
    return {"documentos": rows, "esperados": expected, "obrigatorios_faltando": missing_required,
            "contagem": {"recebidos": len(rows), "analisados": counts.get("ANALISADO", 0), "incompletos": counts.get("INCOMPLETO", 0),
                         "em_processamento": counts.get("EM_PROCESSAMENTO", 0) + counts.get("RECEBIDO", 0),
                         "evidencias": sum(r["evidencias"] for r in rows)},
            "proximas_acoes": actions[:8], "texto": texto}


def for_property(db, prop) -> dict[str, Any]:
    from sqlalchemy import select
    from . import models
    evidences = list(db.scalars(select(models.Evidence).where(models.Evidence.property_id == prop.id)).all())
    iptu = bool(db.scalars(select(models.DebtQuery.id).where(models.DebtQuery.property_id == prop.id, models.DebtQuery.debt_type_code == "IPTU",
                                                            models.DebtQuery.status.in_(("CONCLUIDA", "SEM_OCORRENCIA", "PARCIAL")))).all())
    condo = bool(db.scalars(select(models.PropertyDebt.id).where(models.PropertyDebt.property_id == prop.id,
                                                               models.PropertyDebt.debt_type_code.in_(("COTA_CONDOMINIAL", "MULTA_CONDOMINIAL",
                                                                                                        "JUROS_CONDOMINIAIS", "DESPESA_EXTRAORDINARIA")))).all())
    return summarize(list(prop.documents), evidences=evidences, iptu_consulted=iptu, condo_debt_known=condo)
