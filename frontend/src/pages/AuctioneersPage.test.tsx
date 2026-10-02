import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { AuctioneersPage } from './AuctioneersPage'

function response(body: unknown, ok = true, status = 200) {
  return Promise.resolve({ ok, status, json: () => Promise.resolve(body) }) as Promise<Response>
}

const auctioneer = {
  id: 1, name: 'Leiloeiro X', company: 'LX', status: 'ATIVO',
  portais: [{ id: 10, auctioneer_id: 1, portal: 'Caixa', username: 'u@x', has_secret: true, two_factor_enabled: true, status: 'ATIVO' }],
  documentos: [],
}

describe('AuctioneersPage', () => {
  beforeEach(() => { vi.restoreAllMocks(); globalThis.fetch = vi.fn() })

  it('carrega e lista leiloeiros com portal (sem expor senha)', async () => {
    vi.mocked(fetch).mockReturnValueOnce(response([auctioneer]))
    render(<AuctioneersPage />)
    expect(await screen.findByRole('heading', { name: 'Leiloeiro X' })).toBeInTheDocument()
    expect(screen.getByText('Caixa')).toBeInTheDocument()
    expect(screen.getByText(/credencial salva/)).toBeInTheDocument()
    // Nenhuma senha é renderizada na listagem.
    expect(screen.queryByText(/senha/i)).not.toBeInTheDocument()
  })

  it('estado vazio quando não há leiloeiros', async () => {
    vi.mocked(fetch).mockReturnValueOnce(response([]))
    render(<AuctioneersPage />)
    expect(await screen.findByText('Nenhum leiloeiro')).toBeInTheDocument()
  })

  it('cadastra um leiloeiro', async () => {
    vi.mocked(fetch)
      .mockReturnValueOnce(response([]))
      .mockReturnValueOnce(response({ id: 2, name: 'Novo', status: 'ATIVO', portais: [], documentos: [] }, true, 201))
      .mockReturnValueOnce(response([{ id: 2, name: 'Novo', status: 'ATIVO', portais: [], documentos: [] }]))
    render(<AuctioneersPage />)
    await screen.findByText('Nenhum leiloeiro')
    fireEvent.click(screen.getAllByRole('button', { name: /Novo leiloeiro/ })[0])
    fireEvent.change(screen.getByLabelText('Nome'), { target: { value: 'Novo' } })
    fireEvent.click(screen.getByRole('button', { name: 'Salvar leiloeiro' }))
    expect(await screen.findByText('Leiloeiro cadastrado.')).toBeInTheDocument()
    const postCall = vi.mocked(fetch).mock.calls[1]
    expect(postCall[0]).toContain('/api/leiloeiros')
  })

  it('revela a credencial apenas via ação explícita, exigindo token de administração', async () => {
    // TASK 75.1: o endpoint de recuperação é protegido; a UI pede o token e o
    // envia no header X-Portal-Admin-Token. Sem token, nenhuma chamada é feita.
    vi.spyOn(window, 'prompt').mockReturnValue('token-admin-123')
    vi.mocked(fetch)
      .mockReturnValueOnce(response([auctioneer]))
      .mockReturnValueOnce(response({ portal_id: 10, username: 'u@x', secret: 'minha-senha' }))
    render(<AuctioneersPage />)
    await screen.findByRole('heading', { name: 'Leiloeiro X' })
    fireEvent.click(screen.getByRole('button', { name: /Ver credencial/ }))
    await waitFor(() => expect(screen.getByText('minha-senha')).toBeInTheDocument())
    const revealCall = vi.mocked(fetch).mock.calls[1]
    expect(revealCall[0]).toContain('/portais/10/credencial')
    const headers = (revealCall[1] as RequestInit).headers as Record<string, string>
    expect(headers['X-Portal-Admin-Token']).toBe('token-admin-123')
  })

  it('não chama o endpoint de credencial quando o token não é informado', async () => {
    vi.spyOn(window, 'prompt').mockReturnValue(null)
    vi.mocked(fetch).mockReturnValueOnce(response([auctioneer]))
    render(<AuctioneersPage />)
    await screen.findByRole('heading', { name: 'Leiloeiro X' })
    fireEvent.click(screen.getByRole('button', { name: /Ver credencial/ }))
    // Só a chamada de listagem inicial deve ter ocorrido.
    expect(vi.mocked(fetch).mock.calls).toHaveLength(1)
  })

  // TASK 75.2.1: exclusão de leiloeiro pela UI (confirmação + DELETE + reload).
  it('exclui um leiloeiro após confirmação', async () => {
    vi.spyOn(window, 'confirm').mockReturnValue(true)
    vi.mocked(fetch)
      .mockReturnValueOnce(response([auctioneer]))
      .mockReturnValueOnce(response({ removido: 1, leiloes_desvinculados: [] }))
      .mockReturnValueOnce(response([]))
    render(<AuctioneersPage />)
    await screen.findByRole('heading', { name: 'Leiloeiro X' })
    fireEvent.click(screen.getAllByRole('button', { name: /Excluir/ })[0])
    expect(await screen.findByText('Leiloeiro excluído.')).toBeInTheDocument()
    const delCall = vi.mocked(fetch).mock.calls[1]
    expect(delCall[0]).toContain('/api/leiloeiros/1')
    expect((delCall[1] as RequestInit).method).toBe('DELETE')
  })

  // TASK 75.2.1: exclusão de portal (DELETE sem expor credencial).
  it('exclui um portal após confirmação', async () => {
    vi.spyOn(window, 'confirm').mockReturnValue(true)
    vi.mocked(fetch)
      .mockReturnValueOnce(response([auctioneer]))
      .mockReturnValueOnce(response({ removido: 10, auctioneer_id: 1 }))
      .mockReturnValueOnce(response([{ ...auctioneer, portais: [] }]))
    render(<AuctioneersPage />)
    await screen.findByText('Caixa')
    // Botão "Excluir" do portal (segundo Excluir — o primeiro é do leiloeiro no head).
    const excluirButtons = screen.getAllByRole('button', { name: /Excluir/ })
    fireEvent.click(excluirButtons[excluirButtons.length - 1])
    expect(await screen.findByText('Portal/acesso excluído.')).toBeInTheDocument()
    const delCall = vi.mocked(fetch).mock.calls[1]
    expect(delCall[0]).toContain('/portais/10')
    expect((delCall[1] as RequestInit).method).toBe('DELETE')
  })

  // TASK 75.2.1: edição e exclusão de documento do leiloeiro.
  it('edita os metadados de um documento do leiloeiro', async () => {
    const comDoc = { ...auctioneer, documentos: [{ id: 50, auctioneer_id: 1, doc_type: 'CONTRATO', name: 'Credenciamento', version: 1, observations: '' }] }
    vi.mocked(fetch)
      .mockReturnValueOnce(response([comDoc]))
      .mockReturnValueOnce(response({ id: 50, auctioneer_id: 1, doc_type: 'CONTRATO', name: 'Credenciamento v2', version: 1 }))
      .mockReturnValueOnce(response([comDoc]))
    render(<AuctioneersPage />)
    await screen.findByText('Credenciamento')
    // Abre edição do documento (botão Editar na linha do documento).
    const editButtons = screen.getAllByRole('button', { name: /Editar/ })
    fireEvent.click(editButtons[editButtons.length - 1])
    fireEvent.change(screen.getByLabelText('Nome do documento'), { target: { value: 'Credenciamento v2' } })
    fireEvent.click(screen.getByRole('button', { name: 'Salvar documento' }))
    expect(await screen.findByText('Documento atualizado.')).toBeInTheDocument()
    const patchCall = vi.mocked(fetch).mock.calls[1]
    expect(patchCall[0]).toContain('/documentos/50')
    expect((patchCall[1] as RequestInit).method).toBe('PATCH')
  })

  it('exclui um documento do leiloeiro após confirmação', async () => {
    vi.spyOn(window, 'confirm').mockReturnValue(true)
    const comDoc = { ...auctioneer, documentos: [{ id: 50, auctioneer_id: 1, doc_type: 'CONTRATO', name: 'Credenciamento', version: 1, observations: '' }] }
    vi.mocked(fetch)
      .mockReturnValueOnce(response([comDoc]))
      .mockReturnValueOnce(response({ removido: 50, auctioneer_id: 1 }))
      .mockReturnValueOnce(response([{ ...comDoc, documentos: [] }]))
    render(<AuctioneersPage />)
    await screen.findByText('Credenciamento')
    const excluirButtons = screen.getAllByRole('button', { name: /Excluir/ })
    fireEvent.click(excluirButtons[excluirButtons.length - 1])
    expect(await screen.findByText('Documento excluído.')).toBeInTheDocument()
    const delCall = vi.mocked(fetch).mock.calls[1]
    expect(delCall[0]).toContain('/documentos/50')
    expect((delCall[1] as RequestInit).method).toBe('DELETE')
  })
})
