/**
 * Fallback when the backend checkpointer does not return state (e.g. in-memory saver, cold load).
 * Populated after /process returns full final state.
 */
const PREFIX = 'inboxpilot_thread_state:'

export function cacheThreadState(threadId: string, state: object): void {
  if (typeof window === 'undefined') return
  try {
    sessionStorage.setItem(PREFIX + threadId, JSON.stringify(state))
  } catch {
    /* quota or private mode */
  }
}

export function loadCachedThreadState(threadId: string): Record<string, unknown> | null {
  if (typeof window === 'undefined') return null
  try {
    const raw = sessionStorage.getItem(PREFIX + threadId)
    if (!raw) return null
    const parsed = JSON.parse(raw) as unknown
    return parsed && typeof parsed === 'object' ? (parsed as Record<string, unknown>) : null
  } catch {
    return null
  }
}
