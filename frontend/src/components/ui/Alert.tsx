import { AlertCircle, CheckCircle2, Info, TriangleAlert, X } from 'lucide-react'
import type { ReactNode } from 'react'
import { IconButton } from './IconButton'

type AlertProps = {
  tone?: 'info' | 'success' | 'warning' | 'danger'
  title?: string
  children: ReactNode
  icon?: ReactNode
  onDismiss?: () => void
  className?: string
}

const defaultIcons = { info: Info, success: CheckCircle2, warning: TriangleAlert, danger: AlertCircle }

export function Alert({ tone = 'info', title, children, icon, onDismiss, className = '' }: AlertProps) {
  const DefaultIcon = defaultIcons[tone]
  return (
    <div className={`ui-alert ui-alert-${tone}${className ? ` ${className}` : ''}`} role="alert">
      <span className="ui-alert-icon" aria-hidden="true">{icon ?? <DefaultIcon size={18} />}</span>
      <div className="ui-alert-content">
        {title && <strong>{title}</strong>}
        <span>{children}</span>
      </div>
      {onDismiss && <IconButton label="Fechar mensagem" icon={<X size={16} />} variant="ghost" size="sm" onClick={onDismiss} />}
    </div>
  )
}
