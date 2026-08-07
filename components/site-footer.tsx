'use client'

import { ScanLine } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { useLead } from '@/components/lead-panel'

const columns = [
  {
    title: 'Soluciones B2B',
    links: [
      'Optimización & Analítica',
      'Arquitectura Cloud',
      'Ciberseguridad',
      'Soporte & Infraestructura IT',
    ],
  },
  {
    title: 'Compañía',
    links: ['Tonal-Tech Labs', 'Academy', 'Casos de Éxito', 'Contacto'],
  },
  {
    title: 'Recursos',
    links: ['Reporte de Madurez', 'Certificación ISO 27001', 'Documentación', 'Blog técnico'],
  },
]

export function SiteFooter() {
  const { openLead } = useLead()

  return (
    <footer className="relative overflow-hidden">
      {/* Final CTA */}
      <div className="tt-grid relative border-b border-border">
        <div className="tt-fade-mask absolute inset-0 tt-rails opacity-50" aria-hidden="true" />
        <div className="relative mx-auto max-w-6xl px-5 py-20 text-center lg:px-8 lg:py-28">
          <h2 className="mx-auto max-w-3xl text-balance text-3xl font-semibold tracking-tight lg:text-5xl">
            Diseñemos tu próxima arquitectura invulnerable
          </h2>
          <p className="mx-auto mt-5 max-w-xl text-pretty leading-relaxed text-muted-foreground">
            Comienza con un diagnóstico técnico gratuito. Sin compromiso, con un reporte de
            madurez operativa accionable.
          </p>
          <Button
            onClick={() => openLead()}
            className="mt-8 h-12 px-7 text-[0.95rem]"
          >
            <ScanLine className="size-4" /> Agendar diagnóstico gratuito
          </Button>
        </div>
      </div>

      {/* Links */}
      <div className="mx-auto max-w-6xl px-5 py-14 lg:px-8">
        <div className="grid grid-cols-2 gap-10 md:grid-cols-4">
          <div className="col-span-2 md:col-span-1">
            <div className="flex items-center gap-2.5">
              <span className="flex size-8 items-center justify-center rounded-md border border-foreground/80 bg-foreground text-background">
                <svg width="16" height="16" viewBox="0 0 20 20" fill="none" aria-hidden="true">
                  <path
                    d="M3 6h14M10 6v11M6 10h8"
                    stroke="currentColor"
                    strokeWidth="1.4"
                    strokeLinecap="round"
                  />
                </svg>
              </span>
              <span className="text-[0.95rem] font-semibold tracking-tight">
                Tonal<span className="text-muted-foreground">-Tech</span>
              </span>
            </div>
            <p className="mt-4 max-w-xs text-sm leading-relaxed text-muted-foreground text-pretty">
              Agencia premium de tecnología, software y ciberseguridad para operaciones B2B.
            </p>
          </div>

          {columns.map((col) => (
            <div key={col.title}>
              <p className="font-mono text-[0.7rem] uppercase tracking-[0.15em] text-muted-foreground">
                {col.title}
              </p>
              <ul className="mt-4 space-y-2.5">
                {col.links.map((l) => (
                  <li key={l}>
                    <a
                      href="#"
                      className="text-sm text-muted-foreground transition-colors hover:text-foreground"
                    >
                      {l}
                    </a>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>

        <div className="mt-12 flex flex-col items-start justify-between gap-3 border-t border-border pt-6 sm:flex-row sm:items-center">
          <p className="font-mono text-xs text-muted-foreground">
            © {new Date().getFullYear()} Tonal-Tech · Ingeniería B2B
          </p>
          <div className="flex gap-5 font-mono text-xs text-muted-foreground">
            <a href="#" className="transition-colors hover:text-foreground">
              Privacidad
            </a>
            <a href="#" className="transition-colors hover:text-foreground">
              Términos
            </a>
            <a href="#" className="transition-colors hover:text-foreground">
              ISO 27001
            </a>
          </div>
        </div>
      </div>
    </footer>
  )
}
