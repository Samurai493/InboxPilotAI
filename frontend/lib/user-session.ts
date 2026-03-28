const STORAGE_KEY = 'inboxpilot_user_id'
const GUEST_TOKEN_KEY = 'inboxpilot_guest_access_token'

export function getStoredUserId(): string | null {
  if (typeof window === 'undefined') return null
  return localStorage.getItem(STORAGE_KEY)
}

export function setStoredUserId(id: string): void {
  if (typeof window === 'undefined') return
  localStorage.setItem(STORAGE_KEY, id)
}

export function getGuestAccessToken(): string | null {
  if (typeof window === 'undefined') return null
  return localStorage.getItem(GUEST_TOKEN_KEY)
}

export function setGuestAccessToken(token: string): void {
  if (typeof window === 'undefined') return
  localStorage.setItem(GUEST_TOKEN_KEY, token)
}

export function clearGuestAccessToken(): void {
  if (typeof window === 'undefined') return
  localStorage.removeItem(GUEST_TOKEN_KEY)
}

/**
 * Create or recover a browser user. Returns users.id; stores guest_access_token for Bearer auth
 * until the user signs in with Google (then use Google ID token only).
 */
export async function ensureUserId(apiBaseUrl: string): Promise<string> {
  const { getGoogleIdToken } = await import('@/lib/auth-session')
  const existing = getStoredUserId()
  if (existing && (getGoogleIdToken() || getGuestAccessToken())) {
    return existing
  }

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
  const data = (await res.json()) as { id: string; guest_access_token: string }
  setStoredUserId(data.id)
  setGuestAccessToken(data.guest_access_token)
  return data.id
}
