'use client'

import { ArrowRight, GraduationCap } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { useLead } from '@/components/lead-panel'

const courses = [
  'Código Limpio',
  'Ciberseguridad',
  'Negocios Digitales',
  'Adopción Corporativa',
]

export function AcademyBanner() {
  const { openLead } = useLead()

  return (
    <section id="academy" className="relative border-b border-border">
      <div className="mx-auto max-w-6xl px-5 py-20 lg:px-8 lg:py-24">
        <div className="tt-grid relative overflow-hidden rounded-2xl border border-border bg-secondary/40">
          <div className="tt-fade-mask pointer-events-none absolute inset-0 tt-rails opacity-50" />
          <span className="absolute left-0 top-0 size-4 border-l-2 border-t-2 border-foreground/30" />
          <span className="absolute right-0 bottom-0 size-4 border-r-2 border-b-2 border-foreground/30" />

          <div className="relative flex flex-col items-start gap-8 p-8 lg:flex-row lg:items-center lg:justify-between lg:p-12">
            <div className="max-w-2xl">
              <div className="inline-flex items-center gap-2 rounded-full border border-border bg-background px-3 py-1">
                <GraduationCap className="size-3.5 text-foreground" />
                <span className="font-mono text-[0.7rem] uppercase tracking-[0.18em] text-muted-foreground">
                  Tonal-Tech Academy
                </span>
              </div>
              <h2 className="mt-5 text-balance text-3xl font-semibold tracking-tight lg:text-4xl">
                Capacitación técnica y formación empresarial
              </h2>
              <p className="mt-4 text-pretty leading-relaxed text-muted-foreground">
                Cursos online asíncronos en código limpio, ciberseguridad y negocios
                digitales, más módulos de adopción y capacitación para personal corporativo.
              </p>

              <div className="mt-6 flex flex-wrap gap-2">
                {courses.map((c) => (
                  <span
                    key={c}
                    className="rounded-md border border-border bg-background px-3 py-1.5 font-mono text-xs text-muted-foreground"
                  >
                    {c}
                  </span>
                ))}
              </div>
            </div>

            <div className="w-full shrink-0 lg:w-auto">
              <Button
                onClick={() => openLead('Formación / Academy')}
                className="h-12 w-full px-6 text-[0.95rem] lg:w-auto"
              >
                Explorar cursos / Capacitar equipo
                <ArrowRight className="size-4" />
              </Button>
            </div>
          </div>
        </div>
      </div>
    </section>
  )
}
