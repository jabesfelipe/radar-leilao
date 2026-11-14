# Valor de negócio (caso sintético com gabarito)

Responde, com dados fictícios, à pergunta do investidor: **"vale a pena comprar este imóvel neste leilão?"**

- `valor_negocio.py`: cadastra o caso `fixtures/caso-01` (imóvel A) e um imóvel de controle (B) pela API real,
  envia os documentos, roda extração e `/analisar`, compara com `fixtures/caso-01/gabarito.json` e grava
  `results/valor-negocio/<data>/relatorio.{json,md}` (ignorado pelo Git).
- `test_scoring.py`: autoteste das regras de pontuação (sem API, sem custo).

Desde a v1.0.4 o relatório traz também a seção "Rastreabilidade" (origem e força de cada evidência, pergunta do checklist
usada como trecho, valor da afirmação ausente do documento citado), a situação de cada campo da extração estruturada e a
origem da resolução de cada item do checklist (vínculos lidos de `checklist_evidences`). O gabarito não muda.

Regras: fato só pontua com evidência ligada a trecho do documento do próprio imóvel que contenha os termos do fato;
menção sem evidência vale zero. Heurísticas de alucinação (T1–T6) exigem revisão humana. O relatório mascara CPF.

```bash
# no WSL, com o backend LOCAL rodando (nunca produção)
~/radar-venv/bin/python -m pytest -q e2e/valor-negocio/test_scoring.py
~/radar-venv/bin/python e2e/valor-negocio/valor_negocio.py --api http://127.0.0.1:8100 \
  --db postgresql://postgres@127.0.0.1:54329/radar_hom --log <stdout do backend>
```

O modo é detectado sozinho: sem chave da OpenAI roda a **linha de base** (prova que nada pago é chamado, que a
indisponibilidade é informada e que o financeiro funciona); com chave, avalia a leitura da IA. `--db` é usado só
para leitura (`llm_runs` e posse dos chunks); `--log` verifica CPF/segredos e chamadas ao provider no log.
