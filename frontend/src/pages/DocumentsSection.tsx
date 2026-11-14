import { useCallback, useEffect, useRef, useState, type FormEvent } from 'react'
import { ChevronDown, ChevronRight, FileText, Layers, RefreshCw, Upload } from 'lucide-react'
import { Alert, Badge, Button, Card, EmptyState, Input, LoadingState, Section } from '../components/ui'
import { latestVersion, listDocuments, uploadDocument, type PropertyDocument } from '../services/documents'
import { documentStateLabel, documentStateTone, stageName, stageStateLabel, stageTone } from '../services/analysisStatus'

type DocumentsSectionProps = {
  propertyId: number
}

function formatDate(value?: string) {
  if (!value) return 'Data não informada'
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString('pt-BR')
}

export function DocumentsSection({ propertyId }: DocumentsSectionProps) {
  const [documents, setDocuments] = useState<PropertyDocument[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [formOpen, setFormOpen] = useState(false)
  const [file, setFile] = useState<File | null>(null)
  const [documentType, setDocumentType] = useState('')
  const [source, setSource] = useState('')
  const [uploading, setUploading] = useState(false)
  const [uploadError, setUploadError] = useState('')
  const [successMessage, setSuccessMessage] = useState('')
  const [notReadyMessage, setNotReadyMessage] = useState('')
  const [expanded, setExpanded] = useState<number | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const loadDocuments = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      setDocuments(await listDocuments(propertyId))
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Não foi possível carregar os documentos.')
    } finally {
      setLoading(false)
    }
  }, [propertyId])

  useEffect(() => { void loadDocuments() }, [loadDocuments])

  const resetForm = () => {
    setFile(null)
    setDocumentType('')
    setSource('')
    setUploadError('')
    if (fileInputRef.current) fileInputRef.current.value = ''
  }

  const openForm = () => {
    resetForm()
    setSuccessMessage('')
    setNotReadyMessage('')
    setFormOpen(true)
  }

  const handleUpload = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    if (!file) {
      setUploadError('Selecione um arquivo para enviar.')
      return
    }
    setUploading(true)
    setUploadError('')
    setSuccessMessage('')
    try {
      const created = await uploadDocument(propertyId, { file, document_type: documentType, source })
      setDocuments((current) => [...current, created])
      setFormOpen(false)
      resetForm()
      const processing = latestVersion(created)?.processamento
      if (processing && !processing.pronto_para_analise) {
        // Upload aceito, mas o documento NÃO pode ser analisado (sem texto/OCR): não é "sucesso" pleno.
        setNotReadyMessage(`O arquivo foi recebido, mas ainda não pode ser analisado. ${processing.mensagem}`)
      } else {
        setNotReadyMessage('')
      }
      setSuccessMessage('Documento original enviado e pipeline iniciado.')
    } catch (cause) {
      setUploadError(cause instanceof Error ? cause.message : 'Não foi possível enviar o documento.')
    } finally {
      setUploading(false)
    }
  }

  return (
    <Section title="Documentos" description="Originais preservados, versões e processamento com rastreabilidade." className="documents-section" actions={<Button onClick={openForm}><Upload size={16} /> Enviar documento</Button>}>
      {successMessage && <Alert tone="success" title="Envio concluído" className="documents-feedback">{successMessage}</Alert>}
      {successMessage && notReadyMessage && <Alert tone="danger" title="Documento não pronto para análise" className="documents-feedback">{notReadyMessage}</Alert>}

      {formOpen && (
        <Card variant="elevated" padding="lg" className="document-form-card">
          <form className="document-form" onSubmit={handleUpload} noValidate>
            <label className="ui-field document-file-field">
              <span className="ui-field-label">Arquivo</span>
              <input ref={fileInputRef} className="ui-input document-file-input" type="file" onChange={(event) => { setFile(event.target.files?.[0] ?? null); setUploadError('') }} aria-label="Arquivo do documento" />
            </label>
            <Input label="Tipo do documento (opcional)" placeholder="Ex.: Edital" value={documentType} onChange={(event) => setDocumentType(event.target.value)} />
            <Input label="Origem (opcional)" placeholder="Ex.: Portal do leiloeiro" value={source} onChange={(event) => setSource(event.target.value)} />
            <div className="document-form-actions">
              {uploadError && <Alert tone="danger">{uploadError}</Alert>}
              <Button variant="ghost" type="button" onClick={() => { setFormOpen(false); resetForm() }} disabled={uploading}>Cancelar</Button>
              <Button type="submit" loading={uploading}>Confirmar envio</Button>
            </div>
          </form>
        </Card>
      )}

      {loading ? (
        <LoadingState label="Carregando documentos…" />
      ) : error ? (
        <Card padding="lg" className="documents-error">
          <Alert tone="danger" title="Não foi possível carregar">{error}</Alert>
          <Button variant="secondary" onClick={() => void loadDocuments()}><RefreshCw size={16} /> Tentar novamente</Button>
        </Card>
      ) : documents.length === 0 ? (
        <Card padding="none"><EmptyState title="Nenhum documento enviado" description="Envie edital, matrícula ou outro documento para iniciar o dossiê documental." icon={<FileText size={24} />} action={<Button onClick={openForm}><Upload size={16} /> Enviar documento</Button>} /></Card>
      ) : (
        <div className="document-list">
          {documents.map((document) => {
            const latest = latestVersion(document)
            const isOpen = expanded === document.id
            return (
              <Card key={document.id} padding="none" className="document-item">
                <button type="button" className="document-item-head" aria-expanded={isOpen} onClick={() => setExpanded(isOpen ? null : document.id)}>
                  <div className="document-item-icon"><FileText size={19} /></div>
                  <div className="document-item-info">
                    <strong>{document.name}</strong>
                    <span>{document.document_type} · {document.source}</span>
                  </div>
                  <div className="document-item-meta">
                    <Badge tone="neutral" size="sm"><Layers size={12} /> {document.versions.length} {document.versions.length === 1 ? 'versão' : 'versões'}</Badge>
                    {latest && <Badge tone="info" size="sm">v{latest.version} · {latest.status}</Badge>}
                    {latest?.processamento ? (
                      <Badge tone={documentStateTone(latest.processamento.estado)} size="sm" title={latest.processamento.mensagem}>{documentStateLabel(latest.processamento.estado)}</Badge>
                    ) : (
                      <Badge tone={document.status === 'RECEBIDO' ? 'warning' : 'neutral'} size="sm">{document.status.split('_').join(' ')}</Badge>
                    )}
                    {isOpen ? <ChevronDown size={18} /> : <ChevronRight size={18} />}
                  </div>
                </button>
                {isOpen && (
                  <div className="document-versions">
                    {document.versions.length === 0 ? (
                      <p className="document-versions-empty">Nenhuma versão processada ainda.</p>
                    ) : (
                      document.versions.slice().sort((a, b) => b.version - a.version).map((version) => (
                        <div key={version.id} className="document-version">
                          <div className="document-version-head">
                            <strong>Versão {version.version}</strong>
                            <Badge tone="neutral" size="sm">{version.status.split('_').join(' ')}</Badge>
                          </div>
                          {version.processamento && (
                            <div className="document-processing">
                              <Alert tone={version.processamento.pronto_para_analise ? (version.processamento.nivel_indexacao === 'vetorial' ? 'success' : 'warning') : 'danger'} title={version.processamento.pronto_para_analise ? 'Pronto para análise' : 'Não está pronto para análise'}>
                                {version.processamento.mensagem}
                              </Alert>
                              <ol className="document-stages" aria-label={`Etapas de processamento da versão ${version.version}`}>
                                {version.processamento.etapas.map((stage) => (
                                  <li key={stage.etapa} className="document-stage">
                                    <div className="document-stage-head">
                                      <strong>{stageName(stage.etapa)}</strong>
                                      <Badge tone={stageTone(stage.estado)} size="sm">{stageStateLabel(stage.estado)}</Badge>
                                    </div>
                                    {stage.detalhe && <p className="document-stage-detail">{stage.detalhe}</p>}
                                  </li>
                                ))}
                              </ol>
                            </div>
                          )}
                          <dl className="document-version-facts">
                            <div><dt>Hash</dt><dd className="document-hash">{version.content_hash}</dd></div>
                            <div><dt>Data</dt><dd>{formatDate(version.created_at)}</dd></div>
                          </dl>
                        </div>
                      ))
                    )}
                  </div>
                )}
              </Card>
            )
          })}
        </div>
      )}
    </Section>
  )
}
