# Pós-arrematação

**Status: implementado**, ativado sob demanda por imóvel.

## Objetivo
Acompanhar o que acontece depois da arrematação: etapas, custos previstos e realizados, ocupante e contatos, consultorias de desocupação, minutas de notificação extrajudicial.

## Funcionalidades
- Ativação idempotente do fluxo; atualização de estado, modalidade e orçamento.
- **16 etapas** configuráveis (CRUD).
- Custos pós-arrematação (previsto, realizado, pago).
- Ocupante e contatos, com tentativas de contato **append-only**.
- Consultorias e propostas (comparação de valor e escopo, com escopo incluído e excluído explícitos).
- Minutas de notificação extrajudicial **versionadas** (append-only); registro de envio e recebimento com evidência. A minuta é rascunho para advogado, não peça pronta.

## Endpoints (`/api/imoveis/{id}/pos-arrematacao`, sem JWT)
`GET ""`, `POST /ativar`, `PATCH ""`; `/etapas`, `/custos`, `/contatos` (+ `/{cid}/tentativas`), `/consultorias` (+ `/{cid}/propostas`), `/notificacoes` (+ `/{did}`, `/{did}/versoes`), com POST, PATCH e DELETE onde aplicável.

## Telas
Seção "Pós-arrematação" do imóvel (frontend: serviço `postAuction`).

## Regras
Proibida autotutela; negociação voluntária, documentada e condicionada; custos entram na análise financeira sem dupla contagem.

## Código e especificação
`main.py`, `models.py`. Spec: [MODULO-POS-ARREMATACAO](../specs/MODULO-POS-ARREMATACAO.md). Relatório de validação arquivado: [VALIDACAO-POS-ARREMATACAO](../../99-archive/reports/VALIDACAO-POS-ARREMATACAO.md).
