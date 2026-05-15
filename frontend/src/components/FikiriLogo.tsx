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
  textColor = 'default',
}) => {
  const sizeClasses = {
    xs: 'h-8',
    sm: 'h-12',
    md: 'h-16',
    lg: 'h-20',
    xl: 'h-24',
    '2xl': 'h-32',
    '3xl': 'h-40',
  };

  const logoSrc = {
    full: logoFull,
    circle: logoCircle,
    monochrome: logoMonochrome,
    white: logoWhite,
  };

  const animationClass = animated ? 'animate-pulse' : '';

  const textSizeClasses = {
    xs: 'text-sm',
    sm: 'text-base',
    md: 'text-lg',
    lg: 'text-xl',
    xl: 'text-2xl',
    '2xl': 'text-3xl',
    '3xl': 'text-4xl',
  };
  const subtextSizeClasses = {
    xs: 'text-xs',
    sm: 'text-sm',
    md: 'text-base',
    lg: 'text-lg',
    xl: 'text-lg',
    '2xl': 'text-xl',
    '3xl': 'text-2xl',
  };

  const isLightText = textColor === 'white' || textColor === 'light';

  // Full wordmark: horizontal asset on light UI; on dark backgrounds keep type horizontal (never stack words).
  if (variant === 'full') {
    if (isLightText) {
      return (
        <div className={`flex min-w-0 max-w-full flex-row items-center gap-2 sm:gap-3 ${className}`}>
          <img
            src={logoWhite}
            alt=""
            aria-hidden
            className={`h-10 w-10 shrink-0 object-contain sm:h-12 sm:w-12 ${animationClass}`}
          />
          <div className="flex min-w-0 flex-row flex-nowrap items-baseline gap-x-1.5 sm:gap-x-2">
            <span className={`${textSizeClasses[size]} font-bold tracking-wide text-white drop-shadow-lg whitespace-nowrap`}>
              FIKIRI
            </span>
            <span className={`${subtextSizeClasses[size]} font-medium tracking-wide text-white/95 drop-shadow-lg whitespace-nowrap`}>
              SOLUTIONS
            </span>
          </div>
        </div>
      );
    }

    return (
      <img
        src={logoFull}
        alt="Fikiri Solutions"
        className={`${sizeClasses[size]} w-auto max-w-full shrink-0 object-contain object-left ${animationClass} ${className}`}
      />
    );
  }

  if (showText) {
    return (
      <div className={`flex min-w-0 max-w-full flex-row items-center gap-2 sm:gap-4 ${className}`}>
        <img
          src={logoCircle}
          alt=""
          aria-hidden
          className={`${sizeClasses[size]} shrink-0 object-contain ${animationClass}`}
        />
        <div className="flex min-w-0 flex-row flex-nowrap items-baseline gap-x-1.5 sm:gap-x-2">
          {isLightText ? (
            <>
              <span className={`${textSizeClasses[size]} font-bold tracking-wide text-white drop-shadow-lg whitespace-nowrap`}>
                FIKIRI
              </span>
              <span className={`${subtextSizeClasses[size]} font-medium tracking-wide text-white drop-shadow-lg whitespace-nowrap`}>
                SOLUTIONS
              </span>
            </>
          ) : (
            <>
              <span
                className={`${textSizeClasses[size]} font-bold tracking-wide whitespace-nowrap bg-gradient-to-r from-orange-400 via-orange-500 to-red-600 bg-clip-text text-transparent`}
                style={{
                  background: 'linear-gradient(to right, #FF6B35, #D2691E, #8B0000)',
                  WebkitBackgroundClip: 'text',
                  WebkitTextFillColor: 'transparent',
                }}
              >
                FIKIRI
              </span>
              <span
                className={`${subtextSizeClasses[size]} font-medium tracking-wide whitespace-nowrap bg-gradient-to-r from-orange-400 via-orange-500 to-red-600 bg-clip-text text-transparent`}
                style={{
                  background: 'linear-gradient(to right, #FF6B35, #D2691E, #8B0000)',
                  WebkitBackgroundClip: 'text',
                  WebkitTextFillColor: 'transparent',
                }}
              >
                SOLUTIONS
              </span>
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
