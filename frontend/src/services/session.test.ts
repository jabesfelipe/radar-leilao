import { afterEach, describe, expect, it, vi } from 'vitest'

// Cada teste recarrega o módulo para reiniciar o estado (token em memória e flag de
// instalação idempotente do wrapper de fetch).
async function loadSession(status: number) {
  vi.resetModules()
  localStorage.clear()
  const fetchMock = vi.fn(async () => new Response('{}', { status }))
  window.fetch = fetchMock as unknown as typeof window.fetch
  const session = await import('./session')
  session.installAuthFetch()
  return { session, fetchMock }
}

function recordEvents(names: string[]) {
  const seen: string[] = []
  const handlers = names.map((name) => {
    const handler = () => seen.push(name)
    window.addEventListener(name, handler)
    return [name, handler] as const
  })
  return { seen, stop: () => handlers.forEach(([name, handler]) => window.removeEventListener(name, handler)) }
}

describe('session / installAuthFetch', () => {
  afterEach(() => { localStorage.clear() })

  it('injeta Authorization Bearer nas chamadas /api quando há sessão', async () => {
    const { session, fetchMock } = await loadSession(200)
    session.setSession('token-de-teste', null)
    await window.fetch('/api/imoveis')
    const init = (fetchMock.mock.calls[0] as unknown[])[1] as RequestInit
    expect(new Headers(init.headers).get('Authorization')).toBe('Bearer token-de-teste')
  })

  it('não envia o token para URLs que não são da API', async () => {
    const { session, fetchMock } = await loadSession(200)
    session.setSession('token-de-teste', null)
    await window.fetch('https://example.com/outra-coisa')
    const init = (fetchMock.mock.calls[0] as unknown[])[1] as RequestInit | undefined
    expect(init?.headers ? new Headers(init.headers).get('Authorization') : null).toBeNull()
  })

  it('401 limpa a sessão e sinaliza radar:unauthorized', async () => {
    const { session } = await loadSession(401)
    session.setSession('expirado', null)
    const events = recordEvents(['radar:unauthorized', 'radar:forbidden'])
    await window.fetch('/api/imoveis')
    events.stop()
    expect(session.isAuthenticated()).toBe(false)
    expect(events.seen).toEqual(['radar:unauthorized'])
  })

  it('403 mantém a sessão e sinaliza radar:forbidden (sem deslogar)', async () => {
    const { session } = await loadSession(403)
    session.setSession('valido', null)
    const events = recordEvents(['radar:unauthorized', 'radar:forbidden'])
    await window.fetch('/api/imoveis/1/analisar', { method: 'POST' })
    events.stop()
    expect(session.isAuthenticated()).toBe(true)
    expect(events.seen).toEqual(['radar:forbidden'])
  })

  it('429 sinaliza radar:rate-limited e mantém a sessão', async () => {
    const { session } = await loadSession(429)
    session.setSession('valido', null)
    const events = recordEvents(['radar:rate-limited', 'radar:unauthorized'])
    await window.fetch('/api/imoveis/1/analisar', { method: 'POST' })
    events.stop()
    expect(session.isAuthenticated()).toBe(true)
    expect(events.seen).toEqual(['radar:rate-limited'])
  })
})
