# Radar Leilão — SPEC OFICIAL DE VIBE CODING

Status: APROVADA PARA CODIFICAÇÃO

Esta é a fonte única de implementação do MVP.

Stack: React + TypeScript; Python + FastAPI; PostgreSQL + pgvector; MinIO/local storage; MarkItDown + OCR; LangChain + LangGraph; RAG híbrido; LLM Gateway; Docker/WSL.

Princípios: imóvel é a entidade central; tudo relevante possui histórico; documentos originais são imutáveis; conclusões possuem evidências; LLM interpreta e código determinístico calcula; existe um único Checklist Mestre; reanálise é incremental; memória histórica via RAG não é treinamento; tudo visível é pt-BR; MVP local-first e simples.

Domínios: imóvel, leilão, documentos, matrícula, edital, jurídico, processos, débitos, financeiro, custos, reforma, mercado, comparáveis, ocupação, checklist, evidências, riscos, análises, veredito, histórico, conhecimento e eventos.

Documentos: Original -> MarkItDown/OCR -> Markdown -> chunks/metadata -> embeddings -> pgvector. Preservar original, hash, versão e mapeamento de página/seção.

Checklist Mestre: único, extensível, versionado, ativável/desativável, com origem como metadado. Estados: PENDENTE, EM_ANALISE, CONFIRMADO, RISCO_IDENTIFICADO, ATENCAO, NAO_IDENTIFICADO, NAO_APLICAVEL.

Financeiro: arrematação + comissão + ITBI + registro + condomínio + IPTU + reforma + desocupação + outros = custo total. Calcular desconto, margem, preço/m², aluguel, yield, ROI, prazo, preço máximo e cenários de forma determinística.

RAG: vector search + full text + metadata filtering + histórico/casos. PostgreSQL/pgvector no MVP.

LangChain: LLM, embeddings, retrievers, tools, prompts e parsers. LangGraph: orquestração, estado e reanálise incremental.

Eventos: DOCUMENTO_ADICIONADO, DOCUMENTO_ATUALIZADO, PROCESSO_ADICIONADO, PROCESSO_ATUALIZADO, DEBITO_ADICIONADO, DEBITO_ATUALIZADO, CUSTO_ADICIONADO, COMPARAVEL_ADICIONADO, DADO_IMOVEL_ATUALIZADO, OCUPACAO_ATUALIZADA, ANALISE_SOLICITADA.

Veredito: explicável; mostrar situação por domínio, riscos, pendências, impacto financeiro, evidências, mercado, custos, retorno, ocupação e alterações desde versão anterior. Não limitar a comprar/não comprar.

Frontend completo: Dashboard, Imóveis, Leilão, Documentos, Análise, Veredito, Checklist, Jurídico, Processos, Financeiro, Débitos, Custos, Reforma, Mercado, Comparáveis, Ocupação, Riscos e Histórico.

Ordem: 1 Fundação; 2 Imóvel/Leilão; 3 Documentos; 4 Evidências/Histórico; 5 Checklist; 6 Financeiro; 7 Mercado/Ocupação; 8 IA documental; 9 RAG/LangGraph; 10 Riscos/Veredito; 11 integração final.

Regras para o coding agent: ler esta SPEC; inspecionar código antes de criar; não criar outra SPEC; não recriar arquitetura; não inventar regras; não adicionar AWS/Kubernetes/microserviços sem necessidade; uma task por vez; testar e corrigir; manter pt-BR; preservar histórico; não substituir originais; não esconder regras críticas em prompts.

Critério de aceite: fluxo completo local para cadastrar imóvel/leilão, anexar edital/matrícula, versionar/normalizar/analisar documentos, registrar evidências, executar Checklist Mestre, cadastrar processos/débitos/custos/reforma/comparáveis/ocupação, calcular indicadores, usar RAG, reanalisar incrementalmente, gerar riscos/veredito e consultar histórico.

Fora do MVP: Kubernetes, ECS/EKS, RDS, AWS obrigatório, vector DB externo, Knowledge Graph dedicado, fine-tuning, treinamento próprio, dezenas de agentes, scraping/automação completa de portais externos, infraestrutura distribuída e multi-tenant avançado.

REGRA FINAL: não voltar para arquitetura. Agora é CODIFICAR.