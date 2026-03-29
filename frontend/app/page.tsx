'use client'

import Link from 'next/link'
import Script from 'next/script'
import { useRouter } from 'next/navigation'
import { useCallback, useEffect, useRef, useState } from 'react'
import {
  authenticateWithGoogleIdToken,
  createGmailDraft,
  getAuthenticatedUser,
  getGmailAuthorizationUrl,
  getGmailStatus,
  getPublicAuthConfig,
  getGmailMessage,
  getLatestThreadForGmailMessage,
  listGmailMessagesPage,
  processMessage,
} from '@/lib/api'
import type { GmailMessageResponse, GmailMessagesPageResponse } from '@/lib/api'
import type { GmailStatusResponse } from '@/lib/api'
import { clearGoogleIdToken, getGoogleIdToken, setGoogleIdToken } from '@/lib/auth-session'
import { clearGuestSessionFully, setStoredUserId } from '@/lib/user-session'
import { getGoogleClientIdForGis } from '@/lib/app-settings'
import {
  clearGmailInboxPagesLocalStorage,
  getCachedInboxPage,
  saveInboxPageToLocalStorage,
} from '@/lib/gmail-inbox-pages-local-cache'
import {
  clearInboxNavSession,
  readInboxNavSession,
  saveInboxNavSession,
} from '@/lib/inbox-nav-session'
import {
  clearGmailMessagesLocalStorage,
  mergeGmailMessagesFromLocalStorage,
  saveGmailMessageToLocalStorage,
} from '@/lib/gmail-message-local-cache'
import { cacheThreadState } from '@/lib/thread-state-cache'

/** Inbox list page size and body-prefetch depth (matches `/gmail/messages/page` default). */
const GMAIL_PAGE_SIZE = 50
/** Cap parallel full-message fetches so the API is not hit with ~50 concurrent heavy requests per page. */
const MAX_CONCURRENT_BODY_PREFETCH = 8

function pickListMessageId(
  messages: GmailMessageResponse[],
  preferId: string | null | undefined,
): string | null {
  if (preferId && messages.some((m) => m.id === preferId)) return preferId
  return messages[0]?.id ?? null
}

/** Run after React commits so the scroll container reflects the new list. */
function queueScrollContainerToTop(el: HTMLElement | null) {
  if (!el) return
  requestAnimationFrame(() => {
    requestAnimationFrame(() => {
      el.scrollTop = 0
    })
  })
}

/** Minimal Google Identity Services shape used by this page (avoids `any` on `window`). */
interface GoogleIdClient {
  initialize: (config: {
    client_id: string
    callback: (response: { credential?: string }) => void
  }) => void
  renderButton: (
    parent: HTMLElement,
    options: { theme?: string; size?: string; width?: number; text?: string },
  ) => void
}

declare global {
  interface Window {
    google?: {
      accounts?: {
        id?: GoogleIdClient
      }
    }
  }
}

export default function Home() {
  const router = useRouter()
  const [userId, setUserId] = useState<string | null>(null)
  const [gmailConnected, setGmailConnected] = useState(false)
  const [gmailEmail, setGmailEmail] = useState<string | null>(null)
  const [sessionError, setSessionError] = useState<string | null>(null)
  const [gmailBusy, setGmailBusy] = useState(false)
  const [signedInEmail, setSignedInEmail] = useState<string | null>(null)

  const [gmailMessages, setGmailMessages] = useState<GmailMessageResponse[]>([])
  const [gmailMessagesBusy, setGmailMessagesBusy] = useState(false)
  const [gmailMessagesError, setGmailMessagesError] = useState<string | null>(null)
  const [gmailPageIndex, setGmailPageIndex] = useState(0)
  const [gmailPageTokens, setGmailPageTokens] = useState<Array<string | null>>([null])
  const [gmailNextPageToken, setGmailNextPageToken] = useState<string | null>(null)
  const [selectedGmailMessageId, setSelectedGmailMessageId] = useState<string | null>(null)
  const [selectedGmailMessage, setSelectedGmailMessage] = useState<GmailMessageResponse | null>(null)
  const [selectedGmailMessageBusy, setSelectedGmailMessageBusy] = useState(false)
  const [selectedGmailMessageError, setSelectedGmailMessageError] = useState<string | null>(null)
  const [gmailConnectedFromQuery, setGmailConnectedFromQuery] = useState(false)

  const [composeOpen, setComposeOpen] = useState(false)
  const [composeTo, setComposeTo] = useState('')
  const [composeSubject, setComposeSubject] = useState('')
  const [composeBody, setComposeBody] = useState('')
  const [composeBusy, setComposeBusy] = useState(false)
  const [composeError, setComposeError] = useState<string | null>(null)

  const [workflowBusy, setWorkflowBusy] = useState(false)
  const [workflowError, setWorkflowError] = useState<string | null>(null)
  const [savedThreadIdForMessage, setSavedThreadIdForMessage] = useState<string | null>(null)

  const bodyDetailCacheRef = useRef<Map<string, GmailMessageResponse>>(new Map())
  const bodyPrefetchInFlightRef = useRef<Set<string>>(new Set())
  const bodyPrefetchQueueRef = useRef<{ uid: string; messageId: string }[]>([])
  const bodyPrefetchQueuedIdsRef = useRef<Set<string>>(new Set())
  const prefetchedNextPageRef = useRef<{
    pageToken: string
    page: GmailMessagesPageResponse
  } | null>(null)
  /** Latest explicit message id the reader should show (drops stale async completions). */
  const pendingDetailMessageIdRef = useRef<string | null>(null)
  const detailLoadGenerationRef = useRef(0)
  const detailAbortRef = useRef<AbortController | null>(null)
  /** Invalidates stale background inbox revalidation after navigation. */
  const inboxLoadGenerationRef = useRef(0)
  /** Avoid writing sessionStorage before the first inbox load (would overwrite restore payload). */
  const inboxSessionHydratedRef = useRef(false)
  const gmailInboxListScrollRef = useRef<HTMLDivElement | null>(null)

  useEffect(() => {
    bodyDetailCacheRef.current.clear()
    if (!userId) return
    mergeGmailMessagesFromLocalStorage(userId, bodyDetailCacheRef.current)
  }, [userId])

  const refreshGmail = useCallback(async (uid: string): Promise<GmailStatusResponse> => {
    const status = await getGmailStatus(uid)
    setGmailConnected(status.connected)
    setGmailEmail(status.google_account_email ?? null)
    return status
  }, [])

  const loadSavedThreadForMessage = useCallback(async (uid: string, messageId: string) => {
    try {
      const latest = await getLatestThreadForGmailMessage(messageId, uid)
      if (pendingDetailMessageIdRef.current !== messageId) return
      setSavedThreadIdForMessage(latest.thread_id)
    } catch (lookupErr) {
      if (pendingDetailMessageIdRef.current !== messageId) return
      if (lookupErr instanceof Error && lookupErr.message !== 'NOT_FOUND') {
        console.warn(lookupErr.message)
      }
    }
  }, [])

  const pumpBodyPrefetchQueue = useCallback(() => {
    while (
      bodyPrefetchInFlightRef.current.size < MAX_CONCURRENT_BODY_PREFETCH &&
      bodyPrefetchQueueRef.current.length > 0
    ) {
      const job = bodyPrefetchQueueRef.current.shift()
      if (!job) break
      const { uid, messageId } = job
      if (bodyDetailCacheRef.current.has(messageId)) {
        bodyPrefetchQueuedIdsRef.current.delete(messageId)
        continue
      }
      if (bodyPrefetchInFlightRef.current.has(messageId)) {
        bodyPrefetchQueuedIdsRef.current.delete(messageId)
        continue
      }
      bodyPrefetchInFlightRef.current.add(messageId)
      bodyPrefetchQueuedIdsRef.current.delete(messageId)
      void getGmailMessage(messageId, uid)
        .then((msg) => {
          bodyDetailCacheRef.current.set(messageId, msg)
          saveGmailMessageToLocalStorage(uid, msg)
        })
        .catch(() => {
          /* single-message failures are non-fatal for prefetch */
        })
        .finally(() => {
          bodyPrefetchInFlightRef.current.delete(messageId)
          pumpBodyPrefetchQueue()
        })
    }
  }, [])

  const ensureBodyPrefetched = useCallback(
    (uid: string, messageId: string) => {
      if (bodyDetailCacheRef.current.has(messageId)) return
      if (bodyPrefetchInFlightRef.current.has(messageId)) return
      if (bodyPrefetchQueuedIdsRef.current.has(messageId)) return
      bodyPrefetchQueuedIdsRef.current.add(messageId)
      bodyPrefetchQueueRef.current.push({ uid, messageId })
      pumpBodyPrefetchQueue()
    },
    [pumpBodyPrefetchQueue],
  )

  /** Full message bodies: first 50 on this list only (not the whole thread). */
  const prefetchBodiesFirstFifty = useCallback(
    (uid: string, messageIds: string[]) => {
      for (const id of messageIds.slice(0, GMAIL_PAGE_SIZE)) {
        ensureBodyPrefetched(uid, id)
      }
    },
    [ensureBodyPrefetched],
  )

  /** Background: load the next Gmail list page + prefetch bodies for its first 50 messages. */
  const prefetchNextGmailListPage = useCallback(
    async (uid: string, pageToken: string | null) => {
      prefetchedNextPageRef.current = null
      if (!pageToken) return
      try {
        const page = await listGmailMessagesPage(uid, GMAIL_PAGE_SIZE, pageToken)
        saveInboxPageToLocalStorage(uid, pageToken, page)
        prefetchedNextPageRef.current = { pageToken, page }
        prefetchBodiesFirstFifty(
          uid,
          page.messages.map((m) => m.id),
        )
      } catch {
        prefetchedNextPageRef.current = null
      }
    },
    [prefetchBodiesFirstFifty],
  )

  const loadGmailMessageDetail = useCallback(
    async (uid: string, messageId: string) => {
      detailAbortRef.current?.abort()
      const ac = new AbortController()
      detailAbortRef.current = ac
      const myGen = ++detailLoadGenerationRef.current
      pendingDetailMessageIdRef.current = messageId

      setSelectedGmailMessageError(null)
      setSavedThreadIdForMessage(null)

      const cached = bodyDetailCacheRef.current.get(messageId)
      if (cached) {
        if (myGen !== detailLoadGenerationRef.current) return
        setSelectedGmailMessage(cached)
        setSelectedGmailMessageBusy(false)
        void loadSavedThreadForMessage(uid, messageId)
        return
      }

      setSelectedGmailMessageBusy(true)
      try {
        const msg = await getGmailMessage(messageId, uid, { signal: ac.signal })
        if (myGen !== detailLoadGenerationRef.current) return
        bodyDetailCacheRef.current.set(messageId, msg)
        saveGmailMessageToLocalStorage(uid, msg)
        setSelectedGmailMessage(msg)
        void loadSavedThreadForMessage(uid, messageId)
      } catch (e) {
        if (e instanceof DOMException && e.name === 'AbortError') return
        if (e instanceof Error && e.name === 'AbortError') return
        if (myGen !== detailLoadGenerationRef.current) return
        setSelectedGmailMessage(null)
        setSelectedGmailMessageError(e instanceof Error ? e.message : 'Failed to load message')
      } finally {
        if (myGen === detailLoadGenerationRef.current) {
          setSelectedGmailMessageBusy(false)
        }
      }
    },
    [loadSavedThreadForMessage],
  )

  const loadGmailMessagesPageAt = useCallback(
    async (
      uid: string,
      pageToken: string | null,
      pageIndex: number,
      tokenHistory: Array<string | null>,
      options?: { preferMessageId?: string | null },
    ) => {
      const myGen = ++inboxLoadGenerationRef.current
      prefetchedNextPageRef.current = null
      setGmailMessagesBusy(true)
      setGmailMessagesError(null)
      setSelectedGmailMessage(null)
      setSelectedGmailMessageId(null)
      setSelectedGmailMessageError(null)
      setSavedThreadIdForMessage(null)

      const applyPage = (page: GmailMessagesPageResponse) => {
        setGmailMessages(page.messages)
        setGmailNextPageToken(page.next_page_token ?? null)
        setGmailPageIndex(pageIndex)
        setGmailPageTokens(tokenHistory)
        prefetchBodiesFirstFifty(uid, page.messages.map((m) => m.id))
        void prefetchNextGmailListPage(uid, page.next_page_token ?? null)
      }

      const cached = getCachedInboxPage(uid, pageToken)
      if (cached) {
        try {
          applyPage(cached)
          const pickId = pickListMessageId(cached.messages, options?.preferMessageId)
          if (pickId) {
            setSelectedGmailMessageId(pickId)
            await loadGmailMessageDetail(uid, pickId)
          }
        } finally {
          if (myGen === inboxLoadGenerationRef.current) {
            setGmailMessagesBusy(false)
          }
        }
        void (async () => {
          try {
            const fresh = await listGmailMessagesPage(uid, GMAIL_PAGE_SIZE, pageToken)
            if (myGen !== inboxLoadGenerationRef.current) return
            saveInboxPageToLocalStorage(uid, pageToken, fresh)
            setGmailMessages(fresh.messages)
            setGmailNextPageToken(fresh.next_page_token ?? null)
            prefetchBodiesFirstFifty(uid, fresh.messages.map((m) => m.id))
            void prefetchNextGmailListPage(uid, fresh.next_page_token ?? null)
          } catch {
            /* keep showing cache */
          }
        })()
        return
      }

      try {
        const page = await listGmailMessagesPage(uid, GMAIL_PAGE_SIZE, pageToken)
        if (myGen !== inboxLoadGenerationRef.current) return
        saveInboxPageToLocalStorage(uid, pageToken, page)
        applyPage(page)
        const pickId = pickListMessageId(page.messages, options?.preferMessageId)
        if (pickId) {
          setSelectedGmailMessageId(pickId)
          await loadGmailMessageDetail(uid, pickId)
        }
      } catch (e) {
        if (myGen !== inboxLoadGenerationRef.current) return
        setGmailMessages([])
        setGmailNextPageToken(null)
        setGmailMessagesError(e instanceof Error ? e.message : 'Failed to load messages')
      } finally {
        if (myGen === inboxLoadGenerationRef.current) {
          setGmailMessagesBusy(false)
        }
      }
    },
    [
      loadGmailMessageDetail,
      prefetchBodiesFirstFifty,
      prefetchNextGmailListPage,
    ],
  )

  useEffect(() => {
    let cancelled = false
    ;(async () => {
      try {
        if (!getGoogleIdToken()) return
        const me = await getAuthenticatedUser()
        if (cancelled) return
        setStoredUserId(me.user_id)
        setUserId(me.user_id)
        setSignedInEmail(me.email)
        await refreshGmail(me.user_id)
      } catch (e) {
        if (!cancelled) {
          setSessionError(e instanceof Error ? e.message : 'Could not restore session')
        }
      }
    })()
    return () => {
      cancelled = true
    }
  }, [refreshGmail])

  useEffect(() => {
    if (!userId) return
    const onFocus = () => {
      refreshGmail(userId).catch(() => {})
    }
    window.addEventListener('focus', onFocus)
    return () => window.removeEventListener('focus', onFocus)
  }, [userId, refreshGmail])

  useEffect(() => {
    if (!gmailConnected) {
      inboxSessionHydratedRef.current = false
    }
  }, [gmailConnected])

  useEffect(() => {
    if (!userId || !gmailConnected) return
    let alive = true
    void (async () => {
      try {
        if (gmailConnectedFromQuery) {
          clearInboxNavSession(userId)
          await loadGmailMessagesPageAt(userId, null, 0, [null])
        } else {
          const saved = readInboxNavSession(userId)
          if (saved?.pageTokens?.length) {
            const pi = Math.min(Math.max(0, saved.pageIndex), saved.pageTokens.length - 1)
            const token = saved.pageTokens[pi] ?? null
            await loadGmailMessagesPageAt(userId, token, pi, saved.pageTokens, {
              preferMessageId: saved.selectedMessageId,
            })
          } else {
            await loadGmailMessagesPageAt(userId, null, 0, [null])
          }
        }
      } catch {
        /* loadGmailMessagesPageAt sets error state */
      } finally {
        if (alive) inboxSessionHydratedRef.current = true
      }
    })()
    return () => {
      alive = false
    }
  }, [userId, gmailConnected, gmailConnectedFromQuery, loadGmailMessagesPageAt])

  useEffect(() => {
    if (!userId || !gmailConnected) return
    if (!inboxSessionHydratedRef.current) return
    saveInboxNavSession(userId, {
      pageIndex: gmailPageIndex,
      pageTokens: gmailPageTokens,
      nextPageToken: gmailNextPageToken,
      selectedMessageId: selectedGmailMessageId,
    })
  }, [
    userId,
    gmailConnected,
    gmailPageIndex,
    gmailPageTokens,
    gmailNextPageToken,
    selectedGmailMessageId,
  ])

  useEffect(() => {
    if (typeof window === 'undefined') return
    setGmailConnectedFromQuery(
      new URLSearchParams(window.location.search).get('gmail_connected') === '1',
    )
  }, [])

  // After a successful Gmail OAuth callback, backend redirects back to /?gmail_connected=1.
  // Sometimes the first status read can come back disconnected; poll briefly to stabilize.
  useEffect(() => {
    if (!gmailConnectedFromQuery || !userId) return

    let cancelled = false
    const maxAttempts = 6

    const poll = async (attempt: number) => {
      if (cancelled) return
      try {
        const status = await refreshGmail(userId)
        if (status.connected) {
          return
        }
      } catch {
        // If status endpoint errors temporarily, retry.
      }

      if (attempt < maxAttempts) {
        setTimeout(() => {
          void poll(attempt + 1)
        }, 1000 * attempt)
      }
    }

    void poll(1)

    return () => {
      cancelled = true
    }
  }, [gmailConnectedFromQuery, refreshGmail, loadGmailMessagesPageAt, userId])

  const handleConnectGmail = async () => {
    if (!userId) return
    setGmailBusy(true)
    setSessionError(null)
    try {
      const { authorization_url } = await getGmailAuthorizationUrl(userId)
      window.location.assign(authorization_url)
    } catch (e) {
      setSessionError(e instanceof Error ? e.message : 'Could not start Gmail login')
      setGmailBusy(false)
    }
  }

  const handleGoogleCredential = async (idToken: string) => {
    try {
      setSessionError(null)
      await clearGuestSessionFully()
      setGoogleIdToken(idToken)
      const user = await authenticateWithGoogleIdToken(idToken)
      setStoredUserId(user.user_id)
      setUserId(user.user_id)
      setSignedInEmail(user.email)
      await refreshGmail(user.user_id)
    } catch (e) {
      clearGoogleIdToken()
      setSessionError(e instanceof Error ? e.message : 'Google sign-in failed')
    }
  }

  const handleGoogleScriptLoad = async () => {
    let clientId = getGoogleClientIdForGis() || undefined
    if (!clientId) {
      try {
        const runtimeConfig = await getPublicAuthConfig()
        clientId = runtimeConfig.google_client_id ?? undefined
      } catch {
        // Keep fallback error below.
      }
    }
    if (!clientId) {
      setSessionError(
        'Google client ID is not configured. Set NEXT_PUBLIC_GOOGLE_CLIENT_ID on frontend or GOOGLE_CLIENT_ID on backend.',
      )
      return
    }
    if (!window.google?.accounts?.id) {
      setSessionError('Google Identity Services failed to load')
      return
    }
    window.google.accounts.id.initialize({
      client_id: clientId,
      callback: (response: { credential?: string }) => {
        if (!response?.credential) {
          setSessionError('Missing Google credential')
          return
        }
        handleGoogleCredential(response.credential)
      },
    })
    const container = document.getElementById('google-signin-button')
    if (container) {
      container.innerHTML = ''
      window.google.accounts.id.renderButton(container, {
        theme: 'outline',
        size: 'large',
        width: 320,
        text: 'signin_with',
      })
    }
  }

  const signOut = () => {
    if (userId) {
      clearGmailMessagesLocalStorage(userId)
      clearGmailInboxPagesLocalStorage(userId)
      clearInboxNavSession(userId)
    }
    inboxSessionHydratedRef.current = false
    clearGoogleIdToken()
    void clearGuestSessionFully()
    detailAbortRef.current?.abort()
    detailAbortRef.current = null
    pendingDetailMessageIdRef.current = null
    bodyDetailCacheRef.current.clear()
    bodyPrefetchInFlightRef.current.clear()
    bodyPrefetchQueueRef.current = []
    bodyPrefetchQueuedIdsRef.current.clear()
    prefetchedNextPageRef.current = null
    setUserId(null)
    setSignedInEmail(null)
    setGmailConnected(false)
    setGmailEmail(null)
    setGmailMessages([])
    setGmailMessagesError(null)
    setGmailPageIndex(0)
    setGmailPageTokens([null])
    setGmailNextPageToken(null)
    setSelectedGmailMessageId(null)
    setSelectedGmailMessage(null)
    setSelectedGmailMessageError(null)
    setComposeOpen(false)
    setWorkflowError(null)
    setWorkflowBusy(false)
    setSavedThreadIdForMessage(null)
  }

  const handleNextGmailPage = async () => {
    if (!userId || !gmailNextPageToken || gmailMessagesBusy) return
    const pref = prefetchedNextPageRef.current
    if (pref && pref.pageToken === gmailNextPageToken) {
      const nextIndex = gmailPageIndex + 1
      const nextHistory = [...gmailPageTokens.slice(0, nextIndex), gmailNextPageToken]
      prefetchedNextPageRef.current = null
      setGmailMessages(pref.page.messages)
      setGmailNextPageToken(pref.page.next_page_token ?? null)
      setGmailPageIndex(nextIndex)
      setGmailPageTokens(nextHistory)
      setGmailMessagesError(null)
      setSelectedGmailMessageError(null)
      setSavedThreadIdForMessage(null)
      prefetchBodiesFirstFifty(userId, pref.page.messages.map((m) => m.id))
      void prefetchNextGmailListPage(userId, pref.page.next_page_token ?? null)
      const first = pref.page.messages[0]
      if (first) {
        setSelectedGmailMessageId(first.id)
        await loadGmailMessageDetail(userId, first.id)
      } else {
        setSelectedGmailMessageId(null)
        setSelectedGmailMessage(null)
      }
      queueScrollContainerToTop(gmailInboxListScrollRef.current)
      return
    }
    const nextIndex = gmailPageIndex + 1
    const nextHistory = [...gmailPageTokens.slice(0, nextIndex), gmailNextPageToken]
    await loadGmailMessagesPageAt(userId, gmailNextPageToken, nextIndex, nextHistory)
    queueScrollContainerToTop(gmailInboxListScrollRef.current)
  }

  const handlePrevGmailPage = async () => {
    if (!userId || gmailPageIndex === 0 || gmailMessagesBusy) return
    const prevIndex = gmailPageIndex - 1
    const prevToken = gmailPageTokens[prevIndex] ?? null
    const prevHistory = gmailPageTokens.slice(0, prevIndex + 1)
    await loadGmailMessagesPageAt(userId, prevToken, prevIndex, prevHistory)
    queueScrollContainerToTop(gmailInboxListScrollRef.current)
  }

  const handleRunWorkflow = useCallback(async () => {
    if (!userId || !selectedGmailMessage) return
    setWorkflowBusy(true)
    setWorkflowError(null)
    try {
      const raw = [
        `Subject: ${selectedGmailMessage.subject || '(no subject)'}`,
        `From: ${selectedGmailMessage.from_email}`,
        `Date: ${selectedGmailMessage.date}`,
        '',
        selectedGmailMessage.body || '',
      ].join('\n')
      const result = await processMessage(raw, userId, {
        gmail_message_id: selectedGmailMessage.id,
      })
      if (result.status === 'failed' && result.error) {
        throw new Error(result.error)
      }
      if (result.state && typeof result.state === 'object') {
        cacheThreadState(result.thread_id, result.state as object)
      }
      setSavedThreadIdForMessage(result.thread_id)
      router.push(`/results/${result.thread_id}`)
    } catch (e) {
      setWorkflowError(e instanceof Error ? e.message : 'Workflow failed')
    } finally {
      setWorkflowBusy(false)
    }
  }, [userId, selectedGmailMessage, router])

  const handleComposeSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!userId) return
    setComposeBusy(true)
    setComposeError(null)
    try {
      await createGmailDraft(
        { to: composeTo.trim(), subject: composeSubject.trim(), body: composeBody },
        userId,
      )
      setComposeOpen(false)
      setComposeTo('')
      setComposeSubject('')
      setComposeBody('')
    } catch (err) {
      setComposeError(err instanceof Error ? err.message : 'Could not save draft')
    } finally {
      setComposeBusy(false)
    }
  }

  return (
    <main
      className={
        userId && gmailConnected
          ? 'flex h-screen min-h-0 flex-col bg-gray-100'
          : 'min-h-screen bg-gradient-to-b from-blue-50 to-white'
      }
    >
      <Script
        src="https://accounts.google.com/gsi/client"
        strategy="afterInteractive"
        onLoad={() => {
          void handleGoogleScriptLoad()
        }}
      />
      {userId && gmailConnected ? (
        <>
          <header className="flex shrink-0 items-center justify-between gap-4 border-b border-gray-200 bg-white px-4 py-3 shadow-sm">
            <div className="min-w-0">
              <div className="text-lg font-semibold text-gray-900">InboxPilot</div>
              <div className="truncate text-xs text-gray-500">
                {gmailEmail || signedInEmail || 'Gmail connected'}
              </div>
            </div>
            <div className="flex shrink-0 flex-wrap items-center justify-end gap-2">
              <Link
                href="/history"
                className="rounded-lg border border-gray-300 px-3 py-2 text-sm font-semibold text-gray-700 hover:bg-gray-50"
              >
                Workflow history
              </Link>
              <Link
                href="/settings"
                className="rounded-lg border border-gray-300 px-3 py-2 text-sm font-semibold text-gray-700 hover:bg-gray-50"
              >
                Settings
              </Link>
              <button
                type="button"
                onClick={() => {
                  if (!userId) return
                  clearInboxNavSession(userId)
                  void loadGmailMessagesPageAt(userId, null, 0, [null])
                }}
                disabled={gmailMessagesBusy}
                className="rounded-lg border border-gray-300 px-3 py-2 text-sm font-semibold text-gray-700 hover:bg-gray-50 disabled:cursor-not-allowed disabled:bg-gray-100"
              >
                {gmailMessagesBusy ? 'Loading…' : 'Refresh'}
              </button>
              <button
                type="button"
                onClick={() => {
                  setComposeError(null)
                  setComposeOpen(true)
                }}
                className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-700"
              >
                Compose
              </button>
              <button
                type="button"
                onClick={signOut}
                className="rounded-lg border border-gray-300 px-3 py-2 text-sm font-semibold text-gray-700 hover:bg-gray-50"
              >
                Sign out
              </button>
            </div>
          </header>

          <div className="flex min-h-0 min-w-0 flex-1">
            <aside className="flex w-full max-w-[22rem] shrink-0 flex-col border-r border-gray-200 bg-white min-h-0">
              <div className="flex items-center justify-between gap-2 border-b border-gray-200 px-3 py-2">
                <div className="text-xs font-semibold text-gray-700">
                  {`Inbox (${gmailPageIndex * GMAIL_PAGE_SIZE + 1}–${gmailPageIndex * GMAIL_PAGE_SIZE + gmailMessages.length})`}
                </div>
                <div className="flex items-center gap-1">
                  <button
                    type="button"
                    onClick={() => void handlePrevGmailPage()}
                    disabled={gmailMessagesBusy || gmailPageIndex === 0}
                    className="rounded border border-gray-300 px-2 py-0.5 text-xs text-gray-700 hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-50"
                    aria-label="Previous page of emails"
                    title="Previous page"
                  >
                    ←
                  </button>
                  <button
                    type="button"
                    onClick={() => void handleNextGmailPage()}
                    disabled={gmailMessagesBusy || !gmailNextPageToken}
                    className="rounded border border-gray-300 px-2 py-0.5 text-xs text-gray-700 hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-50"
                    aria-label="Next page of emails"
                    title="Next page"
                  >
                    →
                  </button>
                </div>
              </div>
              <div ref={gmailInboxListScrollRef} className="min-h-0 flex-1 overflow-y-auto p-2">
                {gmailMessagesError && (
                  <p className="mb-2 text-sm text-red-600">{gmailMessagesError}</p>
                )}
                {gmailMessages.length === 0 && !gmailMessagesBusy ? (
                  <p className="text-sm text-gray-600">No messages found.</p>
                ) : null}
                {gmailMessages.map((m) => {
                  const isSelected = m.id === selectedGmailMessageId
                  return (
                    <button
                      key={m.id}
                      type="button"
                      onClick={() => {
                        if (!userId) return
                        setSelectedGmailMessageId(m.id)
                        void loadGmailMessageDetail(userId, m.id)
                      }}
                      className={[
                        'mb-1 w-full rounded-lg border p-2 text-left transition-colors',
                        isSelected
                          ? 'border-blue-500 bg-blue-50'
                          : 'border-transparent hover:bg-gray-50',
                      ].join(' ')}
                    >
                      <div className="text-xs text-gray-500">{m.date}</div>
                      <div className="mt-1 text-sm font-semibold text-gray-900">
                        {m.subject || '(no subject)'}
                      </div>
                      <div className="text-xs text-gray-600">{m.from_email}</div>
                      <div className="mt-1 truncate text-xs text-gray-600">{m.snippet || '-'}</div>
                    </button>
                  )
                })}
                {gmailMessagesBusy ? (
                  <p className="mt-2 text-sm text-gray-600">Loading messages…</p>
                ) : null}
              </div>
            </aside>

            <section className="flex min-h-0 min-w-0 flex-1 flex-col bg-white">
              {selectedGmailMessageBusy ? (
                <p className="shrink-0 border-b border-gray-100 px-6 py-4 text-sm text-gray-600">
                  Loading message…
                </p>
              ) : null}
              {selectedGmailMessageError ? (
                <p className="shrink-0 border-b border-red-100 bg-red-50 px-6 py-4 text-sm text-red-600">
                  {selectedGmailMessageError}
                </p>
              ) : null}
              {workflowError ? (
                <p className="shrink-0 border-b border-red-100 bg-red-50 px-6 py-3 text-sm text-red-600">
                  {workflowError}
                </p>
              ) : null}
              <div className="flex shrink-0 flex-wrap items-center justify-between gap-3 border-b border-gray-100 bg-white px-6 py-3">
                <span className="text-xs font-semibold uppercase tracking-wide text-gray-500">
                  Reader
                </span>
                <div className="flex flex-wrap items-center justify-end gap-2">
                  {savedThreadIdForMessage ? (
                    <Link
                      href={`/results/${encodeURIComponent(savedThreadIdForMessage)}`}
                      className="rounded-lg border border-gray-300 px-4 py-2 text-sm font-semibold text-gray-800 hover:bg-gray-50"
                    >
                      View saved results
                    </Link>
                  ) : null}
                  <button
                    type="button"
                    disabled={!selectedGmailMessage || workflowBusy || selectedGmailMessageBusy}
                    onClick={() => void handleRunWorkflow()}
                    className="rounded-lg bg-primary-600 px-4 py-2 text-sm font-semibold text-white hover:bg-primary-700 disabled:cursor-not-allowed disabled:bg-gray-300"
                  >
                    {workflowBusy ? 'Running workflow…' : 'Run InboxPilot workflow'}
                  </button>
                </div>
              </div>
              <div className="min-h-0 flex-1 overflow-y-auto px-6 py-8 lg:px-12 lg:py-10">
                {selectedGmailMessage && !selectedGmailMessageBusy ? (
                  <>
                    <div className="text-sm text-gray-700">
                      <span className="font-semibold">From:</span> {selectedGmailMessage.from_email}
                    </div>
                    <div className="mt-1 text-xs text-gray-500">{selectedGmailMessage.date}</div>
                    <h2 className="mt-4 text-2xl font-semibold text-gray-900">
                      {selectedGmailMessage.subject || '(no subject)'}
                    </h2>
                    <div className="mt-6 whitespace-pre-wrap break-words text-base leading-relaxed text-gray-800">
                      {selectedGmailMessage.body || (
                        <span className="text-gray-500">No body content.</span>
                      )}
                    </div>
                  </>
                ) : !selectedGmailMessageBusy ? (
                  <p className="text-sm text-gray-600">Select a message to read.</p>
                ) : null}
              </div>
            </section>
          </div>

          {composeOpen ? (
            <div
              className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4"
              role="dialog"
              aria-modal="true"
              aria-labelledby="compose-title"
            >
              <div className="flex max-h-[90vh] w-full max-w-lg flex-col overflow-hidden rounded-xl bg-white shadow-xl">
                <div className="flex items-center justify-between border-b border-gray-200 px-4 py-3">
                  <h2 id="compose-title" className="text-lg font-semibold text-gray-900">
                    New draft
                  </h2>
                  <button
                    type="button"
                    disabled={composeBusy}
                    onClick={() => setComposeOpen(false)}
                    className="rounded-lg p-2 text-2xl leading-none text-gray-500 hover:bg-gray-100 disabled:opacity-50"
                    aria-label="Close"
                  >
                    ×
                  </button>
                </div>
                <form onSubmit={handleComposeSubmit} className="flex min-h-0 flex-1 flex-col overflow-y-auto p-4">
                  {composeError ? (
                    <p className="mb-3 text-sm text-red-600">{composeError}</p>
                  ) : null}
                  <label htmlFor="compose-to" className="text-sm font-medium text-gray-700">
                    To
                  </label>
                  <input
                    id="compose-to"
                    type="email"
                    value={composeTo}
                    onChange={(e) => setComposeTo(e.target.value)}
                    className="mt-1 w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 placeholder:text-gray-400"
                    placeholder="name@example.com"
                    required
                    disabled={composeBusy}
                  />
                  <label htmlFor="compose-subject" className="mt-4 text-sm font-medium text-gray-700">
                    Subject
                  </label>
                  <input
                    id="compose-subject"
                    type="text"
                    value={composeSubject}
                    onChange={(e) => setComposeSubject(e.target.value)}
                    className="mt-1 w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 placeholder:text-gray-400"
                    disabled={composeBusy}
                  />
                  <label htmlFor="compose-body" className="mt-4 text-sm font-medium text-gray-700">
                    Message
                  </label>
                  <textarea
                    id="compose-body"
                    value={composeBody}
                    onChange={(e) => setComposeBody(e.target.value)}
                    rows={8}
                    className="mt-1 min-h-[120px] w-full flex-1 rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 placeholder:text-gray-400"
                    disabled={composeBusy}
                  />
                  <div className="mt-4 flex justify-end gap-2 border-t border-gray-100 pt-4">
                    <button
                      type="button"
                      disabled={composeBusy}
                      onClick={() => setComposeOpen(false)}
                      className="rounded-lg border border-gray-300 px-4 py-2 text-sm font-semibold text-gray-700 hover:bg-gray-50 disabled:opacity-50"
                    >
                      Cancel
                    </button>
                    <button
                      type="submit"
                      disabled={composeBusy}
                      className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-70"
                    >
                      {composeBusy ? 'Saving…' : 'Save draft'}
                    </button>
                  </div>
                </form>
              </div>
            </div>
          ) : null}
        </>
      ) : (
      <div className="container relative mx-auto px-4 py-16">
        <div className="absolute right-4 top-4 z-10 sm:right-8 sm:top-6">
          <Link
            href="/settings"
            className="inline-flex items-center rounded-lg border border-gray-200 bg-white/90 px-3 py-2 text-sm font-semibold text-gray-700 shadow-sm hover:bg-gray-50"
          >
            Settings
          </Link>
        </div>
        <div className="max-w-4xl mx-auto text-center">
          <h1 className="text-5xl font-bold text-gray-900 mb-6">
            InboxPilot AI
          </h1>
          {signedInEmail && (
            <p className="mb-8 text-sm text-gray-600">
              Signed in as{' '}
              <span className="font-medium text-gray-900">{signedInEmail}</span>
            </p>
          )}
          <p className="text-xl text-gray-600 mb-8">
            Transform your messy inbox into structured, reviewable workflows
          </p>
          <p className="text-lg text-gray-500 mb-12">
            Powered by LangGraph • Classify • Draft • Extract • Review
          </p>

          <div className="max-w-xl mx-auto mb-10 rounded-lg border border-gray-200 bg-white p-6 text-left shadow-sm">
            <h2 className="text-lg font-semibold text-gray-900 mb-2">
              Account + Gmail
            </h2>
            {sessionError && (
              <p className="mb-3 text-sm text-red-600">{sessionError}</p>
            )}
            {!userId && <div id="google-signin-button" className="mb-3" />}
            {signedInEmail && (
              <p className="mb-3 text-sm text-gray-700">
                Signed in as <span className="font-medium">{signedInEmail}</span>
              </p>
            )}
            {userId && !gmailConnected && (
              <>
                <p className="mb-4 text-sm text-gray-600">
                  Link your Gmail account so InboxPilot can read and draft mail on
                  your behalf (scopes configured in Google Cloud).
                </p>
                <button
                  type="button"
                  onClick={handleConnectGmail}
                  disabled={gmailBusy}
                  className="w-full rounded-lg bg-red-600 px-4 py-3 text-sm font-semibold text-white hover:bg-red-700 disabled:cursor-not-allowed disabled:bg-gray-400"
                >
                  {gmailBusy ? 'Opening Google…' : 'Connect Gmail'}
                </button>
                <button
                  type="button"
                  onClick={signOut}
                  className="mt-3 w-full rounded-lg border border-gray-300 px-4 py-3 text-sm font-semibold text-gray-700 hover:bg-gray-50"
                >
                  Sign out
                </button>
              </>
            )}
          </div>

          <div className="flex gap-4 justify-center">
            <Link
              href="/inbox"
              className="bg-primary-600 text-white px-8 py-3 rounded-lg font-semibold hover:bg-primary-700 transition-colors"
            >
              Get Started
            </Link>
            <Link
              href="/inbox"
              className="border-2 border-primary-600 text-primary-600 px-8 py-3 rounded-lg font-semibold hover:bg-primary-50 transition-colors"
            >
              Try Demo
            </Link>
          </div>

          <div className="mt-16 grid grid-cols-1 md:grid-cols-3 gap-8">
            <div className="bg-white p-6 rounded-lg shadow-md">
              <h3 className="text-xl font-semibold mb-3">Classify</h3>
              <p className="text-gray-600">
                Automatically classify incoming messages by intent and urgency
              </p>
            </div>
            <div className="bg-white p-6 rounded-lg shadow-md">
              <h3 className="text-xl font-semibold mb-3">Draft</h3>
              <p className="text-gray-600">
                Generate context-aware reply drafts tailored to each message type
              </p>
            </div>
            <div className="bg-white p-6 rounded-lg shadow-md">
              <h3 className="text-xl font-semibold mb-3">Extract</h3>
              <p className="text-gray-600">
                Identify action items, deadlines, and tasks automatically
              </p>
            </div>
          </div>
        </div>
      </div>
      )}
    </main>
  )
}
