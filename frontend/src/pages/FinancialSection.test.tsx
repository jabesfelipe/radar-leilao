import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { FinancialSection } from './FinancialSection'

const cost = { id: 1, property_id: 5, category: 'IPTU', description: 'IPTU 2026', amount: 1200, recurring: true }
const debt = { id: 2, property_id: 5, category: 'CONDOMINIO', creditor: 'Condomínio Central', amount: 3500, reference_date: '2026-01-01', status: 'PENDENTE', evidence_id: 9 }

function response(body: unknown, ok = true, status = 200) {
  return Promise.resolve({ ok, status, json: () => Promise.resolve(body) }) as Promise<Response>
}

function mockLists(costs: unknown[], debts: unknown[]) {
  vi.mocked(fetch)
    .mockReturnValueOnce(response({ property_id: 5, custos: costs, historico: [] }))
    .mockReturnValueOnce(response({ property_id: 5, dividas: debts, historico: [] }))
}

describe('FinancialSection', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
    globalThis.fetch = vi.fn()
  })

  it('exibe carregamento e depois estados vazios de custos e dívidas', async () => {
    mockLists([], [])
    render(<FinancialSection propertyId={5} />)

    expect(screen.getByRole('status')).toHaveTextContent('Carregando dados financeiros')
    expect(await screen.findByText('Nenhum custo cadastrado')).toBeInTheDocument()
    expect(screen.getByText('Nenhuma dívida cadastrada')).toBeInTheDocument()
  })

  it('carrega custos e dívidas existentes', async () => {
    mockLists([cost], [debt])
    render(<FinancialSection propertyId={5} />)

    expect(await screen.findByText('IPTU 2026')).toBeInTheDocument()
    expect(screen.getByText('Recorrente')).toBeInTheDocument()
    expect(screen.getByText('Condomínio Central')).toBeInTheDocument()
    expect(screen.getByText('PENDENTE')).toBeInTheDocument()
    expect(screen.getByText('#9')).toBeInTheDocument()
  })

  it('valida obrigatórios e cadastra um custo', async () => {
    mockLists([], [])
    vi.mocked(fetch).mockReturnValueOnce(response(cost))
    render(<FinancialSection propertyId={5} />)
    await screen.findByText('Nenhum custo cadastrado')

    fireEvent.click(screen.getAllByRole('button', { name: 'Novo custo' })[0])
    fireEvent.click(screen.getByRole('button', { name: 'Salvar custo' }))
    expect(await screen.findByText('Informe a categoria.')).toBeInTheDocument()
    expect(screen.getByText('Informe a descrição.')).toBeInTheDocument()

    fireEvent.change(screen.getByLabelText('Categoria'), { target: { value: 'IPTU' } })
    fireEvent.change(screen.getByLabelText('Descrição'), { target: { value: 'IPTU 2026' } })
    fireEvent.click(screen.getByRole('button', { name: 'Salvar custo' }))

    expect(await screen.findByText('Custo cadastrado com sucesso.')).toBeInTheDocument()
    const postCall = vi.mocked(fetch).mock.calls[2]
    expect(postCall[0]).toContain('/api/imoveis/5/custos')
    expect(JSON.parse(String((postCall[1] as RequestInit).body)).category).toBe('IPTU')
  })

  it('valida obrigatório e cadastra uma dívida', async () => {
    mockLists([], [])
    vi.mocked(fetch).mockReturnValueOnce(response(debt))
    render(<FinancialSection propertyId={5} />)
    await screen.findByText('Nenhuma dívida cadastrada')

    fireEvent.click(screen.getAllByRole('button', { name: 'Nova dívida' })[0])
    fireEvent.click(screen.getByRole('button', { name: 'Salvar dívida' }))
    expect(await screen.findByText('Informe a categoria.')).toBeInTheDocument()

    fireEvent.change(screen.getByLabelText('Categoria'), { target: { value: 'CONDOMINIO' } })
    fireEvent.click(screen.getByRole('button', { name: 'Salvar dívida' }))

    expect(await screen.findByText('Dívida cadastrada com sucesso.')).toBeInTheDocument()
    const postCall = vi.mocked(fetch).mock.calls[2]
    expect(postCall[0]).toContain('/api/imoveis/5/dividas')
    expect(JSON.parse(String((postCall[1] as RequestInit).body)).category).toBe('CONDOMINIO')
  })

  it('exibe erro de cadastro da API', async () => {
    mockLists([], [])
    vi.mocked(fetch).mockReturnValueOnce(response({ detail: 'Dados inválidos' }, false, 422))
    render(<FinancialSection propertyId={5} />)
    await screen.findByText('Nenhum custo cadastrado')

    fireEvent.click(screen.getAllByRole('button', { name: 'Novo custo' })[0])
    fireEvent.change(screen.getByLabelText('Categoria'), { target: { value: 'IPTU' } })
    fireEvent.change(screen.getByLabelText('Descrição'), { target: { value: 'IPTU 2026' } })
    fireEvent.click(screen.getByRole('button', { name: 'Salvar custo' }))

    expect(await screen.findByText('Dados inválidos')).toBeInTheDocument()
  })

  it('trata erro ao carregar e permite tentar novamente', async () => {
    vi.mocked(fetch)
      .mockReturnValueOnce(response({ detail: 'Falha' }, false, 500))
      .mockReturnValueOnce(response({ property_id: 5, dividas: [], historico: [] }))
    render(<FinancialSection propertyId={5} />)

    expect(await screen.findByText('Falha')).toBeInTheDocument()
    mockLists([cost], [debt])
    fireEvent.click(screen.getByRole('button', { name: 'Tentar novamente' }))
    await waitFor(() => expect(screen.getByText('IPTU 2026')).toBeInTheDocument())
  })
})
