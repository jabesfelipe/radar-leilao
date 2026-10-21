# Andamento — Due Diligence Integrada do Radar Leilão

**Data do registro:** 21/10/2026  
**Repositório:** https://github.com/jabesfelipe/radar-leilao  
**Branch consultada:** `main`  
**Último commit verificado:** `0c8932e420ae80657df48a7c3c92068075406316`  
**Mensagem:** `feat(due-diligence): aba no dossiê, testes e documentação`

## 1. Objetivo solicitado

Implementar no dossiê do imóvel quatro frentes de due diligence:
1. Matrícula, titularidade, ônus e restrições registrais.
2. Processos judiciais relacionados ao imóvel, às partes e ao leilão.
3. Prefeitura, IPTU, valor venal e cadastro municipal.
4. Localização, Google Maps, Street View e avaliação do entorno.

A implementação deve reutilizar os módulos atuais, preservar o histórico, apresentar evidências e nunca tratar ausência de resultado como ausência de risco.

## 2. Commits verificados no GitHub

- `d02d8838b7b017084ea161b93178708f212468a5` — fundação backend das quatro frentes, migration `0016_due_diligence`.
- `0c8932e420ae80657df48a7c3c92068075406316` — aba no dossiê, testes e documentação.

O segundo commit é descendente do primeiro, que por sua vez sucede `e8f6fd7a2775fa090c46e08113d824ab8b1e0fc2` (correção do Pós-Arrematação).

## 3. O que o código/documentação registra como implementado

### Backend
- Orquestrador reuse-first para as quatro frentes.
- Modelo `DueDiligenceFront` para estado e resultados por imóvel/frente.
- Modelo `PropertyLocation` para coordenadas, fonte, precisão, links e checklist de localização.
- Migration `0016_due_diligence`.
- Endpoints consolidados de due diligence, localização, geocodificação, registro manual de débito municipal e revisão de frentes.
- Reutilização do domínio judicial existente, de `Debt` para IPTU e do histórico/eventos.
- Sinais determinísticos para Checklist/Riscos/Veredito, sem disparar nova análise LLM.
- Integração Google Maps com tratamento de chave ausente, resposta sem resultados e timeout.

### Frontend
- Aba **Due Diligence** no dossiê.
- Quatro cards com estados distintos: Matrícula/ônus, Processos, Prefeitura/IPTU e Localização.
- Checklist de localização.
- Links externos para Maps/Street View.
- Status da configuração das integrações.

### Documentação
- `docs/DUE-DILIGENCE.md` descreve arquitetura, endpoints, estados, configuração, limites e testes.
- O commit declara atualização de `PROJECT-STATUS` (§28) e `PROJECT-HISTORY`.

## 4. Testes registrados no commit/documentação

Os seguintes resultados estão registrados no commit, mas não foram reexecutados independentemente nesta sessão:
- Backend: **613 passed, 2 skipped**.
- Frontend: **132 passed**.
- TypeScript: `tsc --noEmit` sem erros.
- Migration head declarada: `0016`.
- O imóvel 633 é declarado intacto: 9 análises V1–V9 e nenhuma V10.

O commit não apresenta GitHub Actions check runs associados; isso não invalida os testes locais relatados, mas significa que esta verificação não confirma CI remoto.

## 5. Estado real das integrações externas

| Frente | Estado documentado | Limitação |
|---|---|---|
| Judicial/DataJud | Integração existente reutilizada | A cobertura depende dos campos e das modalidades disponíveis; busca por partes pode não estar disponível em todas as fontes. |
| Google Maps/geocoding | Cliente implementado e testado com mock HTTP | Requer `GOOGLE_MAPS_API_KEY` e faturamento/configuração válidos para chamadas reais. |
| RI Digital | Fluxo de importação manual preparado | Consulta automática não está comprovada; depende de integração/credenciais/autorização. |
| Prefeitura/IPTU | Cadastro manual rastreável preparado | Consulta automática não está comprovada; depende de API/credenciais/autorização do município. |
| Maps/Street View | Links externos disponíveis | Link externo não equivale a consulta automática ou inspeção atualizada do imóvel. |

Nenhuma consulta externa paga ou acesso real a RI Digital/Prefeitura é declarado como executado.

## 6. Pontos a validar localmente após o pull

Esta sessão não tem acesso ao terminal/clone local do usuário; portanto, não executou `git pull`, Docker, migrations nem testes na máquina local.

No ambiente do usuário, executar:
```bash
git status
git pull --ff-only origin main
git log -3 --oneline
./scripts/backup.sh
./scripts/restart.sh
./scripts/health.sh
```

Se houver alterações locais pendentes, revisar antes do pull; não descartar arquivos. Confirmar no log que `0c8932e` está presente. Em seguida, abrir o dossiê do imóvel 633 e validar a aba Due Diligence.

Checklist manual:
- [ ] A aba Due Diligence abre e apresenta os quatro cards.
- [ ] Sem credenciais, as fontes externas aparecem como não configuradas, sem simular sucesso.
- [ ] A localização pode ser registrada/editada e persiste após recarga.
- [ ] Links Maps/Street View abrem o endereço esperado.
- [ ] O checklist de localização é persistido.
- [ ] Débito municipal é registrado sem duplicar custo no Financeiro.
- [ ] A revisão das frentes aparece no Histórico.
- [ ] Falha de uma fonte não bloqueia as demais.
- [ ] O imóvel 633 preserva V1–V9, sem gerar V10.
- [ ] As migrations estão aplicadas e a saúde da aplicação está OK.

## 7. Pendências conhecidas

1. Configurar e testar uma chave real do Google Maps Platform, com limites de uso e faturamento controlados.
2. Confirmar as condições de contratação/acesso e implementar a integração real com RI Digital, caso exista API/serviço autorizado adequado.
3. Confirmar os serviços/API oficiais disponíveis para Curitiba e outros municípios e implementar a integração real quando autorizada.
4. Validar a experiência no navegador local e a persistência real depois do pull.
5. Confirmar que o documento `PROJECT-STATUS.md` reflete o estado atual: o cabeçalho existente consultado ainda contém texto antigo de status e precisa ser reconciliado com as tarefas recentes, preservando o histórico.

## 8. Critério de conclusão

A funcionalidade pode ser considerada **implementada em nível de fundação e interface**, segundo o código e os resultados documentados no commit. Não deve ser considerada completamente validada em ambiente local nem com todas as fontes externas operacionais até concluir as verificações da seção 6 e configurar/testar as integrações externas da seção 5.

## 9. Referências

- [Commit da fundação backend](https://github.com/jabesfelipe/radar-leilao/commit/d02d8838b7b017084ea161b93178708f212468a5)
- [Commit da interface, testes e documentação](https://github.com/jabesfelipe/radar-leilao/commit/0c8932e420ae80657df48a7c3c92068075406316)
- [Documento técnico Due Diligence](https://github.com/jabesfelipe/radar-leilao/blob/main/docs/DUE-DILIGENCE.md)
- [Auditoria do motor financeiro](https://github.com/jabesfelipe/radar-leilao/blob/main/docs/AUDITORIA-MOTOR-FINANCEIRO.md)
- [Validação do Pós-Arrematação](https://github.com/jabesfelipe/radar-leilao/blob/main/docs/VALIDACAO-POS-ARREMATACAO.md)
