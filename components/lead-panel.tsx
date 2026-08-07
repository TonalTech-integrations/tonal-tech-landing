'use client'

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react'
import {
  ArrowLeft,
  ArrowRight,
  Check,
  Loader2,
  ScanLine,
  X,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'
import { companySizes, serviceCategoriesForm } from '@/lib/tonal-data'

interface LeadContextValue {
  openLead: (presetService?: string) => void
}

const LeadContext = createContext<LeadContextValue | null>(null)

export function useLead() {
  const ctx = useContext(LeadContext)
  if (!ctx) throw new Error('useLead must be used within LeadProvider')
  return ctx
}

type Stage = 'form' | 'diagnosing' | 'done'

interface FormState {
  name: string
  email: string
  size: string
  service: string
  requirements: string
}

const emptyForm: FormState = {
  name: '',
  email: '',
  size: '',
  service: '',
  requirements: '',
}

const steps = ['Contacto', 'Perfil', 'Requerimiento'] as const

export function LeadProvider({ children }: { children: ReactNode }) {
  const [open, setOpen] = useState(false)
  const [step, setStep] = useState(0)
  const [stage, setStage] = useState<Stage>('form')
  const [form, setForm] = useState<FormState>(emptyForm)

  const openLead = useCallback((presetService?: string) => {
    setForm({ ...emptyForm, service: presetService ?? '' })
    setStep(0)
    setStage('form')
    setOpen(true)
  }, [])

  const close = useCallback(() => setOpen(false), [])

  useEffect(() => {
    if (!open) return
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setOpen(false)
    }
    window.addEventListener('keydown', onKey)
    document.body.style.overflow = 'hidden'
    return () => {
      window.removeEventListener('keydown', onKey)
      document.body.style.overflow = ''
    }
  }, [open])

  const set = (key: keyof FormState, value: string) =>
    setForm((f) => ({ ...f, [key]: value }))

  const stepValid = useMemo(() => {
    if (step === 0)
      return form.name.trim().length > 1 && /^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(form.email)
    if (step === 1) return form.size !== '' && form.service !== ''
    return form.requirements.trim().length > 4
  }, [step, form])

  const submit = () => {
    setStage('diagnosing')
    window.setTimeout(() => setStage('done'), 2600)
  }

  const value = useMemo(() => ({ openLead }), [openLead])

  return (
    <LeadContext.Provider value={value}>
      {children}

      {/* Overlay */}
      <div
        aria-hidden={!open}
        onClick={close}
        className={cn(
          'fixed inset-0 z-50 bg-foreground/20 backdrop-blur-sm transition-opacity duration-300',
          open ? 'opacity-100' : 'pointer-events-none opacity-0',
        )}
      />

      {/* Slide-over */}
      <aside
        role="dialog"
        aria-modal="true"
        aria-label="Diagnóstico técnico"
        className={cn(
          'fixed inset-y-0 right-0 z-50 flex w-full max-w-md flex-col border-l border-border bg-background shadow-2xl transition-transform duration-400 ease-[cubic-bezier(0.16,1,0.3,1)]',
          open ? 'translate-x-0' : 'translate-x-full',
        )}
      >
        {/* Header */}
        <div className="tt-grid-fine relative flex items-center justify-between border-b border-border px-6 py-5">
          <div className="flex items-center gap-2.5">
            <span className="flex size-8 items-center justify-center rounded-md border border-border bg-secondary">
              <ScanLine className="size-4 text-foreground" />
            </span>
            <div>
              <p className="font-mono text-[0.7rem] uppercase tracking-[0.18em] text-muted-foreground">
                Tonal-Tech
              </p>
              <p className="text-sm font-semibold leading-tight">Diagnóstico Técnico</p>
            </div>
          </div>
          <button
            onClick={close}
            aria-label="Cerrar"
            className="flex size-8 items-center justify-center rounded-md border border-border text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
          >
            <X className="size-4" />
          </button>
        </div>

        {stage === 'form' && (
          <>
            {/* Progress */}
            <div className="flex items-center gap-2 px-6 pt-5">
              {steps.map((label, i) => (
                <div key={label} className="flex flex-1 flex-col gap-1.5">
                  <div
                    className={cn(
                      'h-1 rounded-full transition-colors',
                      i <= step ? 'bg-primary' : 'bg-border',
                    )}
                  />
                  <span
                    className={cn(
                      'font-mono text-[0.65rem] uppercase tracking-wider',
                      i === step ? 'text-foreground' : 'text-muted-foreground',
                    )}
                  >
                    {String(i + 1).padStart(2, '0')} {label}
                  </span>
                </div>
              ))}
            </div>

            {/* Body */}
            <div className="flex-1 overflow-y-auto px-6 py-6">
              {step === 0 && (
                <div className="space-y-5">
                  <Field label="Nombre completo">
                    <input
                      value={form.name}
                      onChange={(e) => set('name', e.target.value)}
                      placeholder="Ada Lovelace"
                      className={inputClass}
                    />
                  </Field>
                  <Field label="Correo corporativo">
                    <input
                      type="email"
                      value={form.email}
                      onChange={(e) => set('email', e.target.value)}
                      placeholder="ada@empresa.com"
                      className={inputClass}
                    />
                  </Field>
                </div>
              )}

              {step === 1 && (
                <div className="space-y-6">
                  <Field label="Tamaño de la empresa">
                    <div className="grid gap-2">
                      {companySizes.map((s) => (
                        <OptionPill
                          key={s}
                          active={form.size === s}
                          onClick={() => set('size', s)}
                        >
                          {s}
                        </OptionPill>
                      ))}
                    </div>
                  </Field>
                  <Field label="Categoría de servicio">
                    <div className="grid gap-2">
                      {serviceCategoriesForm.map((s) => (
                        <OptionPill
                          key={s}
                          active={form.service === s}
                          onClick={() => set('service', s)}
                        >
                          {s}
                        </OptionPill>
                      ))}
                    </div>
                  </Field>
                </div>
              )}

              {step === 2 && (
                <Field label="Describe tu requerimiento">
                  <textarea
                    value={form.requirements}
                    onChange={(e) => set('requirements', e.target.value)}
                    rows={7}
                    placeholder="Cuéntanos sobre tu operación actual, retos técnicos y objetivos…"
                    className={cn(inputClass, 'resize-none leading-relaxed')}
                  />
                </Field>
              )}
            </div>

            {/* Footer nav */}
            <div className="flex items-center justify-between gap-3 border-t border-border px-6 py-4">
              <Button
                variant="ghost"
                onClick={() => setStep((s) => Math.max(0, s - 1))}
                disabled={step === 0}
                className="h-10 px-3"
              >
                <ArrowLeft className="size-4" /> Atrás
              </Button>
              {step < steps.length - 1 ? (
                <Button
                  onClick={() => setStep((s) => s + 1)}
                  disabled={!stepValid}
                  className="h-10 px-5"
                >
                  Continuar <ArrowRight className="size-4" />
                </Button>
              ) : (
                <Button onClick={submit} disabled={!stepValid} className="h-10 px-5">
                  Iniciar diagnóstico <ScanLine className="size-4" />
                </Button>
              )}
            </div>
          </>
        )}

        {stage === 'diagnosing' && (
          <div className="tt-grid-fine flex flex-1 flex-col items-center justify-center gap-6 px-8 text-center">
            <div className="relative flex size-20 items-center justify-center">
              <span className="absolute inset-0 animate-ping rounded-full border border-primary/30" />
              <span className="flex size-20 items-center justify-center rounded-full border border-border bg-background">
                <Loader2 className="size-8 animate-spin text-foreground" />
              </span>
            </div>
            <div className="space-y-1.5">
              <p className="font-mono text-xs uppercase tracking-[0.2em] text-muted-foreground">
                System Diagnosis in Progress
              </p>
              <p className="text-lg font-semibold text-balance">
                Analizando madurez operativa…
              </p>
            </div>
            <DiagnosticTicker />
          </div>
        )}

        {stage === 'done' && (
          <div className="flex flex-1 flex-col items-center justify-center gap-6 px-8 text-center">
            <span className="flex size-16 items-center justify-center rounded-full border border-border bg-secondary">
              <Check className="size-7 text-foreground" />
            </span>
            <div className="space-y-2">
              <p className="text-xl font-semibold text-balance">Diagnóstico agendado</p>
              <p className="text-sm leading-relaxed text-muted-foreground text-pretty">
                Gracias, {form.name.split(' ')[0] || 'equipo'}. Un arquitecto de Tonal-Tech
                revisará tu caso y te contactará en{' '}
                <span className="text-foreground">{form.email}</span> en menos de 24 horas
                hábiles.
              </p>
            </div>
            <Button onClick={close} className="h-10 px-5">
              Entendido
            </Button>
          </div>
        )}
      </aside>
    </LeadContext.Provider>
  )
}

const inputClass =
  'w-full rounded-md border border-input bg-background px-3 py-2.5 text-sm text-foreground placeholder:text-muted-foreground/70 outline-none transition-colors focus:border-ring focus:ring-3 focus:ring-ring/15'

function Field({ label, children }: { label: string; children: ReactNode }) {
  return (
    <label className="block space-y-2">
      <span className="font-mono text-[0.7rem] uppercase tracking-[0.15em] text-muted-foreground">
        {label}
      </span>
      {children}
    </label>
  )
}

function OptionPill({
  active,
  onClick,
  children,
}: {
  active: boolean
  onClick: () => void
  children: ReactNode
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        'flex items-center justify-between rounded-md border px-3.5 py-2.5 text-left text-sm transition-all',
        active
          ? 'border-primary bg-primary/[0.04] font-medium text-foreground'
          : 'border-border text-muted-foreground hover:border-foreground/30 hover:text-foreground',
      )}
    >
      {children}
      <span
        className={cn(
          'flex size-4 items-center justify-center rounded-full border transition-colors',
          active ? 'border-primary bg-primary text-primary-foreground' : 'border-border',
        )}
      >
        {active && <Check className="size-2.5" />}
      </span>
    </button>
  )
}

function DiagnosticTicker() {
  const lines = [
    'Escaneando superficie de infraestructura',
    'Evaluando vectores de seguridad',
    'Mapeando arquitectura de datos',
    'Compilando reporte de madurez',
  ]
  const [i, setI] = useState(0)
  useEffect(() => {
    const t = window.setInterval(() => setI((p) => (p + 1) % lines.length), 650)
    return () => window.clearInterval(t)
  }, [])
  return (
    <p className="font-mono text-xs text-muted-foreground">
      <span className="text-foreground">›</span> {lines[i]}
    </p>
  )
}
