import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { VerdictSection } from './VerdictSection'

const verdict = {
  id: 3,
  property_id: 5,
  analysis_version: 2,
  overall: 'ATENCAO',
  summary: 'Imóvel com pendências relevantes a confirmar.',
  what_is_known: 'Documentação básica recebida.',
  what_is_unknown: 'Situação de ocupação não confirmada.',
  pending_items: ['Confirmar ocupação', 'Validar matrícula'],
  financial: {},
  risk_ids: [9, 10],
  evidence_ids: [21],
}

function response(body: unknown, ok = true, status = 200) {
  return Promise.resolve({ ok, status, json: () => Promise.resolve(body) }) as Promise<Response>
}

function detail(veredito: unknown, veredito_evidencias: unknown[] = []) {
  return response({ imovel: { id: 5 }, riscos: [], veredito, veredito_evidencias })
}

describe('VerdictSection', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
    globalThis.fetch = vi.fn()
  })

  it('exibe carregamento e depois estado vazio', async () => {
    vi.mocked(fetch).mockReturnValueOnce(detail(null))
    render(<VerdictSection propertyId={5} />)

    expect(screen.getByRole('status')).toHaveTextContent('Carregando veredito')
    expect(await screen.findByText('Veredito não disponível')).toBeInTheDocument()
  })

  it('exibe o veredito retornado pelo backend', async () => {
    vi.mocked(fetch).mockReturnValueOnce(detail(verdict))
    render(<VerdictSection propertyId={5} />)

    expect(await screen.findByText('VEREDITO CONSOLIDADO')).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Atenção' })).toBeInTheDocument()
    expect(screen.getByText('Imóvel com pendências relevantes a confirmar.')).toBeInTheDocument()
    expect(screen.getByText('Documentação básica recebida.')).toBeInTheDocument()
    expect(screen.getByText('Confirmar ocupação')).toBeInTheDocument()
    expect(screen.getByText('#9, #10')).toBeInTheDocument()
  })

  it('exibe evidências vinculadas de forma legível (documento/versão/página/fato)', async () => {
    const evidencias = [
      { id: 202, documento: 'EL00440226CPARE.pdf', document_type: 'EDITAL', version: 2, category: 'CHECKLIST', page: 8, fact: 'Responsabilidade por débitos descrita no edital.' },
      { id: 203, documento: '1555528765064.pdf', document_type: 'MATRICULA', version: 3, category: 'DOCUMENTAL' },
    ]
    vi.mocked(fetch).mockReturnValueOnce(detail(verdict, evidencias))
    render(<VerdictSection propertyId={5} />)

    expect(await screen.findByText('📄 EL00440226CPARE.pdf')).toBeInTheDocument()
    // documento, página e seção sempre visíveis (ausência dita explicitamente, nunca inventada)
    expect(screen.getByText('Checklist · versão 2 · Página 8 · Seção não informada')).toBeInTheDocument()
    expect(screen.getByText('Responsabilidade por débitos descrita no edital.')).toBeInTheDocument()
    // segunda evidência sem página/fato não quebra e mostra o que existe
    expect(screen.getByText('📄 1555528765064.pdf')).toBeInTheDocument()
    expect(screen.getByText('Documental · versão 3 · Página não informada · Seção não informada')).toBeInTheDocument()
    expect(screen.getAllByText('Sem trecho de documento vinculado.')).toHaveLength(2)
    // não expõe o ID interno como apresentação principal
    expect(screen.queryByText('#202, #203')).not.toBeInTheDocument()
  })

  it('mostra o fato e, separado, o trecho literal (já mascarado) do documento citado', async () => {
    const evidencias = [{ id: 301, documento: 'matricula.txt', version: 1, category: 'JURIDICO', page: 1, section: 'AV.3', fact: 'Penhora trabalhista averbada.', source_excerpt: 'AV.3/99.901 — PENHORA ... proprietário CPF [CPF].', tem_trecho_documento: true }]
    vi.mocked(fetch).mockReturnValueOnce(detail(verdict, evidencias))
    render(<VerdictSection propertyId={5} />)

    expect(await screen.findByText('Penhora trabalhista averbada.')).toBeInTheDocument()
    expect(screen.getByText('Jurídico · versão 1 · Página 1 · Seção AV.3')).toBeInTheDocument()
    expect(screen.getByLabelText('Trecho literal do documento')).toHaveTextContent('AV.3/99.901 — PENHORA ... proprietário CPF [CPF].')
  })

  it('exibe a recomendação NÃO ARREMATAR com lance, preço máximo e fundamentos por natureza', async () => {
    const desfavoravel = {
      ...verdict, overall: 'DESFAVORAVEL', summary: 'NÃO ARREMATAR por este lance.',
      financial: {
        decisao: {
          recomendacao: { codigo: 'NAO_ARREMATAR', texto: 'NÃO ARREMATAR por este lance. Lance de R$ 240.000 acima do preço máximo de R$ 136.266.', lance_maximo: 136266, lance_maximo_definitivo: true, lance_pretendido: 240000 },
          fundamentos: [
            { tipo: 'INVIABILIDADE_FINANCEIRA', descricao: 'Resultado projetado negativo: prejuízo de R$ 26.550.' },
            { tipo: 'PENDENCIA_DOCUMENTAL', descricao: 'A intimação para purgar a mora foi pessoal?' },
            { tipo: 'ANALISE_AUTOMATICA_INDISPONIVEL', descricao: 'A leitura automática dos documentos não foi executada.' },
          ],
        },
      },
    }
    vi.mocked(fetch).mockReturnValueOnce(detail(desfavoravel))
    render(<VerdictSection propertyId={5} />)

    expect(await screen.findByText('RECOMENDAÇÃO AO INVESTIDOR')).toBeInTheDocument()
    expect(screen.getByText('Não arrematar por este lance')).toBeInTheDocument()
    expect(screen.getByText(/acima do preço máximo de R\$ 136\.266/)).toBeInTheDocument()
    expect(screen.getByText('Lance pretendido').nextSibling).toHaveTextContent('240.000')
    expect(screen.getByText('Preço máximo (meta)').nextSibling).toHaveTextContent('136.266')
    expect(screen.getByText('Inviabilidade financeira')).toBeInTheDocument()
    expect(screen.getByText('Pendências documentais')).toBeInTheDocument()
    expect(screen.getByText('Leitura automática dos documentos')).toBeInTheDocument()
    expect(screen.queryByText('Risco jurídico')).not.toBeInTheDocument()
  })

  it('sem decisão no veredito (legado) não mostra bloco de recomendação', async () => {
    vi.mocked(fetch).mockReturnValueOnce(detail(verdict))
    render(<VerdictSection propertyId={5} />)
    expect(await screen.findByText('VEREDITO CONSOLIDADO')).toBeInTheDocument()
    expect(screen.queryByText('RECOMENDAÇÃO AO INVESTIDOR')).not.toBeInTheDocument()
  })

  it('trata erro e permite tentar novamente', async () => {
    vi.mocked(fetch)
      .mockReturnValueOnce(response({ detail: 'Falha' }, false, 500))
      .mockReturnValueOnce(detail(verdict))
    render(<VerdictSection propertyId={5} />)

    expect(await screen.findByText('Falha')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Tentar novamente' }))
    await waitFor(() => expect(screen.getByRole('heading', { name: 'Atenção' })).toBeInTheDocument())
  })
})
