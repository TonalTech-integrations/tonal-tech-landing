'use client'

import { ArrowRight, ScanLine } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { useLead } from '@/components/lead-panel'

const badges = ['ISO 27001', 'AWS / Azure', 'DevOps', 'Pentesting']

export function TonalHero() {
  const { openLead } = useLead()

  return (
    <section className="relative overflow-hidden border-b border-border pt-16">
      {/* engraved backgrounds */}
      <div className="tt-grid tt-fade-mask absolute inset-0" aria-hidden="true" />
      <div className="tt-rails absolute inset-0 opacity-60" aria-hidden="true" />
      <div
        className="absolute inset-x-0 top-16 h-px bg-gradient-to-r from-transparent via-border to-transparent"
        aria-hidden="true"
      />

      <div className="relative mx-auto max-w-6xl px-5 py-20 lg:px-8 lg:py-28">
        <div className="tt-reveal mb-6 inline-flex items-center gap-2 rounded-full border border-border bg-background/70 px-3 py-1 backdrop-blur">
          <span className="relative flex size-1.5">
            <span className="absolute inline-flex size-full animate-ping rounded-full bg-foreground/40" />
            <span className="relative inline-flex size-1.5 rounded-full bg-foreground" />
          </span>
          <span className="font-mono text-[0.7rem] uppercase tracking-[0.18em] text-muted-foreground">
            Ingeniería B2B · Software · Ciberseguridad
          </span>
        </div>

        <h1
          className="tt-reveal max-w-4xl text-balance text-4xl font-semibold leading-[1.08] tracking-tight sm:text-5xl lg:text-6xl"
          style={{ animationDelay: '80ms' }}
        >
          Arquitectura de software invulnerable, analítica comercial y soluciones de
          infraestructura IT
        </h1>

        <p
          className="tt-reveal mt-6 max-w-2xl text-pretty text-base leading-relaxed text-muted-foreground lg:text-lg"
          style={{ animationDelay: '160ms' }}
        >
          Transformamos operaciones mediante sistemas a la medida, infraestructura
          resiliente, auditorías de ciberseguridad y laboratorios de innovación móvil.
        </p>

        <div
          className="tt-reveal mt-9 flex flex-col gap-3 sm:flex-row"
          style={{ animationDelay: '240ms' }}
        >
          <Button onClick={() => openLead()} className="h-12 px-6 text-[0.95rem]">
            <ScanLine className="size-4" /> Agendar diagnóstico gratuito
          </Button>
          <Button
            variant="outline"
            className="h-12 border-foreground/20 px-6 text-[0.95rem] hover:border-foreground/50"
            onClick={() => {
              document.getElementById('servicios')?.scrollIntoView({ behavior: 'smooth' })
            }}
          >
            Explorar catálogo <ArrowRight className="size-4" />
          </Button>
        </div>

        <div
          className="tt-reveal mt-14 flex flex-wrap items-center gap-x-6 gap-y-3 border-t border-border pt-6"
          style={{ animationDelay: '320ms' }}
        >
          <span className="font-mono text-[0.7rem] uppercase tracking-[0.15em] text-muted-foreground/70">
            Stack certificado
          </span>
          {badges.map((b) => (
            <span
              key={b}
              className="font-mono text-xs tracking-wide text-muted-foreground"
            >
              {b}
            </span>
          ))}
        </div>
      </div>
    </section>
  )
}
