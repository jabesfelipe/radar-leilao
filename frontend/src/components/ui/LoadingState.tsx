type LoadingStateProps = {
  label?: string
  variant?: 'inline' | 'block' | 'skeleton'
  className?: string
}

export function LoadingState({ label = 'Carregando conteúdo', variant = 'block', className = '' }: LoadingStateProps) {
  return (
    <div className={`ui-loading ui-loading-${variant}${className ? ` ${className}` : ''}`} role="status" aria-live="polite">
      {variant === 'skeleton' ? <span className="ui-skeleton" aria-hidden="true" /> : <span className="ui-spinner" aria-hidden="true" />}
      <span>{label}</span>
    </div>
  )
}
