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
  textColor?: 'default' | 'white' | 'light'; // For text color on dark backgrounds
}

export const FikiriLogo: React.FC<FikiriLogoProps> = ({ 
  size = 'md', 
  variant = 'circle',
  className = '',
  animated = false,
  showText = false,
  textColor = 'default'
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
    // Determine text styling based on textColor prop
    const isLightText = textColor === 'white' || textColor === 'light'
    const textSizeClasses = {
      xs: 'text-sm',
      sm: 'text-base',
      md: 'text-lg',
      lg: 'text-xl',
      xl: 'text-2xl',
      '2xl': 'text-3xl',
      '3xl': 'text-4xl'
    }
    const subtextSizeClasses = {
      xs: 'text-xs',
      sm: 'text-sm',
      md: 'text-base',
      lg: 'text-lg',
      xl: 'text-lg',
      '2xl': 'text-xl',
      '3xl': 'text-2xl'
    }
    
    return (
      <div className={`flex items-center space-x-4 ${className}`}>
        <img 
          src={logoCircle}
          alt="Fikiri Solutions"
          className={`${sizeClasses[size]} ${animationClass}`}
        />
        <div className="flex flex-col">
          {isLightText ? (
            <>
              <span className={`${textSizeClasses[size]} font-bold text-white tracking-wide drop-shadow-lg`}>FIKIRI</span>
              <span className={`${subtextSizeClasses[size]} font-medium text-white tracking-wide drop-shadow-lg`}>SOLUTIONS</span>
            </>
          ) : (
            <>
              <span className={`${textSizeClasses[size]} font-bold bg-gradient-to-r from-orange-400 via-orange-500 to-red-600 bg-clip-text text-transparent tracking-wide`} style={{
                background: 'linear-gradient(to right, #FF6B35, #D2691E, #8B0000)',
                WebkitBackgroundClip: 'text',
                WebkitTextFillColor: 'transparent'
              }}>FIKIRI</span>
              <span className={`${subtextSizeClasses[size]} font-medium bg-gradient-to-r from-orange-400 via-orange-500 to-red-600 bg-clip-text text-transparent tracking-wide`} style={{
                background: 'linear-gradient(to right, #FF6B35, #D2691E, #8B0000)',
                WebkitBackgroundClip: 'text',
                WebkitTextFillColor: 'transparent'
              }}>SOLUTIONS</span>
            </>
          )}
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
