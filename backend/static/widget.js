(function () {
  'use strict';

  function dispatchWidgetEvent(name, detail) {
    window.dispatchEvent(new CustomEvent("feature-frontend-widget:".concat(name), { detail: detail }));
  }

  function ensureBodyReady(callback) {
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', callback, { once: true });
      return;
    }
    callback();
  }

  function resolveScriptElement() {
    var current = document.currentScript;
    if (current) {
      return current;
    }
    var scripts = Array.prototype.slice.call(document.querySelectorAll('script'));
    for (var i = 0; i < scripts.length; i += 1) {
      if (scripts[i].dataset && scripts[i].dataset.embedToken !== undefined) {
        return scripts[i];
      }
    }
    return null;
  }

  function readConfig() {
    var scriptEl = resolveScriptElement();
    if (!scriptEl || !scriptEl.src) {
      console.error('[feature-frontend] Unable to locate widget script tag.');
      return null;
    }
    var token = scriptEl.dataset ? scriptEl.dataset.embedToken : null;
    if (!token) {
      console.error('[feature-frontend] Missing data-embed-token attribute.');
      return null;
    }
    var scriptUrl;
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
      token: token,
      baseUrl: scriptUrl.origin,
    };
  }

  function createStyles() {
    var style = document.createElement('style');
    style.textContent = "\n      .ff-widget-button {\n        position: fixed;\n        right: 24px;\n        bottom: 24px;\n        z-index: 2147483000;\n        width: 56px;\n        height: 56px;\n        border-radius: 50%;\n        background: linear-gradient(135deg, #6366f1, #8b5cf6);\n        color: #ffffff;\n        border: none;\n        box-shadow: 0 10px 25px rgba(99, 102, 241, 0.35);\n        cursor: pointer;\n        display: flex;\n        align-items: center;\n        justify-content: center;\n        font-family: 'Inter', system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;\n        font-size: 24px;\n        transition: transform 150ms ease-in-out, box-shadow 150ms ease-in-out;\n      }\n\n      .ff-widget-button:hover,\n      .ff-widget-button:focus {\n        outline: none;\n        transform: scale(1.04);\n        box-shadow: 0 12px 32px rgba(99, 102, 241, 0.45);\n      }\n\n      .ff-widget-overlay {\n        position: fixed;\n        inset: 0;\n        background: rgba(17, 24, 39, 0.45);\n        display: none;\n        align-items: center;\n        justify-content: center;\n        padding: 24px;\n        z-index: 2147482999;\n      }\n\n      .ff-widget-overlay.ff-widget-open {\n        display: flex;\n      }\n\n      .ff-widget-frame-container {\n        width: min(420px, 100%);\n        height: min(640px, 100%);\n        background: #ffffff;\n        border-radius: 18px;\n        overflow: hidden;\n        box-shadow: 0 24px 48px rgba(15, 23, 42, 0.25);\n        transform: translateY(16px);\n        transition: transform 160ms ease-in-out;\n      }\n\n      .ff-widget-overlay.ff-widget-open .ff-widget-frame-container {\n        transform: translateY(0);\n      }\n\n      .ff-widget-iframe {\n        width: 100%;\n        height: 100%;\n        border: none;\n      }\n\n      @media (max-width: 640px) {\n        .ff-widget-button {\n          right: 16px;\n          bottom: 16px;\n        }\n\n        .ff-widget-frame-container {\n          width: 100%;\n          height: 100%;\n          border-radius: 0;\n        }\n      }\n    ";
    return style;
  }

  function createButton() {
    var button = document.createElement('button');
    button.className = 'ff-widget-button';
    button.type = 'button';
    button.title = 'Open AI Assistant chat';
    button.setAttribute('aria-label', 'Open AI Assistant chat');
    button.setAttribute('aria-expanded', 'false');
    button.textContent = '💬';
    return button;
  }

  function createOverlay(embedUrl, onRequestClose) {
    var overlay = document.createElement('div');
    overlay.className = 'ff-widget-overlay';
    var frameWrapper = document.createElement('div');
    frameWrapper.className = 'ff-widget-frame-container';
    var iframe = document.createElement('iframe');
    iframe.className = 'ff-widget-iframe';
    iframe.src = embedUrl;
    iframe.allow = 'camera; microphone; clipboard-write';
    iframe.setAttribute('sandbox', 'allow-forms allow-scripts allow-same-origin');
    frameWrapper.appendChild(iframe);
    overlay.appendChild(frameWrapper);
    overlay.addEventListener('click', function (event) {
      if (event.target === overlay) {
        onRequestClose();
      }
    });
    return overlay;
  }

  function initialize() {
    if (window.FeatureFrontendWidget) {
      return;
    }
    var config = readConfig();
    if (!config) {
      return;
    }
    ensureBodyReady(function () {
      var styles = createStyles();
      var button = createButton();
      var state = 'closed';
      var embedUrl = config.baseUrl + '/embed/chat?token=' + encodeURIComponent(config.token);
      var overlay = createOverlay(embedUrl, close);
      function open() {
        if (state === 'open') {
          return;
        }
        overlay.classList.add('ff-widget-open');
        button.setAttribute('aria-expanded', 'true');
        state = 'open';
        dispatchWidgetEvent('open', {});
      }
      function close() {
        if (state === 'closed') {
          return;
        }
        overlay.classList.remove('ff-widget-open');
        button.setAttribute('aria-expanded', 'false');
        state = 'closed';
        dispatchWidgetEvent('close', {});
      }
      function toggle() {
        if (state === 'open') {
          close();
        } else {
          open();
        }
      }
      button.addEventListener('click', function () {
        toggle();
      });
      document.head.appendChild(styles);
      document.body.appendChild(button);
      document.body.appendChild(overlay);
      var controller = {
        open: open,
        close: close,
        toggle: toggle,
        getState: function () { return state; },
        getToken: function () { return config.token; },
      };
      window.FeatureFrontendWidget = controller;
      dispatchWidgetEvent('ready', { token: config.token });
    });
  }

  initialize();
})();
