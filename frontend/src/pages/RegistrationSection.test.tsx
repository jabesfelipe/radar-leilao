import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { RegistrationSection } from './RegistrationSection'

const registration = {
  id: 3,
  property_id: 5,
  registration_number: '12.345',
  registry_office: '1º CRI',
  comarca: 'São Paulo',
  consultation_date: '2026-01-10',
  holder: 'Fulano de Tal',
  observations: 'Sem ônus registrados',
  document_version_id: 9,
}

function response(body: unknown, ok = true, status = 200) {
  return Promise.resolve({ ok, status, json: () => Promise.resolve(body) }) as Promise<Response>
}

describe('RegistrationSection', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
    globalThis.fetch = vi.fn()
  })

  it('carrega e exibe a matrícula atual com histórico', async () => {
    vi.mocked(fetch).mockReturnValueOnce(response({ property_id: 5, atual: registration, historico: [registration], alteracoes: [] }))
    render(<RegistrationSection propertyId={5} />)

    expect(screen.getByRole('status')).toHaveTextContent('Carregando matrícula')
    expect(await screen.findByText('MATRÍCULA ATUAL')).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: '12.345' })).toBeInTheDocument()
    expect(screen.getByText('1º CRI')).toBeInTheDocument()
    expect(screen.getByText('Histórico de registros')).toBeInTheDocument()
    expect(screen.getByText('Vinculada a documento')).toBeInTheDocument()
  })

  it('mostra estado vazio quando não há matrícula', async () => {
    vi.mocked(fetch).mockReturnValueOnce(response({ property_id: 5, atual: null, historico: [], alteracoes: [] }))
    render(<RegistrationSection propertyId={5} />)

    expect(await screen.findByText('Nenhuma matrícula cadastrada')).toBeInTheDocument()
  })

  it('valida número obrigatório e cadastra a matrícula', async () => {
    vi.mocked(fetch)
      .mockReturnValueOnce(response({ property_id: 5, atual: null, historico: [], alteracoes: [] }))
      .mockReturnValueOnce(response(registration))
      .mockReturnValueOnce(response({ property_id: 5, atual: registration, historico: [registration], alteracoes: [] }))
    render(<RegistrationSection propertyId={5} />)
    await screen.findByText('Nenhuma matrícula cadastrada')

    fireEvent.click(screen.getAllByRole('button', { name: 'Novo registro' })[0])
    fireEvent.click(screen.getByRole('button', { name: 'Salvar matrícula' }))
    expect(await screen.findByText('Informe o número da matrícula.')).toBeInTheDocument()

    fireEvent.change(screen.getByLabelText('Número da matrícula'), { target: { value: '12.345' } })
    fireEvent.click(screen.getByRole('button', { name: 'Salvar matrícula' }))

    expect(await screen.findByText('Matrícula registrada com sucesso.')).toBeInTheDocument()
    const postCall = vi.mocked(fetch).mock.calls[1]
    expect(postCall[0]).toContain('/api/imoveis/5/matricula')
    expect(JSON.parse(String((postCall[1] as RequestInit).body)).registration_number).toBe('12.345')
  })

  it('trata erro da API e permite tentar novamente', async () => {
    vi.mocked(fetch)
      .mockReturnValueOnce(response({ detail: 'Falha ao carregar' }, false, 500))
      .mockReturnValueOnce(response({ property_id: 5, atual: registration, historico: [], alteracoes: [] }))
    render(<RegistrationSection propertyId={5} />)

    expect(await screen.findByText('Falha ao carregar')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Tentar novamente' }))
    await waitFor(() => expect(screen.getByRole('heading', { name: '12.345' })).toBeInTheDocument())
  })
})
