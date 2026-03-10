/**
 * Fikiri Universal JavaScript SDK
 * Works with WordPress, SquareSpace, Replit, and custom websites
 * Version: 1.0.0
 */

(function(window) {
  'use strict';

  // SDK Configuration
  const SDK_VERSION = '1.0.0';
  const DEFAULT_API_URL = 'https://api.fikirisolutions.com';
  const DEFAULT_TIMEOUT = 30000; // 30 seconds

  /**
   * Fikiri SDK Main Class
   */
  class FikiriSDK {
    constructor(config = {}) {
      this.apiKey = config.apiKey || null;
      this.apiUrl = config.apiUrl || DEFAULT_API_URL;
      this.tenantId = config.tenantId || null;
      this.timeout = config.timeout || DEFAULT_TIMEOUT;
      this.features = config.features || [];
      this.debug = config.debug || false;
      
      // Initialize features
      this.chatbot = new ChatbotFeature(this);
      this.leadCapture = new LeadCaptureFeature(this);
      this.forms = new FormsFeature(this);
      
      this._log('SDK initialized', { version: SDK_VERSION });
    }

    /**
     * Initialize SDK with configuration
     */
    static init(config) {
      if (window.Fikiri && window.Fikiri._instance) {
        window.Fikiri._log('SDK already initialized, updating config');
        window.Fikiri._instance._updateConfig(config);
        return window.Fikiri._instance;
      }
      
      const instance = new FikiriSDK(config);
      window.Fikiri = {
        _instance: instance,
        Chatbot: instance.chatbot,
        LeadCapture: instance.leadCapture,
        Forms: instance.forms,
        init: FikiriSDK.init,
        version: SDK_VERSION
      };
      
      return instance;
    }

    /**
     * Update configuration
     */
    _updateConfig(config) {
      if (config.apiKey) this.apiKey = config.apiKey;
      if (config.apiUrl) this.apiUrl = config.apiUrl;
      if (config.tenantId) this.tenantId = config.tenantId;
      if (config.timeout) this.timeout = config.timeout;
      if (config.features) this.features = config.features;
      if (config.debug !== undefined) this.debug = config.debug;
    }

    /**
     * Make API request with retry logic
     */
    async _request(endpoint, options = {}) {
      if (!this.apiKey) {
        throw new Error('API key is required. Call Fikiri.init({ apiKey: "..." }) first.');
      }

      const maxRetries = options.maxRetries !== undefined ? options.maxRetries : 3;
      const retryDelay = options.retryDelay !== undefined ? options.retryDelay : 1000; // 1 second
      const retryableStatuses = options.retryableStatuses || [408, 429, 500, 502, 503, 504];

      const url = `${this.apiUrl}${endpoint}`;
      
      for (let attempt = 0; attempt <= maxRetries; attempt++) {
        try {
          const headers = {
            'Content-Type': 'application/json',
            'X-API-Key': this.apiKey,
            ...options.headers
          };

          if (this.tenantId) {
            headers['X-Tenant-ID'] = this.tenantId;
          }

          const config = {
            method: options.method || 'GET',
            headers,
            ...options
          };

          if (options.body && typeof options.body === 'object') {
            config.body = JSON.stringify(options.body);
          }

          this._log('API request', { endpoint, method: config.method, attempt: attempt + 1 });

          const controller = new AbortController();
          const timeoutId = setTimeout(() => controller.abort(), this.timeout);

          const response = await fetch(url, {
            ...config,
            signal: controller.signal
          });

          clearTimeout(timeoutId);

          // Check if we should retry
          if (!response.ok && retryableStatuses.includes(response.status) && attempt < maxRetries) {
            const delay = retryDelay * Math.pow(2, attempt); // Exponential backoff
            this._log('Retrying request', { endpoint, status: response.status, attempt: attempt + 1, delay });
            await this._sleep(delay);
            continue;
          }

          if (!response.ok) {
            const error = await response.json().catch(() => ({ error: 'Request failed' }));
            throw new Error(error.error || `HTTP ${response.status}`);
          }

          const data = await response.json();
          this._log('API response', { endpoint, success: data.success });
          return data;
        } catch (error) {
          // Retry on network errors (but not on abort/timeout)
          if (error.name !== 'AbortError' && attempt < maxRetries) {
            const delay = retryDelay * Math.pow(2, attempt);
            this._log('Retrying after error', { endpoint, error: error.message, attempt: attempt + 1, delay });
            await this._sleep(delay);
            continue;
          }
          
          this._log('API error', { endpoint, error: error.message, attempts: attempt + 1 });
          throw error;
        }
      }
    }

    /**
     * Sleep helper for retry delays
     */
    _sleep(ms) {
      return new Promise(resolve => setTimeout(resolve, ms));
    }

    /**
     * Debug logging
     */
    _log(message, data = {}) {
      if (this.debug) {
        console.log(`[Fikiri SDK] ${message}`, data);
      }
    }
  }

  /**
   * Chatbot Feature
   */
  class ChatbotFeature {
    constructor(sdk) {
      this.sdk = sdk;
      this.conversationId = null;
      this.widget = null;
    }

    /**
     * Show chatbot widget
     */
    show(options = {}) {
      if (this.widget) {
        this.widget.show();
        return;
      }

      this.widget = new ChatbotWidget(this.sdk, options);
      this.widget.render();
    }

    /**
     * Hide chatbot widget
     */
    hide() {
      if (this.widget) {
        this.widget.hide();
      }
    }

    /**
     * Send query to chatbot
     */
    async query(text, options = {}) {
      const body = {
        query: text,
        conversation_id: options.conversationId || this.conversationId,
        context: options.context || {},
        lead: options.lead || {}
      };

      const response = await this.sdk._request('/api/public/chatbot/query', {
        method: 'POST',
        body
      });

      if (response.success && response.conversation_id) {
        this.conversationId = response.conversation_id;
      }

      return response;
    }
  }

  /**
   * Lead Capture Feature
   */
  class LeadCaptureFeature {
    constructor(sdk) {
      this.sdk = sdk;
    }

    /**
     * Capture a lead
     */
    async capture(data) {
      const body = {
        email: data.email,
        name: data.name,
        phone: data.phone,
        source: data.source || 'website',
        metadata: data.metadata || {},
        auto_create_crm: data.auto_create_crm !== false
      };

      return await this.sdk._request('/api/webhooks/leads/capture', {
        method: 'POST',
        body
      });
    }

    /**
     * Show lead capture form widget
     */
    show(options = {}) {
      const widget = new LeadCaptureWidget(this.sdk, options);
      widget.render();
      return widget;
    }
  }

  /**
   * Forms Feature
   */
  class FormsFeature {
    constructor(sdk) {
      this.sdk = sdk;
    }

    /**
     * Submit form data
     */
    async submit(formData) {
      const body = {
        form_id: formData.formId || 'custom-form',
        fields: formData.fields || {},
        source: formData.source || 'website',
        metadata: formData.metadata || {}
      };

      return await this.sdk._request('/api/webhooks/forms/submit', {
        method: 'POST',
        body
      });
    }
  }

  /**
   * Chatbot Widget UI
   */
  class ChatbotWidget {
    constructor(sdk, options = {}) {
      this.sdk = sdk;
      this.options = {
        theme: options.theme || 'light',
        position: options.position || 'bottom-right',
        title: options.title || 'Chat with us',
        accentColor: options.accentColor || '#0f766e',
        ...options
      };
      this.isVisible = false;
      this.container = null;
      this.button = null;
      this.panel = null;
    }

    render() {
      // Create container
      this.container = document.createElement('div');
      this.container.id = 'fikiri-chatbot-container';
      this.container.innerHTML = this._getHTML();
      document.body.appendChild(this.container);

      // Add styles
      this._injectStyles();

      // Bind events
      this.button = this.container.querySelector('#fikiri-chatbot-button');
      this.panel = this.container.querySelector('#fikiri-chatbot-panel');
      this.input = this.container.querySelector('#fikiri-chatbot-input');
      this.messages = this.container.querySelector('#fikiri-chatbot-messages');

      this.button.addEventListener('click', () => this.toggle());
      this.input.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && this.input.value.trim()) {
          this.sendMessage(this.input.value.trim());
        }
      });

      // Show button initially
      this.showButton();
    }

    show() {
      if (!this.panel) return;
      this.panel.style.display = 'flex';
      this.isVisible = true;
      this.input.focus();
    }

    hide() {
      if (!this.panel) return;
      this.panel.style.display = 'none';
      this.isVisible = false;
    }

    toggle() {
      if (this.isVisible) {
        this.hide();
      } else {
        this.show();
      }
    }

    showButton() {
      if (this.button) {
        this.button.style.display = 'flex';
      }
    }

    async sendMessage(text) {
      if (!text.trim()) return;

      // Add user message
      this.addMessage('user', text);
      this.input.value = '';
      this.input.disabled = true;

      try {
        const response = await this.sdk.chatbot.query(text);
        
        if (response.success) {
          this.addMessage('bot', response.response || 'No response');
        } else {
          this.addMessage('bot', 'Sorry, I encountered an error. Please try again.');
        }
      } catch (error) {
        this.addMessage('bot', 'Sorry, I encountered an error. Please try again.');
        this.sdk._log('Chatbot error', { error: error.message });
      } finally {
        this.input.disabled = false;
        this.input.focus();
      }
    }

    addMessage(type, text) {
      const messageDiv = document.createElement('div');
      messageDiv.className = `fikiri-message fikiri-message-${type}`;
      messageDiv.textContent = text;
      this.messages.appendChild(messageDiv);
      this.messages.scrollTop = this.messages.scrollHeight;
    }

    _getHTML() {
      return `
        <div id="fikiri-chatbot-button" style="display: none;">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
            <path d="M20 2H4C2.9 2 2 2.9 2 4V22L6 18H20C21.1 18 22 17.1 22 16V4C22 2.9 21.1 2 20 2Z" fill="currentColor"/>
          </svg>
        </div>
        <div id="fikiri-chatbot-panel" style="display: none;">
          <div class="fikiri-chatbot-header">
            <span>${this.options.title}</span>
            <button id="fikiri-chatbot-close">×</button>
          </div>
          <div id="fikiri-chatbot-messages"></div>
          <div class="fikiri-chatbot-input-container">
            <input id="fikiri-chatbot-input" type="text" placeholder="Type your message..." />
            <button id="fikiri-chatbot-send">Send</button>
          </div>
        </div>
      `;
    }

    _injectStyles() {
      if (document.getElementById('fikiri-chatbot-styles')) return;

      const style = document.createElement('style');
      style.id = 'fikiri-chatbot-styles';
      style.textContent = `
        #fikiri-chatbot-container {
          font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
          position: fixed;
          z-index: 9999;
        }
        #fikiri-chatbot-button {
          width: 60px;
          height: 60px;
          border-radius: 50%;
          background: ${this.options.accentColor};
          color: white;
          display: flex;
          align-items: center;
          justify-content: center;
          cursor: pointer;
          box-shadow: 0 4px 12px rgba(0,0,0,0.15);
          position: fixed;
          ${this.options.position.includes('right') ? 'right: 20px;' : 'left: 20px;'}
          ${this.options.position.includes('bottom') ? 'bottom: 20px;' : 'top: 20px;'}
        }
        #fikiri-chatbot-panel {
          width: 380px;
          height: 600px;
          background: white;
          border-radius: 12px;
          box-shadow: 0 8px 32px rgba(0,0,0,0.2);
          display: flex;
          flex-direction: column;
          position: fixed;
          ${this.options.position.includes('right') ? 'right: 20px;' : 'left: 20px;'}
          ${this.options.position.includes('bottom') ? 'bottom: 90px;' : 'top: 90px;'}
        }
        .fikiri-chatbot-header {
          padding: 16px;
          border-bottom: 1px solid #eee;
          display: flex;
          justify-content: space-between;
          align-items: center;
          font-weight: 600;
        }
        #fikiri-chatbot-close {
          background: none;
          border: none;
          font-size: 24px;
          cursor: pointer;
          color: #666;
        }
        #fikiri-chatbot-messages {
          flex: 1;
          overflow-y: auto;
          padding: 16px;
        }
        .fikiri-message {
          margin-bottom: 12px;
          padding: 8px 12px;
          border-radius: 8px;
          max-width: 80%;
        }
        .fikiri-message-user {
          background: ${this.options.accentColor};
          color: white;
          margin-left: auto;
        }
        .fikiri-message-bot {
          background: #f0f0f0;
          color: #333;
        }
        .fikiri-chatbot-input-container {
          padding: 16px;
          border-top: 1px solid #eee;
          display: flex;
          gap: 8px;
        }
        #fikiri-chatbot-input {
          flex: 1;
          padding: 10px;
          border: 1px solid #ddd;
          border-radius: 6px;
        }
        #fikiri-chatbot-send {
          padding: 10px 20px;
          background: ${this.options.accentColor};
          color: white;
          border: none;
          border-radius: 6px;
          cursor: pointer;
        }
      `;
      document.head.appendChild(style);
    }
  }

  /**
   * Lead Capture Widget UI
   */
  class LeadCaptureWidget {
    constructor(sdk, options = {}) {
      this.sdk = sdk;
      this.options = {
        fields: options.fields || ['email', 'name'],
        title: options.title || 'Get in touch',
        submitText: options.submitText || 'Submit',
        ...options
      };
    }

    render() {
      // Implementation for lead capture widget
      // Similar pattern to chatbot widget
    }
  }

  // Auto-initialize from data attributes
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initFromAttributes);
  } else {
    initFromAttributes();
  }

  function initFromAttributes() {
    const script = document.querySelector('script[data-fikiri-api-key]');
    if (script) {
      const config = {
        apiKey: script.getAttribute('data-fikiri-api-key'),
        apiUrl: script.getAttribute('data-fikiri-api-url') || DEFAULT_API_URL,
        tenantId: script.getAttribute('data-fikiri-tenant-id'),
        debug: script.getAttribute('data-fikiri-debug') === 'true'
      };
      FikiriSDK.init(config);
    }
  }

  // Export for module systems
  if (typeof module !== 'undefined' && module.exports) {
    module.exports = FikiriSDK;
  }

})(window);
