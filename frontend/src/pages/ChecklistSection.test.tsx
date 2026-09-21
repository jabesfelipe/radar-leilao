import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { ChecklistSection } from './ChecklistSection'

const item = {
  id: 30,
  item_number: 1,
  canonical_key: 'INTIMACAO_PESSOAL',
  question: 'Intimação para purgar mora foi pessoal?',
  category: 'Jurídico',
  domain: ['juridico'],
  origin: 'referência',
  active: true,
  applicable: true,
  state: 'PENDENTE',
  answer: '',
  confidence: 'MEDIA',
  interpretation: null,
  risk: null,
}

const naoAplicavel = { ...item, id: 31, item_number: 2, question: 'Item não aplicável', state: 'NAO_APLICAVEL', applicable: false }

function response(body: unknown, ok = true, status = 200) {
  return Promise.resolve({ ok, status, json: () => Promise.resolve(body) }) as Promise<Response>
}

function detail(checklist: unknown[]) {
  return response({ imovel: { id: 5 }, checklist })
}

describe('ChecklistSection', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
    globalThis.fetch = vi.fn()
  })

  it('exibe carregamento e depois estado vazio', async () => {
    vi.mocked(fetch).mockReturnValueOnce(detail([]))
    render(<ChecklistSection propertyId={5} />)

    expect(screen.getByRole('status')).toHaveTextContent('Carregando checklist')
    expect(await screen.findByText('Checklist não disponível')).toBeInTheDocument()
  })

  it('lista itens com pergunta, categoria, domínio, origem, estado e diferencia não aplicável', async () => {
    vi.mocked(fetch).mockReturnValueOnce(detail([item, naoAplicavel]))
    render(<ChecklistSection propertyId={5} />)

    expect(await screen.findByText('Intimação para purgar mora foi pessoal?')).toBeInTheDocument()
    expect(screen.getAllByText('Jurídico').length).toBeGreaterThan(0)
    expect(screen.getAllByText('juridico').length).toBeGreaterThan(0)
    expect(screen.getAllByText('referência').length).toBeGreaterThan(0)
    expect(screen.getByText('Pendente')).toBeInTheDocument()
    expect(screen.getAllByText('Não aplicável').length).toBeGreaterThan(0)
  })

  it('mapeia rótulos em português para os sete estados oficiais', async () => {
    const states = ['PENDENTE', 'EM_ANALISE', 'CONFIRMADO', 'RISCO_IDENTIFICADO', 'ATENCAO', 'NAO_IDENTIFICADO', 'NAO_APLICAVEL']
    vi.mocked(fetch).mockReturnValueOnce(detail(states.map((state, index) => ({ ...item, id: 100 + index, item_number: index + 1, question: `Item ${state}`, state }))))
    render(<ChecklistSection propertyId={5} />)
    await screen.findByText('Item PENDENTE')

    for (const label of ['Pendente', 'Em análise', 'Confirmado', 'Risco identificado', 'Atenção', 'Não identificado', 'Não aplicável']) {
      expect(screen.getAllByText(label).length).toBeGreaterThan(0)
    }
  })

  it('atualiza um item usando o contrato do PATCH', async () => {
    vi.mocked(fetch)
      .mockReturnValueOnce(detail([item]))
      .mockReturnValueOnce(response({ ...item, state: 'CONFIRMADO', answer: 'Confirmado em cartório', confidence: 'ALTA' }))
    render(<ChecklistSection propertyId={5} />)
    await screen.findByText('Intimação para purgar mora foi pessoal?')

    fireEvent.click(screen.getByRole('button', { name: 'Atualizar item' }))
    fireEvent.change(screen.getByLabelText('Estado'), { target: { value: 'CONFIRMADO' } })
    fireEvent.change(screen.getByLabelText('Confiança'), { target: { value: 'ALTA' } })
    fireEvent.change(screen.getByLabelText('Resposta'), { target: { value: 'Confirmado em cartório' } })
    fireEvent.click(screen.getByRole('button', { name: 'Salvar' }))

    expect(await screen.findByText('Item do checklist atualizado com sucesso.')).toBeInTheDocument()
    const patchCall = vi.mocked(fetch).mock.calls[1]
    expect(patchCall[0]).toContain('/api/imoveis/5/checklist/30')
    expect((patchCall[1] as RequestInit).method).toBe('PATCH')
    const body = JSON.parse(String((patchCall[1] as RequestInit).body))
    expect(body).toEqual({ state: 'CONFIRMADO', answer: 'Confirmado em cartório', confidence: 'ALTA' })
    expect(screen.getByText('Confirmado')).toBeInTheDocument()
  })

  it('preserva dados e permite nova tentativa ao falhar o PATCH', async () => {
    vi.mocked(fetch)
      .mockReturnValueOnce(detail([item]))
      .mockReturnValueOnce(response({ detail: 'Estado inválido' }, false, 422))
    render(<ChecklistSection propertyId={5} />)
    await screen.findByText('Intimação para purgar mora foi pessoal?')

    fireEvent.click(screen.getByRole('button', { name: 'Atualizar item' }))
    fireEvent.click(screen.getByRole('button', { name: 'Salvar' }))

    expect(await screen.findByText('Estado inválido')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Salvar' })).toBeEnabled()
    expect(screen.getByText('Intimação para purgar mora foi pessoal?')).toBeInTheDocument()
  })

  it('trata erro de carregamento e permite retry', async () => {
    vi.mocked(fetch)
      .mockReturnValueOnce(response({ detail: 'Falha' }, false, 500))
      .mockReturnValueOnce(detail([item]))
    render(<ChecklistSection propertyId={5} />)

    fireEvent.click(await screen.findByRole('button', { name: 'Tentar novamente' }))
    await waitFor(() => expect(screen.getByText('Intimação para purgar mora foi pessoal?')).toBeInTheDocument())
  })

  it('desabilita o salvamento e não dispara múltiplos PATCH', async () => {
    let resolvePatch: ((value: Response) => void) | undefined
    const patch = new Promise<Response>((resolve) => { resolvePatch = resolve })
    vi.mocked(fetch)
      .mockReturnValueOnce(detail([item]))
      .mockReturnValueOnce(patch)
    render(<ChecklistSection propertyId={5} />)
    await screen.findByText('Intimação para purgar mora foi pessoal?')

    fireEvent.click(screen.getByRole('button', { name: 'Atualizar item' }))
    const form = screen.getByRole('button', { name: 'Salvar' }).closest('form') as HTMLFormElement
    fireEvent.submit(form)
    const loadingButton = within(form).getByRole('button', { name: 'Carregando…' })
    expect(loadingButton).toBeDisabled()
    fireEvent.submit(form)
    resolvePatch?.(await response({ ...item, state: 'CONFIRMADO' }))
    await screen.findByText('Item do checklist atualizado com sucesso.')
    expect(vi.mocked(fetch)).toHaveBeenCalledTimes(2)
  })
})
