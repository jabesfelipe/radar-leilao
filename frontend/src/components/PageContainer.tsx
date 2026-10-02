import type { ReactNode } from 'react'

type PageContainerProps = {
  title: string
  description: string
  children?: ReactNode
}

export function PageContainer({ title, description, children }: PageContainerProps) {
  return (
    <section className="page-container">
      <div className="page-heading">
        <div>
          <p className="eyebrow">RADAR LEILÃO</p>
          <h2>{title}</h2>
          <p className="page-description">{description}</p>
        </div>
      </div>
      {children}
    </section>
  )
}
