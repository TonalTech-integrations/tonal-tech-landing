import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { CourseDetail } from '@/components/course-detail'
import { getCourseDetail, type CourseDetail as CourseDetailData } from '@/lib/api'

vi.mock('@/lib/api', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/lib/api')>()
  return { ...actual, getCourseDetail: vi.fn() }
})

const mockGetCourseDetail = vi.mocked(getCourseDetail)

afterEach(() => {
  cleanup()
  vi.clearAllMocks()
})

function buildDetail(overrides: Partial<CourseDetailData> = {}): CourseDetailData {
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
    lessons_count: 2,
    enrolled: false,
    completed_lessons: 0,
    modules: [
      {
        id: 1,
        title: 'Fundamentos',
        position: 1,
        lessons: [
          {
            id: 101,
            title: 'Qué es un PLC',
            duration_min: 8,
            is_free: true,
            position: 1,
            has_access: true,
            stream_available: true,
          },
          {
            id: 102,
            title: 'Primer programa ladder',
            duration_min: 14,
            is_free: false,
            position: 2,
            has_access: false,
            stream_available: false,
          },
        ],
      },
    ],
    ...overrides,
  }
}

describe('CourseDetail', () => {
  it('test_course_detail_renders_modules_and_lessons_from_backend', async () => {
    // Arrange
    mockGetCourseDetail.mockResolvedValue(buildDetail())

    // Act
    render(<CourseDetail courseId="plc-basics" onClose={() => {}} />)

    // Assert: nombre, módulos y lecciones llegan del backend
    expect(await screen.findByText('PLC desde cero')).toBeInTheDocument()
    expect(screen.getByText('Fundamentos')).toBeInTheDocument()
    expect(screen.getByText('Qué es un PLC')).toBeInTheDocument()
    expect(screen.getByText('Primer programa ladder')).toBeInTheDocument()
    expect(screen.getByText('Gratis')).toBeInTheDocument()
    expect(mockGetCourseDetail).toHaveBeenCalledWith('plc-basics')
  })

  it('test_course_detail_error_state_retries', async () => {
    // Arrange: la primera carga falla
    mockGetCourseDetail.mockRejectedValueOnce(new Error('red'))
    render(<CourseDetail courseId="plc-basics" onClose={() => {}} />)

    // Assert: se muestra el estado de error
    expect(
      await screen.findByText('No se pudo cargar el curso. Intenta de nuevo en unos segundos.'),
    ).toBeInTheDocument()

    // Act: reintentar con el backend ya disponible
    mockGetCourseDetail.mockResolvedValue(buildDetail())
    fireEvent.click(screen.getByRole('button', { name: 'Reintentar' }))

    // Assert: el detalle se recupera
    expect(await screen.findByText('PLC desde cero')).toBeInTheDocument()
    expect(mockGetCourseDetail).toHaveBeenCalledTimes(2)
  })

  it('test_course_detail_closes_with_escape', async () => {
    // Arrange
    mockGetCourseDetail.mockResolvedValue(buildDetail())
    const onClose = vi.fn()
    render(<CourseDetail courseId="plc-basics" onClose={onClose} />)
    await screen.findByText('PLC desde cero')

    // Act
    fireEvent.keyDown(window, { key: 'Escape' })

    // Assert
    expect(onClose).toHaveBeenCalledTimes(1)
  })
})
