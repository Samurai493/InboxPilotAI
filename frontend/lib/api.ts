/**
 * API client for InboxPilot AI backend
 */

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

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
export async function processMessage(message: string): Promise<ProcessMessageResponse> {
  const response = await fetch(`${API_BASE_URL}/api/v1/process`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      message,
      user_id: 'demo-user', // In MVP, use demo user
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
