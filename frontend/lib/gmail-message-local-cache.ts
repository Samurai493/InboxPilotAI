/**
 * Persist full Gmail message payloads in localStorage (per app user UUID) so repeat
 * opens avoid another API round trip. Cleared on sign-out. Cap keeps storage under quota.
 */
import type { GmailMessageResponse } from '@/lib/api'

const STORAGE_VERSION = 1
const MAX_CACHED_MESSAGES = 80

type StoredRow = { t: number; m: GmailMessageResponse }

type StoredBlob = {
  v: number
  entries: Record<string, StoredRow>
}

function storageKey(userId: string): string {
  return `inboxpilot:gmailMsg:v${STORAGE_VERSION}:${userId}`
}

function parseBlob(raw: string): StoredBlob | null {
  try {
    const parsed = JSON.parse(raw) as StoredBlob
    if (parsed.v !== STORAGE_VERSION || !parsed.entries || typeof parsed.entries !== 'object') {
      return null
    }
    return parsed
  } catch {
    return null
  }
}

function trimEntries(entries: Record<string, StoredRow>): void {
  const pairs = Object.entries(entries)
  if (pairs.length <= MAX_CACHED_MESSAGES) return
  pairs.sort((a, b) => a[1].t - b[1].t)
  const drop = pairs.length - MAX_CACHED_MESSAGES
  for (let i = 0; i < drop; i++) {
    delete entries[pairs[i][0]]
  }
}

/** Merge disk cache into the in-memory Map (call when userId is known). */
export function mergeGmailMessagesFromLocalStorage(
  userId: string,
  target: Map<string, GmailMessageResponse>,
): void {
  if (typeof window === 'undefined') return
  try {
    const raw = localStorage.getItem(storageKey(userId))
    if (!raw) return
    const blob = parseBlob(raw)
    if (!blob) return
    for (const [id, row] of Object.entries(blob.entries)) {
      if (row?.m?.id) target.set(id, row.m)
    }
  } catch {
    /* ignore */
  }
}

/** Persist one message; LRU-ish trim by oldest timestamp. */
export function saveGmailMessageToLocalStorage(userId: string, msg: GmailMessageResponse): void {
  if (typeof window === 'undefined' || !msg?.id) return
  try {
    const key = storageKey(userId)
    const raw = localStorage.getItem(key)
    const blob = raw ? parseBlob(raw) : { v: STORAGE_VERSION, entries: {} as Record<string, StoredRow> }
    if (!blob) {
      localStorage.removeItem(key)
      return
    }
    blob.entries[msg.id] = { t: Date.now(), m: msg }
    trimEntries(blob.entries)
    localStorage.setItem(key, JSON.stringify(blob))
  } catch {
    /* quota exceeded or private mode */
  }
}

export function clearGmailMessagesLocalStorage(userId: string): void {
  if (typeof window === 'undefined') return
  try {
    localStorage.removeItem(storageKey(userId))
  } catch {
    /* ignore */
  }
}
