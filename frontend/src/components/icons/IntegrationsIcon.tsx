import React from 'react'

export function IntegrationsIcon({ className = "w-full h-full" }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 200 200"
      className={className}
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
    >
      {/* Central hub shadow */}
      <ellipse
        cx="100"
        cy="110"
        rx="32"
        ry="5"
        fill="#1a1a1a"
        opacity="0.25"
      />
      
      {/* Central hub */}
      <circle
        cx="100"
        cy="100"
        r="35"
        fill="url(#hubGradient)"
        stroke="white"
        strokeWidth="2.5"
        opacity="0.98"
      />
      
      {/* Hub highlight */}
      <circle
        cx="100"
        cy="100"
        r="35"
        fill="url(#hubHighlight)"
        opacity="0.3"
      />
      {/* Central symbol - connected nodes */}
      <g transform="translate(100, 100)">
        <circle cx="-12" cy="-12" r="4" fill="white" />
        <circle cx="12" cy="-12" r="4" fill="white" />
        <circle cx="0" cy="12" r="4" fill="white" />
        <line x1="-12" y1="-12" x2="12" y2="-12" stroke="white" strokeWidth="2" />
        <line x1="-12" y1="-12" x2="0" y2="12" stroke="white" strokeWidth="2" />
        <line x1="12" y1="-12" x2="0" y2="12" stroke="white" strokeWidth="2" />
      </g>
      
      {/* Top-left icon - Gmail/Mail */}
      <g transform="translate(50, 50)">
        <ellipse cx="0" cy="22" rx="18" ry="3" fill="#1a1a1a" opacity="0.15" />
        <circle cx="0" cy="0" r="20" fill="white" stroke="#737373" strokeWidth="1.5" />
        <circle cx="0" cy="0" r="20" fill="url(#iconHighlight)" opacity="0.2" />
        <text x="0" y="8" fontSize="26" fontWeight="bold" fill="url(#mailGradient)" textAnchor="middle" fontFamily="system-ui, sans-serif">M</text>
        {/* Connecting line */}
        <path
          d="M20 0 Q75 25, 65 65"
          stroke="url(#lineGradient1)"
          strokeWidth="3.5"
          fill="none"
          strokeLinecap="round"
        />
      </g>
      
      {/* Top-right icon - Calendar */}
      <g transform="translate(150, 50)">
        <ellipse cx="0" cy="22" rx="18" ry="3" fill="#1a1a1a" opacity="0.15" />
        <circle cx="0" cy="0" r="20" fill="white" stroke="#737373" strokeWidth="1.5" />
        <circle cx="0" cy="0" r="20" fill="url(#iconHighlight)" opacity="0.2" />
        <rect x="-8" y="-6" width="16" height="12" rx="2" fill="url(#calendarGradient1)" />
        <rect x="-8" y="-6" width="16" height="3" fill="#992D1E" />
        <circle cx="6" cy="4" r="2.5" fill="#F39C12" />
        {/* Connecting line */}
        <path
          d="M-20 0 Q-75 25, -65 65"
          stroke="url(#lineGradient2)"
          strokeWidth="3.5"
          fill="none"
          strokeLinecap="round"
        />
      </g>
      
      {/* Bottom-right icon - Cloud */}
      <g transform="translate(150, 150)">
        <ellipse cx="0" cy="22" rx="18" ry="3" fill="#1a1a1a" opacity="0.15" />
        <circle cx="0" cy="0" r="20" fill="white" stroke="#737373" strokeWidth="1.5" />
        <circle cx="0" cy="0" r="20" fill="url(#iconHighlight)" opacity="0.2" />
        <path
          d="M-8 -2 Q-12 -6, -8 -6 Q-4 -10, 0 -6 Q4 -10, 8 -6 Q12 -6, 8 -2 L8 4 Q8 8, 4 8 L-4 8 Q-8 8, -8 4 Z"
          fill="url(#cloudGradient)"
        />
        {/* Connecting line */}
        <path
          d="M-20 0 Q-75 -25, -65 -65"
          stroke="url(#lineGradient3)"
          strokeWidth="3.5"
          fill="none"
          strokeLinecap="round"
        />
      </g>
      
      {/* Bottom-left icon - Calendar */}
      <g transform="translate(50, 150)">
        <ellipse cx="0" cy="22" rx="18" ry="3" fill="#1a1a1a" opacity="0.15" />
        <circle cx="0" cy="0" r="20" fill="white" stroke="#737373" strokeWidth="1.5" />
        <circle cx="0" cy="0" r="20" fill="url(#iconHighlight)" opacity="0.2" />
        <rect x="-8" y="-6" width="16" height="12" rx="2" fill="url(#calendarGradient2)" />
        <rect x="-8" y="-6" width="16" height="3" fill="#B33B1E" />
        <text x="0" y="6" fontSize="13" fontWeight="bold" fill="white" textAnchor="middle" fontFamily="system-ui, sans-serif">31</text>
        <path d="M6 8 L8 10 L6 10 Z" fill="#E7641C" />
        {/* Connecting line */}
        <path
          d="M20 0 Q75 -25, 65 -65"
          stroke="url(#lineGradient4)"
          strokeWidth="3.5"
          fill="none"
          strokeLinecap="round"
        />
      </g>
      
      <defs>
        <linearGradient id="hubGradient" x1="65" y1="65" x2="135" y2="135">
          <stop offset="0%" stopColor="#B33B1E" />
          <stop offset="50%" stopColor="#E7641C" />
          <stop offset="100%" stopColor="#992D1E" />
        </linearGradient>
        <radialGradient id="hubHighlight" cx="50%" cy="30%">
          <stop offset="0%" stopColor="#FFFFFF" stopOpacity="0.6" />
          <stop offset="100%" stopColor="#FFFFFF" stopOpacity="0" />
        </radialGradient>
        <radialGradient id="iconHighlight" cx="50%" cy="30%">
          <stop offset="0%" stopColor="#FFFFFF" stopOpacity="0.4" />
          <stop offset="100%" stopColor="#FFFFFF" stopOpacity="0" />
        </radialGradient>
        <linearGradient id="mailGradient" x1="0" y1="0" x2="0" y2="16">
          <stop offset="0%" stopColor="#E7641C" />
          <stop offset="100%" stopColor="#B33B1E" />
        </linearGradient>
        <linearGradient id="calendarGradient1" x1="-8" y1="-6" x2="-8" y2="6">
          <stop offset="0%" stopColor="#E7641C" />
          <stop offset="100%" stopColor="#B33B1E" />
        </linearGradient>
        <linearGradient id="calendarGradient2" x1="-8" y1="-6" x2="-8" y2="6">
          <stop offset="0%" stopColor="#B33B1E" />
          <stop offset="100%" stopColor="#992D1E" />
        </linearGradient>
        <linearGradient id="cloudGradient" x1="-8" y1="-6" x2="8" y2="8">
          <stop offset="0%" stopColor="#B33B1E" />
          <stop offset="33%" stopColor="#E7641C" />
          <stop offset="66%" stopColor="#F39C12" />
          <stop offset="100%" stopColor="#992D1E" />
        </linearGradient>
        <linearGradient id="lineGradient1" x1="20" y1="0" x2="65" y2="65">
          <stop offset="0%" stopColor="#E7641C" />
          <stop offset="100%" stopColor="#B33B1E" />
        </linearGradient>
        <linearGradient id="lineGradient2" x1="-20" y1="0" x2="-65" y2="65">
          <stop offset="0%" stopColor="#B33B1E" />
          <stop offset="100%" stopColor="#992D1E" />
        </linearGradient>
        <linearGradient id="lineGradient3" x1="-20" y1="0" x2="-65" y2="-65">
          <stop offset="0%" stopColor="#F39C12" />
          <stop offset="100%" stopColor="#E7641C" />
        </linearGradient>
        <linearGradient id="lineGradient4" x1="20" y1="0" x2="65" y2="-65">
          <stop offset="0%" stopColor="#992D1E" />
          <stop offset="100%" stopColor="#B33B1E" />
        </linearGradient>
      </defs>
    </svg>
  )
}
