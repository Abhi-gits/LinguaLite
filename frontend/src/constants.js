export const LANGUAGES = [
  { code: 'en', label: 'English', script: 'Latin' },
  { code: 'hi', label: 'Hindi', script: 'Devanagari' },
  { code: 'ta', label: 'Tamil', script: 'Tamil', experimental: true },
  { code: 'te', label: 'Telugu', script: 'Telugu', experimental: true },
  { code: 'kn', label: 'Kannada', script: 'Kannada', experimental: true },
  { code: 'ml', label: 'Malayalam', script: 'Malayalam', experimental: true },
  { code: 'bn', label: 'Bengali', script: 'Bengali', experimental: true },
  { code: 'mr', label: 'Marathi', script: 'Devanagari', experimental: true },
  { code: 'gu', label: 'Gujarati', script: 'Gujarati', experimental: true },
  { code: 'pa', label: 'Punjabi', script: 'Gurmukhi', experimental: true },
]

export const EXPERIMENTAL_LANGUAGE_CODES = new Set(
  LANGUAGES.filter((language) => language.experimental).map((language) => language.code),
)

export const AUTO_LANGUAGE = { code: 'auto', label: 'Auto-detect' }

export const MAX_TEXT_LENGTH = 4000

export const TASKS = [
  { id: 'translate', label: 'Translate' },
  { id: 'grammar', label: 'Grammar' },
  { id: 'explain', label: 'Explain' },
  { id: 'transliterate', label: 'Transliterate' },
  { id: 'india_connect', label: 'India Connect' },
]

export const INDIA_CONNECT_AUDIENCES = [
  { id: 'general', label: 'General / not sure' },
  { id: 'friend', label: 'Friend or peer' },
  { id: 'elder', label: 'Older person' },
  { id: 'professional', label: 'Colleague or professional contact' },
  { id: 'service_staff', label: 'Service worker or customer-facing staff' },
]

export const STYLES = [
  { id: 'natural', label: 'Natural', description: 'Fluent, clear language.' },
  { id: 'formal', label: 'Formal', description: 'Polished and professional.' },
  { id: 'casual', label: 'Casual', description: 'Conversational and relaxed.' },
  { id: 'literal', label: 'Literal', description: 'Closer to the source wording.' },
]
