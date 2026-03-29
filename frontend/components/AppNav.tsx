'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { useCallback, useEffect, useState } from 'react'
import { getStoredUserId } from '@/lib/user-session'
import { clearBrowserSession } from '@/lib/browser-session'

const linkBase =
  'inline-flex items-center rounded-lg border px-3 py-2 text-sm font-semibold transition-colors'
const linkIdle = `${linkBase} border-gray-300 text-gray-700 hover:bg-gray-50`
const linkActive = `${linkBase} border-primary-500 bg-primary-50 text-primary-900`

function NavLink({ href, children }: { href: string; children: React.ReactNode }) {
  const pathname = usePathname()
  const active =
    href === '/' ? pathname === '/' : pathname === href || pathname.startsWith(`${href}/`)
  return (
    <Link href={href} className={active ? linkActive : linkIdle}>
      {children}
    </Link>
  )
}

function NavLinkGroup() {
  return (
    <div className="flex flex-wrap items-center gap-2">
      <NavLink href="/">Inbox</NavLink>
      <NavLink href="/inbox">Paste message</NavLink>
      <NavLink href="/history">Workflow history</NavLink>
      <NavLink href="/reviews">Reviews</NavLink>
      <NavLink href="/settings">Settings</NavLink>
    </div>
  )
}

export type AppNavProps = {
  /** Shown under the title when using workspace layout */
  subtitle?: string | null
  /** Optional actions (workspace layout only) */
  trailing?: React.ReactNode
  /**
   * Workspace: left title column + nav + trailing + sign out (Gmail-connected home).
   * Compact: single row (inner pages, marketing).
   */
  layout?: 'workspace' | 'compact'
}

export function AppNav({ subtitle, trailing, layout = 'compact' }: AppNavProps) {
  const pathname = usePathname()
  const [userId, setUserId] = useState<string | null>(null)
  const [signOutBusy, setSignOutBusy] = useState(false)

  useEffect(() => {
    queueMicrotask(() => {
      setUserId(getStoredUserId())
    })
  }, [pathname])

  const handleSignOut = useCallback(async () => {
    if (signOutBusy) return
    setSignOutBusy(true)
    try {
      await clearBrowserSession(getStoredUserId())
      window.location.assign('/')
    } catch {
      setSignOutBusy(false)
    }
  }, [signOutBusy])

  const signOutBtn = userId ? (
    <button
      type="button"
      onClick={() => void handleSignOut()}
      disabled={signOutBusy}
      className="rounded-lg border border-gray-300 px-3 py-2 text-sm font-semibold text-gray-700 hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-60"
    >
      {signOutBusy ? 'Signing out…' : 'Sign out'}
    </button>
  ) : null

  if (layout === 'workspace') {
    return (
      <header className="flex shrink-0 flex-wrap items-center justify-between gap-4 border-b border-gray-200 bg-white px-4 py-3 shadow-sm">
        <div className="min-w-0">
          <Link href="/" className="text-lg font-semibold text-gray-900 hover:text-primary-700">
            InboxPilot
          </Link>
          {subtitle ? (
            <div className="truncate text-xs text-gray-500">{subtitle}</div>
          ) : null}
        </div>
        <div className="flex shrink-0 flex-wrap items-center justify-end gap-2">
          <NavLinkGroup />
          {trailing}
          {signOutBtn}
        </div>
      </header>
    )
  }

  return (
    <header className="sticky top-0 z-40 border-b border-gray-200 bg-white/95 px-4 py-3 shadow-sm backdrop-blur">
      <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-3">
        <Link href="/" className="text-lg font-semibold text-gray-900 hover:text-primary-700">
          InboxPilot
        </Link>
        <div className="flex flex-wrap items-center justify-end gap-2">
          <NavLinkGroup />
          {signOutBtn}
        </div>
      </div>
    </header>
  )
}
