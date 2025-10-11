import {
  type CSSProperties,
  type FormEvent,
  useEffect,
  useMemo,
  useRef,
  useState,
} from 'react'

import type { WidgetPosition } from '../../features/rag/api'

interface ChatPreviewProps {
  name: string
  brandColor: string
  logoUrl?: string
  welcomeMessage: string
  position: WidgetPosition
  token: string
}

interface ChatSource {
  page_url: string
  title?: string
}

interface ChatMessage {
  id: string
  role: 'assistant' | 'user'
  content: string
  sources?: ChatSource[]
}

const DEFAULT_BRAND_COLOR = '#2563eb'
const DEFAULT_WELCOME_MESSAGE = 'How can I help you today?'

const POSITION_LABELS: Record<WidgetPosition, string> = {
  BOTTOM_RIGHT: 'Bottom Right',
  BOTTOM_LEFT: 'Bottom Left',
  TOP_RIGHT: 'Top Right',
  TOP_LEFT: 'Top Left',
}

const PREVIEW_CHAT_STYLES = `
.ff-preview-root {
  color-scheme: light;
  --ff-brand-color: ${DEFAULT_BRAND_COLOR};
  --ff-brand-color-rgb: 37, 99, 235;
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  background: #f8fafc;
  color: #0f172a;
}

.ff-preview-root .ff-chat-wrapper {
  width: min(100%, 420px);
  height: min(100%, 640px);
  border-radius: 20px;
  background: #ffffff;
  box-shadow: 0 24px 48px rgba(15, 23, 42, 0.16);
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.ff-preview-root .ff-chat-header {
  background: var(--ff-brand-color);
  color: #ffffff;
  padding: 20px;
  display: flex;
  gap: 12px;
  align-items: center;
}

.ff-preview-root .ff-chat-header-logo {
  width: 40px;
  height: 40px;
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.16);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 18px;
  font-weight: 600;
}

.ff-preview-root .ff-chat-header-logo img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  border-radius: 12px;
  display: block;
}

.ff-preview-root .ff-chat-header h1 {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
}

.ff-preview-root .ff-chat-header p {
  margin: 4px 0 0;
  font-size: 13px;
  opacity: 0.85;
}

.ff-preview-root .ff-chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  background: linear-gradient(180deg, rgba(241, 245, 249, 0.6), rgba(248, 250, 252, 0.2));
}

.ff-preview-root .ff-message {
  max-width: 85%;
  padding: 12px 16px;
  border-radius: 16px;
  font-size: 14px;
  line-height: 1.5;
  white-space: pre-wrap;
  word-break: break-word;
}

.ff-preview-root .ff-message-user {
  margin-left: auto;
  background: rgba(37, 99, 235, 0.1);
  color: var(--ff-brand-color);
}

.ff-preview-root .ff-message-assistant {
  background: #ffffff;
  border: 1px solid rgba(15, 23, 42, 0.08);
  box-shadow: 0 12px 24px rgba(15, 23, 42, 0.08);
}

.ff-preview-root .ff-sources {
  margin-top: 12px;
  border-top: 1px solid rgba(15, 23, 42, 0.08);
  padding-top: 10px;
  font-size: 12px;
  color: #334155;
}

.ff-preview-root .ff-sources ul {
  margin: 8px 0 0;
  padding: 0;
  list-style: none;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.ff-preview-root .ff-sources a {
  color: var(--ff-brand-color);
  text-decoration: none;
  word-break: break-all;
}

.ff-preview-root .ff-sources a:hover {
  text-decoration: underline;
}

.ff-preview-root .ff-chat-footer {
  padding: 16px 20px 20px;
  border-top: 1px solid rgba(15, 23, 42, 0.08);
  background: #ffffff;
}

.ff-preview-root .ff-suggestions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 12px;
}

.ff-preview-root .ff-suggestion {
  border: 1px solid rgba(15, 23, 42, 0.12);
  border-radius: 999px;
  padding: 8px 12px;
  font-size: 13px;
  cursor: pointer;
  background: #ffffff;
  transition: border-color 120ms ease-in-out, background 120ms ease-in-out;
}

.ff-preview-root .ff-suggestion:hover {
  border-color: var(--ff-brand-color);
  background: rgba(var(--ff-brand-color-rgb), 0.08);
}

.ff-preview-root .ff-chat-footer form {
  display: flex;
  gap: 12px;
}

.ff-preview-root .sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border: 0;
}

.ff-preview-root .ff-chat-input {
  flex: 1;
  resize: none;
  border: 1px solid rgba(15, 23, 42, 0.12);
  border-radius: 14px;
  padding: 12px;
  font-family: inherit;
  font-size: 14px;
  line-height: 1.5;
  min-height: 48px;
  max-height: 120px;
  transition: border-color 120ms ease-in-out, box-shadow 120ms ease-in-out;
}

.ff-preview-root .ff-chat-input:focus {
  outline: none;
  border-color: var(--ff-brand-color);
  box-shadow: 0 0 0 3px rgba(var(--ff-brand-color-rgb), 0.2);
}

.ff-preview-root .ff-chat-input:disabled {
  background: rgba(241, 245, 249, 0.6);
}

.ff-preview-root .ff-chat-submit {
  background: var(--ff-brand-color);
  border: none;
  border-radius: 14px;
  color: #ffffff;
  font-weight: 600;
  padding: 0 20px;
  cursor: pointer;
  transition: opacity 120ms ease-in-out, transform 120ms ease-in-out;
}

.ff-preview-root .ff-chat-submit:disabled {
  opacity: 0.65;
  cursor: progress;
}

.ff-preview-root .ff-chat-submit:not(:disabled):hover {
  transform: translateY(-1px);
}

.ff-preview-root .ff-typing {
  margin-top: 10px;
  font-size: 13px;
  color: rgba(15, 23, 42, 0.6);
}

.ff-preview-root .ff-error-banner {
  margin: 16px 20px 0;
  padding: 10px 14px;
  border-radius: 12px;
  background: rgba(239, 68, 68, 0.1);
  color: #b91c1c;
  font-size: 13px;
}
`

const WIDGET_STYLE_BLOCK = `
.ff-widget-root {
  position: fixed;
  z-index: 2147483000;
  display: flex;
  gap: 16px;
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
}

.ff-widget-root.ff-widget-vertical-bottom {
  flex-direction: column-reverse;
}

.ff-widget-root.ff-widget-vertical-top {
  flex-direction: column;
}

.ff-widget-root.ff-widget-align-left {
  align-items: flex-start;
}

.ff-widget-root.ff-widget-align-right {
  align-items: flex-end;
}

.ff-widget-window {
  width: min(420px, calc(100vw - 32px));
  height: min(640px, calc(100vh - 96px));
  background: #ffffff;
  border-radius: 20px;
  box-shadow: 0 24px 48px rgba(15, 23, 42, 0.16);
  overflow: hidden;
  opacity: 0;
  transform: translateY(12px) scale(0.98);
  transition: opacity 160ms ease, transform 160ms ease;
  pointer-events: none;
}

.ff-widget-root.ff-widget-vertical-top .ff-widget-window {
  transform: translateY(-12px) scale(0.98);
}

.ff-widget-root.ff-widget-open .ff-widget-window {
  opacity: 1;
  transform: translateY(0) scale(1);
  pointer-events: auto;
}

.ff-widget-window-frame {
  width: 100%;
  height: 100%;
}

.ff-widget-iframe {
  width: 100%;
  height: 100%;
  border: none;
}

.ff-widget-button {
  width: 64px;
  height: 64px;
  border-radius: 32px;
  border: none;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: var(--ff-widget-brand-color, ${DEFAULT_BRAND_COLOR});
  color: #ffffff;
  cursor: pointer;
  box-shadow: 0 18px 36px rgba(var(--ff-widget-brand-color-rgb, 37, 99, 235), 0.35);
  transition: transform 150ms ease, box-shadow 150ms ease, opacity 150ms ease;
}

.ff-widget-button:hover,
.ff-widget-button:focus-visible {
  transform: translateY(-2px);
  box-shadow: 0 22px 44px rgba(var(--ff-widget-brand-color-rgb, 37, 99, 235), 0.4);
}

.ff-widget-button:focus {
  outline: none;
}

.ff-widget-button-avatar {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 34px;
  height: 34px;
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.22);
  font-size: 18px;
  font-weight: 600;
}

.ff-widget-button-avatar.ff-widget-has-image {
  background: transparent;
  padding: 0;
}

.ff-widget-button-avatar img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  border-radius: 14px;
  display: block;
}

.ff-widget-button-close {
  display: none;
  font-size: 26px;
  line-height: 1;
  font-weight: 600;
}

.ff-widget-root.ff-widget-open .ff-widget-button-close {
  display: block;
}

.ff-widget-root.ff-widget-open .ff-widget-button-avatar {
  display: none;
}

.ff-widget-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(15, 23, 42, 0.35);
  opacity: 0;
  pointer-events: none;
  transition: opacity 160ms ease;
  z-index: 2147482999;
}

.ff-widget-backdrop.ff-widget-open {
  opacity: 1;
  pointer-events: auto;
}

@media (max-width: 640px) {
  .ff-widget-window {
    width: min(100vw - 24px, 420px);
    height: min(100vh - 80px, 640px);
    border-radius: 16px;
  }

  .ff-widget-button {
    width: 56px;
    height: 56px;
    border-radius: 28px;
  }
}
`

function normalizeBrandColor(value?: string | null): string {
  if (!value) {
    return DEFAULT_BRAND_COLOR
  }
  let color = value.trim()
  if (!color) {
    return DEFAULT_BRAND_COLOR
  }
  if (color.startsWith('#')) {
    color = color.slice(1)
  }
  if (color.length === 3) {
    color = color
      .split('')
      .map((char) => char + char)
      .join('')
  }
  if (!/^([0-9a-fA-F]{6})$/.test(color)) {
    return DEFAULT_BRAND_COLOR
  }
  return `#${color.toUpperCase()}`
}

function brandColorToRgbString(hex: string): string {
  const normalized = normalizeBrandColor(hex)
  const value = normalized.slice(1)
  const numeric = parseInt(value, 16)
  const r = (numeric >> 16) & 255
  const g = (numeric >> 8) & 255
  const b = numeric & 255
  return `${r}, ${g}, ${b}`
}

function createId(): string {
  return `${Math.random().toString(36).slice(2)}${Date.now().toString(36)}`
}

function WidgetButtonPreview({
  position,
  name,
  logoUrl,
  brandColor,
  brandColorRgb,
}: {
  position: WidgetPosition
  name: string
  logoUrl?: string
  brandColor: string
  brandColorRgb: string
}) {
  const buttonStyle = {
    '--ff-widget-brand-color': brandColor,
    '--ff-widget-brand-color-rgb': brandColorRgb,
    position: 'absolute',
    bottom: position.includes('BOTTOM') ? 18 : undefined,
    top: position.includes('TOP') ? 18 : undefined,
    right: position.includes('RIGHT') ? 18 : undefined,
    left: position.includes('LEFT') ? 18 : undefined,
  } as CSSProperties

  const initial = name.trim().charAt(0) || 'A'

  return (
    <div className="flex flex-col items-center gap-4 rounded-3xl border border-slate-800/60 bg-slate-900/40 p-6 text-center text-sm text-slate-300">
      <div className="rounded-full bg-slate-800/80 px-3 py-1 text-xs uppercase tracking-wide text-slate-400">
        Widget Button Preview
      </div>
      <div className="relative h-56 w-full rounded-2xl border border-dashed border-slate-700/70 bg-slate-950/40">
        <button
          type="button"
          className="ff-widget-button"
          style={buttonStyle}
          aria-label={`${name || 'AI Assistant'} chat bubble preview`}
        >
          <span className={`ff-widget-button-avatar${logoUrl ? ' ff-widget-has-image' : ''}`}>
            {logoUrl ? <img src={logoUrl} alt="" referrerPolicy="no-referrer" /> : initial.toUpperCase()}
          </span>
          <span className="ff-widget-button-close" aria-hidden="true">
            ×
          </span>
        </button>
      </div>
      <div className="text-xs text-slate-400">Appears on {POSITION_LABELS[position]}</div>
    </div>
  )
}

export function ChatPreview({
  name,
  brandColor,
  logoUrl,
  welcomeMessage,
  position,
  token,
}: ChatPreviewProps) {
  const normalizedBrandColor = useMemo(() => normalizeBrandColor(brandColor), [brandColor])
  const brandColorRgb = useMemo(() => brandColorToRgbString(normalizedBrandColor), [normalizedBrandColor])

  const [messages, setMessages] = useState<ChatMessage[]>(() => [
    {
      id: createId(),
      role: 'assistant',
      content: welcomeMessage || DEFAULT_WELCOME_MESSAGE,
    },
  ])
  const [inputValue, setInputValue] = useState('')
  const [suggestions, setSuggestions] = useState<string[]>([])
  const [isSending, setIsSending] = useState(false)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)
  const hasInteractedRef = useRef(false)
  const messagesRef = useRef<HTMLDivElement | null>(null)

  useEffect(() => {
    if (hasInteractedRef.current) {
      return
    }
    setMessages([
      {
        id: createId(),
        role: 'assistant',
        content: welcomeMessage || DEFAULT_WELCOME_MESSAGE,
      },
    ])
  }, [welcomeMessage])

  useEffect(() => {
    if (!messagesRef.current) {
      return
    }
    messagesRef.current.scrollTo({ top: messagesRef.current.scrollHeight, behavior: 'smooth' })
  }, [messages])

  const previewStyle = useMemo(() => {
    return {
      '--ff-brand-color': normalizedBrandColor,
      '--ff-brand-color-rgb': brandColorRgb,
    } as CSSProperties
  }, [brandColorRgb, normalizedBrandColor])

  async function handleSend(rawMessage: string) {
    const message = rawMessage.trim()
    if (!message || !token || isSending) {
      return
    }

    setInputValue('')
    setErrorMessage(null)
    setSuggestions([])
    hasInteractedRef.current = true

    const history = messages.map((entry) => ({
      role: entry.role,
      content: entry.content,
    }))

    const userMessage: ChatMessage = {
      id: createId(),
      role: 'user',
      content: message,
    }

    setMessages((prev) => [...prev, userMessage])
    setIsSending(true)

    try {
      const response = await fetch('/v1/rag/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Embed-Token': token,
        },
        body: JSON.stringify({
          question: message,
          conversation_history: history,
        }),
      })

      if (!response.ok) {
        throw new Error(`Failed to fetch response (${response.status})`)
      }

      const payload = await response.json()
      const assistantMessage: ChatMessage = {
        id: createId(),
        role: 'assistant',
        content: typeof payload.answer === 'string' ? payload.answer : DEFAULT_WELCOME_MESSAGE,
        sources: Array.isArray(payload.sources)
          ? (payload.sources as ChatSource[]).filter((source) => Boolean(source && source.page_url))
          : undefined,
      }
      setMessages((prev) => [...prev, assistantMessage])
      if (Array.isArray(payload.suggested_questions)) {
        setSuggestions(
          payload.suggested_questions.filter((question: unknown): question is string => typeof question === 'string' && question.trim().length > 0),
        )
      }
    } catch (error) {
      console.error(error)
      setErrorMessage('Sorry, something went wrong. Please try again.')
      setMessages((prev) => [
        ...prev,
        {
          id: createId(),
          role: 'assistant',
          content: 'Sorry, something went wrong. Please try again.',
        },
      ])
    } finally {
      setIsSending(false)
    }
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    handleSend(inputValue)
  }

  return (
    <div className="flex flex-col gap-4">
      <style>{PREVIEW_CHAT_STYLES}</style>
      <style>{WIDGET_STYLE_BLOCK}</style>
      <div className="text-sm text-slate-400">
        Live preview of your embedded assistant. Updates instantly as you tweak the settings.
      </div>
      <div className="grid gap-6 lg:grid-cols-[minmax(0,460px)_280px]">
        <div className="rounded-3xl border border-slate-800/60 bg-slate-900/40 p-6 shadow-lg shadow-slate-950/30">
          <div className="ff-preview-root" style={previewStyle}>
            <div className="ff-chat-wrapper">
              <header className="ff-chat-header">
                <div className="ff-chat-header-logo">
                  {logoUrl ? (
                    <img src={logoUrl} alt={`${name || 'AI Assistant'} logo`} referrerPolicy="no-referrer" />
                  ) : (
                    (name || 'AI')[0]?.toUpperCase() || 'A'
                  )}
                </div>
                <div>
                  <h1>{name || 'AI Assistant'}</h1>
                  <p>{welcomeMessage || DEFAULT_WELCOME_MESSAGE}</p>
                </div>
              </header>
              {errorMessage && <div className="ff-error-banner">{errorMessage}</div>}
              <main className="ff-chat-messages" ref={messagesRef} role="log" aria-live="polite">
                {messages.map((message) => (
                  <div
                    key={message.id}
                    className={`ff-message ${message.role === 'user' ? 'ff-message-user' : 'ff-message-assistant'}`}
                  >
                    {message.content}
                    {message.sources && message.sources.length > 0 && (
                      <div className="ff-sources">
                        <div>Sources</div>
                        <ul>
                          {message.sources.map((source) => (
                            <li key={source.page_url}>
                              <a href={source.page_url} target="_blank" rel="noopener noreferrer">
                                {source.page_url}
                              </a>
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>
                ))}
              </main>
              <div className="ff-chat-footer">
                {suggestions.length > 0 && (
                  <div className="ff-suggestions">
                    {suggestions.map((suggestion) => (
                      <button
                        key={suggestion}
                        type="button"
                        className="ff-suggestion"
                        onClick={() => handleSend(suggestion)}
                        disabled={isSending}
                      >
                        {suggestion}
                      </button>
                    ))}
                  </div>
                )}
                <form onSubmit={handleSubmit} autoComplete="off">
                  <label htmlFor="ff-preview-input" className="sr-only">
                    Message
                  </label>
                  <textarea
                    id="ff-preview-input"
                    className="ff-chat-input"
                    placeholder="Type your message…"
                    value={inputValue}
                    onChange={(event) => setInputValue(event.target.value)}
                    disabled={isSending}
                    required
                  />
                  <button type="submit" className="ff-chat-submit" disabled={isSending || !inputValue.trim()}>
                    {isSending ? 'Sending…' : 'Send'}
                  </button>
                </form>
                <div className="ff-typing" hidden={!isSending}>
                  Thinking…
                </div>
              </div>
            </div>
          </div>
        </div>
        <WidgetButtonPreview
          position={position}
          name={name || 'AI Assistant'}
          logoUrl={logoUrl}
          brandColor={normalizedBrandColor}
          brandColorRgb={brandColorRgb}
        />
      </div>
    </div>
  )
}

export default ChatPreview
