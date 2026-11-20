# Auditoria da análise v6 (v1.0.12, imóvel de referência)

Auditoria somente leitura da primeira análise feita em produção depois da v1.0.12 (análise v6, 5 agentes, veredito
INCONCLUSIVO, checklist de 27 itens), confrontando o resultado com a matrícula e as condições da venda armazenadas. Nenhum
dado de produção foi alterado e nenhuma análise nova foi rodada. Nomes, números e endereços do imóvel real não constam
deste documento; os testes usam uma matrícula fictícia com o mesmo layout (`tests/test_auditoria_v6.py`).

## Documentos e agentes

- Documentos: matrícula (PDF digitalizado, OCR, 15 trechos, 5 atos lidos em sequência: Av-1, R-2, R-3, Av-4, Av-5) e
  condições da venda (texto, 1 trecho).
- Agentes: documental, jurídico, financeiro, mercado e checklist; os 5 concluíram, sem erro de parsing ou persistência.
  Os 4 primeiros recebem 8 trechos recuperados (7 da matrícula + 1 das condições); o checklist recebe 15. A leitura
  determinística da matrícula (cadeia registral) usa todos os trechos e gerou 16 evidências; nada produzido ficou fora do dossiê.
- Risco que fica: o OCR leu a página em colunas, e parte do R-3 (fiança e "alienou fiduciariamente em favor de") aparece
  depois do Av-4. A cadeia registral ainda identifica a alienação e o credor; a tabela de titularidade avisa quando um
  rótulo aparece num ato que não é contrato.

## Achados e classificação

| Ponto | Situação na v6 | Classificação | Correção |
|---|---|---|---|
| IPTU | Pendente; município identificado; portal exige CPF/CNPJ do proprietário, sem API | DEPENDE DE DADO EXTERNO / FUNCIONA, MAS NÃO ESTÁ VISÍVEL | Linha pendente aponta a consulta assistida; orientação mostra o titular pela matrícula |
| Condomínio | Estimativa não calculada: sem valor mensal (sem comparáveis, padrão do Admin vazio); só rodava por ação do usuário | DEPENDE DE DADO EXTERNO + DEFEITO DE INTEGRAÇÃO | Roda automaticamente (sem gravar) quando o valor mensal é conhecido; linha pendente mostra o período e o que falta |
| Titularidade | Cadastro da matrícula gravado na 1ª análise com a construtora (proprietária original) como titular; telas de Matrícula e Due diligence mostravam esse nome | DEFEITO DE INTEGRAÇÃO | Titular exibido pela cadeia registral (consolidação, Av-5); cadastro preservado, com aviso; tabela de papéis |
| Reforma | Reserva de R$ 100/m² já entrava no custo total, mas aparecia como "não vistoriado"; item 21 dizia "sem estimativa" | FUNCIONA, MAS NÃO ESTÁ VISÍVEL | "Reforma estimada: R$ X — premissa padrão do Radar; confiança baixa"; item 21 cita a premissa e segue pendente |
| Vaga (item 16) | Inconclusivo, embora a matrícula descreva "direito de uso exclusivo ... referente a VAGA" | DEFEITO DE EXTRAÇÃO | Descrição anterior à palavra "vaga" lida: vinculada, sem matrícula própria |
| Quitação (item 04) | Pendente sem usar prazo (360 meses) e 1ª prestação do R-3 | INFORMAÇÃO DISPONÍVEL NÃO APRESENTADA | Teto calculado (parcelas vencidas até a consolidação); continua pendente |
| Privacidade | CPF do comprador lido pelo OCR com uma letra escapava do mascaramento | DEFEITO (privacidade) | Mascaramento de CPF rotulado aceita letras de OCR |

## Checklist jurídico

| Item | Status v6 | Evidência na matrícula / condições | Problema | Status correto |
|---|---|---|---|---|
| 01 Intimação pessoal | Inconclusivo | Av-5: "Certidão de Não Pagamento Pós Edital"; diligências não constam | — | Inconclusivo |
| 02 Intimação por edital | Confirmado | Av-5 (mesmo trecho) | — | Confirmado |
| 03 Notificação dos leilões | Pendente | Não consta (normalmente fora da matrícula) | — | Pendente |
| 04 Mais de 80% quitado | Pendente | R-3: dívida, prazo de 360 meses, 1ª prestação | Prazo não usado | Pendente, com teto de cerca de 26% |
| 05 Garantia de terceiro | Sem restrição identificada | R-3: mútuo da própria aquisição; construtora como fiadora (garantia pessoal) | — | Sem restrição identificada |
| 07 Ação contra o leilão | Pendente | Nenhuma averbação; ações não averbadas ficam fora | — | Pendente |
| 08 Leilões negativos | Inconclusivo | Nenhuma averbação; vendedor declara "Em tratamento" | — | Inconclusivo |
| 09 Contrato e consolidação | Confirmado | R-3 e Av-5, trechos vinculados | — | Confirmado |
| 10 Penhora/indisponibilidade | Sem restrição identificada | 5 atos em sequência, nenhum gravame | — | Sem restrição identificada |
| 12 Locação registrada | Sem restrição identificada | Nenhum registro de locação | — | Sem restrição identificada |
| 14 Evicção | Inconclusivo | Condições da venda (997 caracteres) não tratam de evicção | — | Inconclusivo (depende do documento completo) |
| 15 IPTU e condomínio | Confirmado | Condições: condomínio até 10% (Caixa paga o excedente); tributos abaixo de 10% (acima, a Caixa paga tudo) | — | Confirmado |
| 16 Vaga com matrícula própria | Inconclusivo | Abertura: direito de uso exclusivo de área descoberta referente à vaga | Leitura só depois da palavra | Respondido: não, vinculada à unidade |

## Consistência entre módulos

- Financeiro, inteligência de mercado, veredito e item 15 usam a mesma composição (`viability.debt_exposure` + regras da
  venda). Com a correção, a estimativa condominial automática também passa por ela; não há segundo cálculo.
- O custo total atual difere do registrado no veredito v6 (R$ 5.000,00 a mais) porque a ocupação foi registrada depois da
  análise e a reserva de desocupação passou a valer: o veredito é um retrato da análise e se alinha na próxima.

## Fora do escopo

- Consulta automática de IPTU: os portais exigem CPF/CNPJ do proprietário, login ou verificação de navegador.
- Autorização por imóvel (risco conhecido desde a v1.0.12).
- Correção do cadastro da matrícula gravado em produção: a tela passa a mostrar o titular pela matrícula; o registro antigo
  pode ser editado pelo usuário.
