export class ApiError extends Error {
  constructor(public status: number, message: string, public code?: string) {
    super(message)
  }
}

/**
 * Same-origin JSON fetch. The custom header is the CSRF defence: browsers
 * cannot attach it cross-origin without a CORS preflight, which the API
 * never grants. Session cookies are SameSite=Strict as a second layer.
 */
export async function api<T>(path: string, init: { method?: string; body?: unknown } = {}): Promise<T> {
  const res = await fetch(`/api${path}`, {
    method: init.method ?? (init.body === undefined ? 'GET' : 'POST'),
    credentials: 'same-origin',
    headers: { 'Content-Type': 'application/json', 'X-FTH-CSRF': '1' },
    body: init.body === undefined ? undefined : JSON.stringify(init.body),
  })
  const text = await res.text()
  const data = text ? JSON.parse(text) : null
  if (!res.ok) {
    const detail = data?.detail
    const msg = typeof detail === 'string' ? detail : detail?.message ?? 'Something went wrong. Please try again.'
    throw new ApiError(res.status, msg, detail?.code)
  }
  return data as T
}
