import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { DueDiligenceSection } from './DueDiligenceSection'

function response(body: unknown, ok = true, status = 200) {
  return Promise.resolve({ ok, status, json: () => Promise.resolve(body) }) as Promise<Response>
}

const overview = {
  property_id: 7,
  frentes: {
    MATRICULA: { frente: 'MATRICULA', status: 'NAO_INICIADO', integracao: 'NAO_CONFIGURADO', pendencias: ['Matrícula atualizada não importada/consultada.'], achados: 0, revisado: false, titular: null, matricula: null },
    JUDICIAL: { frente: 'JUDICIAL', status: 'CONSULTADO', integracao: 'CONFIGURADO', pendencias: [], achados: 2, revisado: false, processos: 2, relevantes: 1, homonimos: 1 },
    PREFEITURA: { frente: 'PREFEITURA', status: 'NAO_INICIADO', integracao: 'NAO_CONFIGURADO', pendencias: [], achados: 0, revisado: false, debitos_municipais: 0, total_em_aberto: 0 },
    LOCALIZACAO: { frente: 'LOCALIZACAO', status: 'NAO_INICIADO', integracao: 'NAO_CONFIGURADO', pendencias: ['Coordenadas não geocodificadas/confirmadas.'], achados: 0, revisado: false, geocodificado: false, coordenadas_confirmadas: false },
  },
  localizacao: {
    property_id: 7,
    endereco: 'Rua Teste, 100, Curitiba, PR',
    latitude: null,
    longitude: null,
    coordinates_confirmed: false,
    maps_url: 'https://www.google.com/maps/search/?api=1&query=Rua%20Teste',
    street_view_url: 'https://www.google.com/maps/search/?api=1&query=Rua%20Teste&layer=c',
    location_checklist: [
      { key: 'acesso_viario', label: 'Acesso viário', rating: 'NAO_VERIFICADO' },
      { key: 'transporte_publico', label: 'Transporte público', rating: 'NAO_VERIFICADO' },
    ],
    observations: null,
    integracao_maps: 'NAO_CONFIGURADO',
  },
}

describe('DueDiligenceSection', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
    globalThis.fetch = vi.fn()
  })

  it('exibe os quatro cards de due diligence', async () => {
    vi.mocked(fetch).mockReturnValueOnce(response(overview))
    render(<DueDiligenceSection propertyId={7} />)
    expect(await screen.findByText('Matrícula e ônus')).toBeInTheDocument()
    expect(screen.getByText('Processos judiciais')).toBeInTheDocument()
    expect(screen.getByText('Prefeitura e IPTU')).toBeInTheDocument()
    expect(screen.getByText('Localização e entorno')).toBeInTheDocument()
  })

  it('distingue estados: consultado x não consultado x não configurado', async () => {
    vi.mocked(fetch).mockReturnValueOnce(response(overview))
    render(<DueDiligenceSection propertyId={7} />)
    await screen.findByText('Matrícula e ônus')
    expect(screen.getByText('Consultado')).toBeInTheDocument()       // JUDICIAL
    expect(screen.getAllByText('Não consultado').length).toBeGreaterThan(0)  // MATRICULA/PREFEITURA/LOCALIZACAO
    // nunca usa "sem riscos"
    expect(screen.queryByText(/sem riscos/i)).toBeNull()
  })

  it('mostra links externos e status de integração não configurada na localização', async () => {
    vi.mocked(fetch).mockReturnValueOnce(response(overview))
    render(<DueDiligenceSection propertyId={7} />)
    await screen.findByText('Localização e entorno')
    expect(screen.getByText('Abrir no Google Maps')).toBeInTheDocument()
    expect(screen.getByText('Street View')).toBeInTheDocument()
    // checklist de localização renderizado
    expect(screen.getByText('Acesso viário')).toBeInTheDocument()
  })

  it('registra um débito municipal (consulta manual) reutilizando /dividas', async () => {
    vi.mocked(fetch)
      .mockReturnValueOnce(response(overview))
      .mockReturnValueOnce(response({ divida: {}, financeiro: {} }))
      .mockReturnValueOnce(response(overview))
    render(<DueDiligenceSection propertyId={7} />)
    await screen.findByText('Prefeitura e IPTU')
    fireEvent.click(screen.getByRole('button', { name: /Registrar débito/ }))
    fireEvent.change(screen.getByLabelText('Valor'), { target: { value: '1200' } })
    fireEvent.click(screen.getByRole('button', { name: 'Salvar débito' }))
    await waitFor(() => {
      const call = vi.mocked(fetch).mock.calls.find(([url, init]) => String(url).endsWith('/due-diligence/prefeitura/debito') && init?.method === 'POST')
      expect(call).toBeTruthy()
      const body = JSON.parse(String(call?.[1]?.body))
      expect(body.amount).toBe(1200)
    })
  })

  it('exibe erro quando o carregamento falha', async () => {
    vi.mocked(fetch).mockReturnValueOnce(response({ detail: 'Falhou' }, false, 500))
    render(<DueDiligenceSection propertyId={7} />)
    expect(await screen.findByText('Não foi possível carregar')).toBeInTheDocument()
  })
})
