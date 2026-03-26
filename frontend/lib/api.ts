/**
 * API client for InboxPilot AI backend
 */

import { getStoredUserId } from '@/lib/user-session'

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export { API_BASE_URL }

/** Must match a row in users.id (UUID). From localStorage (home bootstrap), env, or explicit arg. */
function resolveUserId(explicit?: string): string {
  const id =
    explicit ?? getStoredUserId() ?? process.env.NEXT_PUBLIC_DEFAULT_USER_ID
  if (!id) {
    throw new Error(
      'Open the home page once to create your session, or set NEXT_PUBLIC_DEFAULT_USER_ID (users.id UUID)',
    )
  }
  return id
}

export interface ProcessMessageResponse {
  thread_id: string
  status: string
  state?: any
  error?: string
}

export interface ThreadStateResponse {
  thread_id: string
  state: any
  status: string
  error?: string
}

/**
 * Process a message through the workflow
 */
export async function processMessage(
  message: string,
  userId?: string,
): Promise<ProcessMessageResponse> {
  const response = await fetch(`${API_BASE_URL}/api/v1/process`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      message,
      user_id: resolveUserId(userId),
    }),
  })

  if (!response.ok) {
    const error = await response.json().catch(() => ({ error: 'Unknown error' }))
    throw new Error(error.error || `HTTP error! status: ${response.status}`)
  }

  return response.json()
}

/**
 * Get thread state
 */
export async function getThreadState(threadId: string): Promise<ThreadStateResponse> {
  const response = await fetch(`${API_BASE_URL}/api/v1/threads/${threadId}`, {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json',
    },
  })

  if (!response.ok) {
    const error = await response.json().catch(() => ({ error: 'Unknown error' }))
    throw new Error(error.error || `HTTP error! status: ${response.status}`)
  }

  return response.json()
}

export interface GmailStatusResponse {
  connected: boolean
  google_account_email?: string | null
}

export interface GmailAuthorizeResponse {
  authorization_url: string
}

export async function getGmailStatus(userId: string): Promise<GmailStatusResponse> {
  const response = await fetch(
    `${API_BASE_URL}/api/v1/gmail/status/${encodeURIComponent(userId)}`,
    { method: 'GET', headers: { Accept: 'application/json' } },
  )
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Unknown error' }))
    throw new Error(
      (typeof error.detail === 'string' ? error.detail : error.detail?.[0]?.msg) ||
        `HTTP error! status: ${response.status}`,
    )
  }
  return response.json()
}

export async function getGmailAuthorizationUrl(
  userId: string,
): Promise<GmailAuthorizeResponse> {
  const url = new URL(`${API_BASE_URL}/api/v1/gmail/oauth/authorize`)
  url.searchParams.set('user_id', userId)
  const response = await fetch(url.toString(), {
    method: 'GET',
    headers: { Accept: 'application/json' },
  })
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Unknown error' }))
    throw new Error(
      (typeof error.detail === 'string' ? error.detail : error.detail?.[0]?.msg) ||
        `HTTP error! status: ${response.status}`,
    )
  }
  return response.json()
}
