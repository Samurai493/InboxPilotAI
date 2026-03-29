import { getApiBaseUrl } from '@/lib/app-settings'

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

/** Clears guest JWT from localStorage and asks the API to drop the httpOnly guest cookie. */
export async function clearGuestSessionFully(): Promise<void> {
  if (typeof window === 'undefined') return
  localStorage.removeItem(GUEST_TOKEN_KEY)
  await fetch(`${getApiBaseUrl()}/api/v1/auth/guest/clear-cookie`, {
    method: 'POST',
    headers: { Accept: 'application/json' },
    credentials: 'include',
  }).catch(() => {})
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
  if (existing) {
    const probe = await fetch(`${apiBaseUrl}/api/v1/auth/me`, {
      method: 'GET',
      credentials: 'include',
      headers: { Accept: 'application/json' },
    })
    if (probe.ok) {
      const me = (await probe.json()) as { user_id: string }
      if (me.user_id === existing) {
        return existing
      }
    }
  }

  const res = await fetch(`${apiBaseUrl}/api/v1/users/bootstrap`, {
    method: 'POST',
    headers: { Accept: 'application/json' },
    credentials: 'include',
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error(
      typeof err.detail === 'string'
        ? err.detail
        : `Could not create user (${res.status})`,
    )
  }
  const data = (await res.json()) as { id: string; guest_access_token?: string | null }
  setStoredUserId(data.id)
  if (data.guest_access_token) {
    setGuestAccessToken(data.guest_access_token)
  } else {
    clearGuestAccessToken()
  }
  return data.id
}
