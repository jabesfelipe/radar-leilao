import type { HTMLAttributes, ReactNode } from 'react'

type BadgeProps = HTMLAttributes<HTMLSpanElement> & {
  tone?: 'neutral' | 'success' | 'warning' | 'danger' | 'info'
  size?: 'sm' | 'md'
  children: ReactNode
}

export function Badge({ tone = 'neutral', size = 'md', className = '', children, ...props }: BadgeProps) {
  return (
    <span {...props} className={`ui-badge ui-badge-${tone} ui-badge-${size}${className ? ` ${className}` : ''}`}>
      {children}
    </span>
  )
}
