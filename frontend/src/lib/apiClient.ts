/**
 * Centralized API client for CaseClock frontend.
 *
 * Provides a single `apiFetch()` wrapper that:
 * - Attaches Content-Type header by default
 * - Normalizes HTTP errors into typed Error objects
 * - Is ready to attach auth tokens when the backend provides them
 *
 * All hooks MUST use this instead of raw fetch(), so that:
 * - Error messages are consistent
 * - Auth header can be added in one place
 * - Base URL is configurable via environment variable
 *
 * Do NOT invent endpoints here. Only provide transport infrastructure.
 */

export class ApiError extends Error {
  readonly status: number
  readonly statusText: string

  constructor(status: number, statusText: string, message: string) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.statusText = statusText
  }
}

export async function apiFetch<T>(
  path: string,
  options?: RequestInit,
): Promise<T> {
  const baseUrl = import.meta.env.VITE_API_BASE_URL ?? ''
  const url = path.startsWith('http') ? path : `${baseUrl}${path}`
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    // Future: Authorization: `Bearer ${getToken()}`
    ...(options?.headers as Record<string, string> | undefined),
  }

  const response = await fetch(url, {
    ...options,
    headers,
  })

  if (!response.ok) {
    // Normalize all HTTP errors to ApiError with consistent shape
    let message: string
    try {
      const body = await response.json() as { detail?: string; message?: string }
      message = body.detail ?? body.message ?? response.statusText
    } catch {
      message = response.statusText
    }
    throw new ApiError(response.status, response.statusText, message)
  }

  // Handle 204 No Content
  if (response.status === 204) {
    return undefined as T
  }

  return response.json() as Promise<T>
}
