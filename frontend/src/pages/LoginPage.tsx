import { useState, type FormEvent } from 'react'
import { LogIn } from 'lucide-react'
import { Alert, Button, Card, Input } from '../components/ui'
import { login, type Me } from '../services/auth'

type LoginPageProps = { onAuthenticated: (me: Me) => void }

export function LoginPage({ onAuthenticated }: LoginPageProps) {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    setError(''); setLoading(true)
    try {
      const me = await login(email.trim(), password)
      onAuthenticated(me)
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Falha ao autenticar.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="login-screen">
      <Card variant="elevated" padding="lg" className="login-card">
        <div className="login-brand">
          <div className="login-brand-icon"><LogIn size={22} /></div>
          <div>
            <p className="eyebrow">RADAR LEILÃO</p>
            <h2>Entrar</h2>
          </div>
        </div>
        <p className="login-hint">Use suas credenciais para acessar o Radar.</p>
        <form className="login-form" onSubmit={submit} noValidate>
          <Input label="E-mail" type="email" value={email} onChange={(e) => setEmail(e.target.value)} autoComplete="username" required />
          <Input label="Senha" type="password" value={password} onChange={(e) => setPassword(e.target.value)} autoComplete="current-password" required />
          {error && <Alert tone="danger">{error}</Alert>}
          <Button type="submit" loading={loading} disabled={!email || !password}>Entrar</Button>
        </form>
      </Card>
    </div>
  )
}
