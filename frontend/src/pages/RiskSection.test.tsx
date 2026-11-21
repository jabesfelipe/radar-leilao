import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { RiskSection } from './RiskSection'

const risk = {
  chave: 'TERCEIRO_OCUPANTE',
  categoria: 'Ocupação e desocupação',
  titulo: 'Imóvel ocupado',
  o_que_significa: 'Há alguém morando ou usando o imóvel.',
  detalhe: null,
  situacao: 'CONFIRMADO',
  situacao_label: 'Confirmado',
  gravidade: 'MEDIA',
  gravidade_label: 'Média',
  impactos: ['financeiro', 'prazo'],
  estimativa: { texto: 'Reserva considerada no Financeiro: R$ 5.000,00.', valor_base: 5000, valor_conservador: 5000, tipo: 'ESTIMATIVA' },
  evidencia: { documento: 'Edital', pagina: 3, trecho: 'imóvel ocupado', texto: 'Edital, página 3' },
  o_que_fazer: ['Confirmar quem ocupa o imóvel.'],
}

function response(body: unknown, ok = true, status = 200) {
  return Promise.resolve({ ok, status, json: () => Promise.resolve(body) }) as Promise<Response>
}

describe('RiskSection', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
    globalThis.fetch = vi.fn()
  })

  it('exibe carregamento e depois estado vazio', async () => {
    vi.mocked(fetch).mockReturnValueOnce(response({ itens: [] }))
    render(<RiskSection propertyId={5} />)

    expect(screen.getByRole('status')).toHaveTextContent('Carregando riscos')
    expect(await screen.findByText('Nenhum risco identificado')).toBeInTheDocument()
  })

  it('mostra o risco em linguagem simples, sem códigos, versões ou ids', async () => {
    const resolved = { ...risk, chave: 'PENHORA', titulo: 'Penhora na matrícula', categoria: 'Jurídico', situacao: 'RESOLVIDO', situacao_label: 'Resolvido' }
    vi.mocked(fetch).mockReturnValueOnce(response({ itens: [risk, resolved], aviso: 'Cada risco aparece uma vez.' }))
    const { container } = render(<RiskSection propertyId={5} />)

    expect(await screen.findByRole('heading', { name: 'Imóvel ocupado' })).toBeInTheDocument()
    expect(screen.getByText('Ocupação e desocupação')).toBeInTheDocument()
    expect(screen.getByText('Confirmado')).toBeInTheDocument()
    expect(screen.getByText('Financeiro, Prazo')).toBeInTheDocument()
    expect(screen.getByText('Reserva considerada no Financeiro: R$ 5.000,00.')).toBeInTheDocument()
    expect(screen.getByText('Edital, página 3')).toBeInTheDocument()
    expect(screen.getByText('Confirmar quem ocupa o imóvel.')).toBeInTheDocument()
    expect(screen.getByText(/Verificados sem risco ou já resolvidos/)).toBeInTheDocument()
    expect(container.textContent).not.toMatch(/CHECKLIST_|RiskEngine|Evidência #|Versão da análise/)
    expect(vi.mocked(fetch).mock.calls[0][0]).toContain('/api/imoveis/5/riscos-consolidados')
  })

  it('trata erro e permite tentar novamente', async () => {
    vi.mocked(fetch)
      .mockReturnValueOnce(response({ detail: 'Falha' }, false, 500))
      .mockReturnValueOnce(response({ itens: [risk] }))
    render(<RiskSection propertyId={5} />)

    expect(await screen.findByText('Falha')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Tentar novamente' }))
    await waitFor(() => expect(screen.getByRole('heading', { name: 'Imóvel ocupado' })).toBeInTheDocument())
  })
})
