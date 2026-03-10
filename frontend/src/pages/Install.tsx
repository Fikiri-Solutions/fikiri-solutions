import React, { useState, useEffect } from 'react';
import { Copy, Check, Play, ExternalLink } from 'lucide-react';
import { apiClient } from '../services/apiClient';

type Platform = 'wordpress' | 'wix' | 'squarespace' | 'shopify' | 'godaddy' | 'custom';

interface PlatformConfig {
  name: string;
  icon: string;
  steps: {
    title: string;
    code?: string;
    instruction: string;
    screenshot?: string;
  }[];
  videoUrl?: string;
  demoUrl?: string;
}

const InstallPage: React.FC = () => {
  const [selectedPlatform, setSelectedPlatform] = useState<Platform>('wordpress');
  const [copied, setCopied] = useState<string | null>(null);
  const [apiKey, setApiKey] = useState<string | null>(null);
  const [apiKeyStatus, setApiKeyStatus] = useState<'loading' | 'ready' | 'error'>('loading');
  const [apiKeyError, setApiKeyError] = useState<string | null>(null);

  useEffect(() => {
    let isMounted = true;

    const loadApiKey = async () => {
      try {
        const cached = typeof window !== 'undefined' ? localStorage.getItem('fikiri-public-api-key') : null;
        if (cached) {
          if (isMounted) {
            setApiKey(cached);
            setApiKeyStatus('ready');
          }
          return;
        }

        const created = await apiClient.createApiKey({
          name: 'Install Page Key',
          description: 'Generated for install page embed code',
        });
        if (isMounted) {
          setApiKey(created.api_key);
          setApiKeyStatus('ready');
          if (typeof window !== 'undefined') {
            localStorage.setItem('fikiri-public-api-key', created.api_key);
          }
        }
      } catch (error: any) {
        if (isMounted) {
          setApiKeyStatus('error');
          setApiKeyError('Sign in to generate your API key.');
        }
      }
    };

    loadApiKey();

    return () => {
      isMounted = false;
    };
  }, []);

  const resolvedApiKey = apiKey || 'fik_your_api_key_here';

  const platforms: Record<Platform, PlatformConfig> = {
    wordpress: {
      name: 'WordPress',
      icon: '📝',
      steps: [
        {
          title: 'Step 1: Copy this code',
          code: `<script src="https://cdn.fikirisolutions.com/sdk/v1/fikiri-sdk.js"></script>
<script>
  Fikiri.init({
    apiKey: '${resolvedApiKey}',
    features: ['chatbot', 'leadCapture']
  });
  
  window.addEventListener('load', function() {
    Fikiri.Chatbot.show({
      theme: 'light',
      position: 'bottom-right',
      title: 'Need Help?'
    });
  });
</script>`,
          instruction: 'Copy the code above',
          screenshot: '/screenshots/wordpress-step1.png'
        },
        {
          title: 'Step 2: Paste in WordPress',
          instruction: 'Go to Appearance → Theme Editor → theme.liquid (or use "Insert Headers and Footers" plugin). Paste before </head> tag.',
          screenshot: '/screenshots/wordpress-step2.png'
        },
        {
          title: 'Step 3: Done! ✅',
          instruction: 'Save and preview your site. The chatbot will appear in the bottom-right corner.',
          screenshot: '/screenshots/wordpress-step3.png'
        }
      ],
      videoUrl: 'https://www.loom.com/share/wordpress-install',
      demoUrl: 'https://demo.fikirisolutions.com/wordpress'
    },
    wix: {
      name: 'Wix',
      icon: '🎨',
      steps: [
        {
          title: 'Step 1: Copy this code',
          code: `<script src="https://cdn.fikirisolutions.com/sdk/v1/fikiri-sdk.js"></script>
<script>
  window.addEventListener('load', function() {
    if (typeof Fikiri !== 'undefined') {
      Fikiri.init({
        apiKey: '${resolvedApiKey}',
        features: ['chatbot', 'leadCapture']
      });
      
      Fikiri.Chatbot.show({
        theme: 'light',
        position: 'bottom-right',
        title: 'Need Help?'
      });
    }
  });
</script>`,
          instruction: 'Copy the code above',
          screenshot: '/screenshots/wix-step1.png'
        },
        {
          title: 'Step 2: Add HTML Embed',
          instruction: 'Go to Add → Embed → HTML Code. Paste the code and position it.',
          screenshot: '/screenshots/wix-step2.png'
        },
        {
          title: 'Step 3: Done! ✅',
          instruction: 'Publish your site. The chatbot will appear automatically.',
          screenshot: '/screenshots/wix-step3.png'
        }
      ],
      videoUrl: 'https://www.loom.com/share/wix-install',
      demoUrl: 'https://demo.fikirisolutions.com/wix'
    },
    squarespace: {
      name: 'SquareSpace',
      icon: '⬜',
      steps: [
        {
          title: 'Step 1: Copy this code',
          code: `<script src="https://cdn.fikirisolutions.com/sdk/v1/fikiri-sdk.js"></script>
<script>
  Fikiri.init({
    apiKey: '${resolvedApiKey}',
    features: ['chatbot', 'leadCapture']
  });
  
  Fikiri.Chatbot.show({
    theme: 'light',
    position: 'bottom-right',
    title: 'Need Help?'
  });
</script>`,
          instruction: 'Copy the code above',
          screenshot: '/screenshots/squarespace-step1.png'
        },
        {
          title: 'Step 2: Add Code Block',
          instruction: 'Edit page → Add Block → Code. Paste the code and save.',
          screenshot: '/screenshots/squarespace-step2.png'
        },
        {
          title: 'Step 3: Done! ✅',
          instruction: 'The chatbot will appear on your page.',
          screenshot: '/screenshots/squarespace-step3.png'
        }
      ],
      videoUrl: 'https://www.loom.com/share/squarespace-install',
      demoUrl: 'https://demo.fikirisolutions.com/custom'
    },
    shopify: {
      name: 'Shopify',
      icon: '🛒',
      steps: [
        {
          title: 'Step 1: Copy this code',
          code: `<script src="https://cdn.fikirisolutions.com/sdk/v1/fikiri-sdk.js"></script>
<script>
  Fikiri.init({
    apiKey: '${resolvedApiKey}',
    features: ['chatbot', 'leadCapture']
  });
  
  window.addEventListener('load', function() {
    Fikiri.Chatbot.show({
      theme: 'light',
      position: 'bottom-right',
      title: 'Need Help?'
    });
  });
</script>`,
          instruction: 'Copy the code above',
          screenshot: '/screenshots/shopify-step1.png'
        },
        {
          title: 'Step 2: Edit Theme',
          instruction: 'Go to Online Store → Themes → Edit code → theme.liquid. Paste before </head>.',
          screenshot: '/screenshots/shopify-step2.png'
        },
        {
          title: 'Step 3: Done! ✅',
          instruction: 'Save and preview. Chatbot appears on all pages.',
          screenshot: '/screenshots/shopify-step3.png'
        }
      ],
      videoUrl: 'https://www.loom.com/share/shopify-install',
      demoUrl: 'https://demo.fikirisolutions.com/shopify'
    },
    godaddy: {
      name: 'GoDaddy',
      icon: '🌐',
      steps: [
        {
          title: 'Step 1: Copy this code',
          code: `<script src="https://cdn.fikirisolutions.com/sdk/v1/fikiri-sdk.js"></script>
<script>
  window.addEventListener('load', function() {
    if (typeof Fikiri !== 'undefined') {
      Fikiri.init({
        apiKey: '${resolvedApiKey}',
        features: ['chatbot', 'leadCapture']
      });
      
      Fikiri.Chatbot.show({
        theme: 'light',
        position: 'bottom-right',
        title: 'Need Help?'
      });
    }
  });
</script>`,
          instruction: 'Copy the code above',
          screenshot: '/screenshots/godaddy-step1.png'
        },
        {
          title: 'Step 2: Add Custom HTML Block',
          instruction: 'Go to Website → Edit Site → Add Section → Custom HTML. Paste the code.',
          screenshot: '/screenshots/godaddy-step2.png'
        },
        {
          title: 'Step 3: Done! ✅',
          instruction: 'Publish your site. Chatbot appears automatically.',
          screenshot: '/screenshots/godaddy-step3.png'
        }
      ],
      videoUrl: 'https://www.loom.com/share/godaddy-install',
      demoUrl: 'https://demo.fikirisolutions.com/godaddy'
    },
    custom: {
      name: 'Custom HTML',
      icon: '💻',
      steps: [
        {
          title: 'Step 1: Copy this code',
          code: `<script src="https://cdn.fikirisolutions.com/sdk/v1/fikiri-sdk.js"></script>
<script>
  Fikiri.init({
    apiKey: '${resolvedApiKey}',
    features: ['chatbot', 'leadCapture']
  });
  
  window.addEventListener('load', function() {
    Fikiri.Chatbot.show({
      theme: 'light',
      position: 'bottom-right',
      title: 'Need Help?'
    });
  });
</script>`,
          instruction: 'Copy the code above',
          screenshot: '/screenshots/custom-step1.png'
        },
        {
          title: 'Step 2: Paste in your HTML',
          instruction: 'Add before </head> tag in your HTML file.',
          screenshot: '/screenshots/custom-step2.png'
        },
        {
          title: 'Step 3: Done! ✅',
          instruction: 'Save and refresh. Chatbot appears on your site.',
          screenshot: '/screenshots/custom-step3.png'
        }
      ],
      videoUrl: 'https://www.loom.com/share/custom-install',
      demoUrl: 'https://demo.fikirisolutions.com/custom'
    }
  };

  const currentPlatform = platforms[selectedPlatform];

  const handleCopy = (code: string, stepIndex: number) => {
    navigator.clipboard.writeText(code);
    setCopied(`step-${stepIndex}`);
    setTimeout(() => setCopied(null), 2000);
  };

  return (
    <div className="min-h-screen bg-gray-50 py-12 px-4">
      <div className="max-w-6xl mx-auto">
        {/* Header */}
        <div className="text-center mb-12">
          <h1 className="text-4xl font-bold text-gray-900 mb-4">
            Install Fikiri on Your Website
          </h1>
          <p className="text-xl text-gray-600">
            Get more leads in 5 minutes. Choose your platform below.
          </p>
          {apiKeyStatus === 'loading' && (
            <p className="mt-3 text-sm text-gray-500">Loading your API key…</p>
          )}
          {apiKeyStatus === 'error' && (
            <p className="mt-3 text-sm text-red-600">{apiKeyError}</p>
          )}
        </div>

        {/* Platform Selector */}
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4 mb-12">
          {(Object.keys(platforms) as Platform[]).map((platform) => (
            <button
              key={platform}
              onClick={() => setSelectedPlatform(platform)}
              className={`p-6 rounded-lg border-2 transition-all ${
                selectedPlatform === platform
                  ? 'border-teal-600 bg-teal-50 shadow-lg'
                  : 'border-gray-200 bg-white hover:border-gray-300'
              }`}
            >
              <div className="text-4xl mb-2">{platforms[platform].icon}</div>
              <div className="font-semibold text-gray-900">{platforms[platform].name}</div>
            </button>
          ))}
        </div>

        {/* Installation Steps */}
        <div className="bg-white rounded-lg shadow-xl p-8 mb-8">
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-2xl font-bold text-gray-900">
              Installing on {currentPlatform.name}
            </h2>
            <div className="flex gap-4">
              {currentPlatform.videoUrl && (
                <a
                  href={currentPlatform.videoUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center gap-2 text-teal-600 hover:text-teal-700"
                >
                  <Play className="w-5 h-5" />
                  <span>2-min Video</span>
                </a>
              )}
              {currentPlatform.demoUrl && (
                <a
                  href={currentPlatform.demoUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center gap-2 text-teal-600 hover:text-teal-700"
                >
                  <ExternalLink className="w-5 h-5" />
                  <span>Live Demo</span>
                </a>
              )}
            </div>
          </div>

          <div className="space-y-8">
            {currentPlatform.steps.map((step, index) => (
              <div key={index} className="border-l-4 border-teal-500 pl-6">
                <h3 className="text-xl font-semibold text-gray-900 mb-4">
                  {step.title}
                </h3>
                
                {step.code && (
                  <div className="bg-gray-900 rounded-lg p-4 mb-4 relative">
                    <pre className="text-sm text-gray-100 overflow-x-auto">
                      <code>{step.code}</code>
                    </pre>
                    <button
                      onClick={() => handleCopy(step.code!, index)}
                      className="absolute top-4 right-4 p-2 bg-gray-700 hover:bg-gray-600 rounded text-white transition-colors"
                    >
                      {copied === `step-${index}` ? (
                        <Check className="w-5 h-5" />
                      ) : (
                        <Copy className="w-5 h-5" />
                      )}
                    </button>
                  </div>
                )}
                
                <p className="text-gray-700 mb-4">{step.instruction}</p>
                
                {step.screenshot && (
                  <div className="border border-gray-200 rounded-lg overflow-hidden">
                    <img
                      src={step.screenshot}
                      alt={`${currentPlatform.name} Step ${index + 1}`}
                      className="w-full h-auto"
                      onError={(e) => {
                        (e.target as HTMLImageElement).style.display = 'none';
                      }}
                    />
                    <div className="bg-gray-100 p-4 text-sm text-gray-600 text-center">
                      Screenshot: {step.instruction}
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>

        {/* Help Section */}
        <div className="bg-teal-50 border border-teal-200 rounded-lg p-6 text-center">
          <h3 className="text-lg font-semibold text-gray-900 mb-2">
            Need Help?
          </h3>
          <p className="text-gray-700 mb-4">
            Our support team is here to help you get set up in minutes.
          </p>
          <a
            href="mailto:support@fikirisolutions.com"
            className="inline-block bg-teal-600 text-white px-6 py-3 rounded-lg hover:bg-teal-700 transition-colors"
          >
            Contact Support
          </a>
        </div>
      </div>
    </div>
  );
};

export default InstallPage;
