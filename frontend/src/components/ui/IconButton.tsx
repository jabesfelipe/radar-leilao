import type { ButtonHTMLAttributes, ReactNode } from 'react'

type IconButtonProps = Omit<ButtonHTMLAttributes<HTMLButtonElement>, 'aria-label'> & {
  label: string
  icon: ReactNode
  size?: 'sm' | 'md' | 'lg'
  variant?: 'default' | 'ghost'
}

export function IconButton({ label, icon, size = 'md', variant = 'default', className = '', ...props }: IconButtonProps) {
  return (
    <button
      {...props}
      type={props.type ?? 'button'}
      className={`ui-icon-button ui-icon-button-${size} ui-icon-button-${variant}${className ? ` ${className}` : ''}`}
      aria-label={label}
    >
      {icon}
    </button>
  )
}
