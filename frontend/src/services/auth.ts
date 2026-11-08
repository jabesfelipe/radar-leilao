// Serviço de autenticação (Onda 11): login, me, gestão de usuários.
import { setSession, clearSession, type SessionUser } from './session'

const API_BASE_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

export class AuthServiceError extends Error {
  status?: number
  constructor(message: string, status?: number) {
    super(message); this.name = 'AuthServiceError'; this.status = status
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response
  try { response = await fetch(`${API_BASE_URL}${path}`, init) }
  catch { throw new AuthServiceError('Não foi possível conectar ao servidor. Tente novamente.') }
  const payload = await response.json().catch(() => null)
  if (!response.ok) {
    const detail = typeof payload?.detail === 'string' ? payload.detail : 'Não foi possível concluir a operação.'
    throw new AuthServiceError(detail, response.status)
  }
  return payload as T
}

const json = (body: unknown): RequestInit => ({ method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) })

export type Me = { user: SessionUser & { active: boolean; last_login_at?: string | null; created_at: string }; permissions: string[] }

export async function login(email: string, password: string): Promise<Me> {
  const tok = await request<{ access_token: string }>('/api/auth/login', json({ email, password }))
  setSession(tok.access_token, null)
  const me = await request<Me>('/api/auth/me')
  setSession(tok.access_token, { id: me.user.id, email: me.user.email, name: me.user.name, role: me.user.role })
  return me
}

export function logout() { clearSession() }

export function getMe(): Promise<Me> { return request<Me>('/api/auth/me') }

export type AppUser = { id: number; email: string; name: string; role: string; active: boolean; last_login_at?: string | null; created_at: string }

export const listUsers = () => request<{ total: number; itens: AppUser[] }>('/api/auth/usuarios')
export const createUser = (data: { email: string; name?: string; password: string; role: string; active?: boolean }) =>
  request<AppUser>('/api/auth/usuarios', json(data))
export const updateUser = (id: number, data: Partial<{ name: string; role: string; active: boolean; password: string }>) =>
  request<AppUser>(`/api/auth/usuarios/${id}`, { method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) })
