import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { DocumentsSection } from './DocumentsSection'

const documentWithVersions = {
  id: 1,
  property_id: 5,
  name: 'edital.pdf',
  document_type: 'Edital',
  source: 'Portal do leiloeiro',
  status: 'RECEBIDO',
  created_at: '2026-01-10T12:00:00Z',
  versions: [
    { id: 10, version: 1, content_hash: 'hash-v1', original_path: '/orig/v1.pdf', normalized_path: '/norm/v1.md', status: 'RECEBIDO', created_at: '2026-01-10T12:00:00Z' },
    { id: 11, version: 2, content_hash: 'hash-v2', original_path: '/orig/v2.pdf', normalized_path: '/norm/v2.md', status: 'NORMALIZADO', created_at: '2026-01-11T12:00:00Z' },
  ],
}

function response(body: unknown, ok = true, status = 200) {
  return Promise.resolve({ ok, status, json: () => Promise.resolve(body) }) as Promise<Response>
}

function selectFile() {
  const input = screen.getByLabelText('Arquivo do documento')
  const file = new File(['conteudo'], 'matricula.pdf', { type: 'application/pdf' })
  fireEvent.change(input, { target: { files: [file] } })
}

describe('DocumentsSection', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
    globalThis.fetch = vi.fn()
  })

  it('exibe carregamento e depois estado vazio', async () => {
    vi.mocked(fetch).mockReturnValueOnce(response({ documentos: [] }))
    render(<DocumentsSection propertyId={5} />)

    expect(screen.getByRole('status')).toHaveTextContent('Carregando documentos')
    expect(await screen.findByText('Nenhum documento enviado')).toBeInTheDocument()
  })

  it('lista documentos com versão mais recente e múltiplas versões', async () => {
    vi.mocked(fetch).mockReturnValueOnce(response({ documentos: [documentWithVersions] }))
    render(<DocumentsSection propertyId={5} />)

    expect(await screen.findByText('edital.pdf')).toBeInTheDocument()
    expect(screen.getByText('Edital · Portal do leiloeiro')).toBeInTheDocument()
    expect(screen.getByText('2 versões')).toBeInTheDocument()
    expect(screen.getByText('v2 · NORMALIZADO')).toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: /edital\.pdf/ }))
    expect(screen.getByText('Versão 2')).toBeInTheDocument()
    expect(screen.getByText('Versão 1')).toBeInTheDocument()
    expect(screen.getByText('hash-v2')).toBeInTheDocument()
    expect(screen.getByText('/norm/v1.md')).toBeInTheDocument()
  })

  it('faz upload, exibe loading e mostra o novo documento', async () => {
    let resolveUpload: ((value: Response) => void) | undefined
    const uploadResponse = new Promise<Response>((resolve) => { resolveUpload = resolve })
    vi.mocked(fetch)
      .mockReturnValueOnce(response({ documentos: [] }))
      .mockReturnValueOnce(uploadResponse)
    render(<DocumentsSection propertyId={5} />)
    await screen.findByText('Nenhum documento enviado')

    fireEvent.click(screen.getAllByRole('button', { name: 'Enviar documento' })[0])
    selectFile()
    fireEvent.click(screen.getByRole('button', { name: 'Confirmar envio' }))

    expect(screen.getByRole('button', { name: 'Carregando…' })).toBeDisabled()
    resolveUpload?.(await response({ ...documentWithVersions, name: 'matricula.pdf', versions: [documentWithVersions.versions[0]] }))

    expect(await screen.findByText('Documento original enviado e pipeline iniciado.')).toBeInTheDocument()
    expect(screen.getByText('matricula.pdf')).toBeInTheDocument()
    const uploadCall = vi.mocked(fetch).mock.calls[1]
    expect(uploadCall[0]).toContain('/api/imoveis/5/documentos')
    expect((uploadCall[1] as RequestInit).method).toBe('POST')
    expect((uploadCall[1] as RequestInit).body).toBeInstanceOf(FormData)
  })

  it('valida arquivo obrigatório antes do upload', async () => {
    vi.mocked(fetch).mockReturnValueOnce(response({ documentos: [] }))
    render(<DocumentsSection propertyId={5} />)
    await screen.findByText('Nenhum documento enviado')

    fireEvent.click(screen.getAllByRole('button', { name: 'Enviar documento' })[0])
    fireEvent.click(screen.getByRole('button', { name: 'Confirmar envio' }))

    expect(await screen.findByText('Selecione um arquivo para enviar.')).toBeInTheDocument()
    expect(fetch).toHaveBeenCalledTimes(1)
  })

  it('exibe erro de upload da API', async () => {
    vi.mocked(fetch)
      .mockReturnValueOnce(response({ documentos: [] }))
      .mockReturnValueOnce(response({ detail: 'Extensão inválida' }, false, 400))
    render(<DocumentsSection propertyId={5} />)
    await screen.findByText('Nenhum documento enviado')

    fireEvent.click(screen.getAllByRole('button', { name: 'Enviar documento' })[0])
    selectFile()
    fireEvent.click(screen.getByRole('button', { name: 'Confirmar envio' }))

    expect(await screen.findByText('Extensão inválida')).toBeInTheDocument()
  })

  it('exibe erro ao carregar e permite tentar novamente', async () => {
    vi.mocked(fetch)
      .mockReturnValueOnce(response({ detail: 'Falha' }, false, 500))
      .mockReturnValueOnce(response({ documentos: [documentWithVersions] }))
    render(<DocumentsSection propertyId={5} />)

    fireEvent.click(await screen.findByRole('button', { name: 'Tentar novamente' }))
    await waitFor(() => expect(screen.getByText('edital.pdf')).toBeInTheDocument())
  })
})
