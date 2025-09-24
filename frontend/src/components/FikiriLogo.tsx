import React from 'react';
import logoFull from '../assets/logo-full.svg';
import logoCircle from '../assets/logo-circle.svg';
import logoMonochrome from '../assets/logo-monochrome.svg';
import logoWhite from '../assets/logo-white.svg';

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
          <span className="text-xl font-bold text-gray-800 dark:text-white tracking-wide">FIKIRI</span>
          <span className="text-base font-medium text-gray-600 dark:text-gray-300 tracking-wide">SOLUTIONS</span>
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

// Hero Section Component with Brand Gradient
export const HeroSection: React.FC = () => {
  return (
    <section className="relative min-h-screen flex items-center justify-center overflow-hidden">
      {/* Animated Background Gradient */}
      <div className="absolute inset-0 fikiri-gradient-animated"></div>
      
      {/* Content */}
      <div className="relative z-10 text-center px-6 max-w-4xl mx-auto">
        {/* Logo */}
        <div className="mb-8">
          <FikiriLogo size="3xl" variant="white" className="mx-auto" />
        </div>
        
        {/* Main Heading */}
        <h1 className="text-5xl md:text-6xl font-bold text-white mb-6 leading-tight">
          Transform Your Business with{' '}
          <span className="text-yellow-200">AI-Powered</span> Automation
        </h1>
        
        {/* Subheading */}
        <p className="text-xl md:text-2xl text-white/90 mb-8 max-w-2xl mx-auto">
          Streamline operations, boost productivity, and scale your business with intelligent automation solutions
        </p>
        
        {/* CTA Buttons */}
        <div className="flex flex-col sm:flex-row gap-4 justify-center">
          <button className="bg-white text-brand-primary px-8 py-4 rounded-lg font-semibold text-lg hover:bg-gray-100 transition-all duration-300 transform hover:scale-105">
            Get Started Free
          </button>
          <button className="border-2 border-white text-white px-8 py-4 rounded-lg font-semibold text-lg hover:bg-white hover:text-brand-primary transition-all duration-300">
            Watch Demo
          </button>
        </div>
        
        {/* Stats */}
        <div className="mt-16 grid grid-cols-1 md:grid-cols-3 gap-8 text-white">
          <div className="text-center">
            <div className="text-3xl font-bold text-yellow-200">500+</div>
            <div className="text-lg">Businesses Transformed</div>
          </div>
          <div className="text-center">
            <div className="text-3xl font-bold text-yellow-200">95%</div>
            <div className="text-lg">Time Savings</div>
          </div>
          <div className="text-center">
            <div className="text-3xl font-bold text-yellow-200">24/7</div>
            <div className="text-lg">Automated Operations</div>
          </div>
        </div>
      </div>
      
      {/* Scroll Indicator */}
      <div className="absolute bottom-8 left-1/2 transform -translate-x-1/2 text-white animate-bounce">
        <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 14l-7 7m0 0l-7-7m7 7V3" />
        </svg>
      </div>
    </section>
  );
};

// Brand Button Component
interface BrandButtonProps {
  children: React.ReactNode;
  variant?: 'primary' | 'secondary' | 'accent';
  size?: 'sm' | 'md' | 'lg';
  className?: string;
  onClick?: () => void;
}

export const BrandButton: React.FC<BrandButtonProps> = ({
  children,
  variant = 'primary',
  size = 'md',
  className = '',
  onClick
}) => {
  const variantClasses = {
    primary: 'bg-brand-primary hover:bg-brand-secondary text-white',
    secondary: 'bg-transparent border-2 border-brand-primary text-brand-primary hover:bg-brand-primary hover:text-white',
    accent: 'bg-brand-accent hover:bg-brand-secondary text-brand-text hover:text-white'
  };

  const sizeClasses = {
    sm: 'px-4 py-2 text-sm',
    md: 'px-6 py-3 text-base',
    lg: 'px-8 py-4 text-lg'
  };

  return (
    <button
      className={`
        ${variantClasses[variant]} 
        ${sizeClasses[size]} 
        font-semibold rounded-lg transition-all duration-300 
        transform hover:scale-105 focus:outline-none focus:ring-2 
        focus:ring-brand-primary focus:ring-offset-2
        ${className}
      `}
      onClick={onClick}
    >
      {children}
    </button>
  );
};

// Brand Card Component
interface BrandCardProps {
  children: React.ReactNode;
  variant?: 'default' | 'gradient' | 'elevated';
  className?: string;
}

export const BrandCard: React.FC<BrandCardProps> = ({
  children,
  variant = 'default',
  className = ''
}) => {
  const variantClasses = {
    default: 'bg-brand-background border border-brand-text/10',
    gradient: 'fikiri-gradient-subtle border border-brand-text/10',
    elevated: 'bg-brand-background border border-brand-text/10 shadow-lg'
  };

  return (
    <div className={`
      ${variantClasses[variant]} 
      rounded-xl p-6 transition-all duration-300 
      hover:shadow-lg hover:-translate-y-1
      ${className}
    `}>
      {children}
    </div>
  );
};

export default FikiriLogo;
