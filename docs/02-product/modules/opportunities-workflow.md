# Oportunidades e workflow

**Status: implementado** (Ondas 1 e 2). A documentação antiga que diz "máquina de estados ainda não existe" ou "ADR proposto, nada implementado" está desatualizada.

## Objetivo
Conduzir um imóvel em leilão, da prospecção ao encerramento, por fases (F0 a F13) com regras de avanço, hard stops, decisão de comitê e invalidação por novos fatos.

## Funcionalidades
- Cadastro e listagem de oportunidades com filtros (município e outros).
- Máquina de estados: 14 fases, 9 estados de fase, 7 tipos de transição (AVANCO, RETROCESSO, REABERTURA, DESCARTE, ENCERRAMENTO, PERDA, DECISAO).
- Status da oportunidade: EM_PROSPECCAO, EM_ANALISE, EM_DECISAO, APROVADA, ADQUIRIDA, ENCERRADA, DESCARTADA, PERDIDA.
- Hard stops e pendências por fase; decisões de comitê (APROVADA, REPROVADA, ADIADA).
- Modalidade: classificação por evidência e correção manual; aplicabilidade do checklist por modalidade.
- Reavaliação e invalidação (por exemplo, edital atualizado reabre F1, F2, F3, F7 e F8).

## Fases
F0 Intake, F1 Triagem, F2 Documentos, F3 Jurídico-registral, F4 Fiscal-operacional, F5 Localização-inspeção, F6 Ocupação-posse, F7 Viabilidade financeira, F8 Comitê-decisão, F9 Lance-pagamento, F10 Transferência-registro, F11 Posse-regularização, F12 Exploração-saída, F13 Encerramento. F3 a F7 são paralelizáveis e convergem em F8; F8 para F9 exige decisão APROVADA; PERDA só a partir de F9.

## Regras
`workflow_rules.py` (`workflow-v1`) é declarativo; `workflow_engine.py` é puro (avalia, não grava); `modality_rules.py` (`modality-v1`, 5 modalidades, LICITACAO em aberto) cuida de modalidade e supressão de hard stops. Hard stops: ver [evaluation-criteria.md](../../01-business/evaluation-criteria.md#7-hard-stops-e-workflow).

## Endpoints (`/api/oportunidades`)
`GET /modalidades`; `GET ""` (lista); `POST ""` (cria; exige JWT e `analysis:write`); `GET /{id}`, `/{id}/estado`, `/transicoes`, `/hard-stops`, `/pendencias`, `/historico`, `/checklist-aplicavel`; `POST /{id}/transicao`, `/fase/estado`, `/reavaliar`, `/modalidade/classificar`, `/modalidade/corrigir`.

## Permissões
Leitura: qualquer usuário autenticado. Escrita: JWT com `analysis:write` (`authorized_writer`).

## Telas
`/oportunidades`; seção de fase em detalhes do imóvel.

## Dependências
Checklist, riscos, financeiro, due diligence e Central Jurídica alimentam os hard stops.

## Divergências
- `ADR-WORKFLOW-ARCHITECTURE` ainda traz "PROPOSTO"; atualizado por banner (ver [decisions](../../03-architecture/decisions/README.md)).
- As ondas 1 e 2 não criaram migration própria: reusam o schema das migrations 0018 e 0019.

## Código
`backend/app/workflow_rules.py`, `workflow_engine.py`, `modality_rules.py`, `routers/opportunities.py`; specs em [03-architecture/specs](../../03-architecture/specs/).
