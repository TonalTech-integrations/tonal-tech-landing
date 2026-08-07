import {
  BarChart3,
  Layers,
  ShieldCheck,
  Cpu,
  Rocket,
  type LucideIcon,
} from 'lucide-react'

export type ServiceCategory = 'software' | 'support' | 'labs' | 'academy'

export const categoryFilters: { id: ServiceCategory | 'all'; label: string }[] = [
  { id: 'all', label: 'Todo el catálogo' },
  { id: 'software', label: 'B2B Software' },
  { id: 'support', label: 'Soporte IT' },
  { id: 'labs', label: 'Labs' },
  { id: 'academy', label: 'Academy' },
]

export interface ServiceToken {
  id: string
  index: string
  category: ServiceCategory
  title: string
  target: string
  icon: LucideIcon
  badge?: string
  description?: string
  features?: string[]
  tags?: string[]
}

export const services: ServiceToken[] = [
  {
    id: 'optimizacion',
    index: '01',
    category: 'software',
    title: 'Optimización Comercial y Analítica',
    target: 'Empresas medianas',
    icon: BarChart3,
    features: [
      'Sistemas WMS inteligentes',
      'Dashboards de BI & analítica comercial',
      'E-commerce corporativo y portales B2B',
    ],
  },
  {
    id: 'cloud',
    index: '02',
    category: 'software',
    title: 'Arquitectura e Infraestructura Cloud',
    target: 'Empresas en expansión',
    icon: Layers,
    features: [
      'ERP & CRM a la medida',
      'Arquitectura Cloud & DevOps (AWS / Azure)',
      'Refactorización y optimización de software',
    ],
  },
  {
    id: 'ciberseguridad',
    index: '03',
    category: 'software',
    title: 'Ciberseguridad Avanzada y Cumplimiento',
    target: 'Enterprise & grandes cuentas',
    icon: ShieldCheck,
    features: [
      'Auditorías de código fuente (SAST / DAST)',
      'Pruebas de penetración avanzadas (Pentesting)',
      'Consultoría y certificación ISO 27001',
    ],
  },
  {
    id: 'soporte',
    index: '04',
    category: 'support',
    title: 'Soporte de Cómputo e Infraestructura Física',
    target: 'IT local & diagnóstico',
    icon: Cpu,
    badge: 'Soporte Técnico & Diagnóstico',
    features: [
      'Pólizas de mantenimiento preventivo y correctivo de hardware',
      'Optimización de redes locales',
      'Reporte de Madurez Operativa para digitalización',
    ],
  },
  {
    id: 'labs',
    index: '05',
    category: 'labs',
    title: 'Tonal-Tech Labs',
    target: 'App development & innovation lab',
    icon: Rocket,
    badge: 'Mobile & Product Lab',
    description:
      'Nuestro laboratorio de desarrollo y publicación de herramientas móviles en App Store y Google Play.',
    tags: [
      'Sistemas Multiempleo',
      'Finanzas Personales Intuitivas',
      'EdTech & Productividad',
    ],
  },
]

export const companySizes = [
  'Mediana empresa',
  'Grande / Enterprise',
  'Profesional independiente',
] as const

export const serviceCategoriesForm = [
  'Optimización Comercial y Analítica',
  'Arquitectura e Infraestructura Cloud',
  'Ciberseguridad Avanzada',
  'Soporte de Cómputo e Infraestructura IT',
  'Tonal-Tech Labs (Mobile)',
  'Formación / Academy',
] as const
