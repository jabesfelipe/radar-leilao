import type { HTMLAttributes, ReactNode } from 'react'

type SectionProps = HTMLAttributes<HTMLElement> & {
  title?: string
  description?: string
  actions?: ReactNode
  children: ReactNode
}

export function Section({ title, description, actions, className = '', children, ...props }: SectionProps) {
  return (
    <section {...props} className={`ui-section${className ? ` ${className}` : ''}`}>
      {(title || description || actions) && (
        <header className="ui-section-header">
          <div>
            {title && <h3 className="ui-section-title">{title}</h3>}
            {description && <p className="ui-section-description">{description}</p>}
          </div>
          {actions && <div className="ui-section-actions">{actions}</div>}
        </header>
      )}
      {children}
    </section>
  )
}
