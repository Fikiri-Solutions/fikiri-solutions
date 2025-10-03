import React from 'react';

interface LogoTickerProps {
  speed?: number; // Animation speed in seconds
  className?: string;
}

const LogoTicker: React.FC<LogoTickerProps> = ({ speed = 20, className = '' }) => {
  // Company logos data
  const logos = [
    {
      name: 'OpenAI',
      logo: '🤖',
      className: 'text-white bg-slate-800 rounded-lg w-16 h-12 flex items-center justify-center text-2xl'
    },
    {
      name: 'Google', 
      logo: (
        <svg className="w-12 h-12" viewBox="0 0 24 24" fill="currentColor">
          <path fill="#EA4335" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
          <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
          <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2+09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
          <path fill="#4285F4" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
        </svg>
      ),
      className: 'bg-white rounded-lg w-16 h-12 flex items-center justify-center'
    },
    {
      name: 'Redis',
      logo: 'R',
      className: 'text-red-500 bg-white rounded-lg w-16 h-12 flex items-center justify-center text-2xl font-bold'
    },
    {
      name: 'Shopify',
      logo: (
        <svg className="w-12 h-12" viewBox="0 0 48 48" fill="currentColor">
          <path fill="#96BF47" d="M48 26.97c0 10.6-8.31 19.22-18.56 19.22S10.88 37.57 10.88 26.97S19.19 7.75 29.44 7.75S48 16.37 48 26.97z"/>
          <path fill="#5E8E3E" d="M12.24 16.37h.25c2.67 0 5.21-.45 7.73-.22a15.91 15.91 0 00-2.59-7.59c-1.67.01-3.33.28-4.05 2.32-.68 1.94-.54 3.7-.38 3.7-.16.05-.32.05-.49.05-.01-.45-.02-.9-.03-1.35-.02-.9-.04-1.8-.02-2.7 0-.15-.01-.23-.1-.28-.04-.02-.08-.03-.12-.02-.01 0-.02.01-.03.01H12.24z"/>
        </svg>
      ),
      className: 'bg-white rounded-lg w-16 h-12 flex items-center justify-center'
    },
    {
      name: 'Microsoft',
      logo: (
        <svg className="w-12 h-12" viewBox="0 0 24 24" fill="none">
          <rect fill="#F25022" x="1" y="1" width="10" height="10"/>
          <rect fill="#7FBA00" x="13" y="1" width="10" height="10"/>
          <rect fill="#00A4EF" x="1" y="13" width="10" height="10"/>
          <rect fill="#FFB900" x="13" y="13" width="10" height="10"/>
        </svg>
      ),
      className: 'bg-white rounded-lg w-16 h-12 flex items-center justify-center'
    },
    {
      name: 'Stripe',
      logo: (
        <svg className="w-12 h-12" viewBox="0 0 24 24" fill="currentColor">
          <path fill="#635BFF" d="M13.976 9.15a4.42 4.42 0 0 0-.46-.53c2.7-.68 4.6-2.7 5.38-5.15C19.17 6.34 17.49 9.15 13.976 9.15zM11.976 9.15a4.3 4.3 0 0 1-.46-.53C9.816 7.94 8.036 5.85 6.596 3.52A12.27 12.27 0 0 1 10.056 9.15C11.106 9.15 11.596 9.15 11.976 9.15zM6.826 20.62C5.396 18.29 7.176 16.2 9.816 14.39c2.6 1.7 4.48 4.78 5.42 8.25-3.43 2.08-8.41-1.68-8.41-2.02zm15.16-5.47c.14-.85.14-1.7 0-2.55-.46-0.23-.92-.46-1.38-.69.84 2.2.95 4.77-.05 7.2 3.44-.68 5.88-2.73 6.94-5.83-.51-.34-1.01-.68-1.51-1.02zm-15.09.4c.54 2.06 1.12 4.23 2.14 6.22l1.63-.8c-1.17-1.73-1.5-3.89-1.02-6.07-0.77-.69-1.53-1.38-2.3-2.07-.13 1.62.99 3.64 2.55 2.72zm2.82 6.93c.46 1.01.95 1.99 1.47 2.95 1.51.46 3.03.9 4.56 1.33-.46-1.01-.9-2.03-1.33-3.05.41-0.89.82-1.78 1.24-2.67a52.26 52.26 0 0 0-6.94 1.54zm12.63-.69c-0.77.77-1.54 1.54-2.31 2.31-1.06-.52-2.11-1.05-3.17-1.57 0.46-1.01 0.93-2.03 1.41-3.04.89-0.64 1.78-1.28 2.67-1.93.34.34.68.68 1.02 1.02zm0 0"/>
        </svg>
      ),
      className: 'bg-white rounded-lg w-16 h-12 flex items-center justify-center'
    }
  ];

  // Duplicate logos for seamless scrolling
  const duplicatedLogos = [...logos, ...logos, ...logos];

  return (
    <div className={`overflow-hidden w-full ${className}`}>
      <div 
        className="flex items-center gap-8 whitespace-nowrap"
        style={{
          animation: `scroll ${speed}s linear infinite`,
          width: 'fit-content'
        }}
      >
        {duplicatedLogos.map((logo, index) => (
          <div
            key={`${logo.name}-${index}`}
            className="flex items-center justify-center px-6 py-3 opacity-80 hover:opacity-100 transition-opacity duration-300"
          >
            <div className={`${logo.className} flex-shrink-0`}>
              {logo.logo}
            </div>
          </div>
        ))}
      </div>

      {/* CSS Animation */}
      <style jsx>{`
        @keyframes scroll {
          0% {
            transform: translateX(0);
          }
          100% {
            transform: translateX(-33.333%);
          }
        }
      `}</style>
    </div>
  );
};

export default LogoTicker;
