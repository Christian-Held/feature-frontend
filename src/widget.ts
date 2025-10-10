(function () {
  interface WidgetConfig {
    token: string;
    baseUrl: string;
  }

  type WidgetWindow = typeof window & { FeatureFrontendWidget?: WidgetController };

  type WidgetState = 'closed' | 'open';

  interface WidgetController {
    open: () => void;
    close: () => void;
    toggle: () => void;
    getState: () => WidgetState;
    getToken: () => string;
  }

  function dispatchWidgetEvent(name: string, detail: Record<string, unknown>): void {
    window.dispatchEvent(new CustomEvent(`feature-frontend-widget:${name}`, { detail }));
  }

  function ensureBodyReady(callback: () => void): void {
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', callback, { once: true });
      return;
    }
    callback();
  }

  function resolveScriptElement(): HTMLScriptElement | null {
    const current = document.currentScript as HTMLScriptElement | null;
    if (current) {
      return current;
    }

    const scripts = Array.from(document.querySelectorAll('script')) as HTMLScriptElement[];
    return scripts.find((script) => script.dataset.embedToken !== undefined) ?? null;
  }

  function readConfig(): WidgetConfig | null {
    const scriptEl = resolveScriptElement();
    if (!scriptEl || !scriptEl.src) {
      console.error('[feature-frontend] Unable to locate widget script tag.');
      return null;
    }

    const token = scriptEl.dataset.embedToken;
    if (!token) {
      console.error('[feature-frontend] Missing data-embed-token attribute.');
      return null;
    }

    let scriptUrl: URL;
    try {
      scriptUrl = new URL(scriptEl.src, window.location.href);
    } catch (error) {
      console.error('[feature-frontend] Invalid widget script URL.', error);
      return null;
    }

    if (scriptUrl.protocol !== 'https:' && scriptUrl.hostname !== 'localhost') {
      console.error('[feature-frontend] Widget must be served over HTTPS.');
      return null;
    }

    return {
      token,
      baseUrl: scriptUrl.origin,
    };
  }

  function createStyles(): HTMLStyleElement {
    const style = document.createElement('style');
    style.textContent = `
      .ff-widget-button {
        position: fixed;
        right: 24px;
        bottom: 24px;
        z-index: 2147483000;
        width: 56px;
        height: 56px;
        border-radius: 50%;
        background: linear-gradient(135deg, #6366f1, #8b5cf6);
        color: #ffffff;
        border: none;
        box-shadow: 0 10px 25px rgba(99, 102, 241, 0.35);
        cursor: pointer;
        display: flex;
        align-items: center;
        justify-content: center;
        font-family: 'Inter', system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
        font-size: 24px;
        transition: transform 150ms ease-in-out, box-shadow 150ms ease-in-out;
      }

      .ff-widget-button:hover,
      .ff-widget-button:focus {
        outline: none;
        transform: scale(1.04);
        box-shadow: 0 12px 32px rgba(99, 102, 241, 0.45);
      }

      .ff-widget-overlay {
        position: fixed;
        inset: 0;
        background: rgba(17, 24, 39, 0.45);
        display: none;
        align-items: center;
        justify-content: center;
        padding: 24px;
        z-index: 2147482999;
      }

      .ff-widget-overlay.ff-widget-open {
        display: flex;
      }

      .ff-widget-frame-container {
        width: min(420px, 100%);
        height: min(640px, 100%);
        background: #ffffff;
        border-radius: 18px;
        overflow: hidden;
        box-shadow: 0 24px 48px rgba(15, 23, 42, 0.25);
        transform: translateY(16px);
        transition: transform 160ms ease-in-out;
      }

      .ff-widget-overlay.ff-widget-open .ff-widget-frame-container {
        transform: translateY(0);
      }

      .ff-widget-iframe {
        width: 100%;
        height: 100%;
        border: none;
      }

      @media (max-width: 640px) {
        .ff-widget-button {
          right: 16px;
          bottom: 16px;
        }

        .ff-widget-frame-container {
          width: 100%;
          height: 100%;
          border-radius: 0;
        }
      }
    `;
    return style;
  }

  function createButton(): HTMLButtonElement {
    const button = document.createElement('button');
    button.className = 'ff-widget-button';
    button.type = 'button';
    button.title = 'Open AI Assistant chat';
    button.setAttribute('aria-label', 'Open AI Assistant chat');
    button.setAttribute('aria-expanded', 'false');
    button.textContent = '💬';
    return button;
  }

  function createOverlay(embedUrl: string, onRequestClose: () => void): HTMLDivElement {
    const overlay = document.createElement('div');
    overlay.className = 'ff-widget-overlay';

    const frameWrapper = document.createElement('div');
    frameWrapper.className = 'ff-widget-frame-container';

    const iframe = document.createElement('iframe');
    iframe.className = 'ff-widget-iframe';
    iframe.src = embedUrl;
    iframe.allow = 'camera; microphone; clipboard-write';
    iframe.setAttribute('sandbox', 'allow-forms allow-scripts allow-same-origin');

    frameWrapper.appendChild(iframe);
    overlay.appendChild(frameWrapper);

    overlay.addEventListener('click', (event) => {
      if (event.target === overlay) {
        onRequestClose();
      }
    });

    return overlay;
  }

  function initialize(): void {
    if ((window as WidgetWindow).FeatureFrontendWidget) {
      return;
    }

    const config = readConfig();
    if (!config) {
      return;
    }

    ensureBodyReady(() => {
      const styles = createStyles();
      const button = createButton();
      const embedUrl = `${config.baseUrl}/embed/chat?token=${encodeURIComponent(config.token)}`;
      let state: WidgetState = 'closed';

      const overlay = createOverlay(embedUrl, () => {
        close();
      });

      function open(): void {
        if (state === 'open') {
          return;
        }
        overlay.classList.add('ff-widget-open');
        button.setAttribute('aria-expanded', 'true');
        state = 'open';
        dispatchWidgetEvent('open', {});
      }

      function close(): void {
        if (state === 'closed') {
          return;
        }
        overlay.classList.remove('ff-widget-open');
        button.setAttribute('aria-expanded', 'false');
        state = 'closed';
        dispatchWidgetEvent('close', {});
      }

      function toggle(): void {
        if (state === 'open') {
          close();
        } else {
          open();
        }
      }

      button.addEventListener('click', () => {
        toggle();
      });

      document.head.appendChild(styles);
      document.body.appendChild(button);
      document.body.appendChild(overlay);

      const controller: WidgetController = {
        open,
        close,
        toggle,
        getState: () => state,
        getToken: () => config.token,
      };

      (window as WidgetWindow).FeatureFrontendWidget = controller;
      dispatchWidgetEvent('ready', { token: config.token });
    });
  }

  initialize();
})();
