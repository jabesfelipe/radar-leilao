import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { CentralJuridicaSection } from './CentralJuridicaSection'

function response(body: unknown, ok = true, status = 200) {
  return Promise.resolve({ ok, status, json: () => Promise.resolve(body) }) as Promise<Response>
}

const provisionArt27 = {
  id: 2,
  slug: 'lei-9514-1997-art27',
  referencia: 'Art. 27',
  titulo: 'Leilões públicos após a consolidação',
  texto_oficial: 'Uma vez consolidada a propriedade em seu nome, o fiduciário... promoverá público leilão.',
  orientacao_pratica: 'São dois leilões; confira datas e notificações.',
  contextos: ['LEILAO', 'ARREMATACAO'],
  tags: ['leilao'],
  verificacao: 'VERIFICADO',
  fonte: { slug: 'lei-9514-1997', rotulo: 'Lei 9.514/97', tipo: 'LEI', url_oficial: 'https://planalto.gov.br', vigente: true },
}

const central = {
  property_id: 7,
  sintese_juridica: {
    processos_encontrados: 0,
    processos_relevantes: 0,
    pendencias: ['Validar matrícula atualizada.'],
    confirmados: [],
    correlacao: 'NAO_CONFIRMADA',
    situacao_imovel: 'NAO_CONFIRMADA',
    risco_principal: null,
    impacto_financeiro: 'NAO_QUANTIFICADO',
    diligencia_recomendada: 'Validar matrícula atualizada e documentação processual.',
  },
  itens_com_base_legal: [
    {
      canonical_key: 'NOTIFICACAO_DOIS_LEILOES',
      pergunta: 'Houve envio de notificação para a data dos dois leilões?',
      estado: 'PENDENTE',
      categoria: 'JURIDICO',
      referencias: [
        {
          id: 2, slug: 'regra-dois-leiloes', tipo: 'REQUISITO', titulo: 'Dois leilões e lance mínimo do art. 27',
          enunciado: 'Após a consolidação, o imóvel vai a dois leilões.', contextos: ['LEILAO'], severidade: null,
          base_legal: provisionArt27, itens_checklist: [],
        },
      ],
    },
  ],
  total_itens_com_base_legal: 1,
}

const library = {
  total_fontes: 5,
  total_dispositivos: 9,
  total_regras: 8,
  itens_checklist_cobertos: 11,
  itens_checklist_total: 27,
  cobertura_checklist: { NOTIFICACAO_DOIS_LEILOES: 1, EVICCAO: 1 },
  fontes: [
    {
      id: 1, slug: 'lei-9514-1997', tipo: 'LEI', rotulo: 'Lei 9.514/97',
      titulo: 'Lei 9.514/1997', orgao: 'Federal', url_oficial: 'https://planalto.gov.br', ano: 1997,
      vigente: true, verificacao: 'VERIFICADO', resumo: 'Alienação fiduciária de bem imóvel.',
      dispositivos: [provisionArt27],
    },
  ],
  regras: [],
}

describe('CentralJuridicaSection', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
    globalThis.fetch = vi.fn()
  })

  it('mostra a síntese jurídica do imóvel e a cobertura do checklist', async () => {
    vi.mocked(fetch).mockReturnValueOnce(response(central)).mockReturnValueOnce(response(library))
    render(<CentralJuridicaSection propertyId={7} />)
    expect(await screen.findByText('SITUAÇÃO JURÍDICA DO IMÓVEL')).toBeInTheDocument()
    expect(screen.getByText(/11 de 27 itens do checklist/)).toBeInTheDocument()
    expect(screen.getByText('Validar matrícula atualizada.')).toBeInTheDocument()
  })

  it('distingue texto oficial de orientação prática', async () => {
    vi.mocked(fetch).mockReturnValueOnce(response(central)).mockReturnValueOnce(response(library))
    render(<CentralJuridicaSection propertyId={7} />)
    await screen.findByText('SITUAÇÃO JURÍDICA DO IMÓVEL')
    expect(screen.getAllByText('TEXTO OFICIAL').length).toBeGreaterThan(0)
    expect(screen.getAllByText('ORIENTAÇÃO PRÁTICA (MÉTODO RADAR)').length).toBeGreaterThan(0)
  })

  it('exibe a base legal por item do checklist', async () => {
    vi.mocked(fetch).mockReturnValueOnce(response(central)).mockReturnValueOnce(response(library))
    render(<CentralJuridicaSection propertyId={7} />)
    await screen.findByText('BASE LEGAL POR ITEM DO CHECKLIST')
    expect(screen.getByText('Houve envio de notificação para a data dos dois leilões?')).toBeInTheDocument()
    expect(screen.getAllByText('Dois leilões e lance mínimo do art. 27').length).toBeGreaterThan(0)
  })

  it('faz busca textual na biblioteca', async () => {
    vi.mocked(fetch)
      .mockReturnValueOnce(response(central))
      .mockReturnValueOnce(response(library))
      .mockReturnValueOnce(response({ query: 'leilões', contexto: null, modo_busca: 'TEXTUAL', total: 1, resultados: [provisionArt27] }))
    render(<CentralJuridicaSection propertyId={7} />)
    await screen.findByText('BIBLIOTECA JURÍDICA')
    fireEvent.change(screen.getByPlaceholderText(/taxa de ocupação/), { target: { value: 'leilões' } })
    fireEvent.click(screen.getByRole('button', { name: /Buscar/ }))
    await waitFor(() => {
      const call = vi.mocked(fetch).mock.calls.find(([url]) => String(url).includes('/biblioteca/busca'))
      expect(call).toBeTruthy()
    })
    expect(await screen.findByText(/modo textual/)).toBeInTheDocument()
  })

  it('exibe erro quando o carregamento falha', async () => {
    vi.mocked(fetch).mockReturnValueOnce(response({ detail: 'Falhou' }, false, 500)).mockReturnValueOnce(response(library))
    render(<CentralJuridicaSection propertyId={7} />)
    expect(await screen.findByText('Não foi possível carregar')).toBeInTheDocument()
  })
})
