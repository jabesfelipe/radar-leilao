import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { ChecklistSection } from './ChecklistSection'

const master = [
  { canonical_key: 'INTIMACAO_PESSOAL', question: 'Intimação para purgar mora foi pessoal?', category: 'Jurídico', domain: ['juridico'], origin: 'referência', priority: 1 },
  { canonical_key: 'ITEM_NAO_APLICAVEL', question: 'Item não aplicável', category: 'Jurídico', domain: ['juridico'], origin: 'referência', priority: 2 },
]

const result = {
  id: 30,
  checklist_item_id: 5,
  canonical_key: 'INTIMACAO_PESSOAL',
  item_version: 1,
  applicable: true,
  state: 'PENDENTE',
  answer: '',
  confidence: null,
  interpretation: null,
  risk: null,
  previous_result_id: null,
}

function response(body: unknown, ok = true, status = 200) {
  return Promise.resolve({ ok, status, json: () => Promise.resolve(body) }) as Promise<Response>
}

function executions(results: unknown[]) {
  return response([{ id: 1, created_at: '2026-01-01T00:00:00Z', results }])
}

function mockLoad(results: unknown[]) {
  vi.mocked(fetch)
    .mockReturnValueOnce(executions(results))
    .mockReturnValueOnce(response(master))
}

describe('ChecklistSection', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
    globalThis.fetch = vi.fn()
  })

  it('usa o endpoint específico do checklist do imóvel', async () => {
    mockLoad([])
    render(<ChecklistSection propertyId={5} />)
    await screen.findByText('Checklist não disponível')

    expect(vi.mocked(fetch).mock.calls[0][0]).toContain('/api/imoveis/5/checklist')
  })

  it('exibe carregamento e depois estado vazio', async () => {
    mockLoad([])
    render(<ChecklistSection propertyId={5} />)

    expect(screen.getByRole('status')).toHaveTextContent('Carregando checklist')
    expect(await screen.findByText('Checklist não disponível')).toBeInTheDocument()
  })

  it('lista itens enriquecidos e diferencia aplicabilidade em três estados', async () => {
    mockLoad([
      result,
      { ...result, id: 31, canonical_key: 'ITEM_NAO_APLICAVEL', applicable: false },
      { ...result, id: 32, canonical_key: 'SEM_META', applicable: null },
    ])
    render(<ChecklistSection propertyId={5} />)

    expect(await screen.findByText('Intimação para purgar mora foi pessoal?')).toBeInTheDocument()
    expect(screen.getAllByText('Jurídico').length).toBeGreaterThan(0)
    expect(screen.getAllByText('juridico').length).toBeGreaterThan(0)
    expect(screen.getAllByText('referência').length).toBeGreaterThan(0)
    expect(screen.getByText('Aplicável')).toBeInTheDocument()
    expect(screen.getByText('Não aplicável')).toBeInTheDocument()
    // item sem meta usa canonical_key como pergunta e applicable null vira "Não informado"
    expect(screen.getByText('SEM_META')).toBeInTheDocument()
    expect(screen.getAllByText('Não informado').length).toBeGreaterThan(0)
  })

  it('não transforma confidence ausente em MEDIA', async () => {
    mockLoad([result])
    render(<ChecklistSection propertyId={5} />)
    await screen.findByText('Intimação para purgar mora foi pessoal?')

    expect(screen.queryByText('Média')).not.toBeInTheDocument()
    expect(screen.getByText('Não informado')).toBeInTheDocument()
  })

  it('mapeia rótulos em português para os sete estados oficiais', async () => {
    const states = ['PENDENTE', 'EM_ANALISE', 'CONFIRMADO', 'RISCO_IDENTIFICADO', 'ATENCAO', 'NAO_IDENTIFICADO', 'NAO_APLICAVEL']
    const masterMany = states.map((state) => ({ canonical_key: `KEY_${state}`, question: `Item ${state}`, category: 'Jurídico', domain: ['juridico'], origin: 'referência', priority: 1 }))
    vi.mocked(fetch)
      .mockReturnValueOnce(executions(states.map((state, index) => ({ ...result, id: 100 + index, canonical_key: `KEY_${state}`, state }))))
      .mockReturnValueOnce(response(masterMany))
    render(<ChecklistSection propertyId={5} />)
    await screen.findByText('Item PENDENTE')

    for (const label of ['Pendente', 'Em análise', 'Confirmado', 'Risco identificado', 'Atenção', 'Não identificado', 'Não aplicável']) {
      expect(screen.getAllByText(label).length).toBeGreaterThan(0)
    }
  })

  it('não envia confiança artificial quando o usuário não a define', async () => {
    mockLoad([result])
    vi.mocked(fetch).mockReturnValueOnce(response({ ...result, state: 'CONFIRMADO', answer: 'Confirmado em cartório' }))
    render(<ChecklistSection propertyId={5} />)
    await screen.findByText('Intimação para purgar mora foi pessoal?')

    fireEvent.click(screen.getByRole('button', { name: 'Atualizar item' }))
    fireEvent.change(screen.getByLabelText('Estado'), { target: { value: 'CONFIRMADO' } })
    fireEvent.change(screen.getByLabelText('Resposta'), { target: { value: 'Confirmado em cartório' } })
    fireEvent.click(screen.getByRole('button', { name: 'Salvar' }))

    expect(await screen.findByText('Item do checklist atualizado com sucesso.')).toBeInTheDocument()
    const patchCall = vi.mocked(fetch).mock.calls[2]
    expect(patchCall[0]).toContain('/api/imoveis/5/checklist/30')
    expect((patchCall[1] as RequestInit).method).toBe('PATCH')
    const body = JSON.parse(String((patchCall[1] as RequestInit).body))
    expect(body.state).toBe('CONFIRMADO')
    expect(body.answer).toBe('Confirmado em cartório')
    // confiança ausente no item permanece ausente (não vira MEDIA artificial)
    expect(body).not.toHaveProperty('confidence')
  })

  it('preserva interpretação e risco ao atualizar (não sobrescreve com null)', async () => {
    const enriched = { ...result, interpretation: 'Interpretação do agente', risk: 'Risco relevante', confidence: 'ALTA' }
    mockLoad([enriched])
    vi.mocked(fetch).mockReturnValueOnce(response({ ...enriched, state: 'CONFIRMADO' }))
    render(<ChecklistSection propertyId={5} />)
    await screen.findByText('Intimação para purgar mora foi pessoal?')

    fireEvent.click(screen.getByRole('button', { name: 'Atualizar item' }))
    fireEvent.change(screen.getByLabelText('Estado'), { target: { value: 'CONFIRMADO' } })
    fireEvent.click(screen.getByRole('button', { name: 'Salvar' }))

    expect(await screen.findByText('Item do checklist atualizado com sucesso.')).toBeInTheDocument()
    const body = JSON.parse(String((vi.mocked(fetch).mock.calls[2][1] as RequestInit).body))
    expect(body.interpretation).toBe('Interpretação do agente')
    expect(body.risk).toBe('Risco relevante')
    // confiança existente é preservada mesmo sem o usuário reabrir o seletor
    expect(body.confidence).toBe('ALTA')
  })

  it('envia confiança apenas quando o usuário a seleciona', async () => {
    mockLoad([result])
    vi.mocked(fetch).mockReturnValueOnce(response({ ...result, state: 'CONFIRMADO', confidence: 'ALTA' }))
    render(<ChecklistSection propertyId={5} />)
    await screen.findByText('Intimação para purgar mora foi pessoal?')

    fireEvent.click(screen.getByRole('button', { name: 'Atualizar item' }))
    fireEvent.change(screen.getByLabelText('Estado'), { target: { value: 'CONFIRMADO' } })
    fireEvent.change(screen.getByLabelText('Confiança'), { target: { value: 'ALTA' } })
    fireEvent.click(screen.getByRole('button', { name: 'Salvar' }))

    expect(await screen.findByText('Item do checklist atualizado com sucesso.')).toBeInTheDocument()
    const body = JSON.parse(String((vi.mocked(fetch).mock.calls[2][1] as RequestInit).body))
    expect(body.confidence).toBe('ALTA')
  })

  it('preserva dados e permite nova tentativa ao falhar o PATCH', async () => {
    mockLoad([result])
    vi.mocked(fetch).mockReturnValueOnce(response({ detail: 'Estado inválido' }, false, 422))
    render(<ChecklistSection propertyId={5} />)
    await screen.findByText('Intimação para purgar mora foi pessoal?')

    fireEvent.click(screen.getByRole('button', { name: 'Atualizar item' }))
    fireEvent.click(screen.getByRole('button', { name: 'Salvar' }))

    expect(await screen.findByText('Estado inválido')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Salvar' })).toBeEnabled()
    expect(screen.getByText('Intimação para purgar mora foi pessoal?')).toBeInTheDocument()
  })

  it('trata erro de carregamento e permite retry', async () => {
    vi.mocked(fetch).mockReturnValueOnce(response({ detail: 'Falha' }, false, 500))
    render(<ChecklistSection propertyId={5} />)

    expect(await screen.findByText('Falha')).toBeInTheDocument()
    mockLoad([result])
    fireEvent.click(screen.getByRole('button', { name: 'Tentar novamente' }))
    await waitFor(() => expect(screen.getByText('Intimação para purgar mora foi pessoal?')).toBeInTheDocument())
  })

  it('desabilita o salvamento e não dispara múltiplos PATCH', async () => {
    let resolvePatch: ((value: Response) => void) | undefined
    const patch = new Promise<Response>((resolve) => { resolvePatch = resolve })
    mockLoad([result])
    vi.mocked(fetch).mockReturnValueOnce(patch)
    render(<ChecklistSection propertyId={5} />)
    await screen.findByText('Intimação para purgar mora foi pessoal?')

    fireEvent.click(screen.getByRole('button', { name: 'Atualizar item' }))
    const form = screen.getByRole('button', { name: 'Salvar' }).closest('form') as HTMLFormElement
    fireEvent.submit(form)
    expect(within(form).getByRole('button', { name: 'Carregando…' })).toBeDisabled()
    fireEvent.submit(form)
    resolvePatch?.(await response({ ...result, state: 'CONFIRMADO' }))
    await screen.findByText('Item do checklist atualizado com sucesso.')
    expect(vi.mocked(fetch)).toHaveBeenCalledTimes(3)
  })
})
