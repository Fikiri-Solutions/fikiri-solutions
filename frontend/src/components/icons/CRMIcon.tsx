import React from 'react'

export function CRMIcon({ className = "w-full h-full" }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 200 160"
      className={className}
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
    >
      {/* Swirling base shapes with highlights - pushed down for gap below CRM text */}
      <path
        d="M20 145 Q60 118, 100 128 T180 145 Q160 158, 100 152 T20 145"
        fill="url(#swirlGradient1)"
        opacity="0.95"
      />
      <path
        d="M180 145 Q140 118, 100 128 T20 145 Q40 158, 100 152 T180 145"
        fill="url(#swirlGradient2)"
        opacity="0.95"
      />
      
      {/* Swirl highlights */}
      <path
        d="M20 145 Q60 118, 100 128 T180 145 Q160 158, 100 152 T20 145"
        fill="url(#swirlHighlight1)"
        opacity="0.4"
      />
      <path
        d="M180 145 Q140 118, 100 128 T20 145 Q40 158, 100 152 T180 145"
        fill="url(#swirlHighlight2)"
        opacity="0.4"
      />
      
      {/* Three figures with glossy effect */}
      {/* Left figure - Golden */}
      <g transform="translate(50, 35)">
        <circle cx="0" cy="0" r="13" fill="url(#figureGradient1)" />
        <circle cx="-4" cy="-4" r="5" fill="#FFFFFF" opacity="0.5" />
        <rect x="-9" y="9" width="18" height="22" rx="5" fill="url(#figureGradient1)" />
        <rect x="-9" y="9" width="18" height="6" rx="5" fill="#FFFFFF" opacity="0.3" />
      </g>
      
      {/* Center figure - Orange (larger) */}
      <g transform="translate(100, 25)">
        <circle cx="0" cy="0" r="15" fill="url(#figureGradient2)" />
        <circle cx="-5" cy="-5" r="6" fill="#FFFFFF" opacity="0.6" />
        <rect x="-11" y="11" width="22" height="26" rx="6" fill="url(#figureGradient2)" />
        <rect x="-11" y="11" width="22" height="7" rx="6" fill="#FFFFFF" opacity="0.4" />
      </g>
      
      {/* Right figure - Red-orange */}
      <g transform="translate(150, 35)">
        <circle cx="0" cy="0" r="13" fill="url(#figureGradient3)" />
        <circle cx="-4" cy="-4" r="5" fill="#FFFFFF" opacity="0.5" />
        <rect x="-9" y="9" width="18" height="22" rx="5" fill="url(#figureGradient3)" />
        <rect x="-9" y="9" width="18" height="6" rx="5" fill="#FFFFFF" opacity="0.3" />
      </g>
      
      {/* CRM Text with 3D effect */}
      <text
        x="100"
        y="110"
        fontSize="36"
        fontWeight="bold"
        fill="url(#textGradient)"
        textAnchor="middle"
        fontFamily="system-ui, sans-serif"
        style={{ filter: 'drop-shadow(0 2px 4px rgba(0,0,0,0.2))' }}
      >
        CRM
      </text>
      {/* Text highlight */}
      <text
        x="100"
        y="110"
        fontSize="36"
        fontWeight="bold"
        fill="url(#textHighlight)"
        textAnchor="middle"
        fontFamily="system-ui, sans-serif"
        opacity="0.3"
      >
        CRM
      </text>
      
      <defs>
        <linearGradient id="swirlGradient1" x1="20" y1="145" x2="180" y2="145">
          <stop offset="0%" stopColor="#B33B1E" />
          <stop offset="50%" stopColor="#E7641C" />
          <stop offset="100%" stopColor="#F39C12" />
        </linearGradient>
        <linearGradient id="swirlGradient2" x1="180" y1="145" x2="20" y2="145">
          <stop offset="0%" stopColor="#E7641C" />
          <stop offset="50%" stopColor="#F39C12" />
          <stop offset="100%" stopColor="#B33B1E" />
        </linearGradient>
        <linearGradient id="swirlHighlight1" x1="20" y1="145" x2="100" y2="128">
          <stop offset="0%" stopColor="#FFFFFF" stopOpacity="0.3" />
          <stop offset="100%" stopColor="#FFFFFF" stopOpacity="0" />
        </linearGradient>
        <linearGradient id="swirlHighlight2" x1="180" y1="145" x2="100" y2="128">
          <stop offset="0%" stopColor="#FFFFFF" stopOpacity="0.3" />
          <stop offset="100%" stopColor="#FFFFFF" stopOpacity="0" />
        </linearGradient>
        <linearGradient id="figureGradient1" x1="0" y1="0" x2="0" y2="31">
          <stop offset="0%" stopColor="#F39C12" />
          <stop offset="100%" stopColor="#E7641C" />
        </linearGradient>
        <linearGradient id="figureGradient2" x1="0" y1="0" x2="0" y2="37">
          <stop offset="0%" stopColor="#E7641C" />
          <stop offset="100%" stopColor="#B33B1E" />
        </linearGradient>
        <linearGradient id="figureGradient3" x1="0" y1="0" x2="0" y2="31">
          <stop offset="0%" stopColor="#B33B1E" />
          <stop offset="100%" stopColor="#992D1E" />
        </linearGradient>
        <linearGradient id="textGradient" x1="70" y1="110" x2="130" y2="110">
          <stop offset="0%" stopColor="#B33B1E" />
          <stop offset="50%" stopColor="#E7641C" />
          <stop offset="100%" stopColor="#992D1E" />
        </linearGradient>
        <linearGradient id="textHighlight" x1="70" y1="105" x2="130" y2="105">
          <stop offset="0%" stopColor="#FFFFFF" stopOpacity="0.5" />
          <stop offset="100%" stopColor="#FFFFFF" stopOpacity="0" />
        </linearGradient>
      </defs>
    </svg>
  )
}
