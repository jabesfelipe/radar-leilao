import { beforeEach, describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { LoginPage } from './LoginPage'

function ok(body: unknown, status = 200) {
  return Promise.resolve({ ok: status < 400, status, json: () => Promise.resolve(body) }) as Promise<Response>
}

describe('LoginPage', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
    try { localStorage.clear() } catch { /* noop */ }
  })

  it('autentica com credenciais válidas e chama onAuthenticated', async () => {
    globalThis.fetch = vi.fn((input: RequestInfo | URL) => {
      const url = String(input)
      if (url.includes('/api/auth/login')) return ok({ access_token: 'jwt-abc', token_type: 'bearer', expires_in: 3600 })
      if (url.includes('/api/auth/me')) return ok({ user: { id: 1, email: 'a@b.com', name: 'A', role: 'ADMIN', active: true, created_at: '2026-01-01' }, permissions: ['read'] })
      return ok({})
    }) as unknown as typeof fetch
    const onAuth = vi.fn()
    render(<LoginPage onAuthenticated={onAuth} />)
    fireEvent.change(screen.getByLabelText('E-mail'), { target: { value: 'a@b.com' } })
    fireEvent.change(screen.getByLabelText('Senha'), { target: { value: 'senha-forte-123' } })
    fireEvent.click(screen.getByRole('button', { name: 'Entrar' }))
    await waitFor(() => expect(onAuth).toHaveBeenCalled())
  })

  it('exibe erro em credenciais inválidas', async () => {
    globalThis.fetch = vi.fn(() => ok({ detail: 'Credenciais inválidas.' }, 401)) as unknown as typeof fetch
    render(<LoginPage onAuthenticated={vi.fn()} />)
    fireEvent.change(screen.getByLabelText('E-mail'), { target: { value: 'a@b.com' } })
    fireEvent.change(screen.getByLabelText('Senha'), { target: { value: 'errada12' } })
    fireEvent.click(screen.getByRole('button', { name: 'Entrar' }))
    expect(await screen.findByText('Credenciais inválidas.')).toBeInTheDocument()
  })
})
