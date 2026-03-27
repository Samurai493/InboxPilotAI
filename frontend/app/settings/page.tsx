'use client'

import Link from 'next/link'
import { useCallback, useEffect, useMemo, useState, type ChangeEvent } from 'react'
import {
  type AppSettings,
  buildBackendEnvFileContent,
  clearAppSettings,
  defaultAppSettings,
  getApiBaseUrl,
  loadAppSettings,
  mergeImportedEnvIntoSettings,
  saveAppSettings,
} from '@/lib/app-settings'
import { getLlmModelSelectOptionsWithSaved } from '@/lib/llm-models'

const inputClass =
  'mt-1 w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 placeholder:text-gray-400'
const labelClass = 'text-sm font-medium text-gray-800'

type PrimaryLlmKey = 'openaiApiKey' | 'anthropicApiKey' | 'geminiApiKey'

function primaryLlmApiKeyField(provider: string): { label: string; id: string; key: PrimaryLlmKey } {
  if (provider === 'anthropic') {
    return { label: 'ANTHROPIC_API_KEY', id: 'anthropicApiKey', key: 'anthropicApiKey' }
  }
  if (provider === 'google_genai') {
    return { label: 'GEMINI_API_KEY', id: 'geminiApiKey', key: 'geminiApiKey' }
  }
  return { label: 'OPENAI_API_KEY', id: 'openaiApiKey', key: 'openaiApiKey' }
}

export default function SettingsPage() {
  const [s, setS] = useState<AppSettings>(defaultAppSettings)
  const [saved, setSaved] = useState(false)
  const [copyMsg, setCopyMsg] = useState<string | null>(null)
  const [importMsg, setImportMsg] = useState<string | null>(null)
  const [importBusy, setImportBusy] = useState(false)

  useEffect(() => {
    setS(loadAppSettings())
  }, [])

  const update = useCallback(<K extends keyof AppSettings>(key: K, value: AppSettings[K]) => {
    setS((prev) => ({ ...prev, [key]: value }))
    setSaved(false)
  }, [])

  const modelOptions = useMemo(
    () => getLlmModelSelectOptionsWithSaved(s.llmProvider, s.llmModel),
    [s.llmProvider, s.llmModel],
  )

  const handleLlmProviderChange = (e: ChangeEvent<HTMLSelectElement>) => {
    const next = e.target.value
    setS((prev) => ({ ...prev, llmProvider: next, llmModel: '' }))
    setSaved(false)
  }

  const handleLlmModelChange = (e: ChangeEvent<HTMLSelectElement>) => {
    const v = e.target.value
    setS((prev) => ({
      ...prev,
      llmModel: v,
      ...(prev.llmProvider === 'openai' ? { openaiModel: v.trim() ? v : 'gpt-4o-mini' } : {}),
    }))
    setSaved(false)
  }

  const handleSave = () => {
    saveAppSettings(s)
    setSaved(true)
    setCopyMsg(null)
  }

  const handleCopyEnv = async () => {
    const text = buildBackendEnvFileContent(s)
    try {
      await navigator.clipboard.writeText(text)
      setCopyMsg(text ? 'Copied backend/.env snippet to clipboard.' : 'Nothing to copy — fill backend fields first.')
    } catch {
      setCopyMsg('Could not copy. Select and copy manually.')
    }
  }

  const handleClear = () => {
    if (!window.confirm('Clear all saved settings in this browser?')) return
    clearAppSettings()
    setS(defaultAppSettings())
    setSaved(false)
    setCopyMsg(null)
    setImportMsg(null)
  }

  const handleImportFromEnv = async () => {
    setImportBusy(true)
    setImportMsg(null)
    setCopyMsg(null)
    try {
      const feRes = await fetch('/api/settings/frontend-env')
      if (!feRes.ok) throw new Error(`Frontend env: HTTP ${feRes.status}`)
      const fe = (await feRes.json()) as Partial<AppSettings>

      let backend: Partial<AppSettings> | null = null
      let msg: string
      const base = getApiBaseUrl()
      try {
        const beRes = await fetch(`${base}/api/v1/settings/env-template`)
        if (beRes.ok) {
          backend = (await beRes.json()) as Partial<AppSettings>
          msg = 'Imported from frontend .env and backend API.'
        } else if (beRes.status === 404) {
          msg =
            'Backend snapshot skipped (404). Add ENABLE_ENV_TEMPLATE_ENDPOINT=true to backend/.env and restart the API to import server values.'
        } else {
          msg = `Backend snapshot: HTTP ${beRes.status}. Frontend .env values were still applied.`
        }
      } catch {
        msg = `Could not reach ${base} for backend snapshot. Check Backend API URL. Frontend .env values were still applied.`
      }

      setS((prev) => mergeImportedEnvIntoSettings(prev, fe, backend))
      setSaved(false)
      setImportMsg(msg)
    } catch (e) {
      setImportMsg(e instanceof Error ? e.message : 'Import failed')
    } finally {
      setImportBusy(false)
    }
  }

  const primaryLlmKey = primaryLlmApiKeyField(s.llmProvider)

  return (
    <main className="min-h-screen bg-gradient-to-b from-blue-50 to-white">
      <div className="container mx-auto max-w-3xl px-4 py-10">
        <div className="mb-8 flex flex-wrap items-center justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Settings</h1>
            <p className="mt-1 text-sm text-gray-600">
              Local configuration for this browser. Use <strong>Import from .env</strong> to pull{' '}
              <code className="text-xs">NEXT_PUBLIC_*</code> from the frontend build env and (optionally) the running
              API&apos;s loaded <code className="text-xs">backend/.env</code>.
            </p>
          </div>
          <Link
            href="/"
            className="rounded-lg border border-gray-300 bg-white px-4 py-2 text-sm font-semibold text-gray-700 hover:bg-gray-50"
          >
            Back to home
          </Link>
        </div>

        <div className="mb-6 rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-950">
          Storing API keys in the browser is convenient for local development only. Do not use this on shared or
          production machines.
        </div>

        <section className="mb-10 rounded-lg border border-gray-200 bg-white p-6 shadow-sm">
          <h2 className="text-lg font-semibold text-gray-900">Frontend (this app)</h2>
          <p className="mt-1 text-sm text-gray-600">
            Overrides <code className="text-xs">NEXT_PUBLIC_*</code> from build when set. Used immediately after
            Save.
          </p>
          <div className="mt-4 space-y-4">
            <div>
              <label className={labelClass} htmlFor="apiBaseUrl">
                Backend API URL
              </label>
              <input
                id="apiBaseUrl"
                type="url"
                value={s.apiBaseUrl}
                onChange={(e) => update('apiBaseUrl', e.target.value)}
                className={inputClass}
                placeholder="http://localhost:8000"
                autoComplete="off"
              />
            </div>
            <div>
              <label className={labelClass} htmlFor="googleClientId">
                Google OAuth Client ID (browser / Sign-In)
              </label>
              <input
                id="googleClientId"
                type="text"
                value={s.googleClientId}
                onChange={(e) => update('googleClientId', e.target.value)}
                className={inputClass}
                placeholder="xxx.apps.googleusercontent.com"
                autoComplete="off"
              />
            </div>
            <div>
              <label className={labelClass} htmlFor="defaultUserId">
                Default user ID (optional UUID)
              </label>
              <input
                id="defaultUserId"
                type="text"
                value={s.defaultUserId}
                onChange={(e) => update('defaultUserId', e.target.value)}
                className={inputClass}
                placeholder="users.id from database"
                autoComplete="off"
              />
            </div>
          </div>
        </section>

        <section className="mb-10 rounded-lg border border-gray-200 bg-white p-6 shadow-sm">
          <h2 className="text-lg font-semibold text-gray-900">Backend (paste into backend/.env)</h2>
          <p className="mt-1 text-sm text-gray-600">
            Fill these to generate a snippet. Copy and merge into <code className="text-xs">backend/.env</code>, then
            restart the API.
          </p>
          <p className="mt-2 text-sm text-gray-600">
            <strong>Save settings</strong> after changing provider, model, or keys so each workflow run sends{' '}
            <code className="text-xs">llm_provider</code>, <code className="text-xs">llm_model</code>, and any filled
            API keys to the API. Alternatively, put keys only in <code className="text-xs">backend/.env</code> on the
            server (nothing is sent from the browser for keys you leave blank here).
          </p>
          <div className="mt-4 grid grid-cols-1 gap-4 md:grid-cols-2">
            <div className="md:col-span-2">
              <label className={labelClass} htmlFor="llmProvider">
                LLM_PROVIDER
              </label>
              <select
                id="llmProvider"
                value={s.llmProvider}
                onChange={handleLlmProviderChange}
                className={inputClass}
              >
                <option value="openai">openai</option>
                <option value="anthropic">anthropic (Claude)</option>
                <option value="google_genai">google_genai (Gemini)</option>
              </select>
            </div>
            <div className="md:col-span-2">
              <label className={labelClass} htmlFor="llmModel">
                LLM_MODEL (optional override)
              </label>
              <select
                id="llmModel"
                value={s.llmModel}
                onChange={handleLlmModelChange}
                className={inputClass}
              >
                {modelOptions.map((opt) => (
                  <option key={opt.value || '__default__'} value={opt.value}>
                    {opt.label}
                  </option>
                ))}
              </select>
              <p className="mt-1 text-xs text-gray-500">
                Only models supported by this app&apos;s LangChain setup are listed. Choose a provider above first.
              </p>
            </div>
            <div className="md:col-span-2">
              <label className={labelClass} htmlFor={primaryLlmKey.id}>
                {primaryLlmKey.label}
              </label>
              <input
                key={s.llmProvider}
                id={primaryLlmKey.id}
                type="password"
                value={s[primaryLlmKey.key]}
                onChange={(e) => update(primaryLlmKey.key, e.target.value)}
                className={inputClass}
                autoComplete="off"
                placeholder={`Paste ${primaryLlmKey.label} for selected provider`}
              />
            </div>
            {s.llmProvider === 'openai' ? (
              <p className="md:col-span-2 text-sm text-gray-600">
                <code className="text-xs">OPENAI_MODEL</code> in the copied backend snippet follows the model you select
                above (when empty, the snippet uses <code className="text-xs">gpt-4o-mini</code> for OpenAI defaults).
              </p>
            ) : null}
            <div>
              <label className={labelClass} htmlFor="langsmithApiKey">
                LANGSMITH_API_KEY
              </label>
              <input
                id="langsmithApiKey"
                type="password"
                value={s.langsmithApiKey}
                onChange={(e) => update('langsmithApiKey', e.target.value)}
                className={inputClass}
                autoComplete="off"
              />
            </div>
            <div>
              <label className={labelClass} htmlFor="langsmithProject">
                LANGSMITH_PROJECT
              </label>
              <input
                id="langsmithProject"
                type="text"
                value={s.langsmithProject}
                onChange={(e) => update('langsmithProject', e.target.value)}
                className={inputClass}
              />
            </div>
            <div className="flex items-end gap-2 pb-1">
              <label className="flex cursor-pointer items-center gap-2 text-sm font-medium text-gray-800">
                <input
                  type="checkbox"
                  checked={s.langsmithTracing}
                  onChange={(e) => update('langsmithTracing', e.target.checked)}
                  className="accent-primary-600"
                />
                LANGSMITH_TRACING
              </label>
            </div>
            <div className="md:col-span-2">
              <label className={labelClass} htmlFor="databaseUrl">
                DATABASE_URL
              </label>
              <input
                id="databaseUrl"
                type="text"
                value={s.databaseUrl}
                onChange={(e) => update('databaseUrl', e.target.value)}
                className={inputClass}
                placeholder="postgresql://user:pass@localhost:5432/inboxpilot"
                autoComplete="off"
              />
            </div>
            <div className="md:col-span-2">
              <label className={labelClass} htmlFor="redisUrl">
                REDIS_URL
              </label>
              <input
                id="redisUrl"
                type="text"
                value={s.redisUrl}
                onChange={(e) => update('redisUrl', e.target.value)}
                className={inputClass}
                placeholder="redis://localhost:6379/0"
              />
            </div>
            <div className="md:col-span-2">
              <label className={labelClass} htmlFor="secretKey">
                SECRET_KEY
              </label>
              <input
                id="secretKey"
                type="password"
                value={s.secretKey}
                onChange={(e) => update('secretKey', e.target.value)}
                className={inputClass}
                autoComplete="off"
              />
            </div>
            <div>
              <label className={labelClass} htmlFor="googleClientIdBackend">
                GOOGLE_CLIENT_ID (server)
              </label>
              <input
                id="googleClientIdBackend"
                type="text"
                value={s.googleClientIdBackend}
                onChange={(e) => update('googleClientIdBackend', e.target.value)}
                className={inputClass}
              />
            </div>
            <div>
              <label className={labelClass} htmlFor="googleClientSecret">
                GOOGLE_CLIENT_SECRET
              </label>
              <input
                id="googleClientSecret"
                type="password"
                value={s.googleClientSecret}
                onChange={(e) => update('googleClientSecret', e.target.value)}
                className={inputClass}
                autoComplete="off"
              />
            </div>
            <div className="md:col-span-2">
              <label className={labelClass} htmlFor="googleRedirectUri">
                GOOGLE_REDIRECT_URI
              </label>
              <input
                id="googleRedirectUri"
                type="url"
                value={s.googleRedirectUri}
                onChange={(e) => update('googleRedirectUri', e.target.value)}
                className={inputClass}
              />
            </div>
            <div className="md:col-span-2">
              <label className={labelClass} htmlFor="frontendUrl">
                FRONTEND_URL
              </label>
              <input
                id="frontendUrl"
                type="url"
                value={s.frontendUrl}
                onChange={(e) => update('frontendUrl', e.target.value)}
                className={inputClass}
                placeholder="http://localhost:3002"
              />
            </div>
            <div className="md:col-span-2">
              <label className={labelClass} htmlFor="corsOrigins">
                CORS_ORIGINS (comma-separated or JSON array)
              </label>
              <input
                id="corsOrigins"
                type="text"
                value={s.corsOrigins}
                onChange={(e) => update('corsOrigins', e.target.value)}
                className={inputClass}
                placeholder="http://localhost:3000,http://localhost:3002"
              />
            </div>
          </div>
        </section>

        <div className="flex flex-wrap items-center gap-3">
          <button
            type="button"
            onClick={() => void handleImportFromEnv()}
            disabled={importBusy}
            className="rounded-lg border border-primary-200 bg-primary-50 px-5 py-2.5 text-sm font-semibold text-primary-900 hover:bg-primary-100 disabled:cursor-not-allowed disabled:opacity-60"
          >
            {importBusy ? 'Importing…' : 'Import from .env'}
          </button>
          <button
            type="button"
            onClick={handleSave}
            className="rounded-lg bg-primary-600 px-5 py-2.5 text-sm font-semibold text-white hover:bg-primary-700"
          >
            Save settings
          </button>
          <button
            type="button"
            onClick={handleCopyEnv}
            className="rounded-lg border border-gray-300 bg-white px-5 py-2.5 text-sm font-semibold text-gray-700 hover:bg-gray-50"
          >
            Copy backend .env snippet
          </button>
          <button
            type="button"
            onClick={handleClear}
            className="rounded-lg border border-red-200 text-red-700 px-5 py-2.5 text-sm font-semibold hover:bg-red-50"
          >
            Clear all
          </button>
        </div>
        {saved ? (
          <p className="mt-4 text-sm font-medium text-green-700">Saved. Reload the home page if Google Sign-In was not updating.</p>
        ) : null}
        {importMsg ? <p className="mt-2 text-sm text-gray-700">{importMsg}</p> : null}
        {copyMsg ? <p className="mt-2 text-sm text-gray-700">{copyMsg}</p> : null}
      </div>
    </main>
  )
}
