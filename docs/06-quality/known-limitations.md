# Limitações conhecidas

Lista consolidada do que o sistema **não faz** ou faz com restrição hoje. Cada item aponta para a fonte.

## Segurança e exposição
| Limitação | Fonte |
|---|---|
| 148 de 184 rotas sem credencial no backend; proteção por portão do proxy | [security.md](../03-architecture/security.md) |
| HTTP sem TLS; senha, JWT e cookie em texto claro | [infrastructure.md](../04-operations/infrastructure.md#12-segurança-e-limitações) |
| Não usar dados sensíveis no ambiente de testes | idem |
| JWT em `localStorage`; `X-Admin-Token` legado ainda aceito | [auth-users](../02-product/modules/auth-users.md) |

## Produto
| Limitação | Fonte |
|---|---|
| OCR desabilitado (`OCR_ENABLED=false`) | [documents-rag](../02-product/modules/documents-rag.md) |
| Sem `OPENAI_API_KEY`: agentes retornam `SEM_CHAVE` e embeddings ficam pendentes | [integrations.md](../03-architecture/integrations.md) |
| Financeiro: só cenário BASE; sem TIR, VPL nem sensibilidade; ITBI e registro não calculados | [financial-debts](../02-product/modules/financial-debts.md) |
| Sem parametrização fiscal por jurisdição, ato e vigência | [evaluation-criteria](../01-business/evaluation-criteria.md) |
| Registro de Imóveis e Prefeitura sem cliente; débitos manual-assistidos | [due-diligence](../02-product/modules/due-diligence.md) |
| Modalidade LICITACAO com regras em aberto | [opportunities-workflow](../02-product/modules/opportunities-workflow.md) |
| Comparáveis de mercado inseridos manualmente | [market-occupancy](../02-product/modules/market-occupancy.md) |
| Knowledge Graph e leilão judicial como produto fora do MVP | [roadmap](../02-product/roadmap.md) |
| Tela de Administração ainda exibe o campo `X-Admin-Token` | [administration](../02-product/modules/administration.md) |

## Operação
| Limitação | Fonte |
|---|---|
| Backups agendados e cópia externa não confirmados na VPS | [backup-restore](../04-operations/backup-restore.md) |
| Sem monitoramento externo nem alertas | [operations.md](../04-operations/operations.md) |
| Uma única VPS, sem redundância | [infrastructure.md](../04-operations/infrastructure.md) |
| Migrations destrutivas dependem de revisão humana; o pipeline não as detecta | [github-actions.md](../04-operations/github-actions.md#7-limites-conhecidos) |
| Rollback não desfaz schema; recusa quando as heads divergem | [deployment.md](../04-operations/deployment.md#4-rollback) |
| `bootstrap-vps.sh` abortava silenciosamente no passo do firewall (`sshd -T` + `awk`, rc 141); **corrigido no repositório**, coberto por teste, ainda não reexecutado em servidor real | [infrastructure.md §6.1](../04-operations/infrastructure.md#61-troubleshooting-sshd--t-com-awk-no-passo-do-firewall) |

## Divergências entre documentos e código (registradas, não corrigidas)
| Item | Observação |
|---|---|
| `COMPARAVEIS_SUFFICIENTES` | erro de grafia na chave canônica do código; preservada |
| `.github/workflows/release.yml` cita `GITHUB-ACTIONS-DEPLOY §8` | a seção não existia; criada no stub `docs/GITHUB-ACTIONS-DEPLOY.md` |
| Comentários de código citam documentos movidos | listados em [99-archive/README.md](../99-archive/README.md); atualizar quando o código for alterado |
| `database-maintenance.md` usa `-U postgres` | usuário real vem de `POSTGRES_USER` |
| `homologation-guide.md` com numeração repetida | registrado no banner do documento |
