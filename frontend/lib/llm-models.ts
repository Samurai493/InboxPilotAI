/**
 * Curated model IDs for LangChain ChatOpenAI / ChatAnthropic / ChatGoogleGenerativeAI
 * used by the backend (see app.services.llm_utils).
 */

export type LlmModelOption = { value: string; label: string }

/** OpenAI chat models supported by ChatOpenAI in this app. */
export const OPENAI_LLM_MODELS: LlmModelOption[] = [
  { value: 'gpt-4o-mini', label: 'GPT-4o mini' },
  { value: 'gpt-4o', label: 'GPT-4o' },
  { value: 'gpt-4-turbo', label: 'GPT-4 Turbo' },
  { value: 'gpt-3.5-turbo', label: 'GPT-3.5 Turbo' },
]

/** Anthropic Claude models supported by ChatAnthropic in this app. */
export const ANTHROPIC_LLM_MODELS: LlmModelOption[] = [
  { value: 'claude-3-5-sonnet-20241022', label: 'Claude 3.5 Sonnet' },
  { value: 'claude-3-5-haiku-20241022', label: 'Claude 3.5 Haiku' },
  { value: 'claude-3-opus-20240229', label: 'Claude 3 Opus' },
]

/** Google Gemini models (stable IDs for generateContent; 1.x aliases often 404 on current API). */
export const GOOGLE_GENAI_LLM_MODELS: LlmModelOption[] = [
  { value: 'gemini-2.5-flash', label: 'Gemini 2.5 Flash' },
  { value: 'gemini-2.5-flash-lite', label: 'Gemini 2.5 Flash-Lite' },
  { value: 'gemini-2.5-pro', label: 'Gemini 2.5 Pro' },
]

const DEFAULT_CHOICE: LlmModelOption = {
  value: '',
  label: 'Use app default (server .env or built-in)',
}

function modelsForProvider(llmProvider: string): LlmModelOption[] {
  if (llmProvider === 'anthropic') return ANTHROPIC_LLM_MODELS
  if (llmProvider === 'google_genai') return GOOGLE_GENAI_LLM_MODELS
  return OPENAI_LLM_MODELS
}

/** Dropdown options: default row + known models for the selected LLM_PROVIDER. */
export function getLlmModelSelectOptions(llmProvider: string): LlmModelOption[] {
  return [DEFAULT_CHOICE, ...modelsForProvider(llmProvider)]
}

/** If currentValue is non-empty and not in the list (e.g. old import), prepend a single “saved” row. */
export function getLlmModelSelectOptionsWithSaved(
  llmProvider: string,
  currentValue: string,
): LlmModelOption[] {
  const base = getLlmModelSelectOptions(llmProvider)
  const known = new Set(base.map((o) => o.value))
  const t = currentValue?.trim()
  if (t && !known.has(t)) {
    return [{ value: t, label: `Other (saved): ${t}` }, ...base]
  }
  return base
}
