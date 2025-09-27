import React from 'react';

// Accessibility Provider Component
export const AccessibilityProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  return (
    <>
      <SkipToContent />
      <KeyboardNavigation />
      <ColorContrastChecker />
      {children}
    </>
  );
};

// Skip to Content Link
export const SkipToContent: React.FC = () => {
  return (
    <a
      href="#main-content"
      className="sr-only focus:not-sr-only focus:absolute focus:top-4 focus:left-4 bg-brand-primary text-white px-4 py-2 rounded-lg z-50 focus:outline-none focus:ring-2 focus:ring-brand-accent"
      onClick={(e) => {
        e.preventDefault();
        const mainContent = document.getElementById('main-content');
        if (mainContent) {
          mainContent.focus();
          mainContent.scrollIntoView({ behavior: 'smooth' });
        }
      }}
    >
      Skip to main content
    </a>
  );
};

// Keyboard Navigation Handler
export const KeyboardNavigation: React.FC = () => {
  React.useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Alt + M: Focus main content
      if (e.altKey && e.key === 'm') {
        e.preventDefault();
        const mainContent = document.getElementById('main-content');
        if (mainContent) {
          mainContent.focus();
        }
      }
      
      // Alt + N: Focus navigation
      if (e.altKey && e.key === 'n') {
        e.preventDefault();
        const nav = document.querySelector('nav');
        if (nav) {
          const firstLink = nav.querySelector('a') as HTMLElement;
          if (firstLink) {
            firstLink.focus();
          }
        }
      }
      
      // Alt + S: Focus search
      if (e.altKey && e.key === 's') {
        e.preventDefault();
        const search = document.querySelector('input[type="search"], input[placeholder*="search" i]') as HTMLElement;
        if (search) {
          search.focus();
        }
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, []);

  return null;
};

// Color Contrast Checker
export const ColorContrastChecker: React.FC = () => {
  const checkContrast = (foreground: string, background: string): number => {
    // Convert hex to RGB
    const hexToRgb = (hex: string) => {
      const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
      return result ? {
        r: parseInt(result[1], 16),
        g: parseInt(result[2], 16),
        b: parseInt(result[3], 16)
      } : null;
    };

    const getLuminance = (r: number, g: number, b: number) => {
      const [rs, gs, bs] = [r, g, b].map(c => {
        c = c / 255;
        return c <= 0.03928 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4);
      });
      return 0.2126 * rs + 0.7152 * gs + 0.0722 * bs;
    };

    const fgRgb = hexToRgb(foreground);
    const bgRgb = hexToRgb(background);
    
    if (!fgRgb || !bgRgb) return 0;

    const fgLuminance = getLuminance(fgRgb.r, fgRgb.g, fgRgb.b);
    const bgLuminance = getLuminance(bgRgb.r, bgRgb.g, bgRgb.b);
    
    const lighter = Math.max(fgLuminance, bgLuminance);
    const darker = Math.min(fgLuminance, bgLuminance);
    
    return (lighter + 0.05) / (darker + 0.05);
  };

  React.useEffect(() => {
    // Check brand color contrasts
    const brandColors = {
      primary: '#B33B1E',
      secondary: '#E7641C',
      accent: '#F39C12',
      text: '#4B1E0C',
      background: '#F7F3E9'
    };

    const contrasts = {
      'Primary on Background': checkContrast(brandColors.primary, brandColors.background),
      'Text on Background': checkContrast(brandColors.text, brandColors.background),
      'Accent on Background': checkContrast(brandColors.accent, brandColors.background),
      'White on Primary': checkContrast('#FFFFFF', brandColors.primary),
      'White on Secondary': checkContrast('#FFFFFF', brandColors.secondary)
    };

    // Log contrast ratios for debugging
    console.log('Brand Color Contrast Ratios:', contrasts);
    
    // Warn about low contrast
    Object.entries(contrasts).forEach(([pair, ratio]) => {
      if (ratio < 4.5) {
        console.warn(`Low contrast warning: ${pair} has ratio ${ratio.toFixed(2)} (minimum 4.5 recommended)`);
      }
    });
  }, []);

  return null;
};

// Focus Management Hook
export const useFocusManagement = () => {
  const focusableElements = 'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])';
  
  const trapFocus = (element: HTMLElement) => {
    const focusableContent = element.querySelectorAll(focusableElements);
    const firstFocusableElement = focusableContent[0] as HTMLElement;
    const lastFocusableElement = focusableContent[focusableContent.length - 1] as HTMLElement;

    element.addEventListener('keydown', (e) => {
      if (e.key === 'Tab') {
        if (e.shiftKey) {
          if (document.activeElement === firstFocusableElement) {
            lastFocusableElement.focus();
            e.preventDefault();
          }
        } else {
          if (document.activeElement === lastFocusableElement) {
            firstFocusableElement.focus();
            e.preventDefault();
          }
        }
      }
    });
  };

  const restoreFocus = (previousElement: HTMLElement | null) => {
    if (previousElement) {
      previousElement.focus();
    }
  };

  return { trapFocus, restoreFocus };
};

// Screen Reader Announcements
export const useScreenReaderAnnouncement = () => {
  const announce = (message: string, priority: 'polite' | 'assertive' = 'polite') => {
    const announcement = document.createElement('div');
    announcement.setAttribute('aria-live', priority);
    announcement.setAttribute('aria-atomic', 'true');
    announcement.className = 'sr-only';
    announcement.textContent = message;
    
    document.body.appendChild(announcement);
    
    setTimeout(() => {
      document.body.removeChild(announcement);
    }, 1000);
  };

  return { announce };
};

export default AccessibilityProvider;
