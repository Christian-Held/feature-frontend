import type { CSSProperties } from 'react'

import type { WidgetPosition } from '../../features/rag/api'

interface ChatPreviewProps {
  name: string
  brandColor: string
  logoUrl?: string
  welcomeMessage: string
  position: WidgetPosition
}

const POSITION_LABELS: Record<WidgetPosition, string> = {
  BOTTOM_RIGHT: 'Bottom Right',
  BOTTOM_LEFT: 'Bottom Left',
  TOP_RIGHT: 'Top Right',
  TOP_LEFT: 'Top Left',
}

const SAMPLE_USER_MESSAGE = 'Can you tell me more about your services?'
const SAMPLE_ASSISTANT_MESSAGE = 'Absolutely! I can highlight key features, pricing, and more—just ask.'

export function ChatPreview({
  name,
  brandColor,
  logoUrl,
  welcomeMessage,
  position,
}: ChatPreviewProps) {
  const headerStyle: CSSProperties = {
    background: brandColor || '#2563eb',
  }

  const buttonStyle: CSSProperties = {
    background: brandColor || '#2563eb',
    boxShadow: '0 12px 30px rgba(59, 130, 246, 0.3)',
  }

  return (
    <div className="flex flex-col gap-4">
      <div className="text-sm text-slate-400">
        Live preview of your embedded assistant. Updates instantly as you tweak the settings.
      </div>
      <div className="grid gap-6 lg:grid-cols-[1fr_280px]">
        <div className="flex flex-col gap-4">
          <div className="rounded-3xl border border-slate-800/60 bg-slate-900/40 p-6 shadow-lg shadow-slate-950/30">
            <div className="overflow-hidden rounded-3xl bg-white text-slate-900">
              <header style={headerStyle} className="flex items-center gap-3 px-5 py-4 text-white">
                <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-white/20 text-lg font-semibold">
                  {logoUrl ? (
                    <img src={logoUrl} alt={`${name} logo`} className="h-full w-full rounded-2xl object-cover" />
                  ) : (
                    (name || 'AI')[0] ?? 'A'
                  )}
                </div>
                <div>
                  <div className="text-base font-semibold leading-tight">{name || 'AI Assistant'}</div>
                  <div className="text-sm opacity-80">{welcomeMessage || 'How can I help you today?'}</div>
                </div>
              </header>
              <div className="flex flex-col gap-3 bg-slate-50 px-5 py-4 text-sm">
                <div className="mr-auto max-w-[85%] rounded-2xl border border-slate-200 bg-white px-4 py-3 shadow-sm">
                  {welcomeMessage || 'Hello! Ask me anything about your product.'}
                </div>
                <div className="ml-auto max-w-[85%] rounded-2xl bg-blue-100/70 px-4 py-3 text-blue-700">
                  {SAMPLE_USER_MESSAGE}
                </div>
                <div className="mr-auto max-w-[85%] rounded-2xl border border-slate-200 bg-white px-4 py-3 shadow-sm">
                  {SAMPLE_ASSISTANT_MESSAGE}
                </div>
              </div>
              <footer className="border-t border-slate-200/70 bg-white px-5 py-4 text-xs text-slate-500">
                Powered by Feature. Responses adapt to your website content.
              </footer>
            </div>
          </div>
        </div>
        <div className="flex flex-col items-center gap-4 rounded-3xl border border-slate-800/60 bg-slate-900/40 p-6 text-center text-sm text-slate-300">
          <div className="rounded-full bg-slate-800/80 px-3 py-1 text-xs uppercase tracking-wide text-slate-400">
            Widget Button Preview
          </div>
          <div className="relative h-56 w-full rounded-2xl border border-dashed border-slate-700/70 bg-slate-950/40">
            <div
              className="absolute h-14 w-14 rounded-full text-2xl text-white"
              style={{
                ...buttonStyle,
                bottom: position.includes('BOTTOM') ? 18 : undefined,
                top: position.includes('TOP') ? 18 : undefined,
                right: position.includes('RIGHT') ? 18 : undefined,
                left: position.includes('LEFT') ? 18 : undefined,
              }}
            >
              <div className="flex h-full w-full items-center justify-center">💬</div>
            </div>
          </div>
          <div className="text-xs text-slate-400">Appears on {POSITION_LABELS[position]}</div>
        </div>
      </div>
    </div>
  )
}

export default ChatPreview
