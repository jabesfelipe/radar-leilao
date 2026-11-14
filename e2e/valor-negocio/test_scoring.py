"""Autoteste da PONTUAÇÃO do valor_negocio.py (sem API, sem banco, sem custo).

Garante as regras antes do teste pago:
  - fato sem evidência (ou com evidência que não o contém) vale ZERO;
  - fato com evidência ligada a trecho que contém os termos pontua o peso;
  - armadilhas T1..T6 são detectadas;
  - mensagens de "IA indisponível" não contam como afirmação.
Rodar: ~/radar-venv/bin/python -m pytest -q e2e/valor-negocio/test_scoring.py
"""
import json
from pathlib import Path

import valor_negocio as vn

GAB = json.loads((Path(__file__).resolve().parent.parent / "fixtures" / "caso-01" / "gabarito.json").read_text(encoding="utf-8"))
CNJ = {"0001234-56.2020.5.02.0001", "0009876-54.2021.8.26.0100"}
CHUNKS = {
    1: {"content": "AV.3/99.901 PENHORA nos autos da reclamação trabalhista nº 0001234-56.2020.5.02.0001, débito de R$ 37.500,00.", "page": 1, "section": "AV.3"},
    2: {"content": "AV.4/99.901 INDISPONIBILIDADE de bens do proprietário decretada pela CNIB.", "page": 1, "section": "AV.4"},
    3: {"content": "3. SITUAÇÃO DO IMÓVEL: o imóvel encontra-se OCUPADO. A desocupação é de responsabilidade do arrematante.", "page": 1, "section": "3"},
    4: {"content": "6. COMISSÃO DO LEILOEIRO: 5% sobre o valor do arremate.", "page": 1, "section": "6"},
}


def ev(i, fact, chunk_id=None):
    return {"id": i, "fact": fact, "chunk_id": chunk_id, "document_version_id": 1 if chunk_id else None}


def avaliar(evs, checklist=None, extras=None):
    return vn.avaliar_ia(evs, checklist or [], CHUNKS, GAB, True, CNJ, extras or [])


def test_sem_afirmacoes_pontua_zero():
    r = avaliar([])
    assert r["pontuacao"] == 0 and r["afirmacoes_avaliadas"] == 0


def test_mensagem_de_ia_indisponivel_nao_conta():
    r = avaliar([ev(1, "LLM não configurada; análise deste domínio aguarda OPENAI_API_KEY")])
    assert r["afirmacoes_avaliadas"] == 0 and r["pontuacao"] == 0


def test_fato_com_evidencia_que_sustenta_pontua_o_peso():
    r = avaliar([ev(1, "Há penhora trabalhista averbada (AV.3) no valor de R$ 37.500", 1),
                 ev(2, "Indisponibilidade de bens averbada pela CNIB (AV.4)", 2),
                 ev(3, "O imóvel está ocupado e a desocupação cabe ao arrematante", 3)])
    assert r["criticos_encontrados"] == {"F2": True, "F3": True, "F4": True}
    assert r["pontuacao"] == 9
    assert r["armadilhas_por_tipo"]["T6"] == 0


def test_fato_sem_evidencia_vale_zero():
    r = avaliar([ev(1, "Há penhora trabalhista averbada na matrícula")])        # sem chunk
    f2 = next(f for f in r["fatos"] if f["id"] == "F2")
    assert f2["status"] == "MENCIONADO_SEM_EVIDENCIA" and f2["pontos"] == 0 and r["pontuacao"] == 0


def test_evidencia_que_nao_contem_o_fato_vale_zero_e_marca_citacao_fraca():
    r = avaliar([ev(1, "Há penhora trabalhista averbada no imóvel", 4)])        # chunk da comissão
    assert next(f for f in r["fatos"] if f["id"] == "F2")["pontos"] == 0
    assert r["armadilhas_por_tipo"]["T6"] == 1


def test_item_resolvido_pelo_motor_deterministico_nao_conta_como_afirmacao_da_ia():
    r = avaliar([], checklist=[{"canonical_key": "LANCE_MENOR_50_AVALIACAO", "state": "NAO_IDENTIFICADO",
                                "answer": "Não. 2º leilão por R$ 240.000,00 sobre avaliação de R$ 400.000,00 = 60,0%.",
                                "interpretation": "Resolvido automaticamente a partir dos dados cadastrados (cálculo determinístico)."}])
    assert r["afirmacoes_avaliadas"] == 0 and r["pontuacao"] == 0


def test_resposta_do_checklist_sem_evidencia_nao_pontua():
    r = avaliar([], checklist=[{"canonical_key": "x", "state": "RISCO_IDENTIFICADO", "answer": "imóvel ocupado, desocupação pelo arrematante"}])
    assert r["pontuacao"] == 0 and next(f for f in r["fatos"] if f["id"] == "F4")["status"] == "MENCIONADO_SEM_EVIDENCIA"


def test_armadilhas_t1_a_t5():
    r = avaliar([ev(1, "Débito de condomínio de R$ 12.300 conforme edital"),
                 ev(2, "A matrícula está livre de ônus"),
                 ev(3, "O edital permite financiamento e uso de FGTS"),
                 ev(4, "Existe também o processo 1111111-11.2019.8.26.0001"),
                 ev(5, "O imóvel está desocupado")])
    t = r["armadilhas_por_tipo"]
    assert (t["T1"], t["T2"], t["T3"], t["T4"], t["T5"]) == (1, 1, 1, 1, 1)


def test_valor_manual_informado_pelo_investidor_nao_e_t1():
    r = avaliar([ev(1, "Débito de condomínio de R$ 21.600 informado no cadastro")])
    assert r["armadilhas_por_tipo"]["T1"] == 0


def test_negacoes_corretas_nao_disparam_armadilhas():
    r = avaliar([ev(1, "O edital não permite financiamento nem FGTS"),
                 ev(2, "Valores de condomínio e IPTU não constam do edital; apurar")])
    assert r["armadilhas_por_tipo"]["T3"] == 0
    assert r["ausencias_condominio_iptu"]["afirmou_nao_consta"] is True
    assert r["ausencias_condominio_iptu"]["inventou_valor"] is False


def test_mask_nunca_deixa_cpf_no_relatorio():
    assert "111.222.333-96" not in vn.mask("CPF 111.222.333-96") and "[CPF]" in vn.mask("CPF 11122233396")
