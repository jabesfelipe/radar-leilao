import { fireEvent, render, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { AutoResearchCard } from './AutoResearchCard'
import { DocumentSituationCard } from './DocumentSituationCard'
import { sortByPriority, type ChecklistItem } from '../services/checklist'

const ok = (body: unknown) => Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve(body) }) as Promise<Response>

describe('AutoResearchCard', () => {
  beforeEach(() => { vi.restoreAllMocks(); globalThis.fetch = vi.fn() })

  it('não pesquisa sozinho e, sem provedor, explica o que configurar', async () => {
    vi.mocked(fetch).mockReturnValueOnce(ok({ status: 'NAO_CONFIGURADO', texto: 'Defina TAVILY_API_KEY.', consultas: [], comparaveis_criados: [], descartados: [], referencias_condominio: [], portais_iptu: [] }))
    render(<AutoResearchCard propertyId={7} />)
    expect(fetch).not.toHaveBeenCalled()
    fireEvent.click(screen.getByRole('button', { name: /Pesquisar automaticamente/ }))
    expect(await screen.findByText('NAO CONFIGURADO')).toBeInTheDocument()
    expect(screen.getByText(/TAVILY_API_KEY/)).toBeInTheDocument()
    const [url, init] = vi.mocked(fetch).mock.calls[0]
    expect(String(url)).toContain('/api/imoveis/7/pesquisa-automatica')
    expect((init as RequestInit).method).toBe('POST')
  })

  it('mostra consultas, comparáveis com link e descartados com motivo', async () => {
    const onDone = vi.fn()
    vi.mocked(fetch).mockReturnValueOnce(ok({
      status: 'SUCESSO', consultas: [{ tipo: 'VENDA', consulta: 'apartamento à venda', provedor: 'tavily', status: 'SUCESSO', resultados: 2 }],
      comparaveis_criados: [{ id: 1, tipo: 'VENDA', valor: 250000, area_m2: 50, url: 'https://portal.exemplo/1', fonte: 'portal.exemplo', confianca: 'MEDIA' }],
      descartados: [{ url: 'https://portal.exemplo/lista', titulo: 'Lista', motivos: ['Página de listagem com vários imóveis.'] }],
      referencias_condominio: [], portais_iptu: [{ url: 'https://prefeitura.exemplo.gov.br', titulo: 'IPTU', dominio: 'prefeitura.exemplo.gov.br' }],
    }))
    render(<AutoResearchCard propertyId={7} onDone={onDone} />)
    fireEvent.click(screen.getByRole('button', { name: /Pesquisar automaticamente/ }))
    expect(await screen.findByRole('link', { name: 'portal.exemplo' })).toHaveAttribute('href', 'https://portal.exemplo/1')
    expect(screen.getByText(/Página de listagem/)).toBeInTheDocument()
    expect(screen.getByText(/apartamento à venda/)).toBeInTheDocument()
    expect(onDone).toHaveBeenCalled()
  })
})

describe('DocumentSituationCard', () => {
  it('mostra obrigatórios pendentes e contagens', () => {
    render(<DocumentSituationCard situation={{
      texto: '1 documento recebido. Falta(m) obrigatório(s): Edital ou condições da venda.',
      contagem: { recebidos: 1, analisados: 1, incompletos: 0, em_processamento: 0, evidencias: 4 },
      obrigatorios_faltando: ['Edital ou condições da venda'],
      esperados: [{ chave: 'EDITAL', nome: 'Edital ou condições da venda', obrigatorio: true, situacao: 'PENDENTE', por_que: 'Define regras.', proxima_acao: 'Baixar o edital.' }],
      documentos: [{ id: 1, nome: 'matricula.pdf', situacao: 'ANALISADO', situacao_label: 'Analisado', paginas_citadas: [2], evidencias: 4, confianca: { alta: 2, media: 2, baixa: 0 }, pendencias: [] }],
      proximas_acoes: [],
    }} />)
    expect(screen.getByText('Obrigatório')).toBeInTheDocument()
    expect(screen.getByText('Pendente')).toBeInTheDocument()
    expect(screen.getByText('Baixar o edital.')).toBeInTheDocument()
    expect(screen.getByText('Evidências: 4')).toBeInTheDocument()
  })
})

describe('sortByPriority', () => {
  it('coloca itens abertos primeiro, de P0 a P3, e mantém a ordem sem prioridade', () => {
    const base = { question: 'q', state: 'PENDENTE' } as ChecklistItem
    const items = [
      { ...base, id: 1, prioridade: 'P3', resultado: 'PENDENTE' },
      { ...base, id: 2, prioridade: 'P0', resultado: 'CONFIRMADO' },
      { ...base, id: 3, prioridade: 'P1', resultado: 'RISCO_IDENTIFICADO' },
      { ...base, id: 4, prioridade: 'P0', resultado: 'PENDENTE' },
    ] as ChecklistItem[]
    expect(sortByPriority(items).map((i) => i.id)).toEqual([4, 3, 1, 2])
    const plain = [{ ...base, id: 9 }, { ...base, id: 8 }] as ChecklistItem[]
    expect(sortByPriority(plain).map((i) => i.id)).toEqual([9, 8])
  })
})
