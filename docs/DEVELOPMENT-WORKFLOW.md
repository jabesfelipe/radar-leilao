# Radar Leilão — Workflow de Desenvolvimento

## Objetivo

Manter o desenvolvimento incremental, auditável e econômico em tokens.

## Ciclo oficial

```
PROJECT-STATUS.md
      ↓
próxima TASK PENDENTE
      ↓
Kiro implementa
      ↓
commit
      ↓
"da pull"
      ↓
GitHub / compare
      ↓
auditoria do código
      ↓
🟢 aprovado
      ↓
PROJECT-STATUS.md atualizado
      ↓
commit/push documental
      ↓
próxima TASK
```

## Quando houver problema

```
commit do Kiro
      ↓
🔴 auditoria
      ↓
correção objetiva
      ↓
novo commit
      ↓
nova auditoria
      ↓
🟢 aprovação
```

Não avançar para a próxima TASK enquanto a anterior estiver pendente de correção.

## Responsabilidade do Kiro

- Implementar somente a TASK indicada.
- Ler a SPEC antes de codar.
- Respeitar contratos existentes.
- Não inventar regra de negócio.
- Não expandir escopo.
- Rodar testes/build quando aplicável.
- Criar commit com mensagem definida.

## Responsabilidade da revisão

- Validar o commit contra a TASK.
- Comparar com o estado aprovado anterior.
- Inspecionar código alterado.
- Conferir contratos.
- Conferir escopo negativo.
- Identificar overengineering.
- Corrigir quando necessário.
- Só então marcar a TASK como concluída.

## Regra de ouro

**Uma TASK por vez. Um commit rastreável por avanço. Uma aprovação antes da próxima TASK.**

Isso permite que o histórico do GitHub seja também o registro técnico da evolução do produto.


---

## Gate de validação financeira após a Task 4

Antes de encerrar uma tarefa que altere premissas ou cálculos financeiros:

1. Confirmar que os testes automatizados correspondentes foram executados e registrar seus resultados sem extrapolar o que cobrem.
2. Testar na UI premissas completas e incompletas.
3. Salvar e recarregar o imóvel para confirmar persistência.
4. Confirmar que custos materiais ausentes são listados como pendências e que o preço máximo fica marcado como provisório.
5. Confirmar que, com todas as premissas materiais preenchidas e válidas, o estado pode ser definitivo.
6. Registrar o resultado no `docs/PROJECT-STATUS.md` e atualizar esta referência quando o contrato mudar.

**Não declarar E2E concluído apenas com pytest, Vitest ou TypeScript.** Esses testes não substituem a validação manual de fluxo completo na interface.
