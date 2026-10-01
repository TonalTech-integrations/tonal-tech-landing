import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { AcademySection } from '@/components/academy-section'
import { getCourses, type CourseSummary } from '@/lib/api'

vi.mock('@/lib/api', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/lib/api')>()
  return { ...actual, getCourses: vi.fn() }
})

const mockGetCourses = vi.mocked(getCourses)

afterEach(() => {
  cleanup()
  vi.clearAllMocks()
})

function buildCourse(overrides: Partial<CourseSummary> = {}): CourseSummary {
  return {
    id: 'plc-basics',
    name: 'PLC desde cero',
    tagline: 'Automatización industrial práctica',
    description: 'Curso introductorio de PLC',
    price_cents: 4900,
    currency: 'usd',
    level: 'Inicial',
    duration_hours: 6,
    image_path: '/img/plc.png',
    lessons_count: 12,
    enrolled: false,
    completed_lessons: 0,
    ...overrides,
  }
}

describe('AcademySection', () => {
  it('test_landing_academy_section_uses_backend_catalog', async () => {
    // Arrange: el backend devuelve 2 cursos
    mockGetCourses.mockResolvedValue([
      buildCourse(),
      buildCourse({ id: 'scada-pro', name: 'SCADA industrial', enrolled: true }),
    ])

    // Act
    render(<AcademySection />)

    // Assert: la sección muestra el catálogo del backend
    expect(await screen.findByText('PLC desde cero')).toBeInTheDocument()
    expect(screen.getByText('SCADA industrial')).toBeInTheDocument()
    expect(screen.getByText('02 cursos disponibles')).toBeInTheDocument()
    expect(mockGetCourses).toHaveBeenCalledTimes(1)
  })

  it('test_academy_section_error_state_retries', async () => {
    // Arrange: la primera carga falla
    mockGetCourses.mockRejectedValueOnce(new Error('red'))
    render(<AcademySection />)

    // Assert: se muestra el estado de error
    expect(
      await screen.findByText('No se pudo cargar el catálogo. Intenta de nuevo en unos segundos.'),
    ).toBeInTheDocument()

    // Act: reintentar con el backend ya disponible
    mockGetCourses.mockResolvedValue([buildCourse()])
    fireEvent.click(screen.getByRole('button', { name: 'Reintentar' }))

    // Assert: el catálogo se recupera
    expect(await screen.findByText('PLC desde cero')).toBeInTheDocument()
    expect(mockGetCourses).toHaveBeenCalledTimes(2)
  })
})
