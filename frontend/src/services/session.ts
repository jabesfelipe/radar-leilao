// Sessão/autenticação do frontend (Onda 11).
//
// Guarda o JWT (memória + localStorage) e instala UMA vez um wrapper em window.fetch
// que injeta o header Authorization em chamadas à API e sinaliza 401/403 (sessão
// expirada / sem permissão) via evento, sem precisar editar os ~16 serviços. O token
// nunca é logado; a instalação é idempotente.

const API_BASE_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'
const STORAGE_KEY = 'radar.auth.token'
const USER_KEY = 'radar.auth.user'

export type SessionUser = { id: number; email: string; name: string; role: string }

let token: string | null = null
let currentUser: SessionUser | null = null

function load() {
  try {
    token = localStorage.getItem(STORAGE_KEY)
    const raw = localStorage.getItem(USER_KEY)
    currentUser = raw ? (JSON.parse(raw) as SessionUser) : null
  } catch { token = null; currentUser = null }
}
load()

export function getToken(): string | null { return token }
export function getUser(): SessionUser | null { return currentUser }
export function isAuthenticated(): boolean { return !!token }

export function setSession(accessToken: string, user: SessionUser | null) {
  token = accessToken
  currentUser = user
  try {
    localStorage.setItem(STORAGE_KEY, accessToken)
    if (user) localStorage.setItem(USER_KEY, JSON.stringify(user))
  } catch { /* storage indisponível: mantém em memória */ }
  window.dispatchEvent(new CustomEvent('radar:auth-changed'))
}

export function clearSession() {
  token = null
  currentUser = null
  try { localStorage.removeItem(STORAGE_KEY); localStorage.removeItem(USER_KEY) } catch { /* noop */ }
  window.dispatchEvent(new CustomEvent('radar:auth-changed'))
}

// Instala o wrapper global de fetch (idempotente). Injeta Authorization em chamadas à
// API e emite 'radar:unauthorized' em 401 (para o App redirecionar ao login).
let installed = false
export function installAuthFetch() {
  if (installed || typeof window === 'undefined' || !window.fetch) return
  installed = true
  const original = window.fetch.bind(window)
  window.fetch = async (input: RequestInfo | URL, init?: RequestInit): Promise<Response> => {
    const url = typeof input === 'string' ? input : input instanceof URL ? input.toString() : (input as Request).url
    const isApi = url.startsWith(API_BASE_URL) || url.startsWith('/api/')
    let nextInit = init
    if (isApi && token) {
      const headers = new Headers(init?.headers || (typeof input !== 'string' && !(input instanceof URL) ? (input as Request).headers : undefined))
      if (!headers.has('Authorization')) headers.set('Authorization', `Bearer ${token}`)
      nextInit = { ...init, headers }
    }
    const response = await original(input, nextInit)
    if (isApi && response.status === 401) {
      // Sessão expirada/ausente: limpa e sinaliza (o App volta ao login).
      clearSession()
      window.dispatchEvent(new CustomEvent('radar:unauthorized'))
    } else if (isApi && response.status === 403) {
      // Autenticado, mas sem permissão para a operação (RBAC no backend): mantém a
      // sessão e avisa o usuário (o App exibe a mensagem).
      window.dispatchEvent(new CustomEvent('radar:forbidden'))
    } else if (isApi && response.status === 429) {
      // Limite de requisições / operação já em andamento: avisa e permite nova tentativa.
      window.dispatchEvent(new CustomEvent('radar:rate-limited'))
    }
    return response
  }
}
