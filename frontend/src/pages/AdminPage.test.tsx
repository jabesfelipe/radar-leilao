import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { AdminPage } from './AdminPage'

function ok(body: unknown, status = 200) {
  return Promise.resolve({ ok: status < 400, status, json: () => Promise.resolve(body) }) as Promise<Response>
}

const municipios = { total: 4, itens: [
  { id: 1, name: 'Curitiba', state: 'PR', ibge_code: '4106902', coverage_active: true, status: 'ATIVO' },
  { id: 2, name: 'Assis', state: 'SP', ibge_code: '3504008', coverage_active: true, status: 'ATIVO' },
] }
const parametros = { total: 1, itens: [
  { id: 10, key: 'condominio.margem_seguranca_pct', name: 'Margem', category: 'estimativa', data_type: 'DECIMAL', scope: 'GLOBAL', value: '0.1', status: 'ATIVO', version: 1, updated_by: 'admin' },
] }
const tipos = { total: 1, itens: [{ id: 1, code: 'IPTU', label: 'IPTU', group: 'MUNICIPAL', default_nature: 'DIVIDA_EXISTENTE', impacts_finance: true, active: true }] }

function routeFetch() {
  globalThis.fetch = vi.fn((input: RequestInfo | URL) => {
    const url = String(input)
    if (url.includes('/api/admin/municipios')) return ok(municipios)
    if (url.includes('/api/admin/parametros')) return ok(parametros)
    if (url.includes('/api/admin/tipos-debito')) return ok(tipos)
    if (url.includes('/api/admin/fontes')) return ok({ total: 0, itens: [] })
    return ok({ total: 0, itens: [] })
  }) as unknown as typeof fetch
}

describe('AdminPage', () => {
  beforeEach(() => { vi.restoreAllMocks(); routeFetch() })

  it('mostra a visão geral com contagens', async () => {
    render(<AdminPage />)
    expect(await screen.findByText('Municípios cadastrados')).toBeInTheDocument()
    // 4 municípios no overview
    await waitFor(() => expect(screen.getByText('4')).toBeInTheDocument())
  })

  it('exige token para escrita e protege a UI com aviso', async () => {
    render(<AdminPage />)
    expect(await screen.findByText(/exigem o token de administração/i)).toBeInTheDocument()
  })

  it('lista municípios ao abrir a aba', async () => {
    render(<AdminPage />)
    fireEvent.click(screen.getByRole('button', { name: 'Municípios' }))
    expect(await screen.findByText('Curitiba')).toBeInTheDocument()
    expect(screen.getByText('Assis')).toBeInTheDocument()
  })

  it('lista parâmetros e oferece editar/histórico', async () => {
    render(<AdminPage />)
    fireEvent.click(screen.getByRole('button', { name: 'Parâmetros' }))
    expect(await screen.findByText('condominio.margem_seguranca_pct')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Editar' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Histórico' })).toBeInTheDocument()
  })
})
