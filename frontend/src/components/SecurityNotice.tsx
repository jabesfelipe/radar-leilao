import { useEffect, useState } from 'react'
import { Alert } from './ui/Alert'

const securityNoticeMessages: Record<string, string> = {
  'radar:forbidden': 'Você não tem permissão para executar esta operação. Procure um administrador se precisar desse acesso.',
  'radar:rate-limited': 'Muitas requisições ou operação já em andamento. Aguarde um instante e tente novamente.',
}

// Aviso acessível (role="alert") para 403/429 vindos do backend, sem derrubar a sessão.
export function SecurityNotice() {
  const [message, setMessage] = useState<string | null>(null)
  useEffect(() => {
    const handlers = Object.keys(securityNoticeMessages).map((eventName) => {
      const handler = () => setMessage(securityNoticeMessages[eventName])
      window.addEventListener(eventName, handler)
      return [eventName, handler] as const
    })
    return () => handlers.forEach(([eventName, handler]) => window.removeEventListener(eventName, handler))
  }, [])
  if (!message) return null
  return (
    <div style={{ position: 'fixed', top: 12, right: 12, zIndex: 1000, maxWidth: 420 }}>
      <Alert tone="warning" onDismiss={() => setMessage(null)}>{message}</Alert>
    </div>
  )
}
