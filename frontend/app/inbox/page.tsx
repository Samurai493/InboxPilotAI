'use client'

import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { useEffect, useState } from 'react'
import { AppNav } from '@/components/AppNav'
import { processMessage } from '@/lib/api'
import { getApiBaseUrl, getDefaultUserIdFromSettings } from '@/lib/app-settings'
import { cacheThreadState } from '@/lib/thread-state-cache'
import { ensureUserId, getStoredUserId } from '@/lib/user-session'

export default function InboxPage() {
  const [message, setMessage] = useState('')
  const [isProcessing, setIsProcessing] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [bootstrapError, setBootstrapError] = useState<string | null>(null)
  const [bootstrapDone, setBootstrapDone] = useState(false)
  const [resolvedUserId, setResolvedUserId] = useState<string | null>(null)
  const router = useRouter()

  useEffect(() => {
    let cancelled = false
    ;(async () => {
      try {
        const id = await ensureUserId(getApiBaseUrl())
        if (!cancelled) setResolvedUserId(id)
      } catch (e) {
        if (!cancelled) {
          setBootstrapError(e instanceof Error ? e.message : 'Could not start a browser session')
        }
      } finally {
        if (!cancelled) setBootstrapDone(true)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [])

  const effectiveUserId =
    resolvedUserId ?? getStoredUserId() ?? getDefaultUserIdFromSettings()?.trim() ?? ''

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!message.trim()) {
      setError('Please enter a message')
      return
    }
    if (!effectiveUserId) {
      setError('No user session yet. Wait for the page to finish loading or open the home page to sign in.')
      return
    }

    setIsProcessing(true)
    setError(null)

    try {
      const result = await processMessage(message.trim(), effectiveUserId)
      if (result.status === 'failed' && result.error) {
        throw new Error(result.error)
      }
      if (result.thread_id) {
        if (result.state && typeof result.state === 'object') {
          cacheThreadState(result.thread_id, result.state as object)
        }
        router.push(`/results/${result.thread_id}`)
      } else {
        setError('Failed to process message')
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred')
    } finally {
      setIsProcessing(false)
    }
  }

  return (
    <>
      <AppNav layout="compact" />
      <main className="min-h-screen bg-gray-50 py-12">
        <div className="container mx-auto max-w-4xl px-4">
          <div className="rounded-lg bg-white p-8 shadow-lg">
            <h1 className="mb-6 text-3xl font-bold text-gray-900">Process your message</h1>
            <p className="mb-4 text-gray-600">
              Paste an email or message below. InboxPilot will classify it, draft a reply, and extract
              tasks. Your session is tied to this browser (or your Google sign-in from the{' '}
              <Link href="/" className="font-semibold text-primary-600 hover:text-primary-700">
                inbox home
              </Link>
              ).
            </p>
            {bootstrapDone && bootstrapError ? (
              <div className="mb-6 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800">
                {bootstrapError}{' '}
                <Link href="/" className="font-semibold underline">
                  Open home to sign in
                </Link>{' '}
                or check Settings → Backend API URL.
              </div>
            ) : null}
            {!bootstrapDone ? (
              <p className="mb-6 text-sm text-gray-600">Preparing your session…</p>
            ) : null}

            <form onSubmit={(e) => void handleSubmit(e)} className="space-y-6">
              <div>
                <label htmlFor="message" className="mb-2 block text-sm font-medium text-gray-700">
                  Message content
                </label>
                <textarea
                  id="message"
                  value={message}
                  onChange={(e) => setMessage(e.target.value)}
                  rows={12}
                  className="w-full resize-none rounded-lg border border-gray-300 px-4 py-3 focus:border-primary-500 focus:ring-2 focus:ring-primary-500"
                  placeholder="Paste your email or message here..."
                  disabled={isProcessing || !bootstrapDone || !!bootstrapError}
                  aria-invalid={!!error}
                  aria-describedby={error ? 'inbox-form-error' : undefined}
                />
              </div>

              {error ? (
                <div
                  id="inbox-form-error"
                  role="alert"
                  className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-red-700"
                >
                  {error}
                </div>
              ) : null}

              <button
                type="submit"
                disabled={
                  isProcessing || !message.trim() || !bootstrapDone || !!bootstrapError || !effectiveUserId
                }
                className="w-full rounded-lg bg-primary-600 px-6 py-3 font-semibold text-white transition-colors hover:bg-primary-700 disabled:cursor-not-allowed disabled:bg-gray-400"
              >
                {isProcessing ? 'Processing…' : 'Process message'}
              </button>
            </form>

            <div className="mt-8 rounded-lg bg-blue-50 p-4">
              <p className="text-sm text-blue-800">
                <strong>Tip:</strong> Include the full email with headers (From, Subject, etc.) for best
                results.
              </p>
            </div>
          </div>
        </div>
      </main>
    </>
  )
}
