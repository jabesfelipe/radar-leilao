import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { MarketSection } from './MarketSection'

const comparable = { id: 1, property_id: 5, kind: 'VENDA', price: 300000, rent: null, area_m2: 70, source: 'Portal', url: 'https://exemplo.com/anuncio' }

const marketBody = {
  property_id: 5,
  mercado: {
    venda: { quantidade: 1, preco_medio: 300000, preco_mediano: 300000, preco_m2_medio: 4285, preco_m2_mediano: 4285, qualidade: { quantidade: 1, amostra_suficiente: false, dispersao_elevada: false, avaliacao_definitiva: false, avisos: ['Amostra insuficiente'] } },
    aluguel: { quantidade: 0 },
    fontes: [{ kind: 'VENDA', source: 'Portal', url: 'https://exemplo.com/anuncio' }],
    observacao: 'Estimativa baseada apenas em comparáveis cadastrados manualmente; não há verificação externa.',
  },
}

function jsonResponse(body: unknown, ok = true, status = 200) {
  return Promise.resolve({ ok, status, json: () => Promise.resolve(body) }) as Promise<Response>
}

// Roteia o mock de fetch por URL + método (resiliente à ordem das chamadas em Promise.all).
type Route = { match: (url: string, method: string) => boolean; body: unknown; ok?: boolean; status?: number }
function routeFetch(routes: Route[], fallback?: Route) {
  vi.mocked(fetch).mockImplementation((input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input)
    const method = (init?.method || 'GET').toUpperCase()
    const route = routes.find((r) => r.match(url, method)) ?? fallback
    if (!route) throw new Error(`sem rota mockada para ${method} ${url}`)
    return jsonResponse(route.body, route.ok ?? true, route.status ?? 200)
  })
}

// TASK 75.2: a listagem de comparáveis usa o endpoint dedicado /comparaveis (GET).
const listRoute = (comparaveis: unknown[]): Route => ({ match: (u, m) => u.includes('/comparaveis') && m === 'GET', body: { comparaveis } })
const marketRoute = (): Route => ({ match: (u) => u.includes('/mercado'), body: marketBody })

describe('MarketSection', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
    globalThis.fetch = vi.fn()
  })

  it('exibe carregamento e depois estado vazio', async () => {
    routeFetch([listRoute([]), marketRoute()])
    render(<MarketSection propertyId={5} />)

    expect(screen.getByRole('status')).toHaveTextContent('Carregando comparáveis')
    expect(await screen.findByText('Nenhum comparável cadastrado')).toBeInTheDocument()
  })

  it('lista comparáveis existentes', async () => {
    routeFetch([listRoute([comparable]), marketRoute()])
    render(<MarketSection propertyId={5} />)

    expect(await screen.findByText('VENDA')).toBeInTheDocument()
    expect(screen.getByText('70 m²')).toBeInTheDocument()
    expect(screen.getAllByText('Portal').length).toBeGreaterThan(0)
  })

  it('exibe a qualidade da amostra do mercado', async () => {
    routeFetch([listRoute([comparable]), marketRoute()])
    render(<MarketSection propertyId={5} />)

    expect(await screen.findByText('Amostra insuficiente')).toBeInTheDocument()
  })

  it('valida o tipo e cadastra um comparável', async () => {
    routeFetch([
      listRoute([]),
      marketRoute(),
      { match: (u, m) => u.includes('/comparaveis') && m === 'POST', body: comparable },
    ])
    render(<MarketSection propertyId={5} />)
    await screen.findByText('Nenhum comparável cadastrado')

    fireEvent.click(screen.getAllByRole('button', { name: 'Novo comparável' })[0])
    fireEvent.click(screen.getByRole('button', { name: 'Salvar comparável' }))
    expect(await screen.findByText('Informe o tipo do comparável.')).toBeInTheDocument()

    fireEvent.change(screen.getByLabelText('Tipo'), { target: { value: 'VENDA' } })
    fireEvent.click(screen.getByRole('button', { name: 'Salvar comparável' }))

    expect(await screen.findByText('Comparável cadastrado com sucesso.')).toBeInTheDocument()
    const postCall = vi.mocked(fetch).mock.calls.find((c) => String(c[0]).includes('/comparaveis') && (c[1] as RequestInit)?.method === 'POST')
    expect(postCall).toBeTruthy()
    expect(JSON.parse(String((postCall![1] as RequestInit).body)).kind).toBe('VENDA')
  })

  it('exibe erro de cadastro da API', async () => {
    routeFetch([
      listRoute([]),
      marketRoute(),
      { match: (u, m) => u.includes('/comparaveis') && m === 'POST', body: { detail: 'Dados inválidos' }, ok: false, status: 422 },
    ])
    render(<MarketSection propertyId={5} />)
    await screen.findByText('Nenhum comparável cadastrado')

    fireEvent.click(screen.getAllByRole('button', { name: 'Novo comparável' })[0])
    fireEvent.change(screen.getByLabelText('Tipo'), { target: { value: 'VENDA' } })
    fireEvent.click(screen.getByRole('button', { name: 'Salvar comparável' }))

    expect(await screen.findByText('Dados inválidos')).toBeInTheDocument()
  })

  it('edita um comparável (recalcula mercado)', async () => {
    routeFetch([
      listRoute([comparable]),
      marketRoute(),
      { match: (u, m) => /\/comparaveis\/1$/.test(u) && m === 'PATCH', body: { comparavel: { ...comparable, price: 350000 }, mercado: marketBody.mercado } },
    ])
    render(<MarketSection propertyId={5} />)
    await screen.findByText('VENDA')
    fireEvent.click(screen.getByRole('button', { name: /Editar/ }))
    fireEvent.change(screen.getByLabelText('Preço (opcional)'), { target: { value: '350000' } })
    fireEvent.click(screen.getByRole('button', { name: 'Salvar alterações' }))
    expect(await screen.findByText(/Comparável atualizado/)).toBeInTheDocument()
    const patchCall = vi.mocked(fetch).mock.calls.find((c) => /\/comparaveis\/1$/.test(String(c[0])) && (c[1] as RequestInit)?.method === 'PATCH')
    expect(patchCall).toBeTruthy()
  })

  it('exclui um comparável após confirmação', async () => {
    vi.spyOn(window, 'confirm').mockReturnValue(true)
    routeFetch([
      listRoute([comparable]),
      marketRoute(),
      { match: (u, m) => /\/comparaveis\/1$/.test(u) && m === 'DELETE', body: { removido: 1 } },
    ])
    render(<MarketSection propertyId={5} />)
    await screen.findByText('VENDA')
    fireEvent.click(screen.getByRole('button', { name: /Excluir/ }))
    expect(await screen.findByText(/Comparável excluído/)).toBeInTheDocument()
    const delCall = vi.mocked(fetch).mock.calls.find((c) => /\/comparaveis\/1$/.test(String(c[0])) && (c[1] as RequestInit)?.method === 'DELETE')
    expect(delCall).toBeTruthy()
  })

  it('trata erro ao carregar e permite tentar novamente', async () => {
    // 1ª carga: lista falha. Após "tentar novamente": tudo ok.
    let falhou = false
    vi.mocked(fetch).mockImplementation((input: RequestInfo | URL) => {
      const url = String(input)
      if (url.includes('/comparaveis') && !falhou) {
        falhou = true
        return jsonResponse({ detail: 'Falha' }, false, 500)
      }
      if (url.includes('/comparaveis')) return jsonResponse({ comparaveis: [comparable] })
      if (url.includes('/mercado')) return jsonResponse(marketBody)
      throw new Error(`sem rota para ${url}`)
    })
    render(<MarketSection propertyId={5} />)

    fireEvent.click(await screen.findByRole('button', { name: 'Tentar novamente' }))
    await waitFor(() => expect(screen.getByText('VENDA')).toBeInTheDocument())
  })
})
