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
