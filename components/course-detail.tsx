"use client"

import { useCallback, useEffect, useState } from "react"
import Image from "next/image"
import Link from "next/link"
import {
  Check,
  CheckCircle2,
  Clock,
  Loader2,
  Lock,
  PlayCircle,
  Signal,
  X,
} from "lucide-react"

import { formatPrice, getCourseDetail, type CourseDetail as CourseDetailData } from "@/lib/api"

const basePath = process.env.NEXT_PUBLIC_BASE_PATH ?? ""

export function CourseDetail({
  courseId,
  onClose,
}: {
  courseId: string
  onClose: () => void
}) {
  const [course, setCourse] = useState<CourseDetailData | null>(null)
  const [error, setError] = useState("")

  const load = useCallback(() => {
    getCourseDetail(courseId)
      .then(setCourse)
      .catch(() =>
        setError("No se pudo cargar el curso. Intenta de nuevo en unos segundos."),
      )
  }, [courseId])

  useEffect(() => {
    load()
  }, [load])

  // Lock body scroll and support Escape to close.
  useEffect(() => {
    const original = document.body.style.overflow
    document.body.style.overflow = "hidden"
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose()
    }
    window.addEventListener("keydown", onKey)
    return () => {
      document.body.style.overflow = original
      window.removeEventListener("keydown", onKey)
    }
  }, [onClose])

  return (
    <div
      className="fixed inset-0 z-50 flex items-stretch justify-end bg-foreground/40 backdrop-blur-sm md:items-center md:justify-center md:p-6"
      role="dialog"
      aria-modal="true"
      aria-label={course?.name ?? "Curso"}
      onClick={onClose}
    >
      <div
        className="relative flex h-full w-full flex-col overflow-hidden bg-background md:h-auto md:max-h-[90vh] md:max-w-4xl md:rounded-2xl md:border md:border-border"
        onClick={(e) => e.stopPropagation()}
      >
        <button
          type="button"
          onClick={onClose}
          aria-label="Cerrar"
          className="absolute right-4 top-4 z-10 inline-flex size-9 items-center justify-center rounded-full border border-border bg-background/80 text-foreground backdrop-blur transition-colors hover:bg-secondary"
        >
          <X className="size-4" />
        </button>

        <div className="overflow-y-auto">
          {error ? (
            <div className="flex min-h-[50vh] flex-col items-center justify-center gap-4 p-6 text-center">
              <p className="text-sm text-muted-foreground">{error}</p>
              <button
                type="button"
                onClick={() => {
                  setError("")
                  load()
                }}
                className="rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground transition-opacity hover:opacity-90"
              >
                Reintentar
              </button>
            </div>
          ) : !course ? (
            <div className="flex min-h-[50vh] items-center justify-center">
              <Loader2 className="size-5 animate-spin text-muted-foreground" />
            </div>
          ) : (
            <OverviewView course={course} />
          )}
        </div>
      </div>
    </div>
  )
}

function OverviewView({ course }: { course: CourseDetailData }) {
  const unlocked = course.enrolled

  return (
    <>
      {/* Hero */}
      <div className="relative aspect-[16/9] w-full md:aspect-[21/9]">
        <Image
          src={
            course.image_path ? `${basePath}${course.image_path}` : "/placeholder.svg"
          }
          alt={course.name}
          fill
          sizes="(max-width: 768px) 100vw, 900px"
          className="object-cover"
          priority
        />
        <div className="absolute inset-0 bg-gradient-to-t from-background via-background/40 to-transparent" />
        <div className="absolute bottom-0 left-0 right-0 p-6 md:p-8">
          <div className="flex items-center gap-4 font-mono text-[11px] uppercase tracking-widest text-muted-foreground">
            <span className="inline-flex items-center gap-1.5">
              <Signal className="size-3.5" /> {course.level}
            </span>
            <span className="inline-flex items-center gap-1.5">
              <Clock className="size-3.5" /> {course.duration_hours}h
            </span>
            <span>{course.lessons_count} lecciones</span>
          </div>
          <h2 className="mt-3 text-balance text-3xl font-medium tracking-tight text-foreground md:text-4xl">
            {course.name}
          </h2>
        </div>
      </div>

      <div className="grid gap-10 p-6 md:grid-cols-[1fr_300px] md:p-8">
        {/* Left: content */}
        <div className="min-w-0">
          <p className="text-pretty leading-relaxed text-muted-foreground">
            {course.description}
          </p>

          <h3 className="mt-8 font-mono text-xs uppercase tracking-[0.2em] text-muted-foreground">
            Contenido del curso
          </h3>
          <div className="mt-4 divide-y divide-border overflow-hidden rounded-lg border border-border">
            {course.modules.map((mod, mi) => (
              <div key={mod.id}>
                <div className="flex items-center gap-3 bg-secondary px-4 py-3">
                  <span className="font-mono text-xs text-muted-foreground">
                    {(mi + 1).toString().padStart(2, "0")}
                  </span>
                  <span className="text-sm font-medium text-foreground">
                    {mod.title}
                  </span>
                </div>
                <ul>
                  {mod.lessons.map((lesson) => {
                    const accessible = unlocked || lesson.is_free
                    return (
                      <li
                        key={lesson.id}
                        className="flex items-center gap-3 px-4 py-3"
                      >
                        {accessible ? (
                          <PlayCircle className="size-4 shrink-0 text-foreground" />
                        ) : (
                          <Lock className="size-4 shrink-0 text-muted-foreground" />
                        )}
                        <span
                          className={
                            accessible
                              ? "flex-1 text-sm text-foreground"
                              : "flex-1 text-sm text-muted-foreground"
                          }
                        >
                          {lesson.title}
                        </span>
                        {lesson.is_free && !unlocked && (
                          <span className="rounded border border-border px-1.5 py-0.5 font-mono text-[10px] uppercase tracking-widest text-muted-foreground">
                            Gratis
                          </span>
                        )}
                        <span className="font-mono text-xs text-muted-foreground">
                          {lesson.duration_min} min
                        </span>
                      </li>
                    )
                  })}
                </ul>
              </div>
            ))}
          </div>
        </div>

        {/* Right: purchase panel */}
        <aside className="md:sticky md:top-4 md:self-start">
          <div className="rounded-xl border border-border bg-card p-6">
            {unlocked ? (
              <>
                <div className="flex items-center gap-2 text-foreground">
                  <CheckCircle2 className="size-5" />
                  <span className="text-sm font-medium">Curso adquirido</span>
                </div>
                <Link
                  href="/academy"
                  className="mt-5 flex w-full items-center justify-center gap-2 rounded-lg bg-primary px-4 py-3 text-sm font-medium text-primary-foreground transition-opacity hover:opacity-90"
                >
                  <PlayCircle className="size-4" /> Continuar aprendiendo
                </Link>
              </>
            ) : (
              <>
                <div className="flex items-baseline gap-2">
                  <span className="text-3xl font-medium tracking-tight text-foreground">
                    {course.is_free
                      ? "Gratis"
                      : formatPrice(course.price_cents, course.currency)}
                  </span>
                  {!course.is_free && (
                    <span className="font-mono text-xs uppercase tracking-widest text-muted-foreground">
                      pago único
                    </span>
                  )}
                </div>
                <Link
                  href="/academy"
                  className="mt-5 flex w-full items-center justify-center gap-2 rounded-lg bg-primary px-4 py-3 text-sm font-medium text-primary-foreground transition-opacity hover:opacity-90"
                >
                  <Lock className="size-4" /> Desbloquear curso
                </Link>
                <ul className="mt-5 space-y-2.5">
                  {[
                    "Acceso de por vida",
                    "Certificado al finalizar",
                    "Proyectos descargables",
                  ].map((f) => (
                    <li
                      key={f}
                      className="flex items-center gap-2 text-xs text-muted-foreground"
                    >
                      <Check className="size-3.5 text-foreground" /> {f}
                    </li>
                  ))}
                </ul>
              </>
            )}
          </div>
        </aside>
      </div>
    </>
  )
}
