'use client'

import { useEffect, useMemo, useState } from 'react'
import { CheckCircle2, ChevronLeft, Loader2, Lock, PlayCircle } from 'lucide-react'

import {
  formatPrice,
  getCourseDetail,
  getCourseProgress,
  type CourseDetail,
  type LessonProgressEntry,
  type LessonSummary,
} from '@/lib/api'
import { VideoPlayer } from './video-player'

export function CourseViewer({
  courseId,
  isAuthed,
  onBuy,
  onRequireLogin,
  onBack,
}: {
  courseId: string
  isAuthed: boolean
  onBuy: (course: CourseDetail) => void
  onRequireLogin: () => void
  onBack: () => void
}) {
  const [course, setCourse] = useState<CourseDetail | null>(null)
  const [progress, setProgress] = useState<Map<number, LessonProgressEntry>>(new Map())
  const [activeLesson, setActiveLesson] = useState<LessonSummary | null>(null)
  const [error, setError] = useState('')

  const loadProgress = () => {
    if (!isAuthed || !course?.enrolled) return
    getCourseProgress(courseId)
      .then((entries) => setProgress(new Map(entries.map((e) => [e.lesson_id, e]))))
      .catch(() => {})
  }

  useEffect(() => {
    let cancelled = false
    getCourseDetail(courseId)
      .then((detail) => {
        if (!cancelled) setCourse(detail)
      })
      .catch((err) => {
        if (!cancelled) setError(err instanceof Error ? err.message : 'Error al cargar el curso')
      })
    return () => {
      cancelled = true
    }
  }, [courseId])

  useEffect(loadProgress, [courseId, isAuthed, course?.enrolled])

  const totalLessons = useMemo(
    () => course?.modules.reduce((acc, m) => acc + m.lessons.length, 0) ?? 0,
    [course],
  )
  const completedCount = useMemo(
    () => [...progress.values()].filter((p) => p.status === 'completed').length,
    [progress],
  )

  const handleLessonClick = (lesson: LessonSummary) => {
    if (!lesson.has_access) {
      if (!isAuthed) onRequireLogin()
      return
    }
    if (!lesson.stream_available) return
    setActiveLesson(lesson)
  }

  if (error) {
    return (
      <div className="mx-auto max-w-3xl px-6 py-24 text-center">
        <p className="text-muted-foreground">{error}</p>
        <button
          type="button"
          onClick={onBack}
          className="mt-6 inline-flex items-center gap-2 text-sm font-medium text-foreground hover:opacity-75"
        >
          <ChevronLeft className="size-4" /> Volver al catálogo
        </button>
      </div>
    )
  }

  if (!course) {
    return (
      <div className="flex min-h-[50vh] items-center justify-center">
        <Loader2 className="size-5 animate-spin text-muted-foreground" />
      </div>
    )
  }

  return (
    <div className="mx-auto max-w-6xl px-6 py-10 md:py-14">
      <button
        type="button"
        onClick={onBack}
        className="mb-8 inline-flex items-center gap-2 text-sm text-muted-foreground transition-colors hover:text-foreground"
      >
        <ChevronLeft className="size-4" /> Volver al catálogo
      </button>

      <div className="grid gap-10 lg:grid-cols-[1fr_380px]">
        <div>
          {activeLesson ? (
            <div>
              <VideoPlayer
                key={activeLesson.id}
                lessonId={activeLesson.id}
                title={activeLesson.title}
                startAt={progress.get(activeLesson.id)?.position_seconds ?? 0}
                onCompleted={loadProgress}
              />
              <h2 className="mt-4 text-lg font-medium tracking-tight text-foreground">
                {activeLesson.title}
              </h2>
            </div>
          ) : (
            <div
              className="aspect-video w-full rounded-xl border border-border bg-cover bg-center"
              style={{
                backgroundImage: `url(${(process.env.NEXT_PUBLIC_BASE_PATH ?? '') + course.image_path})`,
              }}
            />
          )}

          <div className="mt-6 flex flex-wrap items-center gap-x-5 gap-y-2 font-mono text-xs uppercase tracking-widest text-muted-foreground">
            <span>{course.level}</span>
            <span>{course.duration_hours}h de contenido</span>
            <span>{totalLessons} lecciones</span>
            {course.enrolled && (
              <span className="text-foreground">
                {completedCount}/{totalLessons} completadas
              </span>
            )}
          </div>

          <h1 className="mt-3 text-3xl font-medium tracking-tight text-foreground">
            {course.name}
          </h1>
          <p className="mt-3 max-w-2xl text-sm leading-relaxed text-muted-foreground">
            {course.description}
          </p>

          {!course.enrolled && (
            <div className="mt-6 rounded-xl border border-border bg-card p-5">
              <div className="flex flex-wrap items-center justify-between gap-4">
                <div>
                  <p className="font-mono text-2xl font-medium text-foreground">
                    {formatPrice(course.price_cents, course.currency)}
                  </p>
                  <p className="mt-1 text-xs text-muted-foreground">
                    Acceso de por vida · Certificado al finalizar
                  </p>
                </div>
                <button
                  type="button"
                  onClick={() => (isAuthed ? onBuy(course) : onRequireLogin())}
                  className="rounded-lg bg-primary px-6 py-3 text-sm font-medium text-primary-foreground transition-opacity hover:opacity-90"
                >
                  {isAuthed ? 'Comprar curso' : 'Inicia sesión para comprar'}
                </button>
              </div>
            </div>
          )}
        </div>

        <aside className="space-y-6">
          {course.enrolled && totalLessons > 0 && (
            <div>
              <div className="mb-2 flex items-center justify-between text-xs text-muted-foreground">
                <span>Progreso del curso</span>
                <span>{Math.round((completedCount * 100) / totalLessons)}%</span>
              </div>
              <div className="h-1.5 overflow-hidden rounded-full bg-secondary">
                <div
                  className="h-full rounded-full bg-foreground transition-all"
                  style={{ width: `${(completedCount * 100) / totalLessons}%` }}
                />
              </div>
            </div>
          )}

          {course.modules.map((module, mi) => (
            <div key={module.id} className="overflow-hidden rounded-xl border border-border">
              <div className="border-b border-border bg-card px-4 py-3">
                <p className="font-mono text-[10px] uppercase tracking-widest text-muted-foreground">
                  Módulo {mi + 1}
                </p>
                <h3 className="mt-0.5 text-sm font-medium text-foreground">{module.title}</h3>
              </div>
              <ul className="divide-y divide-border bg-background">
                {module.lessons.map((lesson) => {
                  const entry = progress.get(lesson.id)
                  const completed = entry?.status === 'completed'
                  const isActive = activeLesson?.id === lesson.id
                  return (
                    <li key={lesson.id}>
                      <button
                        type="button"
                        onClick={() => handleLessonClick(lesson)}
                        disabled={!lesson.has_access && isAuthed}
                        className={`flex w-full items-center gap-3 px-4 py-3 text-left transition-colors ${
                          isActive
                            ? 'bg-secondary'
                            : lesson.has_access
                              ? 'hover:bg-secondary/60'
                              : 'cursor-not-allowed opacity-60'
                        }`}
                      >
                        {completed ? (
                          <CheckCircle2 className="size-4 shrink-0 text-foreground" />
                        ) : lesson.has_access ? (
                          <PlayCircle className="size-4 shrink-0 text-foreground" />
                        ) : (
                          <Lock className="size-4 shrink-0 text-muted-foreground" />
                        )}
                        <span className="flex-1 text-sm text-foreground">{lesson.title}</span>
                        {lesson.is_free && !course.enrolled && (
                          <span className="rounded-full border border-border px-2 py-0.5 font-mono text-[9px] uppercase tracking-widest text-muted-foreground">
                            Gratis
                          </span>
                        )}
                        <span className="font-mono text-xs text-muted-foreground">
                          {lesson.duration_min}m
                        </span>
                      </button>
                    </li>
                  )
                })}
              </ul>
            </div>
          ))}
        </aside>
      </div>
    </div>
  )
}
