import { fireEvent, render, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { IptuGuidanceCard } from './IptuGuidanceCard'

describe('IptuGuidanceCard', () => {
  beforeEach(() => { vi.restoreAllMocks(); globalThis.fetch = vi.fn() })

  it('mostra consulta manual assistida com portal, exigências e passos', async () => {
    vi.mocked(fetch).mockReturnValue(Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve({
      property_id: 7, municipality_id: 3, inscricao_imobiliaria: '000000000000', motivo: null,
      orientacao: { municipio: 'Fazenda Rio Grande/PR', automatizado: false, modo: 'MANUAL_ASSISTIDA', motivo: 'Consulta feita pelo CPF/CNPJ do proprietário.',
        fonte: 'Prefeitura de Fazenda Rio Grande', urls: ['https://www.fazendariogrande.pr.gov.br/divisao-de-arrecadacao'], identificador: 'CPF ou CNPJ do proprietário',
        exigencias: ['CPF ou CNPJ do proprietário'], passos: ['Abrir a página da Divisão de Arrecadação.', 'Registrar o resultado na Central de Débitos.'],
        aviso: 'Consulta sem resultado ou indisponível não significa ausência de débito.' },
    }) }) as Promise<Response>)
    render(<IptuGuidanceCard propertyId={7} />)
    expect(fetch).not.toHaveBeenCalled()
    fireEvent.click(screen.getByRole('button', { name: 'Como consultar o IPTU' }))
    expect(await screen.findByText('Consulta manual assistida')).toBeInTheDocument()
    expect(String(vi.mocked(fetch).mock.calls[0][0])).toContain('/api/imoveis/7/debitos/orientacao-iptu')
    expect(screen.getByText('Registrar o resultado na Central de Débitos.')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'https://www.fazendariogrande.pr.gov.br/divisao-de-arrecadacao' })).toHaveAttribute('rel', 'noopener noreferrer')
    expect(screen.getByText(/não significa ausência de débito/)).toBeInTheDocument()
  })

  it('registra o resultado da consulta assistida e o IPTU anual nas premissas', async () => {
    const calls: Array<{ url: string; init?: RequestInit }> = []
    const ok = (body: unknown) => Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve(body) }) as Promise<Response>
    let consulted = false
    vi.mocked(fetch).mockImplementation((input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input)
      calls.push({ url, init })
      if (url.endsWith('/debitos/orientacao-iptu')) return ok({ property_id: 7, municipality_id: 3, inscricao_imobiliaria: '01.02', motivo: null, orientacao: null })
      if (url.endsWith('/iptu/situacao')) return ok({ status: consulted ? 'CONSULTADO' : 'PENDENTE_CONSULTA', status_label: consulted ? 'Consultado' : 'Pendente de consulta', texto: 'x' })
      if (url.endsWith('/debitos/consultar')) { consulted = true; return ok({ consulta: { status: 'CONCLUIDA' } }) }
      if (url.endsWith('/financeiro')) return ok({ property_id: 7, premissas: { corretagem_pct: 0.05 }, financeiro: {} })
      return ok({ property_id: 7, premissas: {}, financeiro: {} })
    })
    render(<IptuGuidanceCard propertyId={7} />)
    fireEvent.click(screen.getByRole('button', { name: 'Como consultar o IPTU' }))
    expect(await screen.findByText('Pendente de consulta')).toBeInTheDocument()
    fireEvent.change(screen.getByLabelText('Valor do débito em aberto'), { target: { value: '850,00' } })
    fireEvent.change(screen.getByLabelText('IPTU anual'), { target: { value: '1.200,00' } })
    fireEvent.click(screen.getByRole('button', { name: 'Registrar resultado' }))
    expect(await screen.findByText(/Resultado registrado/)).toBeInTheDocument()
    const query = calls.find((c) => c.url.endsWith('/debitos/consultar'))!
    expect(JSON.parse(String(query.init?.body))).toMatchObject({ debt_type_code: 'IPTU', municipality_id: 3, itens: [{ updated_amount: 850 }] })
    const put = calls.find((c) => c.init?.method === 'PUT')!
    expect(JSON.parse(String(put.init?.body))).toMatchObject({ corretagem_pct: 0.05, iptu_anual: 1200 })
    expect(await screen.findByText('Consultado')).toBeInTheDocument()
  })
})
