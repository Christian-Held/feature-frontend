(function () {
  'use strict'

  var DEFAULT_BRAND_COLOR = '#2563eb'
  var STYLE_TEMPLATE = "\n    .ff-widget-root {\n      position: fixed;\n      z-index: 2147483000;\n      display: flex;\n      gap: 16px;\n      font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;\n    }\n\n    .ff-widget-root.ff-widget-vertical-bottom {\n      flex-direction: column-reverse;\n    }\n\n    .ff-widget-root.ff-widget-vertical-top {\n      flex-direction: column;\n    }\n\n    .ff-widget-root.ff-widget-align-left {\n      align-items: flex-start;\n    }\n\n    .ff-widget-root.ff-widget-align-right {\n      align-items: flex-end;\n    }\n\n    .ff-widget-window {\n      width: min(420px, calc(100vw - 32px));\n      height: min(640px, calc(100vh - 96px));\n      background: #ffffff;\n      border-radius: 20px;\n      box-shadow: 0 24px 48px rgba(15, 23, 42, 0.16);\n      overflow: hidden;\n      opacity: 0;\n      transform: translateY(12px) scale(0.98);\n      transition: opacity 160ms ease, transform 160ms ease;\n      pointer-events: none;\n    }\n\n    .ff-widget-root.ff-widget-vertical-top .ff-widget-window {\n      transform: translateY(-12px) scale(0.98);\n    }\n\n    .ff-widget-root.ff-widget-open .ff-widget-window {\n      opacity: 1;\n      transform: translateY(0) scale(1);\n      pointer-events: auto;\n    }\n\n    .ff-widget-window-frame {\n      width: 100%;\n      height: 100%;\n    }\n\n    .ff-widget-iframe {\n      width: 100%;\n      height: 100%;\n      border: none;\n    }\n\n    .ff-widget-button {\n      width: 64px;\n      height: 64px;\n      border-radius: 32px;\n      border: none;\n      display: inline-flex;\n      align-items: center;\n      justify-content: center;\n      background: var(--ff-widget-brand-color, #2563eb);\n      color: #ffffff;\n      cursor: pointer;\n      box-shadow: 0 18px 36px rgba(var(--ff-widget-brand-color-rgb, 37, 99, 235), 0.35);\n      transition: transform 150ms ease, box-shadow 150ms ease, opacity 150ms ease;\n    }\n\n    .ff-widget-button:hover,\n    .ff-widget-button:focus-visible {\n      transform: translateY(-2px);\n      box-shadow: 0 22px 44px rgba(var(--ff-widget-brand-color-rgb, 37, 99, 235), 0.4);\n    }\n\n    .ff-widget-button:focus {\n      outline: none;\n    }\n\n    .ff-widget-button-avatar {\n      display: flex;\n      align-items: center;\n      justify-content: center;\n      width: 34px;\n      height: 34px;\n      border-radius: 14px;\n      background: rgba(255, 255, 255, 0.22);\n      font-size: 18px;\n      font-weight: 600;\n    }\n\n    .ff-widget-button-avatar.ff-widget-has-image {\n      background: transparent;\n      padding: 0;\n    }\n\n    .ff-widget-button-avatar img {\n      width: 100%;\n      height: 100%;\n      object-fit: cover;\n      border-radius: 14px;\n      display: block;\n    }\n\n    .ff-widget-button-close {\n      display: none;\n      font-size: 26px;\n      line-height: 1;\n      font-weight: 600;\n    }\n\n    .ff-widget-root.ff-widget-open .ff-widget-button-close {\n      display: block;\n    }\n\n    .ff-widget-root.ff-widget-open .ff-widget-button-avatar {\n      display: none;\n    }\n\n    .ff-widget-backdrop {\n      position: fixed;\n      inset: 0;\n      background: rgba(15, 23, 42, 0.35);\n      opacity: 0;\n      pointer-events: none;\n      transition: opacity 160ms ease;\n      z-index: 2147482999;\n    }\n\n    .ff-widget-backdrop.ff-widget-open {\n      opacity: 1;\n      pointer-events: auto;\n    }\n\n    @media (max-width: 640px) {\n      .ff-widget-window {\n        width: min(100vw - 24px, 420px);\n        height: min(100vh - 80px, 640px);\n        border-radius: 16px;\n      }\n\n      .ff-widget-button {\n        width: 56px;\n        height: 56px;\n        border-radius: 28px;\n      }\n    }\n  "

  function dispatchWidgetEvent(name, detail) {
    try {
      window.dispatchEvent(new CustomEvent('feature-frontend-widget:' + name, { detail: detail }))
    } catch (error) {
      console.error('[feature-frontend] Failed to dispatch widget event', error)
    }
  }

  function ensureBodyReady(callback) {
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', callback, { once: true })
      return
    }
    callback()
  }

  function resolveScriptElement() {
    if (document.currentScript) {
      return document.currentScript
    }
    var scripts = Array.prototype.slice.call(document.querySelectorAll('script[data-embed-token]'))
    return scripts.length ? scripts[scripts.length - 1] : null
  }

  function readBootstrapConfig() {
    var scriptEl = resolveScriptElement()
    if (!scriptEl || !scriptEl.src) {
      console.error('[feature-frontend] Unable to locate widget script tag.')
      return null
    }
    var token = scriptEl.dataset ? scriptEl.dataset.embedToken : null
    if (!token) {
      console.error('[feature-frontend] Missing data-embed-token attribute.')
      return null
    }
    var scriptUrl
    try {
      scriptUrl = new URL(scriptEl.src, window.location.href)
    } catch (error) {
      console.error('[feature-frontend] Invalid widget script URL.', error)
      return null
    }
    if (scriptUrl.protocol !== 'https:' && scriptUrl.hostname !== 'localhost') {
      console.error('[feature-frontend] Widget must be served over HTTPS.')
      return null
    }
    return {
      token: token,
      baseUrl: scriptUrl.origin,
    }
  }

  function normalizeColor(color) {
    if (typeof color !== 'string') {
      return DEFAULT_BRAND_COLOR
    }
    var value = color.trim()
    if (!value) {
      return DEFAULT_BRAND_COLOR
    }
    if (value[0] === '#') {
      value = value.slice(1)
    }
    if (value.length === 3) {
      value = value[0] + value[0] + value[1] + value[1] + value[2] + value[2]
    }
    if (!/^([0-9a-fA-F]{6})$/.test(value)) {
      return DEFAULT_BRAND_COLOR
    }
    return '#' + value.toUpperCase()
  }

  function hexToRgbString(hex) {
    var normalized = normalizeColor(hex)
    var value = normalized.slice(1)
    var bigint = parseInt(value, 16)
    var r = (bigint >> 16) & 255
    var g = (bigint >> 8) & 255
    var b = bigint & 255
    return r + ', ' + g + ', ' + b
  }

  function fetchEmbedConfig(baseUrl, token) {
    var url = baseUrl + '/embed/config?token=' + encodeURIComponent(token)
    return fetch(url, {
      method: 'GET',
      credentials: 'omit',
      cache: 'no-store',
      headers: {
        Accept: 'application/json',
      },
    }).then(function (response) {
      if (!response.ok) {
        throw new Error('Failed to load embed configuration (' + response.status + ')')
      }
      return response.json()
    })
  }

  function ensureStyleElement() {
    if (document.querySelector('style[data-ff-widget-style="true"]')) {
      return
    }
    var style = document.createElement('style')
    style.setAttribute('data-ff-widget-style', 'true')
    style.textContent = STYLE_TEMPLATE
    document.head.appendChild(style)
  }

  function applyPosition(root, position) {
    var offset = 24
    root.style.top = ''
    root.style.bottom = ''
    root.style.left = ''
    root.style.right = ''
    root.classList.remove('ff-widget-vertical-top', 'ff-widget-vertical-bottom', 'ff-widget-align-left', 'ff-widget-align-right')

    var normalized = typeof position === 'string' ? position.toUpperCase() : 'BOTTOM_RIGHT'
    var vertical = normalized.indexOf('TOP') !== -1 ? 'TOP' : 'BOTTOM'
    var horizontal = normalized.indexOf('LEFT') !== -1 ? 'LEFT' : 'RIGHT'

    if (vertical === 'TOP') {
      root.style.top = offset + 'px'
      root.classList.add('ff-widget-vertical-top')
    } else {
      root.style.bottom = offset + 'px'
      root.classList.add('ff-widget-vertical-bottom')
    }

    if (horizontal === 'LEFT') {
      root.style.left = offset + 'px'
      root.classList.add('ff-widget-align-left')
    } else {
      root.style.right = offset + 'px'
      root.classList.add('ff-widget-align-right')
    }
  }

  function buildButtonContents(button, config) {
    var avatar = document.createElement('span')
    avatar.className = 'ff-widget-button-avatar'
    var name = typeof config.name === 'string' && config.name.trim() ? config.name.trim() : 'AI'

    if (config.logo_url) {
      avatar.classList.add('ff-widget-has-image')
      var img = document.createElement('img')
      img.src = config.logo_url
      img.alt = ''
      img.decoding = 'async'
      img.loading = 'lazy'
      img.referrerPolicy = 'no-referrer'
      avatar.appendChild(img)
    } else {
      var initial = name.charAt(0)
      avatar.textContent = initial ? initial.toUpperCase() : 'A'
    }

    var closeIcon = document.createElement('span')
    closeIcon.className = 'ff-widget-button-close'
    closeIcon.setAttribute('aria-hidden', 'true')
    closeIcon.textContent = '×'

    button.appendChild(avatar)
    button.appendChild(closeIcon)
  }

  function initializeWidget(bootstrap, config) {
    ensureStyleElement()

    var brandColor = normalizeColor(config.brand_color || DEFAULT_BRAND_COLOR)
    var brandColorRgb = hexToRgbString(brandColor)

    var root = document.createElement('div')
    root.className = 'ff-widget-root'
    root.style.setProperty('--ff-widget-brand-color', brandColor)
    root.style.setProperty('--ff-widget-brand-color-rgb', brandColorRgb)
    applyPosition(root, config.position || 'BOTTOM_RIGHT')

    var widgetWindow = document.createElement('div')
    widgetWindow.className = 'ff-widget-window'
    var frameWrapper = document.createElement('div')
    frameWrapper.className = 'ff-widget-window-frame'
    var iframe = document.createElement('iframe')
    iframe.className = 'ff-widget-iframe'
    iframe.src = bootstrap.baseUrl + '/embed/chat?token=' + encodeURIComponent(bootstrap.token)
    iframe.allow = 'camera; microphone; clipboard-write'
    iframe.setAttribute('sandbox', 'allow-forms allow-scripts allow-same-origin')
    frameWrapper.appendChild(iframe)
    widgetWindow.appendChild(frameWrapper)

    var button = document.createElement('button')
    button.type = 'button'
    button.className = 'ff-widget-button'
    button.setAttribute('aria-haspopup', 'dialog')
    button.setAttribute('aria-expanded', 'false')
    button.setAttribute('aria-label', (config.name || 'AI Assistant') + ' chat')
    buildButtonContents(button, config)

    root.appendChild(widgetWindow)
    root.appendChild(button)

    var backdrop = document.createElement('div')
    backdrop.className = 'ff-widget-backdrop'

    var state = 'closed'

    function open() {
      if (state === 'open') {
        return
      }
      state = 'open'
      root.classList.add('ff-widget-open')
      backdrop.classList.add('ff-widget-open')
      button.setAttribute('aria-expanded', 'true')
      dispatchWidgetEvent('open', { token: bootstrap.token })
    }

    function close() {
      if (state === 'closed') {
        return
      }
      state = 'closed'
      root.classList.remove('ff-widget-open')
      backdrop.classList.remove('ff-widget-open')
      button.setAttribute('aria-expanded', 'false')
      dispatchWidgetEvent('close', { token: bootstrap.token })
    }

    function toggle() {
      if (state === 'open') {
        close()
      } else {
        open()
      }
    }

    button.addEventListener('click', toggle)
    backdrop.addEventListener('click', close)
    document.addEventListener('keydown', function (event) {
      if (event.key === 'Escape') {
        close()
      }
    })

    ensureBodyReady(function () {
      document.body.appendChild(backdrop)
      document.body.appendChild(root)
      dispatchWidgetEvent('ready', { token: bootstrap.token, config: config })
    })

    var controller = {
      open: open,
      close: close,
      toggle: toggle,
      getState: function () {
        return state
      },
      getToken: function () {
        return bootstrap.token
      },
      getConfig: function () {
        return Object.assign({}, config, {
          brand_color: brandColor,
          brand_color_rgb: brandColorRgb,
        })
      },
    }

    window.FeatureFrontendWidget = controller
  }

  function initialize() {
    if (window.FeatureFrontendWidget) {
      return
    }
    var bootstrap = readBootstrapConfig()
    if (!bootstrap) {
      return
    }

    fetchEmbedConfig(bootstrap.baseUrl, bootstrap.token)
      .then(function (config) {
        initializeWidget(bootstrap, config || {})
      })
      .catch(function (error) {
        console.error('[feature-frontend] Failed to initialise widget.', error)
        dispatchWidgetEvent('error', {
          token: bootstrap.token,
          reason: 'config_fetch_failed',
          message: error && error.message ? error.message : 'Unknown error',
        })
      })
  }

  initialize()
})()
