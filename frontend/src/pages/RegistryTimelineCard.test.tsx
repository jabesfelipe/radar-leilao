import { fireEvent, render, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { RegistryTimelineCard } from './RegistryTimelineCard'

const timeline = {
  property_id: 5, disponivel: true, atos_lidos: ['R-2', 'Av-4'], aviso_nomes: 'Nomes lidos na matrícula, exibidos só para usuários autenticados.',
  idade: { anos: 24, estimada: true, base: 'Av-4', texto: 'Idade estimada de 24 ano(s), a partir da averbação de conclusão de obra (Av-4, 02/03/2002).' },
  datas_chave: { aquisicao: { data: '2001-02-01', ato: 'R-2' }, consolidacao: null },
  eventos: [
    { ato: 'R-2', numero: 2, tipo: 'COMPRA_VENDA', tipo_descricao: 'Compra e venda', data: '2001-02-01', data_texto: '01/02/2001',
      partes: [{ papel: 'VENDEDOR', papel_descricao: 'Vendedor', nome: 'CONSTRUTORA FICTÍCIA LTDA', tipo_pessoa: 'JURIDICA', como_identificado: 'texto' },
        { papel: 'COMPRADOR', papel_descricao: 'Comprador', nome: 'COMPRADOR TESTE FICTÍCIO', tipo_pessoa: 'FISICA', como_identificado: 'texto' }],
      valor: { valor: '111111.11', texto: 'R$ 111.111,11', rotulo: 'preço' }, construtora: 'CONSTRUTORA FICTÍCIA LTDA', conclusao_obra: false,
      trecho: 'R-2 - Matrícula nº 99.999 - COMPRA E VENDA.', chunk_id: 1, pagina: null, secao: 'Página 1',
      documento: { document_id: 1, document_version_id: 1, nome: 'matricula.txt' }, fonte: 'matrícula anexada' },
    { ato: 'Av-4', numero: 4, tipo: 'CONCLUSAO_OBRA', tipo_descricao: 'Conclusão de obra / habite-se', data: '2002-03-02', data_texto: '02/03/2002',
      partes: [], valor: null, construtora: null, conclusao_obra: true, trecho: 'Av-4 - CONCLUSÃO DA OBRA.', chunk_id: 2, pagina: null, secao: null,
      documento: { document_id: 1, document_version_id: 1, nome: 'matricula.txt' }, fonte: 'matrícula anexada' },
  ],
}

describe('RegistryTimelineCard', () => {
  beforeEach(() => { vi.restoreAllMocks(); globalThis.fetch = vi.fn() })

  it('carrega sob demanda e mostra atos, partes, valor, idade e trecho', async () => {
    vi.mocked(fetch).mockReturnValue(Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve(timeline) }) as Promise<Response>)
    render(<RegistryTimelineCard propertyId={5} />)
    expect(fetch).not.toHaveBeenCalled()
    fireEvent.click(screen.getByRole('button', { name: 'Mostrar linha do tempo' }))
    expect(await screen.findByText(/Idade estimada de 24 ano/)).toBeInTheDocument()
    expect(String(vi.mocked(fetch).mock.calls[0][0])).toContain('/api/imoveis/5/matricula/linha-do-tempo')
    expect(screen.getByText('COMPRADOR TESTE FICTÍCIO')).toBeInTheDocument()
    expect(screen.getAllByText('Conclusão de obra').length).toBeGreaterThan(0)
    expect(screen.getByText('“R-2 - Matrícula nº 99.999 - COMPRA E VENDA.”')).toBeInTheDocument()
    expect(screen.getByText(/R\$\s?111\.111,11/)).toBeInTheDocument()
  })

  it('sem matrícula com texto informa o motivo', async () => {
    vi.mocked(fetch).mockReturnValue(Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve({
      property_id: 5, disponivel: false, motivo: 'Sem matrícula com texto anexada ao imóvel.', eventos: [], atos_lidos: [], datas_chave: {},
      idade: { anos: null, estimada: false, base: null, texto: 'Idade não determinável pela matrícula.' } }) }) as Promise<Response>)
    render(<RegistryTimelineCard propertyId={5} />)
    fireEvent.click(screen.getByRole('button', { name: 'Mostrar linha do tempo' }))
    expect(await screen.findByText('Sem matrícula com texto anexada ao imóvel.')).toBeInTheDocument()
  })
})
