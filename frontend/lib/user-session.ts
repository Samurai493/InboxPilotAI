const STORAGE_KEY = 'inboxpilot_user_id'

export function getStoredUserId(): string | null {
  if (typeof window === 'undefined') return null
  return localStorage.getItem(STORAGE_KEY)
}

export function setStoredUserId(id: string): void {
  if (typeof window === 'undefined') return
  localStorage.setItem(STORAGE_KEY, id)
}

export async function ensureUserId(apiBaseUrl: string): Promise<string> {
  const existing = getStoredUserId()
  if (existing) return existing

  const res = await fetch(`${apiBaseUrl}/api/v1/users/bootstrap`, {
    method: 'POST',
    headers: { Accept: 'application/json' },
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error(
      typeof err.detail === 'string'
        ? err.detail
        : `Could not create user (${res.status})`,
    )
  }
  const data = (await res.json()) as { id: string }
  setStoredUserId(data.id)
  return data.id
}
