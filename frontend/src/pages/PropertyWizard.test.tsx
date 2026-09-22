import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { PropertyWizard } from './PropertyWizard'

function response(body: unknown, ok = true, status = 200) {
  return Promise.resolve({ ok, status, json: () => Promise.resolve(body) }) as Promise<Response>
}

describe('PropertyWizard', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
    globalThis.fetch = vi.fn()
  })

  it('percorre as etapas, envia o cadastro completo e navega para o dossiê', async () => {
    const onCreated = vi.fn()
    vi.mocked(fetch).mockReturnValueOnce(response({ id: 42, status: 'EM_ANALISE' }, true, 201))

    render(<PropertyWizard onCancel={() => {}} onCreated={onCreated} />)

    // Etapa 1 — dados básicos
    fireEvent.change(screen.getByLabelText('Nome / identificação'), { target: { value: 'COND PARQUE ARVOREDO' } })
    fireEvent.change(screen.getByLabelText('Cidade'), { target: { value: 'Curitiba' } })
    fireEvent.change(screen.getByLabelText('Estado (UF)'), { target: { value: 'pr' } })
    fireEvent.change(screen.getByLabelText('Quartos'), { target: { value: '3' } })
    fireEvent.click(screen.getByRole('button', { name: 'Avançar' }))

    // Etapa 2 — leilão
    expect(await screen.findByText('1º leilão')).toBeInTheDocument()
    fireEvent.change(screen.getByLabelText('Valor de avaliação (R$)'), { target: { value: '370000' } })
    fireEvent.change(screen.getByLabelText('Valor do 2º leilão (R$)'), { target: { value: '222000' } })
    fireEvent.change(screen.getByLabelText('Número da matrícula'), { target: { value: '25278' } })
    fireEvent.click(screen.getByRole('button', { name: 'Avançar' }))

    // Etapa 3 — fontes
    expect(await screen.findByText('Adicionar fonte')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Avançar' }))

    // Etapa 4 — documentos
    expect(await screen.findByText('Selecionar arquivos')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Avançar' }))

    // Etapa 5 — revisão
    expect(await screen.findByText('COND PARQUE ARVOREDO')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Salvar imóvel' }))

    await waitFor(() => expect(onCreated).toHaveBeenCalledWith(42))

    const postOptions = vi.mocked(fetch).mock.calls[0]?.[1]
    expect(String(vi.mocked(fetch).mock.calls[0]?.[0])).toContain('/api/imoveis/completo')
    const payload = JSON.parse(String(postOptions?.body))
    expect(payload.imovel.title).toBe('COND PARQUE ARVOREDO')
    expect(payload.imovel.state).toBe('PR')
    expect(payload.imovel.bedrooms).toBe(3)
    expect(payload.leilao.appraisal_value).toBe(370000)
    expect(payload.leilao.second_auction_value).toBe(222000)
    expect(payload.matricula.registration_number).toBe('25278')
  })

  it('quando um upload falha, mantém o imóvel e avisa o usuário sem navegar automaticamente', async () => {
    const onCreated = vi.fn()
    // 1) cadastro OK  2) upload edital OK  3) upload matrícula FALHA
    vi.mocked(fetch)
      .mockReturnValueOnce(response({ id: 55, status: 'EM_ANALISE' }, true, 201))
      .mockReturnValueOnce(response({ id: 1, versions: [] }, true, 200))
      .mockReturnValueOnce(response({ detail: 'Falha ao processar documento' }, false, 422))

    render(<PropertyWizard onCancel={() => {}} onCreated={onCreated} />)

    fireEvent.change(screen.getByLabelText('Nome / identificação'), { target: { value: 'Imóvel com docs' } })
    fireEvent.change(screen.getByLabelText('Cidade'), { target: { value: 'Curitiba' } })
    fireEvent.change(screen.getByLabelText('Estado (UF)'), { target: { value: 'PR' } })
    fireEvent.click(screen.getByRole('button', { name: 'Avançar' }))
    fireEvent.click(await screen.findByRole('button', { name: 'Avançar' })) // leilão -> fontes
    fireEvent.click(await screen.findByRole('button', { name: 'Avançar' })) // fontes -> documentos

    // seleciona dois arquivos na etapa de documentos
    const edital = new File(['a'], 'edital.pdf', { type: 'application/pdf' })
    const matricula = new File(['b'], 'matricula.pdf', { type: 'application/pdf' })
    const fileInput = document.querySelector('input[type="file"]') as HTMLInputElement
    fireEvent.change(fileInput, { target: { files: [edital, matricula] } })

    fireEvent.click(screen.getByRole('button', { name: 'Avançar' })) // documentos -> revisão
    fireEvent.click(await screen.findByRole('button', { name: 'Salvar imóvel' }))

    // não navega automaticamente; mostra aviso identificando o documento que falhou
    expect(await screen.findByText('Atenção com os documentos')).toBeInTheDocument()
    expect(screen.getByText('matricula.pdf')).toBeInTheDocument()
    expect(onCreated).not.toHaveBeenCalled()

    // o usuário decide ir ao dossiê
    fireEvent.click(screen.getByRole('button', { name: 'Ir para o dossiê' }))
    await waitFor(() => expect(onCreated).toHaveBeenCalledWith(55))
  })

  it('valida URL de fonte inválida antes de avançar', async () => {
    render(<PropertyWizard onCancel={() => {}} onCreated={() => {}} />)

    fireEvent.change(screen.getByLabelText('Nome / identificação'), { target: { value: 'Imóvel Teste' } })
    fireEvent.change(screen.getByLabelText('Cidade'), { target: { value: 'Curitiba' } })
    fireEvent.change(screen.getByLabelText('Estado (UF)'), { target: { value: 'PR' } })
    fireEvent.click(screen.getByRole('button', { name: 'Avançar' }))

    // pula leilão
    fireEvent.click(await screen.findByRole('button', { name: 'Avançar' }))

    // fontes: adiciona uma com URL inválida
    fireEvent.click(await screen.findByRole('button', { name: 'Adicionar fonte' }))
    fireEvent.change(screen.getByLabelText('URL'), { target: { value: 'not-a-url' } })
    fireEvent.click(screen.getByRole('button', { name: 'Avançar' }))

    expect(await screen.findByText('URL inválida (use http:// ou https://).')).toBeInTheDocument()
  })
})
