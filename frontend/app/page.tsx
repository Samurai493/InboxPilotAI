'use client'

import Link from 'next/link'
import { useCallback, useEffect, useState } from 'react'
import {
  API_BASE_URL,
  getGmailAuthorizationUrl,
  getGmailStatus,
} from '@/lib/api'
import { ensureUserId } from '@/lib/user-session'

export default function Home() {
  const [userId, setUserId] = useState<string | null>(null)
  const [gmailConnected, setGmailConnected] = useState(false)
  const [gmailEmail, setGmailEmail] = useState<string | null>(null)
  const [sessionError, setSessionError] = useState<string | null>(null)
  const [gmailBusy, setGmailBusy] = useState(false)

  const refreshGmail = useCallback(async (uid: string) => {
    const status = await getGmailStatus(uid)
    setGmailConnected(status.connected)
    setGmailEmail(status.google_account_email ?? null)
  }, [])

  useEffect(() => {
    let cancelled = false
    ;(async () => {
      try {
        const id = await ensureUserId(API_BASE_URL)
        if (cancelled) return
        setUserId(id)
        await refreshGmail(id)
      } catch (e) {
        if (!cancelled) {
          setSessionError(e instanceof Error ? e.message : 'Could not start session')
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

  return (
    <main className="min-h-screen bg-gradient-to-b from-blue-50 to-white">
      <div className="container mx-auto px-4 py-16">
        <div className="max-w-4xl mx-auto text-center">
          <h1 className="text-5xl font-bold text-gray-900 mb-6">
            InboxPilot AI
          </h1>
          <p className="text-xl text-gray-600 mb-8">
            Transform your messy inbox into structured, reviewable workflows
          </p>
          <p className="text-lg text-gray-500 mb-12">
            Powered by LangGraph • Classify • Draft • Extract • Review
          </p>

          <div className="max-w-xl mx-auto mb-10 rounded-lg border border-gray-200 bg-white p-6 text-left shadow-sm">
            <h2 className="text-lg font-semibold text-gray-900 mb-2">
              Gmail
            </h2>
            {sessionError && (
              <p className="mb-3 text-sm text-red-600">{sessionError}</p>
            )}
            {!userId && !sessionError && (
              <p className="text-sm text-gray-600">Preparing your session…</p>
            )}
            {userId && gmailConnected && (
              <p className="text-sm text-gray-700">
                Connected as{' '}
                <span className="font-medium">
                  {gmailEmail || 'your Google account'}
                </span>
                . After Google redirects you back to the API, return here and refresh
                this page if the status does not update.
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
    </main>
  )
}
