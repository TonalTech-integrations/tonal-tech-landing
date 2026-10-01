'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { useSearchParams } from 'next/navigation'
import { CheckCircle2, Loader2, XCircle } from 'lucide-react'

import { getSessionStatus, type SessionStatus } from '@/lib/api'

export function SuccessPage() {
  const searchParams = useSearchParams()
  const sessionId = searchParams.get('session_id')
  const [session, setSession] = useState<SessionStatus | null>(null)
  const [error, setError] = useState('')

  useEffect(() => {
    if (!sessionId) return
    getSessionStatus(sessionId)
      .then(setSession)
      .catch(() => setError('No pudimos verificar tu pago. Si ya lo completaste, tu curso aparecerá en tu biblioteca.'))
  }, [sessionId])

  const missingIdError = !sessionId ? 'Falta el identificador de la sesión de pago.' : ''
  const errorMessage = error || missingIdError
  const completed = session?.status === 'complete'

  return (
    <div className="flex min-h-dvh flex-col items-center justify-center bg-background px-6 text-foreground">
      <div className="w-full max-w-md rounded-xl border border-border bg-card p-8 text-center">
        {!session && !errorMessage && (
          <>
            <Loader2 className="mx-auto size-8 animate-spin text-muted-foreground" />
            <h1 className="mt-4 text-xl font-medium tracking-tight">Verificando tu pago...</h1>
          </>
        )}

        {errorMessage && (
          <>
            <XCircle className="mx-auto size-10 text-muted-foreground" />
            <h1 className="mt-4 text-xl font-medium tracking-tight">Algo salió mal</h1>
            <p className="mt-3 text-sm leading-relaxed text-muted-foreground">{errorMessage}</p>
            <Link
              href="/academy"
              className="mt-6 inline-block rounded-lg bg-primary px-6 py-3 text-sm font-medium text-primary-foreground transition-opacity hover:opacity-90"
            >
              Volver a Academy
            </Link>
          </>
        )}

        {session && (
          <>
            <CheckCircle2 className="mx-auto size-10 text-foreground" />
            <h1 className="mt-4 text-2xl font-medium tracking-tight">
              {completed ? 'Pago completado' : 'Pago en proceso'}
            </h1>
            <p className="mt-3 text-sm leading-relaxed text-muted-foreground">
              {completed
                ? 'Tu curso ya está disponible en tu biblioteca. Puedes empezar cuando quieras.'
                : 'Estamos confirmando tu pago. Tu curso aparecerá en tu biblioteca en unos minutos.'}
            </p>
            <div className="mt-6 flex flex-col gap-3">
              {completed && session.course_id ? (
                <Link
                  href="/academy"
                  className="rounded-lg bg-primary px-6 py-3 text-sm font-medium text-primary-foreground transition-opacity hover:opacity-90"
                >
                  Ir a mis cursos
                </Link>
              ) : (
                <Link
                  href="/academy"
                  className="rounded-lg bg-primary px-6 py-3 text-sm font-medium text-primary-foreground transition-opacity hover:opacity-90"
                >
                  Volver a Academy
                </Link>
              )}
              <Link
                href="/"
                className="text-sm text-muted-foreground transition-colors hover:text-foreground"
              >
                Volver al inicio
              </Link>
            </div>
          </>
        )}
      </div>
    </div>
  )
}
