import { act, cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, beforeAll, beforeEach, describe, expect, it, vi } from 'vitest'

import { VideoPlayer } from '@/components/academy/video-player'
import { getStreamUrl } from '@/lib/api'

vi.mock('@/lib/api', () => ({
  getStreamUrl: vi.fn(),
  saveLessonProgress: vi.fn(() => Promise.resolve()),
}))

const mockGetStreamUrl = vi.mocked(getStreamUrl)

// Epoch (segundos) fijo para temporizadores deterministas
const NOW = Math.floor(Date.parse('2026-10-01T12:00:00Z') / 1000)

// jsdom no implementa HTMLMediaElement: currentTime mutable y play() simulados
const currentTimeStore = new WeakMap<HTMLMediaElement, number>()

beforeAll(() => {
  Object.defineProperty(window.HTMLMediaElement.prototype, 'currentTime', {
    configurable: true,
    get(this: HTMLMediaElement) {
      return currentTimeStore.get(this) ?? 0
    },
    set(this: HTMLMediaElement, value: number) {
      currentTimeStore.set(this, value)
    },
  })
  Object.defineProperty(window.HTMLMediaElement.prototype, 'play', {
    configurable: true,
    writable: true,
    value: vi.fn(() => Promise.resolve()),
  })
})

beforeEach(() => {
  vi.useFakeTimers()
  vi.setSystemTime(new Date(NOW * 1000))
})

afterEach(() => {
  cleanup()
  vi.useRealTimers()
  vi.clearAllMocks()
})

function getVideo(container: HTMLElement): HTMLVideoElement {
  const video = container.querySelector('video')
  if (!video) throw new Error('No se renderizó el elemento <video>')
  return video
}

async function flushPromises() {
  await act(async () => {})
}

describe('VideoPlayer', () => {
  it('test_video_player_refreshes_url_before_expiry', async () => {
    // Arrange: URL que expira 120 s después del montaje; video en reproducción
    mockGetStreamUrl
      .mockResolvedValueOnce({ url: 'https://cdn.test/video-1.mp4', expires_at: NOW + 120 })
      .mockResolvedValueOnce({ url: 'https://cdn.test/video-2.mp4', expires_at: NOW + 240 })
    const { container } = render(<VideoPlayer lessonId={7} title="Lección 7" />)
    await flushPromises()
    const video = getVideo(container)
    expect(video.src).toBe('https://cdn.test/video-1.mp4')
    video.currentTime = 42
    Object.defineProperty(video, 'paused', { configurable: true, get: () => false })
    Object.defineProperty(video, 'duration', { configurable: true, get: () => 600 })

    // Act: avanzar el reloj hasta expires_at - 60 s
    await act(async () => {
      await vi.advanceTimersByTimeAsync(60_000)
    })

    // Assert: getStreamUrl re-invocado y src actualizado sin reiniciar la reproducción
    expect(mockGetStreamUrl).toHaveBeenCalledTimes(2)
    expect(mockGetStreamUrl).toHaveBeenLastCalledWith(7)
    expect(video.src).toBe('https://cdn.test/video-2.mp4')
    video.currentTime = 0 // el navegador reinicia la posición al cambiar src
    fireEvent(video, new Event('loadedmetadata'))
    expect(video.currentTime).toBe(42)
    expect(video.play).toHaveBeenCalled()
  })

  it('test_video_player_does_not_refresh_for_short_lessons', async () => {
    // Arrange: URL válida 10 min para una lección de 5 min
    mockGetStreamUrl.mockResolvedValue({ url: 'https://cdn.test/corta.mp4', expires_at: NOW + 600 })
    const { container } = render(<VideoPlayer lessonId={8} title="Lección corta" />)
    await flushPromises()
    expect(getVideo(container).src).toBe('https://cdn.test/corta.mp4')

    // Act: reproducir la lección completa (5 min)
    await act(async () => {
      await vi.advanceTimersByTimeAsync(5 * 60_000)
    })

    // Assert: sin refresco durante la lección (el refresco se programaría a los 9 min)
    expect(mockGetStreamUrl).toHaveBeenCalledTimes(1)
  })

  it('test_video_player_retries_once_on_expired_url_error', async () => {
    // Arrange: el primer src falla (p. ej. 403 por URL expirada)
    mockGetStreamUrl
      .mockResolvedValueOnce({ url: 'https://cdn.test/expirada.mp4', expires_at: NOW + 120 })
      .mockResolvedValueOnce({ url: 'https://cdn.test/renovada.mp4', expires_at: NOW + 240 })
    const { container } = render(<VideoPlayer lessonId={9} title="Lección 9" />)
    await flushPromises()
    const video = getVideo(container)
    expect(video.src).toBe('https://cdn.test/expirada.mp4')

    // Act: falla la reproducción
    fireEvent.error(video)
    await flushPromises()

    // Assert: un solo reintento con URL nueva
    expect(mockGetStreamUrl).toHaveBeenCalledTimes(2)
    expect(video.src).toBe('https://cdn.test/renovada.mp4')

    // Act: la URL renovada también falla
    fireEvent.error(video)
    await flushPromises()

    // Assert: sin segundo reintento; se muestra el estado de error
    expect(mockGetStreamUrl).toHaveBeenCalledTimes(2)
    expect(screen.getByText('No se pudo reproducir el video')).toBeInTheDocument()
  })

  it('test_video_player_handles_missing_expires_at', async () => {
    // Arrange: respuesta antigua sin expires_at
    mockGetStreamUrl.mockResolvedValue({ url: 'https://cdn.test/sin-expira.mp4' })
    const { container } = render(<VideoPlayer lessonId={10} title="Lección 10" />)
    await flushPromises()

    // Assert: reproduce y no programa refresco (compatibilidad)
    expect(getVideo(container).src).toBe('https://cdn.test/sin-expira.mp4')
    await act(async () => {
      await vi.advanceTimersByTimeAsync(60 * 60_000)
    })
    expect(mockGetStreamUrl).toHaveBeenCalledTimes(1)
  })

  it('test_video_player_shows_error_when_initial_load_fails', async () => {
    // Arrange: getStreamUrl falla al montar
    mockGetStreamUrl.mockRejectedValue(new Error('Backend no disponible'))

    // Act
    render(<VideoPlayer lessonId={11} title="Lección 11" />)
    await flushPromises()

    // Assert: se muestra el mensaje de error
    expect(screen.getByText('Backend no disponible')).toBeInTheDocument()
  })

  it('test_video_player_keeps_current_url_when_refresh_fails', async () => {
    // Arrange: el refresco programado falla (p. ej. red)
    mockGetStreamUrl
      .mockResolvedValueOnce({ url: 'https://cdn.test/vigente.mp4', expires_at: NOW + 120 })
      .mockRejectedValueOnce(new Error('fallo de red'))
    const { container } = render(<VideoPlayer lessonId={12} title="Lección 12" />)
    await flushPromises()
    const video = getVideo(container)

    // Act: el temporizador de refresco se dispara
    await act(async () => {
      await vi.advanceTimersByTimeAsync(60_000)
    })

    // Assert: mantiene la URL actual y no muestra estado de error
    expect(mockGetStreamUrl).toHaveBeenCalledTimes(2)
    expect(video.src).toBe('https://cdn.test/vigente.mp4')
    expect(screen.queryByText('No se pudo reproducir el video')).not.toBeInTheDocument()
  })
})
