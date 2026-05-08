import React, { useState } from 'react';
import { Copy, Check, ChevronRight } from 'lucide-react';

type Platform = 'wordpress' | 'wix' | 'squarespace' | 'shopify' | 'godaddy' | 'custom';

interface InstallFlowProps {
  apiKey: string;
  onComplete?: () => void;
}

const InstallFlow: React.FC<InstallFlowProps> = ({ apiKey, onComplete }) => {
  const [selectedPlatform, setSelectedPlatform] = useState<Platform | null>(null);
  const [copied, setCopied] = useState(false);

  const platformConfigs: Record<Platform, { name: string; icon: string; instruction: string; code: string }> = {
    wordpress: {
      name: 'WordPress',
      icon: '📝',
      instruction: 'Go to Appearance → Theme Editor → theme.liquid (or use "Insert Headers and Footers" plugin). Paste before </head> tag.',
      code: `<script src="https://cdn.fikirisolutions.com/sdk/v1/fikiri-sdk.js"></script>
<script>
  Fikiri.init({
    apiKey: '${apiKey}',
    features: ['chatbot', 'leadCapture']
  });
  
  window.addEventListener('load', function() {
    Fikiri.Chatbot.show({
      theme: 'light',
      position: 'bottom-right',
      title: 'Need Help?'
    });
  });
</script>`
    },
    wix: {
      name: 'Wix',
      icon: '🎨',
      instruction: 'Go to Add → Embed → HTML Code. Paste the code and position it.',
      code: `<script src="https://cdn.fikirisolutions.com/sdk/v1/fikiri-sdk.js"></script>
<script>
  window.addEventListener('load', function() {
    if (typeof Fikiri !== 'undefined') {
      Fikiri.init({
        apiKey: '${apiKey}',
        features: ['chatbot', 'leadCapture']
      });
      
      Fikiri.Chatbot.show({
        theme: 'light',
        position: 'bottom-right',
        title: 'Need Help?'
      });
    }
  });
</script>`
    },
    squarespace: {
      name: 'SquareSpace',
      icon: '⬜',
      instruction: 'Edit page → Add Block → Code. Paste the code and save.',
      code: `<script src="https://cdn.fikirisolutions.com/sdk/v1/fikiri-sdk.js"></script>
<script>
  Fikiri.init({
    apiKey: '${apiKey}',
    features: ['chatbot', 'leadCapture']
  });
  
  Fikiri.Chatbot.show({
    theme: 'light',
    position: 'bottom-right',
    title: 'Need Help?'
  });
</script>`
    },
    shopify: {
      name: 'Shopify',
      icon: '🛒',
      instruction: 'Go to Online Store → Themes → Edit code → theme.liquid. Paste before </head>.',
      code: `<script src="https://cdn.fikirisolutions.com/sdk/v1/fikiri-sdk.js"></script>
<script>
  Fikiri.init({
    apiKey: '${apiKey}',
    features: ['chatbot', 'leadCapture']
  });
  
  window.addEventListener('load', function() {
    Fikiri.Chatbot.show({
      theme: 'light',
      position: 'bottom-right',
      title: 'Need Help?'
    });
  });
</script>`
    },
    godaddy: {
      name: 'GoDaddy',
      icon: '🌐',
      instruction: 'Go to Website → Edit Site → Add Section → Custom HTML. Paste the code.',
      code: `<script src="https://cdn.fikirisolutions.com/sdk/v1/fikiri-sdk.js"></script>
<script>
  window.addEventListener('load', function() {
    if (typeof Fikiri !== 'undefined') {
      Fikiri.init({
        apiKey: '${apiKey}',
        features: ['chatbot', 'leadCapture']
      });
      
      Fikiri.Chatbot.show({
        theme: 'light',
        position: 'bottom-right',
        title: 'Need Help?'
      });
    }
  });
</script>`
    },
    custom: {
      name: 'Custom HTML',
      icon: '💻',
      instruction: 'Add before </head> tag in your HTML file.',
      code: `<script src="https://cdn.fikirisolutions.com/sdk/v1/fikiri-sdk.js"></script>
<script>
  Fikiri.init({
    apiKey: '${apiKey}',
    features: ['chatbot', 'leadCapture']
  });
  
  window.addEventListener('load', function() {
    Fikiri.Chatbot.show({
      theme: 'light',
      position: 'bottom-right',
      title: 'Need Help?'
    });
  });
</script>`
    }
  };

  const handleCopy = () => {
    if (selectedPlatform) {
      navigator.clipboard.writeText(platformConfigs[selectedPlatform].code);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  if (!selectedPlatform) {
    return (
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-8 border border-gray-200 dark:border-gray-700">
        <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-6">
          Where is your website built?
        </h2>
        <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
          {(Object.keys(platformConfigs) as Platform[]).map((platform) => (
            <button
              key={platform}
              onClick={() => setSelectedPlatform(platform)}
              className="p-6 border-2 border-gray-200 dark:border-gray-600 rounded-lg hover:border-teal-500 dark:hover:border-teal-400 hover:bg-teal-50 dark:hover:bg-teal-900/30 transition-all text-left"
            >
              <div className="text-3xl mb-2">{platformConfigs[platform].icon}</div>
              <div className="font-semibold text-gray-900 dark:text-white">{platformConfigs[platform].name}</div>
            </button>
          ))}
        </div>
      </div>
    );
  }

  const config = platformConfigs[selectedPlatform];

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-8 border border-gray-200 dark:border-gray-700">
      <div className="flex items-center justify-between mb-6">
        <div>
          <button
            onClick={() => setSelectedPlatform(null)}
            className="text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white mb-2"
          >
            ← Back
          </button>
          <h2 className="text-2xl font-bold text-gray-900 dark:text-white">
            Installing on {config.name}
          </h2>
        </div>
        <div className="text-4xl">{config.icon}</div>
      </div>

      <div className="space-y-6">
        <div>
          <p className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
            Step 1: Copy this code
          </p>
          <div className="bg-gray-900 rounded-lg p-4 relative">
            <pre className="text-sm text-gray-100 overflow-x-auto">
              <code>{config.code}</code>
            </pre>
            <button
              onClick={handleCopy}
              className="absolute top-4 right-4 p-2 bg-gray-700 hover:bg-gray-600 rounded text-white transition-colors"
            >
              {copied ? (
                <Check className="w-5 h-5" />
              ) : (
                <Copy className="w-5 h-5" />
              )}
            </button>
          </div>
          {copied && (
            <p className="mt-2 text-sm text-green-600 dark:text-green-400">✓ Copied to clipboard!</p>
          )}
        </div>

        <div>
          <p className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
            Step 2: Paste it
          </p>
          <div className="bg-gray-50 dark:bg-gray-700/50 border border-gray-200 dark:border-gray-600 rounded-lg p-4">
            <p className="text-gray-700 dark:text-gray-300">{config.instruction}</p>
          </div>
        </div>

        <div className="bg-teal-50 dark:bg-teal-900/30 border border-teal-200 dark:border-teal-800 rounded-lg p-4">
          <div className="flex items-center gap-2">
            <Check className="w-5 h-5 text-teal-600 dark:text-teal-400 shrink-0" />
            <span className="font-semibold text-teal-900 dark:text-teal-100">Step 3: Done! ✅</span>
          </div>
          <p className="mt-2 text-sm text-teal-700 dark:text-teal-200">
            Save and preview your site. The chatbot will appear automatically.
          </p>
        </div>

        {onComplete && (
          <button
            onClick={onComplete}
            className="w-full bg-teal-600 dark:bg-teal-500 text-white py-3 rounded-lg hover:bg-teal-700 dark:hover:bg-teal-600 transition-colors font-semibold flex items-center justify-center gap-2"
          >
            I've Installed It
            <ChevronRight className="w-5 h-5" />
          </button>
        )}
      </div>
    </div>
  );
};

export default InstallFlow;
