import { useEffect, useMemo, useRef, useState } from 'react'

import { runAssistant } from '../api'
import {
  AUTO_LANGUAGE,
  EXPERIMENTAL_LANGUAGE_CODES,
  INDIA_CONNECT_AUDIENCES,
  LANGUAGES,
  MAX_TEXT_LENGTH,
  STYLES,
  TASKS,
} from '../constants'

const HISTORY_KEY = 'lingualite.history.v1'

function languageLabel(code) {
  if (code === AUTO_LANGUAGE.code) return AUTO_LANGUAGE.label
  return LANGUAGES.find((language) => language.code === code)?.label ?? code
}

function languageOptionLabel(language) {
  return `${language.label}${language.experimental ? ' — early access' : ''}`
}

function getResultText(result) {
  return (
    result?.translated_text ??
    result?.corrected_text ??
    result?.explanation ??
    result?.transliterated_text ??
    ''
  )
}

function getIndiaConnectCard(result) {
  if (!result?.translated_text) return ''
  return [
    `Message:\n${result.translated_text}`,
    result.pronunciation_help
      ? `Approximate pronunciation:\n${result.pronunciation_help}`
      : '',
    result.tone_guidance ? `Tone note:\n${result.tone_guidance}` : '',
  ].filter(Boolean).join('\n\n')
}

export default function Translator() {
  const [task, setTask] = useState('translate')
  const [sourceLanguage, setSourceLanguage] = useState('auto')
  const [targetLanguage, setTargetLanguage] = useState('hi')
  const [style, setStyle] = useState('natural')
  const [alternativesCount, setAlternativesCount] = useState(0)
  const [includeExplanation, setIncludeExplanation] = useState(false)
  const [sourceScript, setSourceScript] = useState('auto')
  const [targetScript, setTargetScript] = useState('latin')
  const [audience, setAudience] = useState('general')
  const [sourceText, setSourceText] = useState('')
  const [result, setResult] = useState(null)
  const [status, setStatus] = useState('idle')
  const [error, setError] = useState('')
  const [copied, setCopied] = useState(false)
  const [historyState, setHistoryState] = useState(() => {
    try {
      const stored = window.localStorage.getItem(HISTORY_KEY)
      const entries = stored === null ? [] : JSON.parse(stored)
      if (!Array.isArray(entries)) throw new Error('Stored history has an invalid format.')
      return { entries, error: '' }
    } catch {
      return {
        entries: [],
        error: 'Browser history could not be read. Clear the site data to reset it.',
      }
    }
  })
  const requestController = useRef(null)

  const history = historyState.entries
  const historyError = historyState.error
  const characterCount = sourceText.length
  const isTooLong = characterCount > MAX_TEXT_LENGTH
  const canSubmit = sourceText.trim().length > 0 && !isTooLong && status !== 'loading'
  const resultText = getResultText(result)
  const usesLanguagePair = ['translate', 'india_connect'].includes(task)
    || ['grammar', 'explain'].includes(task)
  const needsLanguageReview = EXPERIMENTAL_LANGUAGE_CODES.has(sourceLanguage)
    || (['translate', 'india_connect'].includes(task)
      && EXPERIMENTAL_LANGUAGE_CODES.has(targetLanguage))

  const outputLabel = useMemo(() => {
    if (status === 'loading') return 'Working…'
    if (task === 'translate') return `Translated ${languageLabel(targetLanguage)}`
    if (task === 'india_connect') return `Suggested ${languageLabel(targetLanguage)} message`
    if (task === 'grammar') return 'Corrected text'
    if (task === 'explain') return 'Explanation'
    return `${targetScript === 'latin' ? 'Latin' : 'Devanagari'} transliteration`
  }, [status, targetLanguage, targetScript, task])

  useEffect(
    () => () => {
      requestController.current?.abort()
    },
    [],
  )

  function saveHistory(entries) {
    setHistoryState({ entries, error: '' })
    try {
      window.localStorage.setItem(HISTORY_KEY, JSON.stringify(entries))
    } catch {
      setHistoryState({
        entries,
        error: 'Could not save history in this browser. You can still use the assistant.',
      })
    }
  }

  function invalidateResult() {
    setResult(null)
    setError('')
    setStatus('idle')
    setCopied(false)
  }

  function changeTask(value) {
    setTask(value)
    invalidateResult()
  }

  function handleSwap() {
    if (sourceLanguage === 'auto') return
    const translatedInput = result?.translated_text
    setSourceLanguage(targetLanguage)
    setTargetLanguage(sourceLanguage)
    if (translatedInput) setSourceText(translatedInput)
    invalidateResult()
  }

  function handleClear() {
    requestController.current?.abort()
    requestController.current = null
    setSourceText('')
    invalidateResult()
  }

  async function handleCopy(
    text = task === 'india_connect' ? getIndiaConnectCard(result) : resultText,
  ) {
    if (!text) return
    try {
      await navigator.clipboard.writeText(text)
      setCopied(true)
    } catch {
      setError('Could not copy the result to the clipboard.')
    }
  }

  function handleDownload() {
    if (!resultText) return
    const downloadText = task === 'india_connect'
      ? getIndiaConnectCard(result)
      : resultText
    const blob = new Blob([downloadText], { type: 'text/plain;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `lingualite-${task}.txt`
    link.click()
    URL.revokeObjectURL(url)
  }

  async function handleSubmit(event) {
    event.preventDefault()
    if (!sourceText.trim()) {
      setError('Enter text to continue.')
      setStatus('error')
      return
    }
    if (isTooLong) {
      setError(`Text is too long. Use ${MAX_TEXT_LENGTH} characters or fewer.`)
      setStatus('error')
      return
    }

    const payload = { task, text: sourceText }
    if (task === 'translate' || task === 'india_connect') {
      Object.assign(payload, {
        source_language: sourceLanguage,
        target_language: targetLanguage,
      })
      if (task === 'translate') {
        Object.assign(payload, {
          style,
          alternatives: alternativesCount,
          include_explanation: includeExplanation,
        })
      } else {
        payload.audience = audience
      }
    } else if (task === 'transliterate') {
      Object.assign(payload, {
        source_language: 'hi',
        source_script: sourceScript,
        target_script: targetScript,
      })
    } else {
      Object.assign(payload, { source_language: sourceLanguage })
    }

    setStatus('loading')
    setError('')
    setCopied(false)
    const controller = new AbortController()
    requestController.current = controller

    try {
      const response = await runAssistant(payload, { signal: controller.signal })
      setResult(response)
      if (response.source_language) {
        setSourceLanguage(response.source_language)
      }
      setStatus('success')
      const entry = {
        id: globalThis.crypto?.randomUUID?.() ?? `${Date.now()}-${Math.random()}`,
        createdAt: new Date().toISOString(),
        task,
        text: sourceText,
        sourceLanguage: response.source_language ?? sourceLanguage,
        targetLanguage,
        style,
        alternativesCount,
        includeExplanation,
        sourceScript,
        targetScript,
        audience,
        result: response,
      }
      saveHistory([entry, ...history].slice(0, 50))
    } catch (requestError) {
      if (requestError?.name === 'AbortError') return
      setResult(null)
      setStatus('error')
      setError(requestError.message || 'The task could not be completed. Please try again.')
    } finally {
      if (requestController.current === controller) requestController.current = null
    }
  }

  function revisit(entry) {
    setTask(entry.task)
    setSourceText(entry.text)
    setSourceLanguage(entry.sourceLanguage)
    setTargetLanguage(entry.targetLanguage)
    setStyle(entry.style)
    setAlternativesCount(entry.alternativesCount)
    setIncludeExplanation(entry.includeExplanation)
    setSourceScript(entry.sourceScript)
    setTargetScript(entry.targetScript)
    setAudience(entry.audience ?? 'general')
    setResult(entry.result)
    setStatus('success')
    setError('')
    setCopied(false)
  }

  function deleteHistoryEntry(id) {
    saveHistory(history.filter((entry) => entry.id !== id))
  }

  return (
    <div className="flex flex-col gap-6">
      <form onSubmit={handleSubmit} className="flex flex-col gap-6">
        <div className="grid gap-4 sm:grid-cols-2">
          <label className="flex flex-col gap-2 text-sm font-medium text-ink" htmlFor="task">
            Task
            <select
              id="task"
              value={task}
              disabled={status === 'loading'}
              onChange={(event) => changeTask(event.target.value)}
              className="h-11 rounded-xl border border-line bg-surface px-3"
            >
              {TASKS.map((option) => (
                <option key={option.id} value={option.id}>{option.label}</option>
              ))}
            </select>
          </label>

          {task === 'translate' ? (
            <div className="flex flex-col gap-2">
              <span className="text-sm font-medium text-ink">Translation style</span>
              <select
                aria-label="Translation style"
                value={style}
                disabled={status === 'loading'}
                onChange={(event) => {
                  setStyle(event.target.value)
                  invalidateResult()
                }}
                className="h-11 rounded-xl border border-line bg-surface px-3"
              >
                {STYLES.map((option) => (
                  <option key={option.id} value={option.id}>{option.label}</option>
                ))}
              </select>
              <p className="text-sm text-muted">{STYLES.find((item) => item.id === style)?.description}</p>
            </div>
          ) : null}
        </div>

        {usesLanguagePair ? (
          <div className="grid items-end gap-2 sm:grid-cols-[1fr_auto_1fr]">
            <LanguageSelect
              id="source-language"
              label="Source language"
              value={sourceLanguage}
              exclude={targetLanguage}
              onChange={(value) => {
                setSourceLanguage(value)
                invalidateResult()
              }}
              disabled={status === 'loading'}
              allowAuto
            />
            {task === 'translate' || task === 'india_connect' ? (
              <>
                <button
                  type="button"
                  onClick={handleSwap}
                  disabled={status === 'loading' || sourceLanguage === AUTO_LANGUAGE.code}
                  aria-label="Swap languages"
                  title={sourceLanguage === 'auto' ? 'Select a source language to swap' : undefined}
                  className="mb-0.5 inline-flex h-11 w-11 items-center justify-center rounded-full border border-line bg-surface text-ink disabled:opacity-50 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
                >
                  <SwapIcon />
                </button>
                <LanguageSelect
                  id="target-language"
                  label="Target language"
                  value={targetLanguage}
                  exclude={sourceLanguage}
                  onChange={(value) => {
                    setTargetLanguage(value)
                    invalidateResult()
                  }}
                  disabled={status === 'loading'}
                />
              </>
            ) : (
              <p className="pb-3 text-sm text-muted sm:col-span-2">
                {task === 'grammar'
                  ? 'Grammar correction preserves the selected or detected language.'
                  : 'Explanations are kept separate from your original text.'}
              </p>
            )}
          </div>
        ) : null}

        {needsLanguageReview && task !== 'transliterate' ? (
          <p
            role="status"
            className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900"
          >
            Regional language support is early access and has not been independently quality-validated.
            Please review important wording with a fluent speaker.
          </p>
        ) : null}

        {task === 'india_connect' ? (
          <div className="flex flex-col gap-2">
            <label htmlFor="india-connect-audience" className="text-sm font-medium text-ink">
              Who are you speaking to?
            </label>
            <select
              id="india-connect-audience"
              value={audience}
              disabled={status === 'loading'}
              onChange={(event) => {
                setAudience(event.target.value)
                invalidateResult()
              }}
              className="h-11 rounded-xl border border-line bg-surface px-3"
            >
              {INDIA_CONNECT_AUDIENCES.map((option) => (
                <option key={option.id} value={option.id}>{option.label}</option>
              ))}
            </select>
            <p className="text-sm text-muted">
              Describe what you want to communicate. LinguaLite drafts a message and provides
              approximate pronunciation and a tone note.
            </p>
          </div>
        ) : null}

        {task === 'transliterate' ? (
          <div className="grid gap-4 sm:grid-cols-2">
            <label className="flex flex-col gap-2 text-sm font-medium text-ink" htmlFor="source-script">
              Input script
              <select
                id="source-script"
                value={sourceScript}
                disabled={status === 'loading'}
                onChange={(event) => {
                  setSourceScript(event.target.value)
                  invalidateResult()
                }}
                className="h-11 rounded-xl border border-line bg-surface px-3"
              >
                <option value="auto">Auto-detect</option>
                <option value="devanagari">Devanagari</option>
                <option value="latin">Latin (romanized Hindi)</option>
              </select>
            </label>
            <label className="flex flex-col gap-2 text-sm font-medium text-ink" htmlFor="target-script">
              Output script
              <select
                id="target-script"
                value={targetScript}
                disabled={status === 'loading'}
                onChange={(event) => {
                  setTargetScript(event.target.value)
                  invalidateResult()
                }}
                className="h-11 rounded-xl border border-line bg-surface px-3"
              >
                <option value="latin">Latin (romanized Hindi)</option>
                <option value="devanagari">Devanagari</option>
              </select>
            </label>
            <p className="text-sm text-muted sm:col-span-2">
              This changes script, not language. Results are AI-generated colloquial romanization.
            </p>
          </div>
        ) : null}

        {task === 'translate' ? (
          <div className="flex flex-wrap items-center gap-5">
            <label className="flex items-center gap-2 text-sm text-ink">
              Alternatives
              <select
                aria-label="Number of alternative translations"
                value={alternativesCount}
                disabled={status === 'loading'}
                onChange={(event) => {
                  setAlternativesCount(Number(event.target.value))
                  invalidateResult()
                }}
                className="h-10 rounded-lg border border-line bg-surface px-2"
              >
                {[0, 1, 2, 3].map((count) => (
                  <option key={count} value={count}>{count === 0 ? 'None' : count}</option>
                ))}
              </select>
            </label>
            <label className="flex items-center gap-2 text-sm text-ink">
              <input
                type="checkbox"
                checked={includeExplanation}
                disabled={status === 'loading'}
                onChange={(event) => {
                  setIncludeExplanation(event.target.checked)
                  invalidateResult()
                }}
              />
              Explain context and word choices
            </label>
          </div>
        ) : null}

        {error ? (
          <div role="alert" className="rounded-xl border border-red-200 bg-danger-bg px-4 py-3 text-sm text-danger">
            {error}
          </div>
        ) : null}

        <div className="grid gap-4 md:grid-cols-2">
          <section className="flex min-h-[18rem] flex-col rounded-2xl border border-line bg-surface p-4 shadow-[0_1px_2px_rgba(28,25,23,0.04)]">
            <div className="mb-2 flex items-center justify-between gap-3">
              <label htmlFor="source-text" className="text-sm font-medium text-ink">
                {task === 'transliterate'
                  ? 'Hindi text'
                  : task === 'india_connect'
                    ? 'What do you want to say?'
                    : languageLabel(sourceLanguage)}
              </label>
              <p className={`text-sm ${isTooLong ? 'text-danger' : 'text-muted'}`} aria-live="polite">
                {characterCount.toLocaleString()} / {MAX_TEXT_LENGTH.toLocaleString()}
              </p>
            </div>
            <textarea
              id="source-text"
              value={sourceText}
              onChange={(event) => {
                setSourceText(event.target.value)
                invalidateResult()
              }}
              disabled={status === 'loading'}
              maxLength={MAX_TEXT_LENGTH + 200}
              placeholder={task === 'india_connect'
                ? 'Describe your intention and include important details'
                : 'Enter text to work with'}
              className="min-h-[14rem] flex-1 resize-y bg-transparent text-base leading-7 text-ink outline-none placeholder:text-stone-400"
              aria-invalid={isTooLong || (!sourceText.trim() && status === 'error')}
              aria-describedby="source-help"
            />
            <p id="source-help" className="sr-only">Maximum {MAX_TEXT_LENGTH} characters.</p>
          </section>

          <section
            className="flex min-h-[18rem] flex-col rounded-2xl border border-line bg-surface p-4 shadow-[0_1px_2px_rgba(28,25,23,0.04)]"
            aria-busy={status === 'loading'}
          >
            <div className="mb-2 flex items-center justify-between gap-3">
              <h2 className="text-sm font-medium text-ink">{outputLabel}</h2>
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={() => handleCopy()}
                  disabled={!resultText}
                  className="rounded-lg px-2 py-1 text-sm font-medium text-accent disabled:text-stone-400"
                >
                  {copied ? 'Copied' : task === 'india_connect' ? 'Copy message card' : 'Copy'}
                </button>
                <button
                  type="button"
                  onClick={handleDownload}
                  disabled={!resultText}
                  className="rounded-lg px-2 py-1 text-sm font-medium text-accent disabled:text-stone-400"
                >
                  Download
                </button>
              </div>
            </div>
            <div className="min-h-[14rem] flex-1 text-base leading-7" aria-live="polite">
              {status === 'loading' ? (
                <p className="text-muted">Working with the configured AI provider…</p>
              ) : resultText ? (
                <p className="whitespace-pre-wrap text-ink">{resultText}</p>
              ) : (
                <p className="text-stone-400">Your result will appear here.</p>
              )}
            </div>
            {result?.changes ? <p className="mt-3 text-sm text-muted">{result.changes}</p> : null}
            {result?.note ? <p className="mt-3 text-sm text-muted">{result.note}</p> : null}
            {task === 'india_connect' && result?.pronunciation_help ? (
              <div className="mt-4 border-t border-line pt-4">
                <h3 className="text-sm font-semibold">Approximate pronunciation</h3>
                <p className="mt-1 whitespace-pre-wrap text-ink">{result.pronunciation_help}</p>
                <p className="mt-1 text-xs text-muted">
                  Romanized spelling is a guide; pronunciation and spelling conventions can vary.
                </p>
              </div>
            ) : null}
            {task === 'india_connect' && result?.tone_guidance ? (
              <div className="mt-3">
                <h3 className="text-sm font-semibold">Tone note</h3>
                <p className="mt-1 whitespace-pre-wrap text-sm text-muted">{result.tone_guidance}</p>
              </div>
            ) : null}
            {result?.alternatives?.length ? (
              <div className="mt-4 space-y-3 border-t border-line pt-4">
                <h3 className="text-sm font-semibold">Alternative translations</h3>
                {result.alternatives.map((item) => (
                  <div key={`${item.text}-${item.nuance}`} className="flex items-start justify-between gap-3">
                    <div>
                      <p className="whitespace-pre-wrap text-ink">{item.text}</p>
                      <p className="text-sm text-muted">{item.nuance}</p>
                    </div>
                    <button
                      type="button"
                      onClick={() => handleCopy(item.text)}
                      className="text-sm text-accent"
                      aria-label={`Copy alternative: ${item.nuance}`}
                    >
                      Copy
                    </button>
                  </div>
                ))}
              </div>
            ) : null}
            {result?.explanation ? (
              <div className="mt-4 border-t border-line pt-4">
                <h3 className="text-sm font-semibold">AI-generated explanation</h3>
                <p className="mt-1 whitespace-pre-wrap text-sm text-muted">{result.explanation}</p>
              </div>
            ) : null}
          </section>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          <button
            type="submit"
            disabled={!canSubmit}
            className="inline-flex h-11 items-center justify-center rounded-xl bg-accent px-5 text-sm font-semibold text-white hover:bg-accent-dark disabled:cursor-not-allowed disabled:bg-stone-300 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
          >
            {status === 'loading' ? 'Working…' : TASKS.find((item) => item.id === task)?.label}
          </button>
          <button
            type="button"
            onClick={handleClear}
            className="inline-flex h-11 items-center justify-center rounded-xl border border-line bg-surface px-5 text-sm font-semibold text-ink hover:bg-paper focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
          >
            Clear
          </button>
        </div>
      </form>

      <section className="rounded-2xl border border-line bg-surface">
        <details>
          <summary className="cursor-pointer px-4 py-3 text-sm font-semibold text-ink">
            Local history ({history.length})
          </summary>
          <div className="space-y-3 border-t border-line p-4">
            <p className="text-xs text-muted">History is stored only in this browser. It is sent only when you submit a new task.</p>
            {historyError ? <p role="alert" className="text-sm text-danger">{historyError}</p> : null}
            {history.length === 0 ? <p className="text-sm text-muted">No saved results yet.</p> : null}
            {history.map((entry) => (
              <div key={entry.id} className="flex items-center justify-between gap-3 border-b border-line pb-3">
                <button type="button" onClick={() => revisit(entry)} className="min-w-0 flex-1 text-left">
                  <span className="block truncate text-sm font-medium text-ink">
                    {TASKS.find((item) => item.id === entry.task)?.label}: {entry.text}
                  </span>
                  <span className="text-xs text-muted">{new Date(entry.createdAt).toLocaleString()}</span>
                </button>
                <button
                  type="button"
                  onClick={() => deleteHistoryEntry(entry.id)}
                  className="text-sm text-danger"
                  aria-label={`Delete history item: ${entry.text.slice(0, 40)}`}
                >
                  Delete
                </button>
              </div>
            ))}
          </div>
        </details>
      </section>
    </div>
  )
}

function LanguageSelect({ id, label, value, exclude, onChange, disabled, allowAuto = false }) {
  return (
    <div className="flex flex-col gap-2">
      <label htmlFor={id} className="text-sm font-medium text-ink">{label}</label>
      <select
        id={id}
        value={value}
        disabled={disabled}
        onChange={(event) => onChange(event.target.value)}
        className="h-11 w-full rounded-xl border border-line bg-surface px-3 text-sm text-ink focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
      >
        {allowAuto ? <option value={AUTO_LANGUAGE.code}>{AUTO_LANGUAGE.label}</option> : null}
        {LANGUAGES.map((language) => (
          <option key={language.code} value={language.code} disabled={language.code === exclude}>
            {languageOptionLabel(language)}
          </option>
        ))}
      </select>
    </div>
  )
}

function SwapIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <path
        d="M7 7h11l-3-3M17 17H6l3 3"
        stroke="currentColor"
        strokeWidth="1.8"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  )
}
