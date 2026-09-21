import { useId, type InputHTMLAttributes, type ReactNode } from 'react'

type InputProps = InputHTMLAttributes<HTMLInputElement> & {
  label?: string
  hint?: string
  error?: string
  leadingIcon?: ReactNode
  trailingAction?: ReactNode
}

export function Input({ label, hint, error, leadingIcon, trailingAction, id, className = '', ...props }: InputProps) {
  const generatedId = useId()
  const inputId = id ?? generatedId
  const descriptionId = `${inputId}-description`
  const errorId = `${inputId}-error`
  const describedBy = [error ? errorId : null, hint ? descriptionId : null].filter(Boolean).join(' ') || undefined
  return (
    <div className={`ui-field${error ? ' ui-field-error' : ''}${className ? ` ${className}` : ''}`}>
      {label && <label className="ui-field-label" htmlFor={inputId}>{label}</label>}
      <div className="ui-control-wrap">
        {leadingIcon && <span className="ui-control-icon" aria-hidden="true">{leadingIcon}</span>}
        <input {...props} id={inputId} className="ui-input" aria-invalid={error ? true : undefined} aria-describedby={describedBy} />
        {trailingAction && <span className="ui-control-action">{trailingAction}</span>}
      </div>
      {error ? <p className="ui-field-message ui-field-message-error" id={errorId}>{error}</p> : hint ? <p className="ui-field-message" id={descriptionId}>{hint}</p> : null}
    </div>
  )
}
