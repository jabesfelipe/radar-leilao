# 02 — Produto

Mapa de módulos do Radar Leilão, com status verificado no código. Status usados: **implementado**, **parcial**, **planejado**, **descontinuado**.

## Módulos

| Módulo | Status | Telas principais | Documento |
|---|---|---|---|
| Dashboard e hubs | implementado | `/dashboard`, hubs | [dashboard-hubs](modules/dashboard-hubs.md) |
| Oportunidades e workflow (F0-F13) | implementado | `/oportunidades` | [opportunities-workflow](modules/opportunities-workflow.md) |
| Imóveis e cadastro | implementado | `/imoveis`, `/imoveis/{id}` | [properties](modules/properties.md) |
| Documentos e RAG | implementado (OCR off, embeddings dependem de chave) | seção Documentos | [documents-rag](modules/documents-rag.md) |
| Jurídico e Central Jurídica | implementado (Registro/Prefeitura sem cliente) | `/juridico` | [legal](modules/legal.md) |
| Financeiro e Débitos | implementado (cenário BASE) | `/financeiro` | [financial-debts](modules/financial-debts.md) |
| Mercado e Ocupação | implementado | `/mercado`, `/ocupacao` | [market-occupancy](modules/market-occupancy.md) |
| Checklist, riscos, veredito, análise | implementado (IA exige chave) | `/checklist`, `/riscos`, `/veredito` | [checklist-risks-verdict](modules/checklist-risks-verdict.md) |
| Due diligence | parcial | seção Due Diligence | [due-diligence](modules/due-diligence.md) |
| Pós-arrematação | implementado | seção Pós-arrematação | [post-auction](modules/post-auction.md) |
| Leiloeiros | implementado | `/leiloeiros` | [auctioneers](modules/auctioneers.md) |
| Administração | implementado | `/administracao` | [administration](modules/administration.md) |
| Autenticação e usuários | implementado (rotas legadas sem JWT) | LoginPage | [auth-users](modules/auth-users.md) |

Nenhum módulo está descontinuado. O módulo de Knowledge Graph da especificação original foi declarado como camada evolutiva fora do MVP.

## Outros documentos

- [roadmap.md](roadmap.md): o que está planejado.
- [specs/](specs/): especificações de domínio de produto (matrizes, central jurídica, due diligence, pós-arrematação, workflow ponta a ponta).

## Estado das especificações de produto

| Especificação | Situação |
|---|---|
| [CENTRAL-JURIDICA](specs/CENTRAL-JURIDICA.md) | válida |
| [DUE-DILIGENCE](specs/DUE-DILIGENCE.md) | válida |
| [MODULO-POS-ARREMATACAO](specs/MODULO-POS-ARREMATACAO.md) | válida |
| [MATRIZ-CHECKLIST-MODALIDADE](specs/MATRIZ-CHECKLIST-MODALIDADE.md) | **atualizar**: diz "nada implementado", mas a aplicabilidade existe |
| [MATRIZ-CURADORIA-JURIDICA](specs/MATRIZ-CURADORIA-JURIDICA.md) | válida como referência de curadoria |
| [MATRIZ-CUSTOS-TRIBUTOS-EMOLUMENTOS](specs/MATRIZ-CUSTOS-TRIBUTOS-EMOLUMENTOS.md) | válida; lacunas ainda abertas |
| [WORKFLOW-LEILAO-END-TO-END](specs/WORKFLOW-LEILAO-END-TO-END.md) | **atualizar**: diz "máquina de estados ainda não existe", mas o workflow foi implementado |
| [REVISAO-ANOTACOES-LEILAO](specs/REVISAO-ANOTACOES-LEILAO.md) | backlog / hipóteses (não é fato) |
| [TODO-CENTRAL-JURIDICA](specs/TODO-CENTRAL-JURIDICA.md) | pendências da curadoria |

Regra de leitura: onde uma spec afirmar "nada implementado" ou "proposto", confira primeiro o módulo correspondente acima.

## Nota sobre referências internas das specs

Os textos movidos para `specs/` foram preservados sem edição de conteúdo (exceto banners de status). Referências do tipo `docs/NOME.md` dentro deles
usam os caminhos anteriores; para achar o destino atual, consulte o inventário em [../README.md](../README.md#inventário-e-classificação-79-documentos).
