import React, { useState, useEffect } from 'react';
import { Copy, Check } from 'lucide-react';

interface ChatbotPreviewProps {
  apiKey: string;
  onCodeGenerated?: (code: string) => void;
}

const ChatbotPreview: React.FC<ChatbotPreviewProps> = ({ apiKey, onCodeGenerated }) => {
  const [theme, setTheme] = useState<'light' | 'dark'>('light');
  const [position, setPosition] = useState<'bottom-right' | 'bottom-left' | 'top-right' | 'top-left'>('bottom-right');
  const [title, setTitle] = useState('Need Help?');
  const [primaryColor, setPrimaryColor] = useState('#0f766e');
  const [copied, setCopied] = useState(false);

  const generateCode = () => {
    return `<script src="https://cdn.fikirisolutions.com/sdk/v1/fikiri-sdk.js"></script>
<script>
  Fikiri.init({
    apiKey: '${apiKey}',
    features: ['chatbot', 'leadCapture']
  });
  
  window.addEventListener('load', function() {
    Fikiri.Chatbot.show({
      theme: '${theme}',
      position: '${position}',
      title: '${title}',
      primaryColor: '${primaryColor}'
    });
  });
</script>`;
  };

  const handleCopy = () => {
    const code = generateCode();
    navigator.clipboard.writeText(code);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
    
    if (onCodeGenerated) {
      onCodeGenerated(code);
    }
  };

  useEffect(() => {
    if (onCodeGenerated) {
      onCodeGenerated(generateCode());
    }
  }, [theme, position, title, primaryColor, apiKey]);

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-8 border border-gray-200 dark:border-gray-700">
      <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-6">
        Customize Your Chatbot
      </h2>

      <div className="grid md:grid-cols-2 gap-8">
        {/* Customization Options */}
        <div className="space-y-6">
          <div>
            <p className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Theme
            </p>
            <div className="flex gap-4">
              <button
                onClick={() => setTheme('light')}
                className={`px-4 py-2 rounded-lg border-2 transition-all ${
                  theme === 'light'
                    ? 'border-teal-600 dark:border-teal-500 bg-teal-50 dark:bg-teal-900/30 text-teal-900 dark:text-teal-100'
                    : 'border-gray-200 dark:border-gray-600 hover:border-gray-300 dark:hover:border-gray-500 text-gray-700 dark:text-gray-300'
                }`}
              >
                Light
              </button>
              <button
                onClick={() => setTheme('dark')}
                className={`px-4 py-2 rounded-lg border-2 transition-all ${
                  theme === 'dark'
                    ? 'border-teal-600 dark:border-teal-500 bg-teal-50 dark:bg-teal-900/30 text-teal-900 dark:text-teal-100'
                    : 'border-gray-200 dark:border-gray-600 hover:border-gray-300 dark:hover:border-gray-500 text-gray-700 dark:text-gray-300'
                }`}
              >
                Dark
              </button>
            </div>
          </div>

          <div>
            <p className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Position
            </p>
            <div className="grid grid-cols-2 gap-2">
              {(['bottom-right', 'bottom-left', 'top-right', 'top-left'] as const).map((pos) => (
                <button
                  key={pos}
                  onClick={() => setPosition(pos)}
                  className={`px-4 py-2 rounded-lg border-2 transition-all text-sm ${
                    position === pos
                      ? 'border-teal-600 dark:border-teal-500 bg-teal-50 dark:bg-teal-900/30 text-teal-900 dark:text-teal-100'
                      : 'border-gray-200 dark:border-gray-600 hover:border-gray-300 dark:hover:border-gray-500 text-gray-700 dark:text-gray-300'
                  }`}
                >
                  {pos.replace('-', ' ')}
                </button>
              ))}
            </div>
          </div>

          <div>
            <label htmlFor="chatbot-title" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Title
            </label>
            <input
              id="chatbot-title"
              name="chatbot_title"
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-teal-500 focus:border-teal-500"
              placeholder="Need Help?"
            />
          </div>

          <div>
            <label htmlFor="chatbot-primary-color" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Primary Color
            </label>
            <div className="flex gap-4 items-center">
              <input
                id="chatbot-primary-color"
                name="chatbot_primary_color"
                type="color"
                value={primaryColor}
                onChange={(e) => setPrimaryColor(e.target.value)}
                className="w-16 h-10 border border-gray-300 dark:border-gray-600 rounded cursor-pointer bg-transparent"
                aria-label="Primary color picker"
              />
              <label htmlFor="chatbot-primary-color-hex" className="sr-only">
                Primary color hex value
              </label>
              <input
                id="chatbot-primary-color-hex"
                name="chatbot_primary_color_hex"
                type="text"
                value={primaryColor}
                onChange={(e) => setPrimaryColor(e.target.value)}
                className="flex-1 px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-teal-500 focus:border-teal-500"
                placeholder="#0f766e"
                autoComplete="off"
              />
            </div>
          </div>
        </div>

        {/* Live Preview */}
        <div>
          <p className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
            Live Preview
          </p>
          <div className="border-2 border-gray-200 dark:border-gray-600 rounded-lg p-6 bg-gray-50 dark:bg-gray-900/50 relative" style={{ minHeight: '400px' }}>
            {/* Simulated Chatbot */}
            <div
              className={`absolute ${position === 'bottom-right' ? 'bottom-4 right-4' : ''} ${position === 'bottom-left' ? 'bottom-4 left-4' : ''} ${position === 'top-right' ? 'top-4 right-4' : ''} ${position === 'top-left' ? 'top-4 left-4' : ''} w-80 rounded-lg shadow-xl border border-gray-200 dark:border-gray-600`}
              style={{ backgroundColor: theme === 'dark' ? '#1f2937' : '#ffffff' }}
            >
              {/* Chatbot Header */}
              <div
                className="px-4 py-3 rounded-t-lg text-white font-semibold flex items-center justify-between"
                style={{ backgroundColor: primaryColor }}
              >
                <span>{title}</span>
                <button className="text-white opacity-75 hover:opacity-100">×</button>
              </div>
              
              {/* Chatbot Body */}
              <div className="p-4" style={{ minHeight: '300px', maxHeight: '300px', overflowY: 'auto' }}>
                <div className="space-y-4">
                  <div className="flex justify-start">
                    <div className="bg-gray-100 rounded-lg px-4 py-2 max-w-xs" style={{ backgroundColor: theme === 'dark' ? '#374151' : '#f3f4f6', color: theme === 'dark' ? '#f9fafb' : '#111827' }}>
                      <p className="text-sm">Hello! How can I help you today?</p>
                    </div>
                  </div>
                  <div className="flex justify-end">
                    <div className="rounded-lg px-4 py-2 max-w-xs text-white text-sm" style={{ backgroundColor: primaryColor }}>
                      <p>I'm interested in your services</p>
                    </div>
                  </div>
                </div>
              </div>
              
              {/* Chatbot Input */}
              <div className="px-4 py-3 border-t border-gray-200 dark:border-gray-600">
                <label htmlFor="chatbot-preview-compose" className="sr-only">
                  Preview chat message
                </label>
                <input
                  id="chatbot-preview-compose"
                  name="preview_message"
                  type="text"
                  placeholder="Type your message..."
                  autoComplete="off"
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-teal-500 focus:border-teal-500"
                  style={{ backgroundColor: theme === 'dark' ? '#374151' : '#ffffff', color: theme === 'dark' ? '#f9fafb' : '#111827' }}
                />
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Generated Code */}
      <div className="mt-8">
        <div className="flex items-center justify-between mb-2">
          <p className="block text-sm font-medium text-gray-700 dark:text-gray-300">
            Generated Code
          </p>
          <button
            onClick={handleCopy}
            className="flex items-center gap-2 px-4 py-2 bg-teal-600 text-white rounded-lg hover:bg-teal-700 transition-colors"
          >
            {copied ? (
              <>
                <Check className="w-4 h-4" />
                Copied!
              </>
            ) : (
              <>
                <Copy className="w-4 h-4" />
                Copy Code
              </>
            )}
          </button>
        </div>
        <div className="bg-gray-900 rounded-lg p-4">
          <pre className="text-sm text-gray-100 overflow-x-auto">
            <code>{generateCode()}</code>
          </pre>
        </div>
      </div>
    </div>
  );
};

export default ChatbotPreview;
