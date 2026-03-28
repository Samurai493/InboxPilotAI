/**
 * Persists inbox list position (page cursor stack + selection) in sessionStorage so leaving
 * the home route (e.g. workflow history) and returning restores the same view.
 */
const STORAGE_VERSION = 1

export type InboxNavSnapshot = {
  v: typeof STORAGE_VERSION
  pageIndex: number
  pageTokens: Array<string | null>
  nextPageToken: string | null
  selectedMessageId: string | null
}

function key(userId: string): string {
  return `inboxpilot:inboxNav:v${STORAGE_VERSION}:${userId}`
}

export function readInboxNavSession(userId: string): InboxNavSnapshot | null {
  if (typeof window === 'undefined') return null
  try {
    const raw = sessionStorage.getItem(key(userId))
    if (!raw) return null
    const parsed = JSON.parse(raw) as InboxNavSnapshot
    if (parsed.v !== STORAGE_VERSION || !Array.isArray(parsed.pageTokens)) return null
    if (parsed.pageTokens.length === 0) return null
    return parsed
  } catch {
    return null
  }
}

export function saveInboxNavSession(userId: string, snapshot: Omit<InboxNavSnapshot, 'v'>): void {
  if (typeof window === 'undefined') return
  try {
    const full: InboxNavSnapshot = { v: STORAGE_VERSION, ...snapshot }
    sessionStorage.setItem(key(userId), JSON.stringify(full))
  } catch {
    /* quota / private mode */
  }
}

export function clearInboxNavSession(userId: string): void {
  if (typeof window === 'undefined') return
  try {
    sessionStorage.removeItem(key(userId))
  } catch {
    /* ignore */
  }
}
