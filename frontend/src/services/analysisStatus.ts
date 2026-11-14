// Apresentação do status HONESTO da análise (calculado no backend; ver ai/analysis_status.py).
// "concluida" só aparece quando todos os agentes executaram. Qualquer outra coisa é sinalizada.

export type Tone = 'success' | 'warning' | 'danger' | 'info' | 'neutral'

export function analysisTone(status: string | null | undefined): Exclude<Tone, 'neutral'> {
  switch (status) {
    case 'concluida': return 'success'
    case 'parcial': return 'warning'
    case 'falha': return 'danger'
    default: return 'info'
  }
}

export function analysisTitle(status: string | null | undefined): string {
  switch (status) {
    case 'concluida': return 'Análise concluída'
    case 'parcial': return 'Análise parcial'
    case 'falha': return 'Análise sem resultado da IA'
    case 'em_processamento': return 'Análise em processamento'
    case 'legado': return 'Análise anterior (status não registrado)'
    default: return 'Análise'
  }
}

export function analysisLabel(status: string | null | undefined): string {
  switch (status) {
    case 'concluida': return 'Concluída'
    case 'parcial': return 'Parcial'
    case 'falha': return 'Falha'
    case 'em_processamento': return 'Em processamento'
    default: return 'Sem status'
  }
}

/** Tom/rótulo do estado de prontidão de um documento (backend: documents/readiness.py). */
export function documentStateTone(state: string | null | undefined): Tone {
  switch (state) {
    case 'INDEXADO': return 'success'
    case 'INDEXADO_PARCIAL':
    case 'PRONTO_SEM_EMBEDDING':
    case 'PROCESSANDO': return 'warning'
    case 'SEM_TEXTO':
    case 'OCR_NECESSARIO':
    case 'OCR_FALHOU':
    case 'ERRO': return 'danger'
    default: return 'neutral'
  }
}

export function documentStateLabel(state: string | null | undefined): string {
  switch (state) {
    case 'INDEXADO': return 'Indexado'
    case 'INDEXADO_PARCIAL': return 'Indexado parcialmente'
    case 'PRONTO_SEM_EMBEDDING': return 'Pronto (só texto)'
    case 'PROCESSANDO': return 'Processando'
    case 'SEM_TEXTO': return 'Sem texto'
    case 'OCR_NECESSARIO': return 'OCR necessário'
    case 'OCR_FALHOU': return 'OCR falhou'
    case 'ERRO': return 'Erro'
    default: return state ? state.split('_').join(' ') : 'Sem estado'
  }
}

export function stageTone(state: string): Tone {
  switch (state) {
    case 'concluida': return 'success'
    case 'parcial':
    case 'pendente': return 'warning'
    case 'falhou': return 'danger'
    case 'indisponivel': return 'warning'
    default: return 'neutral'
  }
}

export function stageStateLabel(state: string): string {
  switch (state) {
    case 'concluida': return 'Concluída'
    case 'parcial': return 'Parcial'
    case 'pendente': return 'Pendente'
    case 'falhou': return 'Falhou'
    case 'indisponivel': return 'Indisponível'
    case 'nao_aplicavel': return 'Não se aplica'
    default: return state
  }
}

export function stageName(stage: string): string {
  switch (stage) {
    case 'upload': return 'Upload'
    case 'ocr': return 'OCR'
    case 'extracao': return 'Extração de texto'
    case 'chunking': return 'Divisão em trechos'
    case 'embedding': return 'Embeddings'
    case 'indexacao': return 'Indexação'
    default: return stage
  }
}
