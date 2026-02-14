import React from 'react'

export function EmailIcon({ className = "w-full h-full" }: { className?: string }) {
  const uniqueId = `envelope-${Math.random().toString(36).substr(2, 9)}`
  
  return (
    <svg
      viewBox="0 0 120 90"
      className={className}
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
    >
      <defs>
        <linearGradient id={`${uniqueId}-flap`} x1="10" y1="25" x2="110" y2="25">
          <stop offset="0%" stopColor="#F39C12" />
          <stop offset="50%" stopColor="#E7641C" />
          <stop offset="100%" stopColor="#B33B1E" />
        </linearGradient>
        <linearGradient id={`${uniqueId}-body`} x1="10" y1="25" x2="10" y2="75">
          <stop offset="0%" stopColor="#FFFFFF" />
          <stop offset="100%" stopColor="#F5F5F5" />
        </linearGradient>
        <linearGradient id={`${uniqueId}-highlight`} x1="10" y1="25" x2="110" y2="25">
          <stop offset="0%" stopColor="#FFFFFF" stopOpacity="0.5" />
          <stop offset="50%" stopColor="#F39C12" stopOpacity="0.3" />
          <stop offset="100%" stopColor="#FFFFFF" stopOpacity="0.2" />
        </linearGradient>
      </defs>
      
      {/* Shadow */}
      <ellipse
        cx="60"
        cy="85"
        rx="50"
        ry="4"
        fill="#1a1a1a"
        opacity="0.2"
      />
      
      {/* Envelope body - top edge at y=30 where flap meets */}
      <path
        d="M10 30 L60 58 L110 30 L110 75 L10 75 Z"
        fill={`url(#${uniqueId}-body)`}
        stroke="#B33B1E"
        strokeWidth="2.5"
      />
      
      {/* Envelope flap - folded top with clear top edge (10,18)-(110,18) */}
      <path
        d="M10 18 L110 18 L110 30 L60 58 L10 30 Z"
        fill={`url(#${uniqueId}-flap)`}
        stroke="#B33B1E"
        strokeWidth="2.5"
      />
      
      {/* Top edge of flap - distinct line so the top is clearly visible */}
      <line x1="10" y1="18" x2="110" y2="18" stroke="#992D1E" strokeWidth="2.5" strokeLinecap="round" />
      
      {/* Highlight on flap */}
      <path
        d="M10 18 L110 18 L110 30 L60 58 L10 30 Z"
        fill={`url(#${uniqueId}-highlight)`}
        opacity="0.35"
      />
      
      {/* Fold lines from flap to point */}
      <line x1="10" y1="30" x2="60" y2="58" stroke="#992D1E" strokeWidth="1.5" opacity="0.6" />
      <line x1="110" y1="30" x2="60" y2="58" stroke="#992D1E" strokeWidth="1.5" opacity="0.6" />
    </svg>
  )
}
