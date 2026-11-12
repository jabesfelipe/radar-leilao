# Roadmap

> Consolidado a partir dos itens **planejados ou abertos** registrados na documentação e no código. Não há datas
> comprometidas. Os roadmaps e backlogs antigos (`ROADMAP-MASTER`, `ROADMAP-EXECUTION`, `ROADMAP-PLATAFORMA-COMPLETA`,
> `FEATURE-BACKLOG`, `EVOLUTION-BACKLOG`, etc.) estão em [99-archive/planning](../99-archive/planning/) e podem conter itens já entregues.

## Planejado (aceito como direção)

| Item | Origem | Observação |
|---|---|---|
| Cenários OTIMISTA e PESSIMISTA no motor financeiro | `finance.py` (apenas BASE) | pendente |
| TIR, VPL, fluxo descontado e grid de sensibilidade | MATRIZ-CUSTOS | pendente |
| Parametrização fiscal por jurisdição, ato, base, vigência e fonte | MATRIZ-CUSTOS | exige ADR |
| Modalidade LICITACAO (regras em aberto) | `modality_rules.py` | em aberto |
| Autenticação nas rotas legadas (≈ 148 sem credencial) | auditoria de segurança | antes de qualquer acesso público |
| TLS e domínio | [deployment.md](../04-operations/deployment.md#6-referência-futura-domínio-e-tls-não-existe-hoje) | pendente |
| Backups agendados e cópia externa na VPS | [infrastructure.md](../04-operations/infrastructure.md#14-pendências) | pendente |
| Consulta automática a Registro de Imóveis e Prefeitura | SPEC-ADAPTADORES-CONSULTA-MUNICIPAL | sem cliente hoje |
| Curadoria da Central Jurídica | TODO-CENTRAL-JURIDICA | pendente (ver o TODO) |
| Desativação do `X-Admin-Token` | [operations.md](../04-operations/operations.md#3-desativação-controlada-do-x-admin-token-legado) | planejada |
| Correção do `bootstrap-vps.sh` (leitura de porta SSH) | [infrastructure.md](../04-operations/infrastructure.md#61-troubleshooting-sshd--t-com-awk-no-passo-do-firewall) | concluída no repositório; validação em servidor novo pendente |

## Em discussão (sem decisão)

Integração com portais de leilão, registro eletrônico, RTD e serviços de desocupação; teses tributárias e de ocupação onerosa.
Ver [01-business/evaluation-criteria.md](../01-business/evaluation-criteria.md#9-em-discussão-não-implementado-sem-decisão).

## Fora do escopo declarado

Leilão judicial como produto (V1); Knowledge Graph (camada evolutiva, fora do MVP).
