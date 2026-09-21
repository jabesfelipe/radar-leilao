import type { ReactNode } from 'react'

type EmptyStateProps = {
  title: string
  description?: string
  icon?: ReactNode
  action?: ReactNode
  className?: string
}

export function EmptyState({ title, description, icon, action, className = '' }: EmptyStateProps) {
  return (
    <div className={`ui-empty-state${className ? ` ${className}` : ''}`}>
      {icon && <div className="ui-empty-icon" aria-hidden="true">{icon}</div>}
      <h3>{title}</h3>
      {description && <p>{description}</p>}
      {action && <div className="ui-empty-action">{action}</div>}
    </div>
  )
}
