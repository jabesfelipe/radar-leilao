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
const parametros = { total: 12, itens: [
  { id: 10, key: 'condominio.margem_seguranca_pct', name: 'Margem', category: 'estimativa', data_type: 'DECIMAL', scope: 'GLOBAL', value: '0.1', status: 'ATIVO', version: 1, updated_by: 'admin' },
  { id: 11, key: 'viabilidade.fator_venda_avaliacao', name: 'Fator de venda preliminar sobre a avaliação', category: 'financeiro', data_type: 'DECIMAL', scope: 'GLOBAL', value: '0.85', default_value: '0.85', unit: 'fração', status: 'ATIVO', version: 1, updated_by: 'seed' },
  { id: 12, key: 'viabilidade.itbi_aliquota', name: 'ITBI (alíquota)', category: 'financeiro', data_type: 'DECIMAL', scope: 'GLOBAL', value: null, default_value: null, unit: 'fração', status: 'ATIVO', version: 1, updated_by: 'seed' },
  { id: 13, key: 'mercado.amostra_minima', name: 'Amostra mínima', category: 'mercado', data_type: 'INTEGER', scope: 'GLOBAL', value: '7', status: 'ATIVO', version: 1, updated_by: 'seed' },
] }
const tipos = { total: 1, itens: [{ id: 1, code: 'IPTU', label: 'IPTU', group: 'MUNICIPAL', default_nature: 'DIVIDA_EXISTENTE', impacts_finance: true, active: true }] }
const cobertura = {
  total: 1,
  itens: [{ id: 5, municipality_id: 1, debt_type_code: 'IPTU', level: 'AUTOMATIZAVEL', situation: 'DISPONIVEL', method: 'PORTAL_PUBLICO', active: true, last_validated_at: null }],
  nao_investigados: [{ municipality_id: 1, debt_type_code: 'DIVIDA_ATIVA_MUNICIPAL', level: 'NAO_INVESTIGADA' }],
  ressalva: 'Cobertura não investigada não implica ausência de débito; é um estado a ser apurado.',
}

function routeFetch() {
  globalThis.fetch = vi.fn((input: RequestInfo | URL) => {
    const url = String(input)
    if (url.includes('/api/admin/municipios')) return ok(municipios)
    if (url.includes('/api/admin/parametros')) return ok(parametros)
    if (url.includes('/api/admin/tipos-debito')) return ok(tipos)
    if (url.includes('/api/admin/cobertura')) return ok(cobertura)
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
    expect(screen.getAllByRole('button', { name: 'Editar' }).length).toBe(4)
    expect(screen.getAllByRole('button', { name: 'Histórico' }).length).toBe(4)
  })

  it('premissas financeiras: só as categorias financeiras, com padrão e pendência visíveis e valor por município', async () => {
    render(<AdminPage />)
    fireEvent.click(screen.getByRole('button', { name: 'Premissas financeiras' }))
    expect(await screen.findByText('viabilidade.fator_venda_avaliacao')).toBeInTheDocument()
    expect(screen.getByText('0.85 fração')).toBeInTheDocument()
    expect(screen.getByText('não configurado')).toBeInTheDocument()                       // ITBI sem padrão do sistema
    expect(screen.queryByText('mercado.amostra_minima')).not.toBeInTheDocument()          // outra categoria fica na aba Parâmetros
    expect(screen.getByText(/nunca sobrescreve o valor informado/)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Cadastrar valor do município' })).toBeInTheDocument()
  })

  it('mostra a matriz de cobertura com nível e cobertura não investigada', async () => {
    render(<AdminPage />)
    fireEvent.click(screen.getByRole('button', { name: 'Cobertura' }))
    // AUTOMATIZAVEL e "Cobertura não investigada" aparecem em múltiplos nós
    // (Badge/option e Alert/título do card) → usar getAllByText.
    await waitFor(() => expect(screen.getAllByText('AUTOMATIZAVEL').length).toBeGreaterThan(0))
    expect(screen.getAllByText(/Cobertura não investigada/i).length).toBeGreaterThan(0)
    expect(screen.getByText('DIVIDA_ATIVA_MUNICIPAL')).toBeInTheDocument()
  })

  it('oferece formulário de cadastro de fontes na aba Fontes', async () => {
    render(<AdminPage />)
    fireEvent.click(screen.getByRole('button', { name: 'Fontes de consulta' }))
    expect(await screen.findByText('Nova fonte')).toBeInTheDocument()
    expect(screen.getByText('Nome da fonte')).toBeInTheDocument()
  })
})
