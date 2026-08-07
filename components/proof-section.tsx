const metrics = [
  { value: '99.98%', label: 'Uptime de infraestructura gestionada' },
  { value: '+180', label: 'Auditorías de seguridad ejecutadas' },
  { value: '4.2M', label: 'Transacciones B2B procesadas / mes' },
  { value: '24 h', label: 'Respuesta en soporte crítico' },
]

const cases = [
  {
    sector: 'Retail / WMS',
    result: 'Reducción del 38% en tiempos de picking tras implementar WMS inteligente.',
  },
  {
    sector: 'Fintech / Cloud',
    result: 'Migración a arquitectura cloud multi-región con cero downtime.',
  },
  {
    sector: 'Salud / Seguridad',
    result: 'Certificación ISO 27001 y remediación completa post-pentesting.',
  },
]

export function ProofSection() {
  return (
    <section id="casos" className="relative border-b border-border">
      <div className="mx-auto max-w-6xl px-5 py-20 lg:px-8 lg:py-24">
        <p className="font-mono text-[0.7rem] uppercase tracking-[0.2em] text-muted-foreground">
          Casos de éxito
        </p>
        <h2 className="mt-3 max-w-2xl text-balance text-3xl font-semibold tracking-tight lg:text-4xl">
          Resultados medibles en operaciones críticas
        </h2>

        <div className="mt-10 grid grid-cols-2 divide-x divide-y divide-border overflow-hidden rounded-xl border border-border lg:grid-cols-4 lg:divide-y-0">
          {metrics.map((m) => (
            <div key={m.label} className="tt-grid-fine bg-card p-6">
              <p className="text-3xl font-semibold tracking-tight lg:text-4xl">{m.value}</p>
              <p className="mt-2 text-sm leading-snug text-muted-foreground text-pretty">
                {m.label}
              </p>
            </div>
          ))}
        </div>

        <div className="mt-4 grid gap-4 md:grid-cols-3">
          {cases.map((c) => (
            <div
              key={c.sector}
              className="rounded-xl border border-border bg-card p-6 transition-colors hover:border-foreground/30"
            >
              <span className="font-mono text-[0.7rem] uppercase tracking-[0.15em] text-muted-foreground">
                {c.sector}
              </span>
              <p className="mt-3 leading-relaxed text-foreground text-pretty">{c.result}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}
