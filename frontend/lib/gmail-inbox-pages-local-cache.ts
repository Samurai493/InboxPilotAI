/**
 * Persist Gmail inbox list pages (per cursor) in localStorage for instant back/forward
 * navigation. Same caveats as message cache: per app user UUID, cleared on sign-out.
 */
import type { GmailMessagesPageResponse } from '@/lib/api'

const STORAGE_VERSION = 1
const MAX_CACHED_PAGES = 30
/** After this age, cache is ignored on first paint (network fetch instead). */
export const INBOX_PAGE_CACHE_TTL_MS = 10 * 60 * 1000

type PageRow = { t: number; p: GmailMessagesPageResponse }

type PageBlob = {
  v: number
  pages: Record<string, PageRow>
}

function pagesStorageKey(userId: string): string {
  return `inboxpilot:gmailInboxPages:v${STORAGE_VERSION}:${userId}`
}

function cursorStorageKey(pageToken: string | null): string {
  if (pageToken === null || pageToken === '') return '__root__'
  return pageToken
}

function parsePageBlob(raw: string): PageBlob | null {
  try {
    const parsed = JSON.parse(raw) as PageBlob
    if (parsed.v !== STORAGE_VERSION || !parsed.pages || typeof parsed.pages !== 'object') {
      return null
    }
    return parsed
  } catch {
    return null
  }
}

function trimPages(pages: Record<string, PageRow>): void {
  const pairs = Object.entries(pages)
  if (pairs.length <= MAX_CACHED_PAGES) return
  pairs.sort((a, b) => a[1].t - b[1].t)
  const drop = pairs.length - MAX_CACHED_PAGES
  for (let i = 0; i < drop; i++) {
    delete pages[pairs[i][0]]
  }
}

/** Return cached page if present and younger than TTL. */
export function getCachedInboxPage(
  userId: string,
  pageToken: string | null,
  maxAgeMs: number = INBOX_PAGE_CACHE_TTL_MS,
): GmailMessagesPageResponse | null {
  if (typeof window === 'undefined') return null
  try {
    const raw = localStorage.getItem(pagesStorageKey(userId))
    if (!raw) return null
    const blob = parsePageBlob(raw)
    if (!blob) return null
    const row = blob.pages[cursorStorageKey(pageToken)]
    if (!row?.p?.messages) return null
    if (Date.now() - row.t > maxAgeMs) return null
    return row.p
  } catch {
    return null
  }
}

export function saveInboxPageToLocalStorage(
  userId: string,
  pageToken: string | null,
  page: GmailMessagesPageResponse,
): void {
  if (typeof window === 'undefined') return
  try {
    const key = pagesStorageKey(userId)
    const raw = localStorage.getItem(key)
    const blob = raw
      ? parsePageBlob(raw)
      : { v: STORAGE_VERSION, pages: {} as Record<string, PageRow> }
    if (!blob) {
      localStorage.removeItem(key)
      return
    }
    const ck = cursorStorageKey(pageToken)
    blob.pages[ck] = { t: Date.now(), p: page }
    trimPages(blob.pages)
    localStorage.setItem(key, JSON.stringify(blob))
  } catch {
    /* quota */
  }
}

export function clearGmailInboxPagesLocalStorage(userId: string): void {
  if (typeof window === 'undefined') return
  try {
    localStorage.removeItem(pagesStorageKey(userId))
  } catch {
    /* ignore */
  }
}
