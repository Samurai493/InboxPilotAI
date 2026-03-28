/**
 * API client for InboxPilot AI backend
 */

import { getGuestAccessToken, getStoredUserId } from '@/lib/user-session'
import { getGoogleIdToken } from '@/lib/auth-session'
import {
  getApiBaseUrl,
  getDefaultUserIdFromSettings,
  hasStoredAppSettings,
  loadAppSettings,
} from '@/lib/app-settings'

export { getApiBaseUrl } from '@/lib/app-settings'

function authHeaders(extra?: Record<string, string>): Record<string, string> {
  const token = getGoogleIdToken() || getGuestAccessToken()
  return {
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...(extra ?? {}),
  }
}

/** For pages that do not import the full API helper set. */
export function getAuthHeaders(extra?: Record<string, string>): Record<string, string> {
  return authHeaders(extra)
}

/** Must match a row in users.id (UUID). From localStorage (home bootstrap), env, or explicit arg. */
function resolveUserId(explicit?: string): string | undefined {
  const id = explicit ?? getStoredUserId() ?? getDefaultUserIdFromSettings()
  return id
}

export interface ProcessMessageResponse {
  thread_id: string
  status: string
  state?: any
  error?: string
}

export interface AuthUserResponse {
  user_id: string
  email: string
  name?: string | null
}

export interface PublicAuthConfigResponse {
  google_client_id?: string | null
}

export interface ThreadStateResponse {
  thread_id: string
  state: any
  status: string
  error?: string
  /** Present when state was loaded from DB snapshot (checkpointer empty). */
  source?: string | null
}

export interface WorkflowThreadSummary {
  id: string
  thread_id: string
  status: string
  gmail_message_id?: string | null
  created_at?: string | null
  intent?: string | null
  subject?: string | null
  selected_agent?: string | null
}

export interface WorkflowThreadListResponse {
  threads: WorkflowThreadSummary[]
}

export interface LatestThreadForMessageResponse {
  thread_id: string
  status: string
  created_at?: string | null
}

export interface ProcessMessageOptions {
  /** When false, backend uses general draft/extract only (no domain specialists). Default true. */
  use_specialist?: boolean
  /** Gmail message id for linking persisted runs to an inbox email. */
  gmail_message_id?: string | null
  /** Override saved Settings for this request only (e.g. tests). */
  llm_provider?: string
  llm_model?: string
  openai_api_key?: string
  anthropic_api_key?: string
  gemini_api_key?: string
}

/**
 * Process a message through the workflow
 */
export async function processMessage(
  message: string,
  userId?: string,
  options?: ProcessMessageOptions,
): Promise<ProcessMessageResponse> {
  const resolvedUserId = resolveUserId(userId)

  const body: Record<string, unknown> = {
    message,
    ...(resolvedUserId ? { user_id: resolvedUserId } : {}),
    ...(options?.use_specialist === false ? { use_specialist: false } : {}),
    ...(options?.gmail_message_id ? { gmail_message_id: options.gmail_message_id } : {}),
  }

  if (options?.llm_provider !== undefined) {
    body.llm_provider = options.llm_provider
    if (options.llm_model !== undefined) body.llm_model = options.llm_model
    if (options.openai_api_key?.trim()) body.openai_api_key = options.openai_api_key.trim()
    if (options.anthropic_api_key?.trim()) body.anthropic_api_key = options.anthropic_api_key.trim()
    if (options.gemini_api_key?.trim()) body.gemini_api_key = options.gemini_api_key.trim()
  } else if (hasStoredAppSettings()) {
    const s = loadAppSettings()
    body.llm_provider = s.llmProvider?.trim() || 'openai'
    if (s.llmModel?.trim()) body.llm_model = s.llmModel.trim()
    if (s.openaiApiKey?.trim()) body.openai_api_key = s.openaiApiKey.trim()
    if (s.anthropicApiKey?.trim()) body.anthropic_api_key = s.anthropicApiKey.trim()
    if (s.geminiApiKey?.trim()) body.gemini_api_key = s.geminiApiKey.trim()
  }

  const response = await fetch(`${getApiBaseUrl()}/api/v1/process`, {
    method: 'POST',
    headers: {
      ...authHeaders(),
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(body),
  })

  if (!response.ok) {
    const error = await response.json().catch(() => ({}))
    const detail = (error as { detail?: unknown; error?: string }).detail
    const msg =
      typeof detail === 'string'
        ? detail
        : Array.isArray(detail) && detail[0]?.msg
          ? detail[0].msg
          : (error as { error?: string }).error
    throw new Error(msg || `HTTP error! status: ${response.status}`)
  }

  return response.json()
}

/**
 * Get thread state (checkpointer or database snapshot).
 */
export async function getThreadState(
  threadId: string,
  userId?: string,
): Promise<ThreadStateResponse> {
  const url = new URL(
    `${getApiBaseUrl()}/api/v1/threads/${encodeURIComponent(threadId)}`,
  )
  const uid = resolveUserId(userId)
  if (uid) url.searchParams.set('user_id', uid)

  const response = await fetch(url.toString(), {
    method: 'GET',
    headers: authHeaders({
      'Content-Type': 'application/json',
    }),
  })

  if (!response.ok) {
    const error = await response.json().catch(() => ({ error: 'Unknown error' }))
    const detail = (error as { detail?: unknown }).detail
    const msg =
      typeof detail === 'string'
        ? detail
        : (error as { error?: string }).error
    throw new Error(msg || `HTTP error! status: ${response.status}`)
  }

  return response.json()
}

export async function listWorkflowThreads(
  userId?: string,
  limit: number = 50,
): Promise<WorkflowThreadListResponse> {
  const url = new URL(`${getApiBaseUrl()}/api/v1/threads`)
  url.searchParams.set('limit', String(limit))
  const uid = resolveUserId(userId)
  if (uid) url.searchParams.set('user_id', uid)

  const response = await fetch(url.toString(), {
    method: 'GET',
    headers: authHeaders({ Accept: 'application/json' }),
  })
  if (!response.ok) {
    const error = await response.json().catch(() => ({}))
    const detail = (error as { detail?: unknown }).detail
    const msg = typeof detail === 'string' ? detail : `HTTP error! status: ${response.status}`
    throw new Error(msg)
  }
  return response.json()
}

export async function getLatestThreadForGmailMessage(
  gmailMessageId: string,
  userId?: string,
): Promise<LatestThreadForMessageResponse> {
  const url = new URL(
    `${getApiBaseUrl()}/api/v1/threads/by-gmail/${encodeURIComponent(gmailMessageId)}`,
  )
  const uid = resolveUserId(userId)
  if (uid) url.searchParams.set('user_id', uid)

  const response = await fetch(url.toString(), {
    method: 'GET',
    headers: authHeaders({ Accept: 'application/json' }),
  })
  if (response.status === 404) {
    throw new Error('NOT_FOUND')
  }
  if (!response.ok) {
    const error = await response.json().catch(() => ({}))
    const detail = (error as { detail?: unknown }).detail
    const msg = typeof detail === 'string' ? detail : `HTTP error! status: ${response.status}`
    throw new Error(msg)
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

export interface GmailMessageResponse {
  id: string
  subject: string
  from_email: string
  date: string
  body: string
  snippet: string
}

export interface GmailMessagesPageResponse {
  messages: GmailMessageResponse[]
  next_page_token?: string | null
}

export async function getGmailStatus(userId: string): Promise<GmailStatusResponse> {
  const response = await fetch(
    `${getApiBaseUrl()}/api/v1/gmail/status/${encodeURIComponent(userId)}`,
    { method: 'GET', headers: authHeaders({ Accept: 'application/json' }) },
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
  const url = new URL(`${getApiBaseUrl()}/api/v1/gmail/oauth/authorize`)
  url.searchParams.set('user_id', userId)
  const response = await fetch(url.toString(), {
    method: 'GET',
    headers: authHeaders({ Accept: 'application/json' }),
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

export async function listGmailMessages(
  userId?: string,
  maxResults: number = 50,
): Promise<GmailMessageResponse[]> {
  const url = new URL(`${getApiBaseUrl()}/api/v1/gmail/messages`)
  url.searchParams.set('max_results', String(maxResults))
  if (userId) url.searchParams.set('user_id', userId)

  const response = await fetch(url.toString(), {
    method: 'GET',
    headers: authHeaders({ Accept: 'application/json' }),
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

export async function listGmailMessagesPage(
  userId?: string,
  maxResults: number = 50,
  pageToken?: string | null,
): Promise<GmailMessagesPageResponse> {
  const url = new URL(`${getApiBaseUrl()}/api/v1/gmail/messages/page`)
  url.searchParams.set('max_results', String(maxResults))
  if (userId) url.searchParams.set('user_id', userId)
  if (pageToken) url.searchParams.set('page_token', pageToken)

  const response = await fetch(url.toString(), {
    method: 'GET',
    headers: authHeaders({ Accept: 'application/json' }),
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

export async function getGmailMessage(
  messageId: string,
  userId?: string,
  options?: { signal?: AbortSignal },
): Promise<GmailMessageResponse> {
  const url = new URL(
    `${getApiBaseUrl()}/api/v1/gmail/messages/${encodeURIComponent(messageId)}`,
  )
  if (userId) url.searchParams.set('user_id', userId)

  const response = await fetch(url.toString(), {
    method: 'GET',
    headers: authHeaders({ Accept: 'application/json' }),
    signal: options?.signal,
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

export async function createGmailDraft(
  payload: { to: string; subject: string; body: string },
  userId?: string,
): Promise<unknown> {
  const url = new URL(`${getApiBaseUrl()}/api/v1/gmail/drafts`)
  if (userId) url.searchParams.set('user_id', userId)
  const response = await fetch(url.toString(), {
    method: 'POST',
    headers: {
      ...authHeaders({ Accept: 'application/json' }),
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(payload),
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

export async function authenticateWithGoogleIdToken(
  idToken: string,
): Promise<AuthUserResponse> {
  const response = await fetch(`${getApiBaseUrl()}/api/v1/auth/google`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Accept: 'application/json',
    },
    body: JSON.stringify({ id_token: idToken }),
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

export async function getAuthenticatedUser(): Promise<AuthUserResponse> {
  const response = await fetch(`${getApiBaseUrl()}/api/v1/auth/me`, {
    method: 'GET',
    headers: authHeaders({ Accept: 'application/json' }),
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

export async function getPublicAuthConfig(): Promise<PublicAuthConfigResponse> {
  const response = await fetch(`${getApiBaseUrl()}/api/v1/auth/config`, {
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
