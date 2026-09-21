# Radar Leilão — Histórico de Implementação

Este documento registra a trajetória técnica do projeto e os commits que representam as etapas já executadas.

## Marco inicial

- `5e2872cb790299122697774931696f9b1266eadd` — docs: init
- `3f370691fb3f20d90e950ca18d293ad66afb6bf8` — docs: adiciona spec oficial do vibe coding do MVP
- `1333c2f43277c2c6be3e6aad3ca0247ade19af15` — docs: consolida arquitetura mestre completa para vibe coding
- `baebc3eb1f6ec297cabb2437786aa63d0ccf6d55` — docs: remove documentos antigos consolidados na arquitetura mestre

## Implementação do MVP

### Fundação e arquitetura

- `d984909c9354e4472c999e5820fb0871064f309d` — feat: implementa MVP do Radar Leilão em português
- `1be818451b38cf5b691f0fc0707a6e2610a40005` — feat: alinha arquitetura do Radar à SPEC oficial
- `db5e488b2bfe3906f42d285553e84a4438993acc` — feat: implementa primeira análise real com LLM, RAG e LangGraph
- `f7bad52fe9c6d5613f39a44cf90ac9941087dc0d` — fix: estabiliza RAG híbrido com isolamento e ranking normalizado
- `7218b87f0c8a4122c998c88c36cd9e9fec3d4db5` — feat: adiciona rastreabilidade e controle de custos LLM
- `f39fb619e0bb9c36bb5ecd5bb8c721ec4335b7a1` — fix: endurece segurança do fluxo LLM

### Domínio, documentos e análise

- `5261c6c84c3ee346d8e1e4974bc9342572820e3b` — feat: implementa Checklist Mestre versionado
- `df8c11ba7571714684c4582bfbc4a43ffa1eaf79` — feat: implementa motor financeiro determinístico
- `04333e888a432a57559a5853b33ebaa930a34067` — feat: implementa motor determinístico de mercado
- `5300ab6b35df859deca08d5a5724acacf6a9076f` — feat: adiciona cadastro de ocupação do imóvel
- `0fd36e1a8011aae819d539c91cd20f5d5fa90ea6` — feat: adiciona cadastro de processos jurídicos
- `d3b1d69c088359577ea5a3ca5f76d8872d3cbbcd` — feat: adiciona versionamento de documentos
- `ad81ad0f90f3a190b51b173aa81239a20dea8059` — feat: consolida custos e dividas do imovel
- `1fc9dba87d68d7c6649df2e55ca5f75a82219e70` — feat: adiciona cadastro de matricula e edital
- `080cdd8d1059ccfde1f70d9b23086c05c71c7635` — feat: consolida evidencias e vinculos
- `ad55db96b817e5858077d09eb675a492fc29105e` — feat: consolida pipeline documental para RAG
- `5672cbc08436b1365820723ed261ab2584266f0e` — feat: adiciona extracao documental estruturada
- `4f54f07a92ff58ddde214038504609b2e686c817` — fix: exige rastreabilidade na extracao documental

## Agents e orquestração

- `db12b25704f8deb29e5adbda933b4c16319b3411` — feat: normaliza evidencias documentais
- `95a28afeb84f55c0a6b2678e8191c7f1476f6f32` — feat: adiciona endpoint do Document Agent
- `32ca1957abbfe35ffa7a1752696c6fbc1c8beb58` — fix: ajusta rastreabilidade do Document Agent
- `060b6a6a89715695262df4dc5f99f18de82f68bf` — feat: adiciona Juridico Agent
- `5f7ee44826468ff87930db9c79a5cf96c8d5fe30` — feat: adiciona Financeiro Agent
- `f3b71965c6dd7e6e0ab7c54709c91088629d60b3` — feat: adiciona Mercado Agent
- `118dbf463f99aff3a2f558502eb9df0edb6f6514` — feat: adiciona Checklist Agent
- `3971ba926f96f82cb4763957c0fa7d8156cc18a3` — feat: consolida orquestracao com LangGraph
- `5d91b8e4bbfc2c5bab02c310151440c65b1476b7` — fix: separa consolidacao de risk e verdict no langgraph
- `d659aef262b428bf5f1d5320dd0aa56721e0ac5a` — feat: adiciona impact analyzer deterministico
- `3f87a76bce36f4cd123b8455328fa1d9be446356` — feat: implementa reanalise incremental
- `d416345516fe11c7c27a1684a4071d916433dfaf` — fix: limita checklist na reanalise incremental
- `b76c77311b60d082d169397cdab8bbf412a8d14a` — feat: adiciona consolidacao dos resultados dos agents
- `023bb2856fd67ce168b9137e18e3a506f8780f61` — feat: implementa risk engine deterministico
- `acc515f321a6f827ae32c10be98972940530fe08` — fix: remove regras de risco nao formalizadas
- `12b2914abe3fe672c4fed1b27f2da4d5b444aeb3` — feat: implementa verdict engine deterministico
- `37386bb47b246252ebdc0ba595b90b5d953c8910` — feat: implementa comparacao de historico de analises
- `f7d951ac3ebdcec98e4524e6d8152b9e124e2d40` — feat: adiciona memoria estruturada de casos
- `1c5f95ca9b287eb1487fc58a5f95117729dd4075` — feat: adiciona busca estruturada de memoria
- `e4e9f394c599df4661f96084ec2c8b16e185d113` — feat: adiciona embeddings na memoria de casos
- `e5572d3cfaa0123eaa1ad0dace196e9b400d2380` — feat: adiciona busca semantica da memoria
- `9636f93c61e10e2702176ef882f1894a54bf6550` — feat: adiciona busca hibrida da memoria
- `64b156ef60c662071709ef8970d2bc20f8f361da` — feat: adiciona evals basicos dos agents

## Frontend

- `e8f8a9a7172220c3ed90430c9a3aac34e1a1edf0` — feat: cria foundation do frontend
- `4d248c724ab53d4347bf5ffcddc2c7769b40f0ed` — fix: reforca responsividade do frontend
- `392f9b677f6bc73cb19c7769d32403d225e1b962` — feat: cria identidade visual e design system do radar
- `0c10233c0a8b379e22a39c40050e5377533aa435` — feat: implementa cadastro basico de imovel
- `d244a08e375e4b2c23f88e9acbeccd84fe12719b` — fix: remove enum artificial de tipo de imovel
- `c7c9ac51de790282bd65b32f3c94c4dc8eb0f43f` — feat: cria hub de detalhe do imovel
- `147e8bc5cd8e7a10dfcb95a6a95c12e05f101f08` — feat: implementa documentos no hub do imovel
- `1c330c430793bf2da50ed462ef16f34aff24da38` — feat: implementa matricula e edital no hub do imovel
- `a4f5d761167cccda07e233816af05cda449b0e73` — feat: implementa processos juridicos no hub do imovel
- `30f366678b9359238cdca08d5a5724acacf6a9076f` — feat: implementa financeiro no hub do imovel

## Correções que devem permanecer registradas

### Reanálise incremental

O primeiro commit da reanálise criava ChecklistExecution mesmo quando checklist não estava entre os domínios afetados. Isso foi corrigido no commit:

`d416345516fe11c7c27a1684a4071d916433dfaf`

Regra preservada: checklist só deve ser executado quando estiver efetivamente afetado.

### Risk Engine

O primeiro Risk Engine adicionou regras não formalizadas sobre custo financeiro e ausência de documentos. Essas regras foram removidas no commit:

`acc515f321a6f827ae32c10be98972940530fe08`

Regra preservada: Risk Engine não pode inventar regras de negócio.

### Cadastro de imóvel

O primeiro cadastro frontend criou enum artificial para tipo de imóvel. A correção:

`d244a08e375e4b2c23f88e9acbeccd84fe12719b`

Regra preservada: respeitar contrato real; não restringir artificialmente valores aceitos.

---

## Estado documental atual

A arquitetura mestre foi consolidada na SPEC oficial e os documentos antigos redundantes foram removidos do repositório. O objetivo é evitar múltiplas fontes de verdade.

Documentos centrais atuais:

- `SPEC-VIBE-CODING-RADAR-LEILAO.md`
- `docs/PROJECT-STATUS.md`
- `docs/PROJECT-HISTORY.md`

A partir de agora, alterações de andamento devem ser registradas principalmente em `PROJECT-STATUS.md`, enquanto `PROJECT-HISTORY.md` funciona como histórico de commits/marcos.
