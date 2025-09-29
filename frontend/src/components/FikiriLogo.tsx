import React from 'react';
import logoFull from '../assets/logo-full.png';
import logoCircle from '../assets/logo-circle.png';
import logoMonochrome from '../assets/logo-monochrome.png';
import logoWhite from '../assets/logo-white.png';

interface FikiriLogoProps {
  size?: 'xs' | 'sm' | 'md' | 'lg' | 'xl' | '2xl' | '3xl';
  variant?: 'full' | 'circle' | 'monochrome' | 'white';
  className?: string;
  animated?: boolean;
  showText?: boolean;
}

export const FikiriLogo: React.FC<FikiriLogoProps> = ({ 
  size = 'md', 
  variant = 'circle',
  className = '',
  animated = false,
  showText = false
}) => {
  const sizeClasses = {
    xs: 'h-8',
    sm: 'h-12',
    md: 'h-16',
    lg: 'h-20',
    xl: 'h-24',
    '2xl': 'h-32',
    '3xl': 'h-40'
  };

  const logoSrc = {
    full: logoFull,
    circle: logoCircle,
    monochrome: logoMonochrome,
    white: logoWhite
  };

  const animationClass = animated ? 'animate-pulse' : '';

  if (variant === 'full' || showText) {
    return (
      <div className={`flex items-center space-x-4 ${className}`}>
        <img 
          src={logoCircle}
          alt="Fikiri Solutions"
          className={`${sizeClasses[size]} ${animationClass}`}
        />
        <div className="flex flex-col">
          <span className="text-xl font-bold bg-gradient-to-r from-orange-400 via-orange-500 to-red-600 bg-clip-text text-transparent tracking-wide" style={{
            background: 'linear-gradient(to right, #FF6B35, #D2691E, #8B0000)',
            WebkitBackgroundClip: 'text',
            WebkitTextFillColor: 'transparent'
          }}>FIKIRI</span>
          <span className="text-base font-medium bg-gradient-to-r from-orange-400 via-orange-500 to-red-600 bg-clip-text text-transparent tracking-wide" style={{
            background: 'linear-gradient(to right, #FF6B35, #D2691E, #8B0000)',
            WebkitBackgroundClip: 'text',
            WebkitTextFillColor: 'transparent'
          }}>SOLUTIONS</span>
        </div>
      </div>
    );
  }

  return (
    <img 
      src={logoSrc[variant]}
      alt="Fikiri Solutions"
      className={`${sizeClasses[size]} ${animationClass} ${className}`}
    />
  );
};


export default FikiriLogo;
