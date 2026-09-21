import { useId, type TextareaHTMLAttributes } from 'react'

type TextareaProps = TextareaHTMLAttributes<HTMLTextAreaElement> & {
  label?: string
  hint?: string
  error?: string
}

export function Textarea({ label, hint, error, id, className = '', ...props }: TextareaProps) {
  const generatedId = useId()
  const textareaId = id ?? generatedId
  const descriptionId = `${textareaId}-description`
  const errorId = `${textareaId}-error`
  const describedBy = [error ? errorId : null, hint ? descriptionId : null].filter(Boolean).join(' ') || undefined
  return (
    <div className={`ui-field${error ? ' ui-field-error' : ''}${className ? ` ${className}` : ''}`}>
      {label && <label className="ui-field-label" htmlFor={textareaId}>{label}</label>}
      <textarea {...props} id={textareaId} className="ui-textarea" aria-invalid={error ? true : undefined} aria-describedby={describedBy} />
      {error ? <p className="ui-field-message ui-field-message-error" id={errorId}>{error}</p> : hint ? <p className="ui-field-message" id={descriptionId}>{hint}</p> : null}
    </div>
  )
}
