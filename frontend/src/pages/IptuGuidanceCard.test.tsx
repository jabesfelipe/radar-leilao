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
})
