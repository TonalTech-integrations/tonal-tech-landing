"use client"

import { useCallback, useEffect, useState } from "react"
import Image from "next/image"
import { ArrowUpRight, Clock, Loader2, Lock, PlayCircle, Signal } from "lucide-react"

import { formatPrice, getCourses, type CourseSummary } from "@/lib/api"
import { CourseDetail } from "@/components/course-detail"

const basePath = process.env.NEXT_PUBLIC_BASE_PATH ?? ""

export function AcademySection() {
  const [courses, setCourses] = useState<CourseSummary[] | null>(null)
  const [error, setError] = useState("")
  const [activeCourseId, setActiveCourseId] = useState<string | null>(null)

  const loadCourses = useCallback(() => {
    getCourses()
      .then(setCourses)
      .catch(() =>
        setError("No se pudo cargar el catálogo. Intenta de nuevo en unos segundos."),
      )
  }, [])

  useEffect(() => {
    loadCourses()
  }, [loadCourses])

  const loading = courses === null && !error

  return (
    <section
      id="academy"
      className="relative overflow-hidden border-t border-border bg-background"
    >
      {/* Grid backdrop, echoing the reference site */}
      <div
        aria-hidden="true"
        className="pointer-events-none absolute inset-0 opacity-[0.4]"
        style={{
          backgroundImage:
            "linear-gradient(to right, var(--border) 1px, transparent 1px), linear-gradient(to bottom, var(--border) 1px, transparent 1px)",
          backgroundSize: "64px 64px",
          maskImage:
            "radial-gradient(ellipse 80% 60% at 50% 0%, black 40%, transparent 100%)",
        }}
      />

      <div className="relative mx-auto max-w-6xl px-6 py-24 md:py-32">
        {/* Header */}
        <div className="flex flex-col gap-6 md:flex-row md:items-end md:justify-between">
          <div className="max-w-2xl">
            <span className="inline-flex items-center gap-2 font-mono text-xs uppercase tracking-[0.2em] text-muted-foreground">
              <span className="h-px w-8 bg-foreground" />
              Academy
            </span>
            <h2 className="mt-5 text-balance text-4xl font-medium tracking-tight text-foreground md:text-5xl">
              Cursos de ingeniería que se aprenden haciendo
            </h2>
            <p className="mt-4 text-pretty leading-relaxed text-muted-foreground">
              Formación técnica en automatización y control industrial.
              Previsualiza las primeras lecciones gratis y desbloquea el curso
              completo con un pago único.
            </p>
          </div>
          <div className="font-mono text-xs uppercase tracking-[0.2em] text-muted-foreground">
            {(courses?.length ?? 0).toString().padStart(2, "0")} cursos disponibles
          </div>
        </div>

        {error ? (
          <div className="mt-14 flex flex-col items-center gap-4 rounded-xl border border-border bg-card px-5 py-12 text-center">
            <p className="text-sm text-muted-foreground">{error}</p>
            <button
              type="button"
              onClick={() => {
                setError("")
                loadCourses()
              }}
              className="rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground transition-opacity hover:opacity-90"
            >
              Reintentar
            </button>
          </div>
        ) : loading ? (
          <div className="mt-14 flex justify-center rounded-xl border border-border bg-card px-5 py-12">
            <Loader2 className="size-5 animate-spin text-muted-foreground" />
          </div>
        ) : (
          <div className="mt-14 grid gap-px overflow-hidden rounded-xl border border-border bg-border md:grid-cols-2 lg:grid-cols-3">
            {courses?.map((course) => (
              <button
                key={course.id}
                type="button"
                onClick={() => setActiveCourseId(course.id)}
                className="group flex flex-col bg-card text-left transition-colors hover:bg-secondary focus:outline-none focus-visible:ring-2 focus-visible:ring-ring"
              >
                <div className="relative aspect-[4/3] overflow-hidden">
                  <Image
                    src={
                      course.image_path
                        ? `${basePath}${course.image_path}`
                        : "/placeholder.svg"
                    }
                    alt={course.name}
                    fill
                    sizes="(max-width: 768px) 100vw, 33vw"
                    className="object-cover transition-transform duration-500 group-hover:scale-105"
                  />
                  <div className="absolute left-3 top-3 flex items-center gap-1.5 rounded-full border border-border bg-background/90 px-2.5 py-1 font-mono text-[10px] uppercase tracking-widest text-foreground backdrop-blur">
                    {course.enrolled ? (
                      <>
                        <PlayCircle className="size-3" /> Desbloqueado
                      </>
                    ) : course.is_free ? (
                      <>
                        <PlayCircle className="size-3" /> Gratis
                      </>
                    ) : (
                      <>
                        <Lock className="size-3" />{" "}
                        {formatPrice(course.price_cents, course.currency)}
                      </>
                    )}
                  </div>
                </div>

                <div className="flex flex-1 flex-col gap-4 p-5">
                  <div className="flex items-center gap-4 font-mono text-[11px] uppercase tracking-widest text-muted-foreground">
                    <span className="inline-flex items-center gap-1.5">
                      <Signal className="size-3.5" /> {course.level}
                    </span>
                    <span className="inline-flex items-center gap-1.5">
                      <Clock className="size-3.5" /> {course.duration_hours}h
                    </span>
                  </div>

                  <div className="flex-1">
                    <h3 className="text-lg font-medium tracking-tight text-foreground">
                      {course.name}
                    </h3>
                    <p className="mt-1.5 text-sm leading-relaxed text-muted-foreground">
                      {course.tagline}
                    </p>
                  </div>

                  <div className="flex items-center justify-between border-t border-border pt-4">
                    <span className="font-mono text-xs uppercase tracking-widest text-muted-foreground">
                      {course.lessons_count} lecciones
                    </span>
                    <span className="inline-flex items-center gap-1 text-sm font-medium text-foreground">
                      Ver curso
                      <ArrowUpRight className="size-4 transition-transform group-hover:translate-x-0.5 group-hover:-translate-y-0.5" />
                    </span>
                  </div>
                </div>
              </button>
            ))}
          </div>
        )}
      </div>

      {activeCourseId && (
        <CourseDetail
          key={activeCourseId}
          courseId={activeCourseId}
          onClose={() => setActiveCourseId(null)}
        />
      )}
    </section>
  )
}
