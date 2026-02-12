import React from 'react';

interface LogoTickerProps {
  speed?: number; // Animation speed in seconds
  className?: string;
}

const LogoTicker: React.FC<LogoTickerProps> = ({ speed = 20, className = '' }) => {
  // Company logos data - Replace these img tags with actual logo files
  // For now using stylized logos with company colors and initials
  const logos = [
    {
      name: 'OpenAI',
      logo: (
        <div className="bg-slate-800 text-white rounded-lg w-12 h-8 flex items-center justify-center font-bold">
          AI
        </div>
      ),
      className: 'bg-white rounded-lg w-20 h-12 flex items-center justify-center px-3 shadow-lg'
    },
    {
      name: 'Google', 
      logo: (
        <div className="flex space-x-1">
          <div className="w-3 h-8 bg-blue-500 rounded-sm"></div>
          <div className="w-3 h-8 bg-red-500 rounded-sm"></div>
          <div className="w-3 h-8 bg-yellow-500 rounded-sm"></div>
          <div className="w-3 h-8 bg-green-500 rounded-sm"></div>
        </div>
      ),
      className: 'bg-white rounded-lg w-20 h-12 flex items-center justify-center px-2 shadow-lg'
    },
    {
      name: 'Redis',
      logo: (
        <div className="bg-red-600 text-white rounded-lg w-12 h-8 flex items-center justify-center font-bold">
          R
        </div>
      ),
      className: 'bg-white rounded-lg w-20 h-12 flex items-center justify-center px-2 shadow-lg'
    },
    {
      name: 'Shopify',
      logo: (
        <div className="bg-green-600 text-white rounded-lg w-12 h-8 flex items-center justify-center font-bold">
          S
        </div>
      ),
      className: 'bg-white rounded-lg w-20 h-12 flex items-center justify-center px-2 shadow-lg'
    },
    {
      name: 'Microsoft',
      logo: (
        <div className="grid grid-cols-2 gap-1">
          <div className="w-3 h-3 bg-red-500 rounded-sm"></div>
          <div className="w-3 h-3 bg-green-500 rounded-sm"></div>
          <div className="w-3 h-3 bg-blue-500 rounded-sm"></div>
          <div className="w-3 h-3 bg-yellow-500 rounded-sm"></div>
        </div>
      ),
      className: 'bg-white rounded-lg w-20 h-12 flex items-center justify-center px-2 shadow-lg'
    },
    {
      name: 'Stripe',
      logo: (
        <div className="bg-purple-600 text-white rounded-lg w-12 h-8 flex items-center justify-center font-bold">
          $
        </div>
      ),
      className: 'bg-white rounded-lg w-20 h-12 flex items-center justify-center px-2 shadow-lg'
    }
  ];

  // Duplicate logos for seamless scrolling
  const duplicatedLogos = [...logos, ...logos, ...logos];

  return (
    <>
      <div className={`overflow-hidden w-full ${className}`}>
        <div 
          className="flex items-center gap-8 whitespace-nowrap"
          style={{
            width: 'fit-content',
            animation: `scroll ${speed}s linear infinite`
          }}
        >
          {duplicatedLogos.map((logo, index) => (
            <div
              key={`${logo.name}-${index}`}
              className="flex items-center justify-center px-6 py-3 opacity-80 hover:opacity-100 transition-opacity duration-300 group"
            >
              <div className={`${logo.className} flex-shrink-0 group-hover:shadow-xl transition-shadow`}>
                {logo.logo}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Legal disclaimer */}
      <div className="text-xs text-white/50 text-center mt-4">
        Integrates with industry-leading APIs and platforms
      </div>

      <style dangerouslySetInnerHTML={{
        __html: `
          @keyframes scroll {
            0% {
              transform: translateX(0);
            }
            100% {
              transform: translateX(-33.333%);
            }
          }
          
          /* Hover effect enhancement */
          .group:hover {
            transform: scale(1.05);
            transition: transform 0.2s ease-in-out;
          }
        `
      }} />
    </>
  );
};

export default LogoTicker;