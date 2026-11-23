'use client'

import { useEffect, useRef, useState } from 'react'
import { AlertCircle, Loader2 } from 'lucide-react'

import { getStreamUrl, saveLessonProgress } from '@/lib/api'

const PROGRESS_INTERVAL_MS = 10_000
const REFRESH_MARGIN_MS = 60_000

export function VideoPlayer({
  lessonId,
  title,
  startAt = 0,
  onCompleted,
}: {
  lessonId: number
  title: string
  startAt?: number
  onCompleted?: () => void
}) {
  const videoRef = useRef<HTMLVideoElement>(null)
  const [src, setSrc] = useState<string | null>(null)
  const [error, setError] = useState('')
  const [expiresAt, setExpiresAt] = useState<number | null>(null)
  const resumedRef = useRef(false)
  const retriedRef = useRef(false)
  const startAtRef = useRef(startAt)
  const wasPlayingRef = useRef(false)

  useEffect(() => {
    let cancelled = false
    resumedRef.current = false
    retriedRef.current = false
    wasPlayingRef.current = false
    getStreamUrl(lessonId)
      .then(({ url, expires_at }) => {
        if (cancelled) return
        setSrc(url)
        setExpiresAt(expires_at ?? null)
      })
      .catch((err) => {
        if (!cancelled) setError(err instanceof Error ? err.message : 'No se pudo cargar el video')
      })
    return () => {
      cancelled = true
    }
  }, [lessonId])

  useEffect(() => {
    if (!src || expiresAt === null) return
    let cancelled = false
    const delay = Math.max(expiresAt * 1000 - Date.now() - REFRESH_MARGIN_MS, 0)
    const timer = window.setTimeout(() => {
      getStreamUrl(lessonId)
        .then(({ url, expires_at }) => {
          if (cancelled) return
          const video = videoRef.current
          if (video) {
            resumedRef.current = false
            startAtRef.current = video.currentTime
            wasPlayingRef.current = !video.paused
          }
          setSrc(url)
          setExpiresAt(expires_at ?? null)
        })
        .catch(() => {})
    }, delay)
    return () => {
      cancelled = true
      window.clearTimeout(timer)
    }
  }, [src, expiresAt, lessonId])

  useEffect(() => {
    if (!src) return
    const video = videoRef.current
    if (!video) return

    const report = (status: 'in_progress' | 'completed') => {
      saveLessonProgress(lessonId, status, video.currentTime).catch(() => {})
    }

    const onLoadedMetadata = () => {
      const resumeAt = startAtRef.current
      if (!resumedRef.current && resumeAt > 0 && resumeAt < video.duration - 5) {
        video.currentTime = resumeAt
      }
      resumedRef.current = true
      if (wasPlayingRef.current) {
        wasPlayingRef.current = false
        video.play().catch(() => {})
      }
    }
    const onError = () => {
      if (retriedRef.current) {
        setError('No se pudo reproducir el video')
        return
      }
      retriedRef.current = true
      startAtRef.current = video.currentTime
      wasPlayingRef.current = !video.paused
      resumedRef.current = false
      getStreamUrl(lessonId)
        .then(({ url, expires_at }) => {
          setSrc(url)
          setExpiresAt(expires_at ?? null)
        })
        .catch(() => setError('No se pudo reproducir el video'))
    }
    const onEnded = () => {
      report('completed')
      onCompleted?.()
    }
    const interval = window.setInterval(() => {
      if (!video.paused && !video.ended) report('in_progress')
    }, PROGRESS_INTERVAL_MS)

    video.addEventListener('loadedmetadata', onLoadedMetadata)
    video.addEventListener('pause', () => report('in_progress'))
    video.addEventListener('ended', onEnded)
    video.addEventListener('error', onError)

    return () => {
      window.clearInterval(interval)
      video.removeEventListener('loadedmetadata', onLoadedMetadata)
      video.removeEventListener('ended', onEnded)
      video.removeEventListener('error', onError)
    }
  }, [src, lessonId, onCompleted])

  if (error) {
    return (
      <div className="flex aspect-video items-center justify-center rounded-xl border border-border bg-card">
        <div className="flex items-center gap-2 px-4 text-center">
          <AlertCircle className="size-4 shrink-0 text-muted-foreground" />
          <p className="text-sm text-muted-foreground">{error}</p>
        </div>
      </div>
    )
  }

  if (!src) {
    return (
      <div className="flex aspect-video items-center justify-center rounded-xl border border-border bg-card">
        <Loader2 className="size-5 animate-spin text-muted-foreground" />
      </div>
    )
  }

  return (
    <video
      ref={videoRef}
      src={src}
      title={title}
      controls
      className="aspect-video w-full rounded-xl border border-border bg-black"
    />
  )
}
