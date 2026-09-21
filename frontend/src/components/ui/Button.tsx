import type { ButtonHTMLAttributes, ReactNode } from 'react'

type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: 'primary' | 'secondary' | 'ghost' | 'danger'
  size?: 'sm' | 'md' | 'lg'
  loading?: boolean
  fullWidth?: boolean
  children: ReactNode
}

export function Button({ variant = 'primary', size = 'md', loading = false, fullWidth = false, disabled, className = '', children, ...props }: ButtonProps) {
  return (
    <button
      {...props}
      type={props.type ?? 'button'}
      className={`ui-button ui-button-${variant} ui-button-${size}${fullWidth ? ' ui-button-full' : ''}${className ? ` ${className}` : ''}`}
      disabled={disabled || loading}
      aria-busy={loading || undefined}
    >
      {loading && <span className="ui-spinner" aria-hidden="true" />}
      <span>{loading ? 'Carregando…' : children}</span>
    </button>
  )
}
