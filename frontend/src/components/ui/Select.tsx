import { useId, type ReactNode, type SelectHTMLAttributes } from 'react'

type SelectProps = SelectHTMLAttributes<HTMLSelectElement> & {
  label?: string
  hint?: string
  error?: string
  children: ReactNode
}

export function Select({ label, hint, error, id, className = '', children, ...props }: SelectProps) {
  const generatedId = useId()
  const selectId = id ?? generatedId
  const descriptionId = `${selectId}-description`
  const errorId = `${selectId}-error`
  const describedBy = [error ? errorId : null, hint ? descriptionId : null].filter(Boolean).join(' ') || undefined
  return (
    <div className={`ui-field${error ? ' ui-field-error' : ''}${className ? ` ${className}` : ''}`}>
      {label && <label className="ui-field-label" htmlFor={selectId}>{label}</label>}
      <select {...props} id={selectId} className="ui-select" aria-invalid={error ? true : undefined} aria-describedby={describedBy}>{children}</select>
      {error ? <p className="ui-field-message ui-field-message-error" id={errorId}>{error}</p> : hint ? <p className="ui-field-message" id={descriptionId}>{hint}</p> : null}
    </div>
  )
}
