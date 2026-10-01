'use client'

import { useState } from 'react'
import { AlertCircle, Loader2 } from 'lucide-react'

import { loginUser, registerUser, setToken, type User } from '@/lib/api'

type Tab = 'login' | 'register'

export function LoginForm({ onSuccess }: { onSuccess: (user: User) => void }) {
  const [tab, setTab] = useState<Tab>('login')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError('')
    try {
      const action = tab === 'login' ? loginUser : registerUser
      const response = await action(email, password)
      setToken(response.access_token)
      onSuccess(response.user)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error desconocido')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="rounded-xl border border-border bg-card p-6 md:p-8">
      <div className="mb-6 grid grid-cols-2 gap-1 rounded-lg border border-border bg-background p-1">
        {(['login', 'register'] as const).map((t) => (
          <button
            key={t}
            type="button"
            onClick={() => {
              setTab(t)
              setError('')
            }}
            className={`rounded-md px-3 py-2 text-sm font-medium transition-colors ${
              tab === t
                ? 'bg-foreground text-background'
                : 'text-muted-foreground hover:text-foreground'
            }`}
          >
            {t === 'login' ? 'Iniciar sesión' : 'Crear cuenta'}
          </button>
        ))}
      </div>

      <form onSubmit={handleSubmit} className="space-y-4">
        {error && (
          <div className="flex items-start gap-2 rounded-md border border-border bg-secondary/50 p-3">
            <AlertCircle className="mt-0.5 size-4 shrink-0 text-foreground" />
            <p className="text-sm text-foreground">{error}</p>
          </div>
        )}

        <label className="block space-y-1.5">
          <span className="font-mono text-xs uppercase tracking-wider text-muted-foreground">
            Correo electrónico
          </span>
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="tu@email.com"
            required
            className="w-full rounded-md border border-input bg-background px-3 py-2.5 text-sm text-foreground outline-none transition-colors placeholder:text-muted-foreground/70 focus:border-ring focus:ring-3 focus:ring-ring/15"
          />
        </label>

        <label className="block space-y-1.5">
          <span className="font-mono text-xs uppercase tracking-wider text-muted-foreground">
            Contraseña{tab === 'register' ? ' (mín. 8 caracteres)' : ''}
          </span>
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            minLength={tab === 'register' ? 8 : undefined}
            required
            className="w-full rounded-md border border-input bg-background px-3 py-2.5 text-sm text-foreground outline-none transition-colors placeholder:text-muted-foreground/70 focus:border-ring focus:ring-3 focus:ring-ring/15"
          />
        </label>

        <button
          type="submit"
          disabled={loading}
          className="flex w-full items-center justify-center gap-2 rounded-lg bg-primary px-4 py-3 text-sm font-medium text-primary-foreground transition-opacity hover:opacity-90 disabled:opacity-60"
        >
          {loading && <Loader2 className="size-4 animate-spin" />}
          {tab === 'login' ? 'Entrar a Academy' : 'Crear cuenta y entrar'}
        </button>
      </form>

      <p className="mt-5 text-center text-xs leading-relaxed text-muted-foreground">
        Tus cursos, progreso y certificados quedan guardados en tu cuenta.
      </p>
    </div>
  )
}
