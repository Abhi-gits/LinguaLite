const API_BASE = import.meta.env.VITE_API_BASE_URL ?? ''

export class ApiError extends Error {
  constructor(message, { status, code } = {}) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.code = code
  }
}

export async function runAssistant(payload, { signal } = {}) {
  let response
  try {
    response = await fetch(`${API_BASE}/api/assist`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
      signal,
    })
  } catch (error) {
    if (error?.name === 'AbortError') {
      throw error
    }
    throw new ApiError(
      'The configured AI provider is unavailable. Confirm the LinguaLite API and provider are running.',
      { status: 0, code: 'provider_unavailable' },
    )
  }

  let body
  try {
    body = await response.json()
  } catch {
    body = {}
  }

  if (!response.ok) {
    throw new ApiError(
      body.message || 'Translation could not be completed. Please try again.',
      { status: response.status, code: body.error || 'request_failed' },
    )
  }

  if (body.task !== payload.task) {
    throw new ApiError(
      'The AI provider returned an unusable response. No result was invented.',
      { status: 502, code: 'malformed_response' },
    )
  }

  return body
}
