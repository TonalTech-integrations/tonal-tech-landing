const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000"

// ---------- Tipos ----------

export interface User {
  id: number
  email: string
  created_at: string
}

export interface TokenResponse {
  access_token: string
  token_type: string
  user: User
}

export interface LessonSummary {
  id: number
  title: string
  duration_min: number
  is_free: boolean
  position: number
  has_access: boolean
  stream_available: boolean
}

export interface ModuleSummary {
  id: number
  title: string
  position: number
  lessons: LessonSummary[]
}

export interface CourseSummary {
  id: string
  name: string
  tagline: string
  description: string
  price_cents: number
  currency: string
  level: string
  duration_hours: number
  image_path: string
  lessons_count: number
  enrolled: boolean
  completed_lessons: number
  is_free?: boolean
}

export interface CourseDetail extends CourseSummary {
  modules: ModuleSummary[]
}

export interface MyCourseEntry {
  course_id: string
  name: string
  image_path: string
  total_lessons: number
  completed_lessons: number
  progress_pct: number
}

export type LessonStatus = "not_started" | "in_progress" | "completed"

export interface LessonProgressEntry {
  lesson_id: number
  status: LessonStatus
  position_seconds: number
}

// ---------- Token ----------

export function getToken(): string | null {
  if (typeof window === "undefined") return null
  return localStorage.getItem("academy_token")
}

export function setToken(token: string) {
  localStorage.setItem("academy_token", token)
}

export function clearToken() {
  localStorage.removeItem("academy_token")
}

// ---------- Fetch helpers ----------

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const token = getToken()
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  }
  const res = await fetch(`${API_BASE_URL}${path}`, { ...init, headers })
  if (res.status === 401 && token) clearToken()
  if (!res.ok) {
    let detail = `Error ${res.status}`
    try {
      const body = await res.json()
      if (body?.detail) detail = body.detail
    } catch {
      /* respuesta no JSON */
    }
    throw new Error(detail)
  }
  return res.json()
}

// ---------- Auth ----------

export async function registerUser(email: string, password: string): Promise<TokenResponse> {
  return apiFetch("/auth/register", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  })
}

export async function loginUser(email: string, password: string): Promise<TokenResponse> {
  return apiFetch("/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  })
}

export async function getMe(): Promise<User> {
  return apiFetch("/auth/me")
}

export async function getMyCourses(): Promise<MyCourseEntry[]> {
  const data = await apiFetch<{ courses: MyCourseEntry[] }>("/auth/users/me/courses")
  return data.courses
}

// ---------- Courses ----------

export async function getCourses(): Promise<CourseSummary[]> {
  const data = await apiFetch<{ courses: CourseSummary[] }>("/courses")
  return data.courses
}

export async function getCourseDetail(courseId: string): Promise<CourseDetail> {
  return apiFetch(`/courses/${courseId}`)
}

export async function getCourseProgress(courseId: string): Promise<LessonProgressEntry[]> {
  const data = await apiFetch<{ course_id: string; lessons: LessonProgressEntry[] }>(
    `/courses/${courseId}/progress`,
  )
  return data.lessons
}

export async function saveLessonProgress(
  lessonId: number,
  status: LessonStatus,
  positionSeconds: number,
): Promise<void> {
  await apiFetch(`/lessons/${lessonId}/progress`, {
    method: "PUT",
    body: JSON.stringify({ status, position_seconds: Math.round(positionSeconds) }),
  })
}

export interface SessionStatus {
  session_id: string
  status: string
  course_id: string | null
}

export async function getSessionStatus(sessionId: string): Promise<SessionStatus> {
  return apiFetch(`/payments/session-status/${sessionId}`)
}

export interface StreamUrl {
  url: string
  expires_at?: number
}

export async function getStreamUrl(lessonId: number): Promise<StreamUrl> {
  const data = await apiFetch<{ stream_url: string; expires_at?: number }>(
    `/lessons/${lessonId}/stream-url`,
  )
  return { url: data.stream_url, expires_at: data.expires_at }
}

// ---------- Checkout (Stripe hosted, existente) ----------

export async function createCheckoutSession(
  courseId: string,
  customerEmail: string,
): Promise<{ session_id: string; checkout_url: string }> {
  return apiFetch("/payments/checkout-session", {
    method: "POST",
    body: JSON.stringify({ course_id: courseId, customer_email: customerEmail }),
  })
}

// ---------- Utilidades ----------

export function formatPrice(cents: number, currency = "usd"): string {
  return `$${(cents / 100).toFixed(2)} ${currency.toUpperCase()}`
}
