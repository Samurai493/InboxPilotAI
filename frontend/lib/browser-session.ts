import { clearGoogleIdToken } from '@/lib/auth-session'
import { clearGuestSessionFully, clearStoredUserId } from '@/lib/user-session'
import { clearGmailInboxPagesLocalStorage } from '@/lib/gmail-inbox-pages-local-cache'
import { clearInboxNavSession } from '@/lib/inbox-nav-session'
import { clearGmailMessagesLocalStorage } from '@/lib/gmail-message-local-cache'

/**
 * Clears tokens, stored user id, and Gmail inbox caches. Safe to call from any page.
 * In-memory caches on the home inbox screen must still be reset by that page when needed.
 */
export async function clearBrowserSession(userId: string | null): Promise<void> {
  if (userId) {
    clearGmailMessagesLocalStorage(userId)
    clearGmailInboxPagesLocalStorage(userId)
    clearInboxNavSession(userId)
  }
  clearGoogleIdToken()
  clearStoredUserId()
  await clearGuestSessionFully()
}
