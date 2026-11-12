# Due diligence

**Status: parcial.** Visão consolidada e revisão implementadas; consultas automáticas a Registro de Imóveis e Prefeitura **não existem** (sem cliente).

## Objetivo
Orquestrar a investigação do imóvel em 4 frentes e indicar a que item do checklist cada frente alimenta.

## Frentes
| Frente | Item de checklist alimentado | Observação |
|---|---|---|
| MATRICULA | CONSOLIDACAO_REGISTRADA | divergência edital × matrícula gera o hard stop `MATRICULA_DIVERGENTE` |
| JUDICIAL | ACAO_QUESTIONAMENTO | usa a Judicial API quando configurada |
| PREFEITURA | RESPONSABILIDADE_DEBITOS | débito municipal registrado manualmente |
| LOCALIZACAO | REGIAO_SERVICOS | geocodificação Google opcional |

Frentes sem credencial ficam `NAO_CONFIGURADO`; o fluxo continua por importação manual.

## Endpoints
`GET /api/imoveis/{id}/due-diligence` (somente leitura, não dispara consultas); `POST .../due-diligence/prefeitura/debito` (registro manual); `POST .../due-diligence/{frente}/revisar` (marca como revisada ou reabre, com anotação do responsável).

## Telas
Seção "Due Diligence" do imóvel.

## Regras
Reaproveita o agregado de débitos (`Debt`) e as entidades de matrícula e processos; não cria modelo concorrente.

## Código e especificação
`main.py` (rotas). Spec: [DUE-DILIGENCE](../specs/DUE-DILIGENCE.md); adaptadores municipais planejados: [SPEC-ADAPTADORES-CONSULTA-MUNICIPAL](../../03-architecture/specs/SPEC-ADAPTADORES-CONSULTA-MUNICIPAL.md).
