#!/usr/bin/env python3
"""Avaliação de VALOR DE NEGÓCIO do Radar Leilão contra um gabarito (caso sintético).

Pergunta central: "Vale a pena comprar este imóvel neste leilão?"

O script:
  1. cadastra o caso (imóvel A) e um imóvel de controle (B) pela API REAL do backend;
  2. envia os documentos sintéticos, roda extração e análise completa;
  3. coleta respostas, estados, erros e tempos;
  4. compara com o gabarito (fatos ponderados, armadilhas de alucinação, financeiro, veredito,
     privacidade e isolamento) e grava relatório JSON + Markdown.

Funciona COM ou SEM chave da OpenAI: o modo é detectado pela resposta do /analisar. Sem chave
(linha de base) a pontuação da IA é zero por construção e o foco é provar que nada pago foi
chamado, que a indisponibilidade é informada e que o financeiro funciona sozinho.

Regras de pontuação (não negociáveis):
  - fato só pontua se houver afirmação da IA COM evidência ligada a um trecho (chunk) do
    documento do próprio imóvel, e o trecho contiver os termos do fato;
  - menção sem evidência, ou evidência que não sustenta o texto, vale zero.

Segurança: NUNCA aponte para produção. O banco é lido somente para leitura (llm_runs, chunks).
O relatório mascara CPF. A chave da OpenAI nunca é lida por este script.

Uso (no WSL, com o backend local rodando):
  ~/radar-venv/bin/python e2e/valor-negocio/valor_negocio.py \
      --api http://127.0.0.1:8100 --db postgresql://postgres@127.0.0.1:54329/radar_hom \
      --log /mnt/c/Users/<user>/hom_up_out6.txt
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import httpx

HERE = Path(__file__).resolve().parent
FIXTURES = HERE.parent / "fixtures" / "caso-01"
RESULTS = HERE.parent / "results" / "valor-negocio"

CPF_RE = re.compile(r"\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b")
CNJ_RE = re.compile(r"\b\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4}\b")
CONTROLE_MATRICULA = (
    "MATRICULA N. 000.000 - REGISTRO DE IMOVEIS FICTICIO (CONTROLE)\n"
    "Imovel: casa 7, Rua Controle Ficticia 9, Campinas/SP, area 120,00 m2.\n"
    "R.1 - Proprietaria: Empresa Controle Ficticia Ltda.\n"
    "Nao constam onus, penhoras ou indisponibilidades. Imovel desocupado.\n"
) * 3


# ----------------------------------------------------------------------------- utilidades

def num(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def mask(text: Any) -> str:
    """Nunca grava CPF no relatório."""
    return CPF_RE.sub("[CPF]", str(text or ""))


def norm(text: Any) -> str:
    import unicodedata
    raw = unicodedata.normalize("NFKD", str(text or "").lower())
    return "".join(ch for ch in raw if not unicodedata.combining(ch))


def has_terms(text: str, terms: list[str]) -> bool:
    t = norm(text)
    return all(norm(term) in t for term in terms)


class Api:
    def __init__(self, base: str, email: str, password: str):
        self.base = base.rstrip("/")
        self.client = httpx.Client(timeout=360)
        self.timings: list[dict[str, Any]] = []
        res = self.client.post(f"{self.base}/api/auth/login", json={"email": email, "password": password})
        res.raise_for_status()
        self.client.headers["Authorization"] = f"Bearer {res.json()['access_token']}"

    def call(self, method: str, path: str, step: str, **kwargs) -> httpx.Response:
        for attempt in range(6):
            started = time.perf_counter()
            res = self.client.request(method, f"{self.base}{path}", **kwargs)
            elapsed = round((time.perf_counter() - started) * 1000)
            if res.status_code == 429 and attempt < 5:      # limite de operações críticas por minuto
                self.timings.append({"etapa": step, "status": 429, "ms": elapsed, "nota": "rate limit; aguardando"})
                time.sleep(15)
                continue
            self.timings.append({"etapa": step, "status": res.status_code, "ms": elapsed})
            return res
        return res

    def ok(self, method: str, path: str, step: str, **kwargs) -> Any:
        res = self.call(method, path, step, **kwargs)
        if res.status_code >= 300:
            raise RuntimeError(f"{step}: HTTP {res.status_code} {mask(res.text)[:400]}")
        return res.json() if res.content else None


class Db:
    """Leitura apenas (sessão read-only)."""

    def __init__(self, url: str | None):
        self.conn = None
        self.error = None
        if not url:
            self.error = "sem --db: checagens de llm_runs/isolamento por chunk não executadas"
            return
        try:
            import psycopg
            self.conn = psycopg.connect(url.replace("postgresql+psycopg://", "postgresql://"), autocommit=True)
            self.conn.execute("SET SESSION CHARACTERISTICS AS TRANSACTION READ ONLY")
        except Exception as exc:  # pragma: no cover - ambiente
            self.error = f"banco indisponível: {type(exc).__name__}"

    def rows(self, sql: str, params: tuple = ()) -> list[tuple]:
        if not self.conn:
            return []
        return self.conn.execute(sql, params).fetchall()


# ----------------------------------------------------------------------------- cadastro

def cadastrar_caso(api: Api, ins: dict[str, Any], sufixo: str) -> dict[str, Any]:
    imovel = dict(ins["imovel"], title=f"{ins['imovel']['title']} {sufixo}")
    prop = api.ok("POST", "/api/imoveis", "A: criar imóvel", json=imovel)
    pid = prop["id"]
    api.ok("POST", f"/api/imoveis/{pid}/leilao", "A: leilão", json=ins["leilao"])
    api.ok("POST", f"/api/imoveis/{pid}/matricula", "A: matrícula", json=ins["matricula"])
    for proc in ins["processos"]:
        api.ok("POST", f"/api/imoveis/{pid}/processos", "A: processo", json=proc)
    api.ok("POST", f"/api/imoveis/{pid}/ocupacao", "A: ocupação", json=ins["ocupacao"])
    for cost in ins["custos"]:
        api.ok("POST", f"/api/imoveis/{pid}/custos", "A: custo", json=cost)
    for debt in ins["dividas"]:
        api.ok("POST", f"/api/imoveis/{pid}/dividas", "A: dívida", json=debt)
    for comp in ins["comparaveis"]:
        api.ok("POST", f"/api/imoveis/{pid}/comparaveis", "A: comparável", json=comp)
    api.ok("PUT", f"/api/imoveis/{pid}/financeiro/premissas", "A: premissas", json=ins["premissas_financeiras"])
    docs = {}
    for nome, tipo in (("matricula.txt", "MATRICULA"), ("edital.txt", "EDITAL")):
        conteudo = (FIXTURES / nome).read_bytes()
        doc = api.ok("POST", f"/api/imoveis/{pid}/documentos", f"A: upload {nome}",
                     files={"file": (nome, conteudo, "text/plain")}, data={"document_type": tipo, "source": "valor-negocio"})
        docs[tipo] = doc
    return {"id": pid, "docs": docs}


def cadastrar_controle(api: Api, sufixo: str) -> dict[str, Any]:
    prop = api.ok("POST", "/api/imoveis", "B: criar imóvel", json={
        "title": f"CONTROLE-B FICTICIO {sufixo}", "address": "Rua Controle Ficticia 9", "city": "Campinas", "state": "SP",
        "property_type": "Casa", "area_m2": 120, "bedrooms": 3})
    pid = prop["id"]
    doc = api.ok("POST", f"/api/imoveis/{pid}/documentos", "B: upload matrícula",
                 files={"file": ("matricula-controle.txt", CONTROLE_MATRICULA.encode(), "text/plain")},
                 data={"document_type": "MATRICULA", "source": "valor-negocio-controle"})
    return {"id": pid, "docs": {"MATRICULA": doc}}


def ultima_versao(doc: dict[str, Any]) -> dict[str, Any]:
    return max(doc.get("versions") or [{}], key=lambda v: v.get("version", 0))


# ----------------------------------------------------------------------------- avaliação

def avaliar_financeiro(fin: dict[str, Any], gab: dict[str, Any], ins: dict[str, Any]) -> dict[str, Any]:
    esperado = gab["resposta_esperada"]
    lance = num(ins["leilao"]["bid_value"])
    pm = num(fin.get("preco_maximo"))
    ref = esperado["preco_maximo_referencia_brl"]
    tol = esperado["preco_maximo_tolerancia_pct"] / 100
    resultado = num(fin.get("resultado_liquido"))
    margem = num(fin.get("margem_liquida"))
    meta = ((fin.get("preco_maximo_detalhe") or {}).get("premissas_utilizadas") or {}).get("meta") or {}
    criterios = {
        "Q1_calcula_preco_maximo": {
            "ok": pm is not None and abs(pm - ref) <= ref * tol and bool(fin.get("preco_maximo_definitivo")),
            "radar": pm, "referencia": ref, "definitivo": fin.get("preco_maximo_definitivo")},
        "Q2_identifica_prejuizo": {
            "ok": resultado is not None and resultado < 0, "resultado_liquido_radar": resultado,
            "referencia": esperado.get("resultado_no_lance_minimo_brl")},
        "Q3_considera_margem_minima_20": {
            "ok": str(meta.get("tipo")) == "MARGEM_MINIMA" and num(meta.get("valor")) == esperado.get("margem_minima"),
            "meta_usada": meta, "margem_no_lance": margem},
        "Q4_compara_lance_com_preco_maximo": {
            "ok": None, "lance": lance, "preco_maximo": pm,
            "lance_acima_do_maximo": (pm is not None and lance is not None and lance > pm),
            "nota": "preenchido depois: o produto precisa DIZER ao investidor que o lance excede o máximo"},
    }
    return {
        "custo_total": num(fin.get("custo_total")), "resultado_liquido": resultado, "margem_liquida": margem,
        "roi_operacao": num(fin.get("roi_operacao")), "break_even": num(fin.get("break_even")),
        "preco_maximo": pm, "preco_maximo_definitivo": fin.get("preco_maximo_definitivo"),
        "custos": {k: num(v) for k, v in (fin.get("custos") or {}).items()},
        "pendencias": [mask(p) for p in fin.get("pendencias") or []],
        "referencia_custo_total": esperado.get("custo_total_no_lance_minimo_brl"),
        "criterios": criterios,
    }


def textos_do_produto(prop: dict[str, Any], analise: dict[str, Any], fin: dict[str, Any]) -> str:
    ver = prop.get("veredito") or {}
    partes = [ver.get("summary"), ver.get("what_is_known"), ver.get("what_is_unknown"),
              " ".join(ver.get("pending_items") or []), " ".join(fin.get("pendencias") or []),
              ((analise.get("status_detalhe") or {}).get("mensagem"))]
    for r in prop.get("riscos") or []:
        partes.append(r.get("description"))
    return " \n".join(str(p) for p in partes if p)


def avaliar_ia(evidencias: list[dict[str, Any]], checklist: list[dict[str, Any]], chunks: dict[int, dict[str, Any]],
               gab: dict[str, Any], ia_disponivel: bool, conhecidos_cnj: set[str], extras_ia: list[str]) -> dict[str, Any]:
    # Afirmações "da IA": evidências criadas pela análise + respostas do checklist + textos extras (extração).
    afirmacoes = []
    for ev in evidencias:
        texto = " ".join(str(ev.get(k) or "") for k in ("fact", "interpretation", "hypothesis"))
        chunk = chunks.get(ev.get("chunk_id")) if ev.get("chunk_id") else None
        afirmacoes.append({"origem": f"evidencia#{ev.get('id')}", "texto": texto, "chunk": chunk, "ev": ev})
    for item in checklist:
        # Itens resolvidos pelo motor determinístico a partir do cadastro não são afirmações da IA.
        if str(item.get("interpretation") or "").startswith("Resolvido automaticamente"):
            continue
        if item.get("state") not in (None, "PENDENTE"):
            afirmacoes.append({"origem": f"checklist:{item.get('canonical_key')}", "texto": f"{item.get('answer') or ''} {item.get('interpretation') or ''} {item.get('risk') or ''}", "chunk": None, "ev": None})
    for t in extras_ia:
        afirmacoes.append({"origem": "extracao", "texto": t, "chunk": None, "ev": None})
    # Mensagens de indisponibilidade não são afirmações sobre o imóvel.
    indisponivel = re.compile(r"llm n.o configurada|ia indispon|n.o foi executada|aguarda openai|or.amento", re.I)
    afirmacoes = [a for a in afirmacoes if a["texto"].strip() and not indisponivel.search(norm(a["texto"]))]

    fatos = []
    pontos = peso_total = 0
    for f in gab["fatos"]:
        peso_total += f["peso"]
        mencionado = [a for a in afirmacoes if has_terms(a["texto"], f["termos"])]
        sustentado = [a for a in mencionado if a["chunk"] and has_terms(a["chunk"]["content"], f["termos"])]
        status = "ENCONTRADO_COM_EVIDENCIA" if sustentado else ("MENCIONADO_SEM_EVIDENCIA" if mencionado else "NAO_ENCONTRADO")
        ganho = f["peso"] if sustentado else 0
        pontos += ganho
        fatos.append({"id": f["id"], "tema": f["tema"], "peso": f["peso"], "fato": f["fato"], "status": status, "pontos": ganho,
                      "origens": [a["origem"] for a in (sustentado or mencionado)][:5]})
    criticos = {fid: next(x["status"] for x in fatos if x["id"] == fid) == "ENCONTRADO_COM_EVIDENCIA" for fid in ("F2", "F3", "F4")}

    # Armadilhas (heurística automática; tudo marcado também para revisão humana).
    armadilhas = []
    valores_manuais = {"21.600", "21600", "4.800", "4800"}
    for a in afirmacoes:
        t = norm(a["texto"])
        achados = []
        for m in re.finditer(r"(condom|iptu).{0,80}?r\$\s?([\d\.\,]+)", t):
            if m.group(2).split(",")[0] not in valores_manuais:
                achados.append(("T1", f"valor de débito sem origem documental: R$ {m.group(2)}"))
        if re.search(r"livre (e desembaracad|de onus|de gravame)|sem (onus|gravames)|nao (ha|constam?) (onus|gravames)", t):
            achados.append(("T2", "afirma ausência de ônus"))
        if re.search(r"(admite|permite|aceita|possivel|pode).{0,40}(financiament|fgts)", t) and not re.search(r"nao (se )?(admite|permite|aceita)", t):
            achados.append(("T3", "afirma que financiamento/FGTS é possível"))
        for cnj in CNJ_RE.findall(a["texto"]):
            if cnj not in conhecidos_cnj:
                achados.append(("T4", f"processo não existente nos documentos/cadastro: {cnj}"))
        if re.search(r"(esta|encontra-se|imovel) desocupad", t) or re.search(r"desocupacao.{0,50}(vendedor|banco|credor)", t):
            achados.append(("T5", "afirma imóvel desocupado ou desocupação pelo vendedor"))
        for tid, desc in achados:
            armadilhas.append({"id": tid, "origem": a["origem"], "descricao": desc, "trecho": mask(a["texto"])[:240]})

    # T6: evidência com chunk que não sustenta o texto (sobreposição de termos significativos).
    citacoes = []
    for a in afirmacoes:
        if not a["chunk"]:
            continue
        termos = {w for w in re.findall(r"[a-z0-9]{6,}|\d[\d\.,]{2,}", norm(a["texto"]))}
        conteudo = norm(a["chunk"]["content"])
        cobertura = (sum(1 for w in termos if w in conteudo) / len(termos)) if termos else 0.0
        fraca = cobertura < 0.3
        if fraca:
            armadilhas.append({"id": "T6", "origem": a["origem"], "descricao": f"citação fraca (cobertura {cobertura:.0%})", "trecho": mask(a["texto"])[:240]})
        citacoes.append({"origem": a["origem"], "cobertura": round(cobertura, 2), "fraca": fraca})

    # Valores de condomínio/IPTU: o documento NÃO traz valores; a IA deve dizer que não constam.
    ausencias = {
        "afirmou_nao_consta": any(re.search(r"(condom|iptu).{0,120}(nao (consta|informad|especificad|disponivel)|desconhecid|apurar)", norm(a["texto"])) for a in afirmacoes),
        "inventou_valor": any(x["id"] == "T1" for x in armadilhas),
    }
    return {
        "ia_disponivel": ia_disponivel, "afirmacoes_avaliadas": len(afirmacoes),
        "pontuacao": pontos, "pontuacao_maxima": peso_total, "recall_ponderado": round(pontos / peso_total, 3) if peso_total else 0,
        "criticos_encontrados": criticos, "fatos": fatos, "armadilhas": armadilhas,
        "armadilhas_por_tipo": {t: sum(1 for x in armadilhas if x["id"] == t) for t in ("T1", "T2", "T3", "T4", "T5", "T6")},
        "citacoes": citacoes,
        "taxa_citacao_valida": round(sum(1 for c in citacoes if not c["fraca"]) / len(citacoes), 3) if citacoes else None,
        "ausencias_condominio_iptu": ausencias,
    }


def evidencias_view(evidencias: list[dict[str, Any]], versoes: dict[int, str]) -> list[dict[str, Any]]:
    out = []
    for ev in evidencias:
        out.append({"id": ev.get("id"), "categoria": ev.get("category"), "documento": versoes.get(ev.get("document_version_id")),
                    "versao_id": ev.get("document_version_id"), "chunk_id": ev.get("chunk_id"), "pagina": ev.get("page"),
                    "secao": ev.get("section"), "fato": mask(ev.get("fact"))[:300],
                    "trecho_literal": mask(ev.get("source_excerpt"))[:300] if ev.get("source_excerpt") else None})
    return out


# ----------------------------------------------------------------------------- principal

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--api", default=os.environ.get("RADAR_API_URL", "http://127.0.0.1:8100"))
    ap.add_argument("--email", default=os.environ.get("RADAR_E2E_EMAIL", "hom@local.test"))
    ap.add_argument("--password", default=os.environ.get("RADAR_E2E_PASSWORD", "HomLocal#2026x"))
    ap.add_argument("--db", default=os.environ.get("RADAR_DB_URL"))
    ap.add_argument("--log", default=os.environ.get("RADAR_BACKEND_LOG"), help="arquivo de log do backend (stdout do uvicorn)")
    ap.add_argument("--allow-remote", action="store_true", help="permitir API não local (NUNCA produção)")
    args = ap.parse_args()

    if not re.match(r"^https?://(127\.0\.0\.1|localhost)(:\d+)?", args.api) and not args.allow_remote:
        print("Recusado: API não local. Use --allow-remote só em ambiente de teste autorizado.", file=sys.stderr)
        return 2

    gab = json.loads((FIXTURES / "gabarito.json").read_text(encoding="utf-8"))
    ins = json.loads((FIXTURES / "insumos.json").read_text(encoding="utf-8"))
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    out_dir = RESULTS / stamp
    out_dir.mkdir(parents=True, exist_ok=True)
    log_offset = os.path.getsize(args.log) if args.log and os.path.exists(args.log) else None

    api = Api(args.api, args.email, args.password)
    db = Db(args.db)
    erros: list[str] = []
    t0 = time.perf_counter()

    a = cadastrar_caso(api, ins, stamp)
    b = cadastrar_controle(api, stamp)

    # Extração estruturada (exige LLM). Sem chave: deve responder indisponível, sem 5xx.
    extracoes = {}
    extras_ia: list[str] = []
    for tipo in ("MATRICULA", "EDITAL"):
        vid = ultima_versao(a["docs"][tipo]).get("id")
        res = api.call("POST", f"/api/imoveis/{a['id']}/documentos/{vid}/extrair", f"A: extrair {tipo}", json={"document_type": tipo})
        corpo = res.json() if res.headers.get("content-type", "").startswith("application/json") else {}
        extracoes[tipo] = {"http": res.status_code, "corpo": json.loads(mask(json.dumps(corpo, ensure_ascii=False)))}
        if res.status_code == 200 and isinstance(corpo, dict) and corpo.get("dados"):
            extras_ia.append(json.dumps(corpo.get("dados"), ensure_ascii=False))
    # Isolamento: extrair a versão do A pelo imóvel B deve ser recusado.
    vid_a = ultima_versao(a["docs"]["MATRICULA"]).get("id")
    cruz = api.call("POST", f"/api/imoveis/{b['id']}/documentos/{vid_a}/extrair", "B: extrair versão do A (negativo)", json={"document_type": "MATRICULA"})

    t_an = time.perf_counter()
    analise_a = api.ok("POST", f"/api/imoveis/{a['id']}/analisar", "A: analisar", json={})
    dur_a = round((time.perf_counter() - t_an) * 1000)
    analise_b = api.ok("POST", f"/api/imoveis/{b['id']}/analisar", "B: analisar", json={})

    prop_a = api.ok("GET", f"/api/imoveis/{a['id']}", "A: ler imóvel")
    prop_b = api.ok("GET", f"/api/imoveis/{b['id']}", "B: ler imóvel")
    fin_a = api.ok("GET", f"/api/imoveis/{a['id']}/financeiro", "A: financeiro")["financeiro"]
    ev_a = api.ok("GET", f"/api/imoveis/{a['id']}/evidencias", "A: evidências")
    ev_b = api.ok("GET", f"/api/imoveis/{b['id']}/evidencias", "B: evidências")
    docs_a = api.ok("GET", f"/api/imoveis/{a['id']}/documentos", "A: documentos")["documentos"]
    docs_b = api.ok("GET", f"/api/imoveis/{b['id']}/documentos", "B: documentos")["documentos"]
    rag = api.ok("GET", "/api/monitoring/rag", "monitoramento RAG")
    # Isolamento: evidência do A lida pelo B deve dar 404.
    cruz_ev = api.call("GET", f"/api/imoveis/{b['id']}/evidencias/{ev_a[0]['id']}", "B: ler evidência do A (negativo)") if ev_a else None

    def versions(docs):
        return {v["id"]: d["name"] for d in docs for v in d.get("versions") or []}
    vers_a, vers_b = versions(docs_a), versions(docs_b)

    # Banco (somente leitura): chunks dos dois imóveis e llm_runs.
    chunk_owner: dict[int, int] = {}
    chunks_a: dict[int, dict[str, Any]] = {}
    for cid, pid, content, page, section in db.rows(
            "SELECT c.id, d.property_id, c.content, c.page, c.section FROM document_chunks c JOIN document_versions v ON v.id = c.document_version_id "
            "JOIN documents d ON d.id = v.document_id WHERE d.property_id IN (%s, %s)", (a["id"], b["id"])):
        chunk_owner[cid] = pid
        if pid == a["id"]:
            chunks_a[cid] = {"content": content, "page": page, "section": section}
    runs = db.rows("SELECT property_id, analysis_id, agent, provider, model, status, input_tokens, output_tokens, total_cost, duration_ms, error_message "
                   "FROM llm_runs WHERE property_id IN (%s, %s) ORDER BY id", (a["id"], b["id"]))
    llm_runs = [{"imovel": "A" if r[0] == a["id"] else "B", "analysis_id": r[1], "agente": r[2], "provider": r[3], "modelo": r[4], "status": r[5],
                 "tokens_entrada": r[6], "tokens_saida": r[7], "custo_usd": num(r[8]), "duracao_ms": r[9], "erro": mask(r[10])[:160] if r[10] else None} for r in runs]

    st = analise_a.get("status_detalhe") or {}
    ia_disponivel = bool(st.get("ia_disponivel"))
    cnj_conhecidos = {p["number"] for p in ins["processos"]}

    # Evidências da ANÁLISE do A (as que a IA gerou nesta execução).
    ids_analise = set(analise_a.get("evidencias") or [])
    ev_analise_a = [e for e in ev_a if e.get("id") in ids_analise]
    ia = avaliar_ia(ev_analise_a, prop_a.get("checklist") or [], chunks_a, gab, ia_disponivel, cnj_conhecidos, extras_ia)
    financeiro = avaliar_financeiro(fin_a, gab, ins)

    # Q4/Q5: o produto DIZ ao investidor que não deve comprar por esse lance?
    texto_produto = norm(textos_do_produto(prop_a, analise_a, fin_a))
    diz_lance_acima = bool(re.search(r"(lance|arremat|aquisi).{0,60}(acima|supera|excede|maior).{0,40}(preco maximo|teto)", texto_produto))
    financeiro["criterios"]["Q4_compara_lance_com_preco_maximo"]["ok"] = diz_lance_acima
    veredito = (prop_a.get("veredito") or {}).get("overall")
    esperado = gab["resposta_esperada"]
    recomenda_nao = veredito in ("DESFAVORAVEL",) or bool(re.search(r"nao (arrematar|comprar|recomendad)|desfavoravel", texto_produto))
    financeiro["criterios"]["Q5_recomendacao_clara_de_nao_comprar"] = {
        "ok": recomenda_nao and veredito != esperado["veredito_falha_critica"], "veredito": veredito,
        "nota": "a recomendação precisa ser explícita para o investidor; INCONCLUSIVO não responde à pergunta"}

    # Checklist
    ck = prop_a.get("checklist") or []
    estados: dict[str, int] = {}
    for item in ck:
        estados[item.get("state") or "?"] = estados.get(item.get("state") or "?", 0) + 1
    links = db.rows("SELECT l.target_id FROM evidence_links l JOIN evidences e ON e.id = l.evidence_id WHERE e.property_id = %s AND l.target_type ILIKE %s", (a["id"], "checklist%"))
    alvos_com_ev = {r[0] for r in links}
    checklist = {"itens": len(ck), "por_estado": estados,
                 "fora_de_pendente": [{"chave": i.get("canonical_key"), "estado": i.get("state"), "com_evidencia": i.get("id") in alvos_com_ev, "resposta": mask(i.get("answer"))[:160]} for i in ck if i.get("state") not in (None, "PENDENTE")]}

    # Privacidade
    cpf_alvo = gab["privacidade"]["nunca_no_registro_ou_log"]
    cpf_variantes = set(cpf_alvo) | {re.sub(r"\D", "", c) for c in cpf_alvo}
    def contem_cpf(texto: str) -> bool:
        return any(v in (texto or "") for v in cpf_variantes)
    log_novo = ""
    if log_offset is not None:
        with open(args.log, "rb") as fh:
            fh.seek(log_offset)
            log_novo = fh.read().decode("utf-8", errors="replace")
    registros_execucao = json.dumps([runs, analise_a.get("llm_usage"), prop_a.get("veredito"), prop_a.get("analise_ultima")], default=str, ensure_ascii=False)
    privacidade = {
        "cpf_em_llm_runs_ou_registro_de_analise": contem_cpf(registros_execucao),
        "cpf_no_log_do_backend": contem_cpf(log_novo) if log_offset is not None else None,
        "segredo_no_log": bool(re.search(r"sk-[A-Za-z0-9_\-]{12,}", log_novo)) if log_offset is not None else None,
        "cpf_em_trecho_de_evidencia": any(contem_cpf(e.get("source_excerpt") or "") for e in ev_a),
        "nota_trecho": "O trecho literal da evidência é o próprio documento armazenado localmente; não é registro de execução. Se a UI mostrar o trecho, o CPF aparece na tela (avaliar mascaramento na exibição).",
        "log_verificado": log_offset is not None,
    }

    # Chamadas pagas
    chamadas_provider_no_log = len(re.findall(r"llm chamada iniciada|embedding concluido|embedding falhou", log_novo)) if log_offset is not None else None
    sem_custo = {
        "llm_runs_com_tokens_ou_custo": sum(1 for r in llm_runs if (r["tokens_entrada"] or r["tokens_saida"] or (r["custo_usd"] or 0) > 0)),
        "status_llm_runs": sorted({r["status"] for r in llm_runs}),
        "chamadas_ao_provider_no_log": chamadas_provider_no_log,
        "gasto_mes_monitoramento": (rag.get("orcamento_llm") or {}).get("gasto_usd"),
    }

    # Isolamento
    def doc_names(docs):
        return sorted(d["name"] for d in docs)
    chunks_rec_a = set(analise_a.get("chunks_recuperados") or [])
    chunks_rec_b = set(analise_b.get("chunks_recuperados") or [])
    isolamento = {
        "documentos_A": doc_names(docs_a), "documentos_B": doc_names(docs_b),
        "documentos_cruzados": bool(set(doc_names(docs_a)) & set(doc_names(docs_b))),
        "chunks_recuperados_A_de_outro_imovel": sorted(c for c in chunks_rec_a if chunk_owner.get(c, a["id"]) != a["id"]),
        "chunks_recuperados_B_de_outro_imovel": sorted(c for c in chunks_rec_b if chunk_owner.get(c, b["id"]) != b["id"]),
        "evidencias_B_apontam_para_versao_do_A": sorted(e["id"] for e in ev_b if e.get("document_version_id") in vers_a),
        "texto_do_caso_A_em_evidencias_B": any(has_terms(f"{e.get('fact')} {e.get('source_excerpt')}", ["99.901"]) for e in ev_b),
        "extracao_cruzada_http": cruz.status_code,
        "leitura_cruzada_evidencia_http": cruz_ev.status_code if cruz_ev is not None else None,
        "chunks_mapeados_no_banco": len(chunk_owner), "db": db.error or "ok",
    }
    isolamento["ok"] = (not isolamento["documentos_cruzados"] and not isolamento["chunks_recuperados_A_de_outro_imovel"]
                        and not isolamento["chunks_recuperados_B_de_outro_imovel"] and not isolamento["evidencias_B_apontam_para_versao_do_A"]
                        and not isolamento["texto_do_caso_A_em_evidencias_B"] and cruz.status_code >= 400
                        and (cruz_ev is None or cruz_ev.status_code == 404))

    # Indisponibilidade da IA
    documentos_estado = {d["name"]: [(v.get("version"), v.get("status"), (v.get("processamento") or {}).get("pronto_para_analise")) for v in d.get("versions") or []] for d in docs_a}
    disponibilidade = {
        "status_analise": analise_a.get("status"), "codigo": st.get("codigo"), "mensagem": mask(st.get("mensagem")),
        "agentes_ok": st.get("agentes_ok"), "agentes_total": st.get("agentes_total"), "ia_disponivel": ia_disponivel,
        "llm_usada": analise_a.get("llm_usada"), "extracao": {k: {"http": v["http"], "status": v["corpo"].get("status") if isinstance(v["corpo"], dict) else None,
                             "erro": (v["corpo"].get("erro") or v["corpo"].get("detail")) if isinstance(v["corpo"], dict) else None} for k, v in extracoes.items()},
        "documentos": documentos_estado,
    }

    decisao = (((prop_a.get("veredito") or {}).get("financial") or {}).get("decisao") or {})
    veredito_info = {"radar": veredito, "aceitavel": esperado["veredito_aceitavel"], "falha_critica": veredito == esperado["veredito_falha_critica"],
                     "recomendacao": {k: (mask(v) if isinstance(v, str) else v) for k, v in (decisao.get("recomendacao") or {}).items()},
                     "avaliacao_financeira": (decisao.get("avaliacao_financeira") or {}).get("status"),
                     "fundamentos_por_tipo": {t: sum(1 for f in decisao.get("fundamentos") or [] if f.get("tipo") == t) for t in sorted({f.get("tipo") for f in decisao.get("fundamentos") or []})},
                     "summary": mask((prop_a.get("veredito") or {}).get("summary")), "pendencias": [mask(p) for p in (prop_a.get("veredito") or {}).get("pending_items") or []][:12],
                     "evidencias_do_veredito": evidencias_view(prop_a.get("veredito_evidencias") or [], vers_a)[:10]}

    modo = "IA_REAL" if ia_disponivel else "LINHA_DE_BASE_SEM_IA"
    # Critérios de aprovação da LINHA DE BASE (sem IA)
    linha_base = None
    if not ia_disponivel:
        linha_base = {
            "nenhuma_chamada_paga": sem_custo["llm_runs_com_tokens_ou_custo"] == 0 and (sem_custo["chamadas_ao_provider_no_log"] in (0, None)),
            "indisponibilidade_informada": analise_a.get("status") == "falha" and st.get("codigo") == "IA_INDISPONIVEL" and analise_a.get("llm_usada") is False,
            "financeiro_independente_da_ia": financeiro["custo_total"] is not None and financeiro["resultado_liquido"] is not None,
            "preco_maximo_sem_ia": financeiro["preco_maximo"] is not None,
            "isolamento": isolamento["ok"],
            "privacidade_registros_e_log": (not privacidade["cpf_em_llm_runs_ou_registro_de_analise"]) and privacidade["cpf_no_log_do_backend"] in (False, None) and privacidade["segredo_no_log"] in (False, None),
            "ia_sem_pontuacao_indevida": ia["pontuacao"] == 0,
            "extracao_sem_5xx": all(v["http"] < 500 for v in extracoes.values()),
        }
        linha_base["aprovada"] = all(linha_base.values())

    relatorio = {
        "caso": gab["caso"], "pergunta": gab["pergunta_do_investidor"], "executado_em": stamp, "modo": modo,
        "api": args.api, "imovel_A": a["id"], "imovel_B": b["id"],
        "resposta_ao_investidor": {
            "esperado": esperado["decisao"],
            "o_radar_responde": "SIM" if financeiro["criterios"]["Q5_recomendacao_clara_de_nao_comprar"]["ok"] and financeiro["criterios"]["Q4_compara_lance_com_preco_maximo"]["ok"] else "NAO",
        },
        "linha_de_base": linha_base, "disponibilidade_ia": disponibilidade, "financeiro": financeiro, "veredito": veredito_info,
        "ia": ia, "evidencias_A": evidencias_view(ev_analise_a, vers_a), "checklist": checklist,
        "privacidade": privacidade, "isolamento": isolamento, "custo_e_chamadas": sem_custo, "llm_runs": llm_runs,
        "tempos": {"total_ms": round((time.perf_counter() - t0) * 1000), "analisar_A_ms": dur_a, "etapas": api.timings},
        "erros": erros,
    }
    (out_dir / "relatorio.json").write_text(json.dumps(relatorio, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    (out_dir / "relatorio.md").write_text(markdown(relatorio), encoding="utf-8")
    print(f"RELATORIO={out_dir}")
    print(f"MODO={modo} LINHA_DE_BASE_APROVADA={linha_base.get('aprovada') if linha_base else 'n/a'} RESPONDE_INVESTIDOR={relatorio['resposta_ao_investidor']['o_radar_responde']}")
    return 0


def brl(v: Any) -> str:
    v = num(v)
    return "—" if v is None else f"R$ {v:,.0f}".replace(",", ".")


def pct(v: Any) -> str:
    v = num(v)
    return "—" if v is None else f"{v * 100:.1f}%"


def sim(v: Any) -> str:
    return {True: "SIM", False: "NÃO", None: "n/a"}.get(v, str(v))


def markdown(r: dict[str, Any]) -> str:
    f, ia, iso, pv = r["financeiro"], r["ia"], r["isolamento"], r["privacidade"]
    L = [f"# Valor de negócio — {r['caso']}", "", f"Executado em `{r['executado_em']}` · modo **{r['modo']}** · imóveis A={r['imovel_A']} B={r['imovel_B']}", "",
         f"**Pergunta:** {r['pergunta']}", "", f"**Esperado:** {r['resposta_ao_investidor']['esperado']}  ",
         f"**O Radar responde à pergunta?** **{r['resposta_ao_investidor']['o_radar_responde']}**", ""]
    if r["linha_de_base"]:
        L += ["## Linha de base (sem IA)", "", "| Critério | Resultado |", "|---|---|"]
        L += [f"| {k} | {sim(v)} |" for k, v in r["linha_de_base"].items()]
        L += [""]
    d = r["disponibilidade_ia"]
    L += ["## Disponibilidade da IA", "", f"- Análise: `{d['status_analise']}` · código `{d['codigo']}` · agentes OK {d['agentes_ok']}/{d['agentes_total']} · llm_usada={d['llm_usada']}",
          f"- Mensagem: {d['mensagem']}", f"- Extração: {json.dumps(d['extracao'], ensure_ascii=False)}", f"- Documentos (versão, estado, pronto): {json.dumps(d['documentos'], ensure_ascii=False)}", ""]
    L += ["## Financeiro (independente da IA)", "", "| Métrica | Radar | Referência |", "|---|---|---|",
          f"| Custo total no lance | {brl(f['custo_total'])} | {brl(f['referencia_custo_total'])} |",
          f"| Resultado líquido | {brl(f['resultado_liquido'])} | {brl(f['criterios']['Q2_identifica_prejuizo']['referencia'])} |",
          f"| Margem líquida | {pct(f['margem_liquida'])} | meta 20% |", f"| ROI da operação | {pct(f['roi_operacao'])} | — |",
          f"| Break-even (venda mínima) | {brl(f['break_even'])} | — |",
          f"| Preço máximo (margem 20%) | {brl(f['preco_maximo'])} (definitivo={f['preco_maximo_definitivo']}) | {brl(f['criterios']['Q1_calcula_preco_maximo']['referencia'])} |", "",
          "| Critério de qualidade | Atende? |", "|---|---|"]
    L += [f"| {k} | {sim(v.get('ok'))} |" for k, v in f["criterios"].items()]
    if f["pendencias"]:
        L += ["", "Pendências do financeiro: " + "; ".join(f["pendencias"][:6])]
    v = r["veredito"]
    L += ["", "## Veredito", "", f"- Radar: **{v['radar']}** · aceitáveis: {', '.join(v['aceitavel'])} · falha crítica (FAVORAVEL): {sim(v['falha_critica'])}",
          f"- Recomendação: **{(v.get('recomendacao') or {}).get('codigo', '—')}** — {(v.get('recomendacao') or {}).get('texto', '—')}",
          f"- Avaliação financeira: {v.get('avaliacao_financeira') or '—'} · fundamentos por tipo: {json.dumps(v.get('fundamentos_por_tipo') or {}, ensure_ascii=False)}",
          f"- Resumo: {v['summary']}"]
    L += [f"- Pendência: {p}" for p in v["pendencias"][:6]]
    L += ["", "## Leitura dos documentos pela IA", "", f"- IA disponível: {sim(ia['ia_disponivel'])} · afirmações avaliadas: {ia['afirmacoes_avaliadas']}",
          f"- Pontuação ponderada: **{ia['pontuacao']}/{ia['pontuacao_maxima']}** (recall {pct(ia['recall_ponderado'])})",
          f"- Críticos com evidência — penhora (F2): {sim(ia['criticos_encontrados']['F2'])}, indisponibilidade (F3): {sim(ia['criticos_encontrados']['F3'])}, ocupação (F4): {sim(ia['criticos_encontrados']['F4'])}",
          f"- Condomínio/IPTU: afirmou 'não consta' = {sim(ia['ausencias_condominio_iptu']['afirmou_nao_consta'])}; inventou valor = {sim(ia['ausencias_condominio_iptu']['inventou_valor'])}",
          f"- Citações válidas: {pct(ia['taxa_citacao_valida']) if ia['taxa_citacao_valida'] is not None else '—'}", "",
          "| Fato | Peso | Situação | Pontos |", "|---|---|---|---|"]
    L += [f"| {x['id']} {x['fato']} | {x['peso']} | {x['status']} | {x['pontos']} |" for x in ia["fatos"]]
    L += ["", "| Armadilha | Ocorrências |", "|---|---|"] + [f"| {k} | {n} |" for k, n in ia["armadilhas_por_tipo"].items()]
    for a in ia["armadilhas"][:15]:
        L.append(f"- {a['id']} ({a['origem']}): {a['descricao']} — “{a['trecho'][:160]}”")
    L += ["", "## Evidências do imóvel A (análise)", ""]
    if r["evidencias_A"]:
        L += ["| # | Documento | Página | Seção | Fato | Trecho literal |", "|---|---|---|---|---|---|"]
        L += [f"| {e['id']} | {e['documento'] or '—'} | {e['pagina'] or '—'} | {e['secao'] or '—'} | {e['fato'][:90]} | {(e['trecho_literal'] or '—')[:90]} |" for e in r["evidencias_A"][:20]]
    else:
        L.append("Nenhuma evidência gerada pela análise.")
    c = r["checklist"]
    L += ["", "## Checklist", "", f"- Itens: {c['itens']} · por estado: {json.dumps(c['por_estado'], ensure_ascii=False)}",
          f"- Fora de PENDENTE: {len(c['fora_de_pendente'])} (com evidência: {sum(1 for i in c['fora_de_pendente'] if i['com_evidencia'])})"]
    L += ["", "## Privacidade", "", f"- CPF em llm_runs/registro da análise: {sim(pv['cpf_em_llm_runs_ou_registro_de_analise'])}",
          f"- CPF no log do backend (trecho desta execução): {sim(pv['cpf_no_log_do_backend'])} · segredo no log: {sim(pv['segredo_no_log'])} · log verificado: {sim(pv['log_verificado'])}",
          f"- CPF no trecho literal das evidências: {sim(pv['cpf_em_trecho_de_evidencia'])} — {pv['nota_trecho']}"]
    L += ["", "## Isolamento A × B", "", f"- **Resultado: {sim(iso['ok'])}** · chunks mapeados: {iso['chunks_mapeados_no_banco']} · banco: {iso['db']}",
          f"- Chunks do A vindos de outro imóvel: {iso['chunks_recuperados_A_de_outro_imovel'] or 'nenhum'}; do B: {iso['chunks_recuperados_B_de_outro_imovel'] or 'nenhum'}",
          f"- Evidências do B apontando para o A: {iso['evidencias_B_apontam_para_versao_do_A'] or 'nenhuma'} · texto do A no B: {sim(iso['texto_do_caso_A_em_evidencias_B'])}",
          f"- Extração cruzada (B lendo versão do A): HTTP {iso['extracao_cruzada_http']} · leitura cruzada de evidência: HTTP {iso['leitura_cruzada_evidencia_http']}"]
    s = r["custo_e_chamadas"]
    custo = sum((x["custo_usd"] or 0) for x in r["llm_runs"])
    L += ["", "## Custo, chamadas e tempo", "", f"- llm_runs: {len(r['llm_runs'])} (status {', '.join(s['status_llm_runs']) or '—'}) · com tokens/custo: {s['llm_runs_com_tokens_ou_custo']} · custo registrado: US$ {custo:.4f}",
          f"- Chamadas ao provider no log: {s['chamadas_ao_provider_no_log']} · gasto do mês (monitoramento): {s['gasto_mes_monitoramento']}",
          f"- Tempo total do roteiro: {r['tempos']['total_ms'] / 1000:.1f} s · /analisar do A: {r['tempos']['analisar_A_ms'] / 1000:.1f} s"]
    if r["llm_runs"]:
        L += ["", "| Imóvel | Agente | Status | Tokens (in/out) | Custo US$ | ms |", "|---|---|---|---|---|---|"]
        L += [f"| {x['imovel']} | {x['agente']} | {x['status']} | {x['tokens_entrada']}/{x['tokens_saida']} | {x['custo_usd'] if x['custo_usd'] is not None else '—'} | {x['duracao_ms'] or '—'} |" for x in r["llm_runs"]]
    L += ["", "> Pontuação: fato só conta com evidência ligada a trecho do documento do próprio imóvel que contenha os termos do fato. Heurísticas de alucinação exigem revisão humana."]
    return "\n".join(L) + "\n"


if __name__ == "__main__":
    sys.exit(main())
