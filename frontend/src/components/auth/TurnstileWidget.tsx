import { useEffect, useRef } from 'react'

interface TurnstileWidgetProps {
  siteKey: string
  onVerify: (token: string) => void
  onError?: () => void
  onExpire?: () => void
}

declare global {
  interface Window {
    turnstile?: {
      render: (
        container: HTMLElement,
        options: {
          sitekey: string
          callback: (token: string) => void
          'error-callback'?: () => void
          'expired-callback'?: () => void
          theme?: 'light' | 'dark'
        }
      ) => string
      reset: (widgetId: string) => void
      remove: (widgetId: string) => void
    }
  }
}

export function TurnstileWidget({
  siteKey,
  onVerify,
  onError,
  onExpire,
}: TurnstileWidgetProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const widgetIdRef = useRef<string | null>(null)

  useEffect(() => {
    if (!containerRef.current) return

    let scriptElement: HTMLScriptElement | null = null

    const loadTurnstile = () => {
      if (window.turnstile && containerRef.current) {
        // Turnstile already loaded
        widgetIdRef.current = window.turnstile.render(containerRef.current, {
          sitekey: siteKey,
          callback: onVerify,
          'error-callback': onError,
          'expired-callback': onExpire,
          theme: 'dark',
        })
      } else {
        // Load Turnstile script
        scriptElement = document.createElement('script')
        scriptElement.src = 'https://challenges.cloudflare.com/turnstile/v0/api.js'
        scriptElement.async = true
        scriptElement.defer = true

        scriptElement.onload = () => {
          if (window.turnstile && containerRef.current) {
            widgetIdRef.current = window.turnstile.render(containerRef.current, {
              sitekey: siteKey,
              callback: onVerify,
              'error-callback': onError,
              'expired-callback': onExpire,
              theme: 'dark',
            })
          }
        }

        document.body.appendChild(scriptElement)
      }
    }

    loadTurnstile()

    return () => {
      // Cleanup
      if (window.turnstile && widgetIdRef.current) {
        try {
          window.turnstile.remove(widgetIdRef.current)
        } catch (e) {
          // Ignore cleanup errors
        }
      }
      if (scriptElement && document.body.contains(scriptElement)) {
        document.body.removeChild(scriptElement)
      }
    }
  }, [siteKey, onVerify, onError, onExpire])

  return <div ref={containerRef} className="flex justify-center" />
}
