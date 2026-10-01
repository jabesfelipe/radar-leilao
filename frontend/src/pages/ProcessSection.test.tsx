import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { ProcessSection } from './ProcessSection'

const legalProcess = {
  id: 8,
  property_id: 5,
  number: '0001234-56.2026.8.26.0100',
  court: 'TJSP',
  comarca: 'São Paulo',
  nature: 'Execução',
  subject: 'Cobrança',
  status: 'Em andamento',
  polo_active: 'Banco X',
  polo_passive: 'Fulano',
  distribution_date: '2026-01-15',
  observations: 'Penhora registrada',
  source: 'e-SAJ',
  impact: 'Possível constrição',
  evidence_id: 21,
}

function response(body: unknown, ok = true, status = 200) {
  return Promise.resolve({ ok, status, json: () => Promise.resolve(body) }) as Promise<Response>
}

describe('ProcessSection', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
    globalThis.fetch = vi.fn()
  })

  it('exibe carregamento e depois estado vazio', async () => {
    vi.mocked(fetch).mockReturnValueOnce(response({ property_id: 5, processos: [], historico: [] }))
    render(<ProcessSection propertyId={5} />)

    expect(screen.getByRole('status')).toHaveTextContent('Carregando processos')
    expect(await screen.findByText('Nenhum processo cadastrado')).toBeInTheDocument()
  })

  it('lista os processos com os campos do contrato', async () => {
    vi.mocked(fetch).mockReturnValueOnce(response({ property_id: 5, processos: [legalProcess], historico: [] }))
    render(<ProcessSection propertyId={5} />)

    expect(await screen.findByRole('heading', { name: '0001234-56.2026.8.26.0100' })).toBeInTheDocument()
    expect(screen.getByText('TJSP')).toBeInTheDocument()
    expect(screen.getByText('Em andamento')).toBeInTheDocument()
    expect(screen.getByText('Banco X')).toBeInTheDocument()
    expect(screen.getByText('#21')).toBeInTheDocument()
  })

  it('valida apenas o número e cadastra o processo', async () => {
    vi.mocked(fetch)
      .mockReturnValueOnce(response({ property_id: 5, processos: [], historico: [] }))
      .mockReturnValueOnce(response(legalProcess))
    render(<ProcessSection propertyId={5} />)
    await screen.findByText('Nenhum processo cadastrado')

    fireEvent.click(screen.getAllByRole('button', { name: 'Novo processo' })[0])
    fireEvent.click(screen.getByRole('button', { name: 'Salvar processo' }))
    expect(await screen.findByText('Informe o número do processo.')).toBeInTheDocument()
    expect(fetch).toHaveBeenCalledTimes(1)

    fireEvent.change(screen.getByLabelText('Número do processo'), { target: { value: '0001234-56.2026.8.26.0100' } })
    fireEvent.click(screen.getByRole('button', { name: 'Salvar processo' }))

    expect(await screen.findByText('Processo cadastrado com sucesso.')).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: '0001234-56.2026.8.26.0100' })).toBeInTheDocument()
    const postCall = vi.mocked(fetch).mock.calls[1]
    expect(postCall[0]).toContain('/api/imoveis/5/processos')
    expect(JSON.parse(String((postCall[1] as RequestInit).body)).number).toBe('0001234-56.2026.8.26.0100')
  })

  it('exibe erro de cadastro da API', async () => {
    vi.mocked(fetch)
      .mockReturnValueOnce(response({ property_id: 5, processos: [], historico: [] }))
      .mockReturnValueOnce(response({ detail: 'Dados inválidos' }, false, 422))
    render(<ProcessSection propertyId={5} />)
    await screen.findByText('Nenhum processo cadastrado')

    fireEvent.click(screen.getAllByRole('button', { name: 'Novo processo' })[0])
    fireEvent.change(screen.getByLabelText('Número do processo'), { target: { value: '123' } })
    fireEvent.click(screen.getByRole('button', { name: 'Salvar processo' }))

    expect(await screen.findByText('Dados inválidos')).toBeInTheDocument()
  })

  it('trata erro ao carregar e permite tentar novamente', async () => {
    vi.mocked(fetch)
      .mockReturnValueOnce(response({ detail: 'Falha' }, false, 500))
      .mockReturnValueOnce(response({ property_id: 5, processos: [legalProcess], historico: [] }))
    render(<ProcessSection propertyId={5} />)

    fireEvent.click(await screen.findByRole('button', { name: 'Tentar novamente' }))
    await waitFor(() => expect(screen.getByRole('heading', { name: '0001234-56.2026.8.26.0100' })).toBeInTheDocument())
  })

  it('exibe correlação e vínculo quando o processo vem da Judicial API', async () => {
    const correlated = { ...legalProcess, correlation_level: 'MEDIA', link_origin: 'AUTOMATICA' }
    vi.mocked(fetch).mockReturnValueOnce(response({ property_id: 5, processos: [correlated], historico: [] }))
    render(<ProcessSection propertyId={5} />)

    expect(await screen.findByText(/Correlação: MEDIA/)).toBeInTheDocument()
    expect(screen.getByText('AUTOMATICA')).toBeInTheDocument()
  })

  it('pesquisa judicial exibe o resumo das fontes e processos encontrados', async () => {
    vi.mocked(fetch)
      .mockReturnValueOnce(response({ property_id: 5, processos: [], historico: [] })) // load inicial
      .mockReturnValueOnce(response({
        property_id: 5, disponivel: true, search_id: 'abc', processos_criados: 1,
        processos_atualizados: 0, processos_relevantes: 1, sinais_criados: 2,
        fontes: [{ tribunal: 'TJPR', status: 'SUCCESS' }], avisos: [],
      })) // consultar
      .mockReturnValueOnce(response({ property_id: 5, processos: [{ ...legalProcess, correlation_level: 'ALTA', link_origin: 'AUTOMATICA' }], historico: [] })) // reload

    render(<ProcessSection propertyId={5} />)
    await screen.findByText('Nenhum processo cadastrado')

    fireEvent.click(screen.getByRole('button', { name: /Pesquisar processos/ }))
    fireEvent.change(screen.getByLabelText('Nome da parte'), { target: { value: 'João da Silva' } })
    fireEvent.click(screen.getByRole('button', { name: /^Pesquisar$/ }))

    expect(await screen.findByText(/Pesquisa judicial concluída/)).toBeInTheDocument()
    expect(screen.getByText(/1 fonte\(s\) consultada\(s\)/)).toBeInTheDocument()
    const consultCall = vi.mocked(fetch).mock.calls[1]
    expect(consultCall[0]).toContain('/api/imoveis/5/processos/consultar')
  })

  it('pesquisa judicial avisa quando a fonte está indisponível', async () => {
    vi.mocked(fetch)
      .mockReturnValueOnce(response({ property_id: 5, processos: [], historico: [] }))
      .mockReturnValueOnce(response({ property_id: 5, disponivel: false, mensagem: 'Judicial API indisponível; análise não interrompida.' }))
      .mockReturnValueOnce(response({ property_id: 5, processos: [], historico: [] }))

    render(<ProcessSection propertyId={5} />)
    await screen.findByText('Nenhum processo cadastrado')

    fireEvent.click(screen.getByRole('button', { name: /Pesquisar processos/ }))
    fireEvent.change(screen.getByLabelText('Nome da parte'), { target: { value: 'João da Silva' } })
    fireEvent.click(screen.getByRole('button', { name: /^Pesquisar$/ }))

    expect(await screen.findByText('Judicial API indisponível')).toBeInTheDocument()
  })

  it('vincula um processo ao imóvel', async () => {
    const correlated = { ...legalProcess, correlation_level: 'MEDIA', link_origin: 'AUTOMATICA' }
    vi.mocked(fetch)
      .mockReturnValueOnce(response({ property_id: 5, processos: [correlated], historico: [] })) // load
      .mockReturnValueOnce(response({ property_id: 5, processo: { ...correlated, link_origin: 'VALIDADA' } })) // vincular
      .mockReturnValueOnce(response({ property_id: 5, processos: [{ ...correlated, link_origin: 'VALIDADA' }], historico: [] })) // reload

    render(<ProcessSection propertyId={5} />)
    fireEvent.click(await screen.findByRole('button', { name: 'Vincular ao imóvel' }))

    expect(await screen.findByText('Processo vinculado ao imóvel (validado).')).toBeInTheDocument()
    const linkCall = vi.mocked(fetch).mock.calls[1]
    expect(linkCall[0]).toContain('/juridico/processos/8/vincular')
  })
})
