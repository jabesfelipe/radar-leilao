import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { SourcesSection } from './SourcesSection'

const source = { id: 7, property_id: 5, source_type: 'EDITAL', url: 'https://exemplo.com/edital', description: 'Edital oficial', origin: 'Caixa' }

function response(body: unknown, ok = true, status = 200) {
  return Promise.resolve({ ok, status, json: () => Promise.resolve(body) }) as Promise<Response>
}

describe('SourcesSection', () => {
  beforeEach(() => { vi.restoreAllMocks(); globalThis.fetch = vi.fn() })

  it('lista as fontes do imóvel', async () => {
    vi.mocked(fetch).mockReturnValueOnce(response([source]))
    render(<SourcesSection propertyId={5} />)
    expect(await screen.findByText('EDITAL')).toBeInTheDocument()
    expect(screen.getByText('Edital oficial')).toBeInTheDocument()
  })

  it('estado vazio quando não há fontes', async () => {
    vi.mocked(fetch).mockReturnValueOnce(response([]))
    render(<SourcesSection propertyId={5} />)
    expect(await screen.findByText('Nenhuma fonte cadastrada')).toBeInTheDocument()
  })

  it('edita uma fonte (PATCH) e atualiza a lista', async () => {
    vi.mocked(fetch)
      .mockReturnValueOnce(response([source]))
      .mockReturnValueOnce(response({ ...source, description: 'Edital retificado' }))
    render(<SourcesSection propertyId={5} />)
    await screen.findByText('EDITAL')
    fireEvent.click(screen.getByRole('button', { name: /Editar/ }))
    fireEvent.change(screen.getByLabelText('Descrição (opcional)'), { target: { value: 'Edital retificado' } })
    fireEvent.click(screen.getByRole('button', { name: 'Salvar alterações' }))
    expect(await screen.findByText(/Fonte atualizada/)).toBeInTheDocument()
    const patchCall = vi.mocked(fetch).mock.calls[1]
    expect(patchCall[0]).toContain('/api/imoveis/5/fontes/7')
    expect((patchCall[1] as RequestInit).method).toBe('PATCH')
  })

  it('exclui uma fonte após confirmação', async () => {
    vi.spyOn(window, 'confirm').mockReturnValue(true)
    vi.mocked(fetch)
      .mockReturnValueOnce(response([source]))
      .mockReturnValueOnce(response({ removido: 7 }))
    render(<SourcesSection propertyId={5} />)
    await screen.findByText('EDITAL')
    fireEvent.click(screen.getByRole('button', { name: /Excluir/ }))
    expect(await screen.findByText(/Fonte excluída/)).toBeInTheDocument()
    const delCall = vi.mocked(fetch).mock.calls[1]
    expect(delCall[0]).toContain('/api/imoveis/5/fontes/7')
    expect((delCall[1] as RequestInit).method).toBe('DELETE')
  })

  it('trata erro da API ao excluir', async () => {
    vi.spyOn(window, 'confirm').mockReturnValue(true)
    vi.mocked(fetch)
      .mockReturnValueOnce(response([source]))
      .mockReturnValueOnce(response({ detail: 'Falha ao excluir' }, false, 500))
    render(<SourcesSection propertyId={5} />)
    await screen.findByText('EDITAL')
    fireEvent.click(screen.getByRole('button', { name: /Excluir/ }))
    await waitFor(() => expect(screen.getByText('Falha ao excluir')).toBeInTheDocument())
  })
})
