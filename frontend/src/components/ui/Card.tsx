import type { HTMLAttributes, ReactNode } from 'react'

type CardProps = HTMLAttributes<HTMLDivElement> & {
  variant?: 'default' | 'elevated' | 'brand'
  padding?: 'none' | 'sm' | 'md' | 'lg'
  children: ReactNode
}

export function Card({ variant = 'default', padding = 'md', className = '', children, ...props }: CardProps) {
  return (
    <div {...props} className={`ui-card ui-card-${variant} ui-card-padding-${padding}${className ? ` ${className}` : ''}`}>
      {children}
    </div>
  )
}
