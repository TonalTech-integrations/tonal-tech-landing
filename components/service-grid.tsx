'use client'

import { useMemo, useState } from 'react'
import { ArrowUpRight, Check } from 'lucide-react'
import { cn } from '@/lib/utils'
import { useLead } from '@/components/lead-panel'
import {
  categoryFilters,
  services,
  type ServiceCategory,
  type ServiceToken,
} from '@/lib/tonal-data'

export function ServiceGrid() {
  const [filter, setFilter] = useState<ServiceCategory | 'all'>('all')

  const visible = useMemo(
    () => services.filter((s) => filter === 'all' || s.category === filter),
    [filter],
  )

  return (
    <section id="servicios" className="relative border-b border-border">
      <div className="tt-rails absolute inset-0 opacity-40" aria-hidden="true" />
      <div className="relative mx-auto max-w-6xl px-5 py-20 lg:px-8 lg:py-24">
        <div className="flex flex-col gap-6 md:flex-row md:items-end md:justify-between">
          <div className="max-w-xl">
            <p className="font-mono text-[0.7rem] uppercase tracking-[0.2em] text-muted-foreground">
              Catálogo de ingeniería
            </p>
            <h2 className="mt-3 text-balance text-3xl font-semibold tracking-tight lg:text-4xl">
              Tokens de servicio segmentados
            </h2>
            <p className="mt-3 text-pretty leading-relaxed text-muted-foreground">
              Módulos de ingeniería diseñados por objetivo de negocio. Filtra por categoría
              para aislar la solución adecuada.
            </p>
          </div>
        </div>

        {/* Filter tabs */}
        <div className="mt-8 flex flex-wrap gap-2">
          {categoryFilters.map((f) => (
            <button
              key={f.id}
              onClick={() => setFilter(f.id)}
              className={cn(
                'rounded-full border px-4 py-1.5 text-sm transition-all',
                filter === f.id
                  ? 'border-foreground bg-foreground text-background'
                  : 'border-border text-muted-foreground hover:border-foreground/40 hover:text-foreground',
              )}
            >
              {f.label}
            </button>
          ))}
        </div>

        {/* Grid */}
        <div className="mt-8 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {visible.map((s, i) => (
            <ServiceCard key={s.id} service={s} highlight={s.category === 'labs'} order={i} />
          ))}
        </div>
      </div>
    </section>
  )
}

function ServiceCard({
  service,
  highlight,
  order,
}: {
  service: ServiceToken
  highlight?: boolean
  order: number
}) {
  const { openLead } = useLead()
  const Icon = service.icon

  return (
    <article
      className={cn(
        'group relative flex flex-col overflow-hidden rounded-xl border border-border bg-card p-6 transition-all duration-300 hover:-translate-y-1 hover:border-foreground/40 hover:shadow-[0_16px_40px_-24px_oklch(0.21_0.02_257_/_0.5)]',
        highlight && 'sm:col-span-2 lg:col-span-1',
      )}
    >
      <div
        className="tt-grid-fine absolute inset-0 opacity-0 transition-opacity duration-300 group-hover:opacity-100"
        aria-hidden="true"
      />
      {/* corner ticks */}
      <span className="absolute left-0 top-0 size-3 border-l border-t border-foreground/20" />
      <span className="absolute right-0 top-0 size-3 border-r border-t border-foreground/20" />

      <div className="relative flex items-start justify-between">
        <span className="flex size-11 items-center justify-center rounded-lg border border-border bg-secondary text-foreground transition-colors group-hover:border-foreground/30">
          <Icon className="size-5" strokeWidth={1.6} />
        </span>
        <span className="font-mono text-xs text-muted-foreground/60">{service.index}</span>
      </div>

      <div className="relative mt-5 flex-1">
        {service.badge && (
          <span
            className={cn(
              'mb-3 inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 font-mono text-[0.65rem] uppercase tracking-wider',
              highlight
                ? 'border-foreground/30 bg-foreground text-background'
                : 'border-border bg-secondary text-muted-foreground',
            )}
          >
            {highlight && <span className="size-1 rounded-full bg-background" />}
            {service.badge}
          </span>
        )}

        <p className="font-mono text-[0.7rem] uppercase tracking-[0.15em] text-muted-foreground">
          {service.target}
        </p>
        <h3 className="mt-1.5 text-lg font-semibold leading-snug tracking-tight text-balance">
          {service.title}
        </h3>

        {service.description && (
          <p className="mt-3 text-sm leading-relaxed text-muted-foreground text-pretty">
            {service.description}
          </p>
        )}

        {service.features && (
          <ul className="mt-4 space-y-2.5">
            {service.features.map((f) => (
              <li key={f} className="flex gap-2.5 text-sm text-muted-foreground">
                <Check className="mt-0.5 size-4 shrink-0 text-foreground/70" />
                <span className="leading-snug">{f}</span>
              </li>
            ))}
          </ul>
        )}

        {service.tags && (
          <div className="mt-4 flex flex-wrap gap-2">
            {service.tags.map((t) => (
              <span
                key={t}
                className="rounded-md border border-border bg-background px-2.5 py-1 font-mono text-[0.7rem] text-muted-foreground"
              >
                {t}
              </span>
            ))}
          </div>
        )}
      </div>

      <button
        onClick={() => openLead(service.title)}
        className="relative mt-6 flex items-center justify-between border-t border-border pt-4 text-sm font-medium text-foreground"
      >
        Cotizar servicio
        <span className="flex size-7 items-center justify-center rounded-md border border-border transition-all group-hover:border-foreground group-hover:bg-foreground group-hover:text-background">
          <ArrowUpRight className="size-4" />
        </span>
      </button>
    </article>
  )
}
