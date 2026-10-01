'use client'

import { useCallback, useEffect, useState } from 'react'
import Image from 'next/image'
import Link from 'next/link'
import { ArrowUpRight, CheckCircle2, Loader2, Lock, LogOut, PlayCircle } from 'lucide-react'

import {
  clearToken,
  createCheckoutSession,
  formatPrice,
  getCourses,
  getMe,
  getMyCourses,
  getToken,
  type CourseDetail,
  type CourseSummary,
  type MyCourseEntry,
  type User,
} from '@/lib/api'
import { LoginForm } from './login-form'
import { CourseViewer } from './course-viewer'

type View = 'catalog' | 'course' | 'login'

export function AcademyPage() {
  const [user, setUser] = useState<User | null>(null)
  const [courses, setCourses] = useState<CourseSummary[]>([])
  const [myCourses, setMyCourses] = useState<MyCourseEntry[]>([])
  const [view, setView] = useState<View>('catalog')
  const [activeCourseId, setActiveCourseId] = useState<string | null>(null)
  const [catalogError, setCatalogError] = useState('')
  const [booting, setBooting] = useState(true)
  const [checkoutLoading, setCheckoutLoading] = useState(false)
  const [checkoutError, setCheckoutError] = useState('')

  const refreshMyCourses = useCallback(() => {
    getMyCourses()
      .then(setMyCourses)
      .catch(() => setMyCourses([]))
  }, [])

  useEffect(() => {
    getCourses()
      .then(setCourses)
      .catch(() => setCatalogError('No se pudo cargar el catálogo. Intenta de nuevo en unos segundos.'))

    const token = getToken()
    const authCheck = token
      ? getMe()
          .then((u) => {
            setUser(u)
            refreshMyCourses()
          })
          .catch(() => setUser(null))
      : Promise.resolve()
    authCheck.finally(() => setBooting(false))
  }, [refreshMyCourses])

  const handleAuthSuccess = (u: User) => {
    setUser(u)
    refreshMyCourses()
    getCourses().then(setCourses).catch(() => {})
    setView('catalog')
  }

  const handleLogout = () => {
    clearToken()
    setUser(null)
    setMyCourses([])
    setView('catalog')
    getCourses().then(setCourses).catch(() => {})
  }

  const openCourse = (id: string) => {
    setActiveCourseId(id)
    setView('course')
    window.scrollTo({ top: 0 })
  }

  const handleBuy = async (course: CourseDetail) => {
    if (!user) return
    setCheckoutLoading(true)
    setCheckoutError('')
    try {
      const { checkout_url } = await createCheckoutSession(course.id, user.email)
      window.location.href = checkout_url
    } catch (err) {
      setCheckoutError(err instanceof Error ? err.message : 'No se pudo iniciar el pago')
      setCheckoutLoading(false)
    }
  }

  const isAuthed = user !== null
  const myIds = new Set(myCourses.map((c) => c.course_id))

  return (
    <div className="min-h-dvh bg-background text-foreground">
      <header className="sticky top-0 z-40 border-b border-border bg-background/95 backdrop-blur-sm">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
          <Link href="/" className="flex items-center gap-2.5 transition-opacity hover:opacity-75">
            <Image
              src={`${process.env.NEXT_PUBLIC_BASE_PATH ?? ''}/logo.jpg`}
              alt="Tonal-Tech"
              width={32}
              height={32}
              unoptimized
              className="size-8"
            />
            <span className="text-[15px] font-semibold tracking-tight">Tonal-Tech Academy</span>
          </Link>

          <div className="flex items-center gap-4">
            {booting ? null : isAuthed ? (
              <>
                <span className="hidden text-sm text-muted-foreground sm:inline">{user.email}</span>
                <button
                  type="button"
                  onClick={handleLogout}
                  className="inline-flex items-center gap-1.5 text-sm text-muted-foreground transition-colors hover:text-foreground"
                >
                  <LogOut className="size-3.5" /> Salir
                </button>
              </>
            ) : (
              <button
                type="button"
                onClick={() => setView('login')}
                className="rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground transition-opacity hover:opacity-90"
              >
                Acceder
              </button>
            )}
          </div>
        </div>
      </header>

      <main>
        {booting ? (
          <div className="flex min-h-[60vh] items-center justify-center">
            <Loader2 className="size-5 animate-spin text-muted-foreground" />
          </div>
        ) : view === 'login' && !isAuthed ? (
          <div className="mx-auto max-w-md px-6 py-16 md:py-24">
            <div className="mb-8 text-center">
              <h1 className="text-3xl font-medium tracking-tight text-foreground">
                Accede a Academy
              </h1>
              <p className="mt-3 text-sm leading-relaxed text-muted-foreground">
                Inicia sesión para ver tus cursos, tu progreso y desbloquear el contenido completo.
              </p>
            </div>
            <LoginForm onSuccess={handleAuthSuccess} />
            <button
              type="button"
              onClick={() => setView('catalog')}
              className="mt-6 w-full text-center text-sm text-muted-foreground transition-colors hover:text-foreground"
            >
              Seguir explorando el catálogo
            </button>
          </div>
        ) : view === 'course' && activeCourseId ? (
          <>
            {checkoutError && (
              <div className="mx-auto max-w-6xl px-6 pt-6">
                <p className="rounded-md border border-border bg-card px-4 py-3 text-sm text-foreground">
                  {checkoutError}
                </p>
              </div>
            )}
            <CourseViewer
              key={activeCourseId}
              courseId={activeCourseId}
              isAuthed={isAuthed}
              onBuy={handleBuy}
              onRequireLogin={() => setView('login')}
              onBack={() => {
                setView('catalog')
                setActiveCourseId(null)
                if (isAuthed) refreshMyCourses()
                getCourses().then(setCourses).catch(() => {})
              }}
            />
            {checkoutLoading && (
              <div className="fixed inset-0 z-50 flex items-center justify-center bg-background/70 backdrop-blur-sm">
                <div className="flex items-center gap-3 rounded-xl border border-border bg-card px-6 py-4">
                  <Loader2 className="size-4 animate-spin" />
                  <p className="text-sm text-foreground">Redirigiendo a pago seguro...</p>
                </div>
              </div>
            )}
          </>
        ) : (
          <div className="mx-auto max-w-6xl px-6 py-12 md:py-16">
            <div className="mb-10">
              <h1 className="text-4xl font-medium tracking-tight text-foreground md:text-5xl">
                Tonal-Tech Academy
              </h1>
              <p className="mt-3 max-w-xl text-sm leading-relaxed text-muted-foreground">
                Cursos de ingeniería con proyectos reales. Compra una vez y accede de por vida, tu
                progreso se guarda en tu cuenta.
              </p>
            </div>

            {isAuthed && myCourses.length > 0 && (
              <section className="mb-14">
                <h2 className="mb-5 font-mono text-xs uppercase tracking-[0.2em] text-muted-foreground">
                  Mis cursos
                </h2>
                <div className="grid gap-px overflow-hidden rounded-xl border border-border bg-border sm:grid-cols-2 lg:grid-cols-3">
                  {myCourses.map((entry) => (
                    <MyCourseCard key={entry.course_id} entry={entry} onSelect={() => openCourse(entry.course_id)} />
                  ))}
                </div>
              </section>
            )}

            <section>
              <h2 className="mb-5 font-mono text-xs uppercase tracking-[0.2em] text-muted-foreground">
                Catálogo
              </h2>
              {catalogError ? (
                <p className="rounded-xl border border-border bg-card px-5 py-8 text-center text-sm text-muted-foreground">
                  {catalogError}
                </p>
              ) : courses.length === 0 ? (
                <div className="flex justify-center rounded-xl border border-border bg-card px-5 py-12">
                  <Loader2 className="size-5 animate-spin text-muted-foreground" />
                </div>
              ) : (
                <div className="grid gap-px overflow-hidden rounded-xl border border-border bg-border sm:grid-cols-2 lg:grid-cols-3">
                  {courses.map((course) => (
                    <CatalogCard
                      key={course.id}
                      course={course}
                      owned={myIds.has(course.id) || course.enrolled}
                      onSelect={() => openCourse(course.id)}
                    />
                  ))}
                </div>
              )}
            </section>
          </div>
        )}
      </main>
    </div>
  )
}

const basePath = process.env.NEXT_PUBLIC_BASE_PATH ?? ''

function CatalogCard({
  course,
  owned,
  onSelect,
}: {
  course: CourseSummary
  owned: boolean
  onSelect: () => void
}) {
  return (
    <button
      type="button"
      onClick={onSelect}
      className="group flex flex-col bg-card text-left transition-colors hover:bg-secondary focus:outline-none focus-visible:ring-2 focus-visible:ring-ring"
    >
      <div className="relative aspect-[4/3] overflow-hidden">
        <Image
          src={basePath + course.image_path}
          alt={course.name}
          fill
          sizes="(max-width: 768px) 100vw, 33vw"
          className="object-cover transition-transform duration-500 group-hover:scale-105"
        />
        <div className="absolute left-3 top-3 flex items-center gap-1.5 rounded-full border border-border bg-background/90 px-2.5 py-1 font-mono text-[10px] uppercase tracking-widest text-foreground backdrop-blur">
          {owned ? (
            <>
              <PlayCircle className="size-3" /> En tu biblioteca
            </>
          ) : (
            <>
              <Lock className="size-3" /> {formatPrice(course.price_cents, course.currency)}
            </>
          )}
        </div>
      </div>

      <div className="flex flex-1 flex-col gap-4 p-5">
        <div className="flex items-center gap-4 font-mono text-[11px] uppercase tracking-widest text-muted-foreground">
          <span>{course.level}</span>
          <span>{course.duration_hours}h</span>
          <span>{course.lessons_count} lecciones</span>
        </div>

        <div className="flex-1">
          <h3 className="text-lg font-medium tracking-tight text-foreground">{course.name}</h3>
          <p className="mt-1.5 text-sm leading-relaxed text-muted-foreground">{course.tagline}</p>
        </div>

        {owned && course.completed_lessons > 0 && (
          <div>
            <div className="h-1 overflow-hidden rounded-full bg-secondary">
              <div
                className="h-full rounded-full bg-foreground transition-all"
                style={{
                  width: `${Math.round((course.completed_lessons * 100) / Math.max(course.lessons_count, 1))}%`,
                }}
              />
            </div>
            <p className="mt-1.5 text-[11px] text-muted-foreground">
              {course.completed_lessons} de {course.lessons_count} completadas
            </p>
          </div>
        )}

        <div className="flex items-center justify-between border-t border-border pt-4">
          <span className="font-mono text-xs uppercase tracking-widest text-muted-foreground">
            {owned ? 'Continuar' : 'Ver detalles'}
          </span>
          <ArrowUpRight className="size-4 text-foreground transition-transform group-hover:-translate-y-0.5 group-hover:translate-x-0.5" />
        </div>
      </div>
    </button>
  )
}

function MyCourseCard({ entry, onSelect }: { entry: MyCourseEntry; onSelect: () => void }) {
  return (
    <button
      type="button"
      onClick={onSelect}
      className="group flex flex-col bg-card text-left transition-colors hover:bg-secondary focus:outline-none focus-visible:ring-2 focus-visible:ring-ring"
    >
      <div className="relative aspect-[16/7] overflow-hidden">
        <Image
          src={basePath + entry.image_path}
          alt={entry.name}
          fill
          sizes="(max-width: 768px) 100vw, 33vw"
          className="object-cover transition-transform duration-500 group-hover:scale-105"
        />
        {entry.progress_pct === 100 && (
          <div className="absolute right-3 top-3 flex items-center gap-1.5 rounded-full border border-border bg-background/90 px-2.5 py-1 font-mono text-[10px] uppercase tracking-widest text-foreground backdrop-blur">
            <CheckCircle2 className="size-3" /> Completado
          </div>
        )}
      </div>
      <div className="flex flex-1 flex-col gap-3 p-5">
        <h3 className="text-base font-medium tracking-tight text-foreground">{entry.name}</h3>
        <div>
          <div className="h-1 overflow-hidden rounded-full bg-secondary">
            <div
              className="h-full rounded-full bg-foreground transition-all"
              style={{ width: `${entry.progress_pct}%` }}
            />
          </div>
          <p className="mt-1.5 text-[11px] text-muted-foreground">
            {entry.completed_lessons} de {entry.total_lessons} lecciones · {entry.progress_pct}%
          </p>
        </div>
      </div>
    </button>
  )
}
