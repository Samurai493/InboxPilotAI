const GOOGLE_ID_TOKEN_KEY = 'inboxpilot_google_id_token'

export function getGoogleIdToken(): string | null {
  if (typeof window === 'undefined') return null
  return localStorage.getItem(GOOGLE_ID_TOKEN_KEY)
}

export function setGoogleIdToken(token: string): void {
  if (typeof window === 'undefined') return
  localStorage.setItem(GOOGLE_ID_TOKEN_KEY, token)
}

export function clearGoogleIdToken(): void {
  if (typeof window === 'undefined') return
  localStorage.removeItem(GOOGLE_ID_TOKEN_KEY)
}
