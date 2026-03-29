/**
 * Browser-local app configuration (API URL, OAuth client ID, backend .env draft).
 * Secrets here are only on this device; prefer backend/.env for production servers.
 */

export const APP_SETTINGS_STORAGE_KEY = 'inboxpilot_app_settings_v1'

export interface AppSettings {
  /** Backend API origin, e.g. http://localhost:8000 */
  apiBaseUrl: string
  /** Google Identity Services (Web client ID); same app as backend GOOGLE_CLIENT_ID often */
  googleClientId: string
  /** Optional fixed users.id UUID for API calls */
  defaultUserId: string
  /** openai | anthropic | google_genai */
  llmProvider: string
  llmModel: string
  openaiApiKey: string
  openaiModel: string
  anthropicApiKey: string
  geminiApiKey: string
  langsmithApiKey: string
  langsmithProject: string
  langsmithTracing: boolean
  databaseUrl: string
  redisUrl: string
  secretKey: string
  googleClientIdBackend: string
  googleClientSecret: string
  googleRedirectUri: string
  frontendUrl: string
  /** Comma-separated origins or JSON array string for CORS_ORIGINS */
  corsOrigins: string
}

export function defaultAppSettings(): AppSettings {
  return {
    apiBaseUrl: '',
    googleClientId: '',
    defaultUserId: '',
    llmProvider: 'openai',
    llmModel: '',
    openaiApiKey: '',
    openaiModel: 'gpt-4o-mini',
    anthropicApiKey: '',
    geminiApiKey: '',
    langsmithApiKey: '',
    langsmithProject: 'inboxpilot-ai',
    langsmithTracing: true,
    databaseUrl: '',
    redisUrl: '',
    secretKey: '',
    googleClientIdBackend: '',
    googleClientSecret: '',
    googleRedirectUri: 'http://localhost:8000/api/v1/gmail/oauth/callback',
    frontendUrl: 'http://localhost:3002',
    corsOrigins: 'http://localhost:3000,http://localhost:3001,http://localhost:3002',
  }
}

export function loadAppSettings(): AppSettings {
  if (typeof window === 'undefined') return defaultAppSettings()
  try {
    const raw = localStorage.getItem(APP_SETTINGS_STORAGE_KEY)
    if (!raw) return defaultAppSettings()
    const parsed = JSON.parse(raw) as Partial<AppSettings>
    return { ...defaultAppSettings(), ...parsed }
  } catch {
    return defaultAppSettings()
  }
}

export function saveAppSettings(next: Partial<AppSettings>): AppSettings {
  const merged = { ...loadAppSettings(), ...next }
  if (typeof window !== 'undefined') {
    localStorage.setItem(APP_SETTINGS_STORAGE_KEY, JSON.stringify(merged))
  }
  return merged
}

export function clearAppSettings(): void {
  if (typeof window !== 'undefined') {
    localStorage.removeItem(APP_SETTINGS_STORAGE_KEY)
  }
}

/** True after the user has saved Settings at least once (localStorage key exists). */
export function hasStoredAppSettings(): boolean {
  if (typeof window === 'undefined') return false
  return !!localStorage.getItem(APP_SETTINGS_STORAGE_KEY)
}

/** Apply non-empty values from partial into a copy of current (strings: skip empty; booleans: always apply). */
export function mergeImportedEnvIntoSettings(
  current: AppSettings,
  frontend: Partial<AppSettings>,
  backend: Partial<AppSettings> | null,
): AppSettings {
  const apply = (base: AppSettings, partial: Partial<AppSettings>): AppSettings => {
    const next = { ...base }
    for (const key of Object.keys(partial) as (keyof AppSettings)[]) {
      const v = partial[key]
      if (v === undefined) continue
      if (typeof v === 'string' && v.trim() === '') continue
      ;(next as Record<string, unknown>)[key] = v
    }
    return next
  }
  let out = apply(current, frontend)
  if (backend) out = apply(out, backend)
  return out
}

/** Effective API base URL: saved value, then build env, then default. */
export function getApiBaseUrl(): string {
  if (typeof window !== 'undefined') {
    const s = loadAppSettings().apiBaseUrl?.trim()
    if (s) return s.replace(/\/$/, '')
  }
  return process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
}

/** GIS client ID: Next public env first, then Settings (when env is unset). */
export function getGoogleClientIdForGis(): string {
  const fromEnv = process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID?.trim()
  if (fromEnv) return fromEnv
  if (typeof window !== 'undefined') {
    const s = loadAppSettings().googleClientId?.trim()
    if (s) return s
  }
  return ''
}

export function getDefaultUserIdFromSettings(): string | undefined {
  if (typeof window === 'undefined') return undefined
  const id = loadAppSettings().defaultUserId?.trim()
  return id || undefined
}

