'use client'

import { useEffect, useState } from 'react'
import { ChevronDown, Menu, X } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'
import { useLead } from '@/components/lead-panel'

const solutions = [
  { label: 'Optimización & Analítica', href: '#servicios' },
  { label: 'Arquitectura Cloud', href: '#servicios' },
  { label: 'Ciberseguridad', href: '#servicios' },
  { label: 'Soporte & Infraestructura IT', href: '#servicios' },
]

const navLinks = [
  { label: 'Tonal-Tech Labs', href: '#servicios' },
  { label: 'Academy', href: '#academy' },
  { label: 'Casos de Éxito', href: '#casos' },
]

function Logo() {
  return (
    <a href="#" className="flex items-center gap-2.5" aria-label="Tonal-Tech inicio">
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
    </a>
  )
}

export function SiteHeader() {
  const { openLead } = useLead()
  const [scrolled, setScrolled] = useState(false)
  const [mobileOpen, setMobileOpen] = useState(false)

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 8)
    onScroll()
    window.addEventListener('scroll', onScroll, { passive: true })
    return () => window.removeEventListener('scroll', onScroll)
  }, [])

  return (
    <header
      className={cn(
        'fixed inset-x-0 top-0 z-40 transition-colors duration-300',
        scrolled
          ? 'border-b border-border bg-background/85 backdrop-blur-md'
          : 'border-b border-transparent',
      )}
    >
      <div className="mx-auto flex h-16 max-w-6xl items-center justify-between px-5 lg:px-8">
        <Logo />

        <nav className="hidden items-center gap-1 lg:flex">
          <div className="group relative">
            <button className="flex items-center gap-1 rounded-md px-3 py-2 text-sm text-muted-foreground transition-colors hover:text-foreground">
              Soluciones B2B
              <ChevronDown className="size-3.5 transition-transform group-hover:rotate-180" />
            </button>
            <div className="invisible absolute left-0 top-full w-64 translate-y-1 pt-2 opacity-0 transition-all duration-200 group-hover:visible group-hover:translate-y-0 group-hover:opacity-100">
              <div className="tt-grid-fine overflow-hidden rounded-lg border border-border bg-background p-1.5 shadow-xl">
                {solutions.map((s, i) => (
                  <a
                    key={s.label}
                    href={s.href}
                    className="flex items-center gap-3 rounded-md px-3 py-2.5 text-sm text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
                  >
                    <span className="font-mono text-[0.65rem] text-muted-foreground/60">
                      {String(i + 1).padStart(2, '0')}
                    </span>
                    {s.label}
                  </a>
                ))}
              </div>
            </div>
          </div>
          {navLinks.map((l) => (
            <a
              key={l.label}
              href={l.href}
              className="rounded-md px-3 py-2 text-sm text-muted-foreground transition-colors hover:text-foreground"
            >
              {l.label}
            </a>
          ))}
        </nav>

        <div className="hidden lg:block">
          <Button
            variant="outline"
            onClick={() => openLead()}
            className="h-10 border-foreground/25 px-4 font-medium hover:border-foreground/50"
          >
            Diagnóstico Técnico Gratuito
          </Button>
        </div>

        <button
          className="flex size-9 items-center justify-center rounded-md border border-border text-foreground lg:hidden"
          onClick={() => setMobileOpen((o) => !o)}
          aria-label="Menú"
        >
          {mobileOpen ? <X className="size-5" /> : <Menu className="size-5" />}
        </button>
      </div>

      {mobileOpen && (
        <div className="border-t border-border bg-background px-5 py-4 lg:hidden">
          <div className="flex flex-col gap-1">
            <p className="px-3 py-2 font-mono text-[0.65rem] uppercase tracking-wider text-muted-foreground">
              Soluciones B2B
            </p>
            {solutions.map((s) => (
              <a
                key={s.label}
                href={s.href}
                onClick={() => setMobileOpen(false)}
                className="rounded-md px-3 py-2 text-sm text-muted-foreground hover:bg-muted hover:text-foreground"
              >
                {s.label}
              </a>
            ))}
            <div className="my-2 h-px bg-border" />
            {navLinks.map((l) => (
              <a
                key={l.label}
                href={l.href}
                onClick={() => setMobileOpen(false)}
                className="rounded-md px-3 py-2 text-sm text-muted-foreground hover:bg-muted hover:text-foreground"
              >
                {l.label}
              </a>
            ))}
            <Button
              onClick={() => {
                setMobileOpen(false)
                openLead()
              }}
              className="mt-3 h-11"
            >
              Diagnóstico Técnico Gratuito
            </Button>
          </div>
        </div>
      )}
    </header>
  )
}
