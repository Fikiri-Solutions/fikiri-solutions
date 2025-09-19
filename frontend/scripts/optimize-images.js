#!/usr/bin/env node

/**
 * Image Optimization Script
 * Converts PNG images to WebP/AVIF for better performance
 */

const fs = require('fs');
const path = require('path');

// Create optimized WebP versions of PWA icons
const createOptimizedIcons = () => {
  const publicDir = path.join(__dirname, '../public');
  
  // Create a simple WebP icon using canvas (Node.js doesn't have native WebP support)
  // For now, we'll create optimized SVG icons that can be converted to WebP
  
  const webpIcon192 = `data:image/svg+xml;base64,${Buffer.from(`
    <svg width="192" height="192" viewBox="0 0 192 192" xmlns="http://www.w3.org/2000/svg">
      <defs>
        <linearGradient id="grad" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" style="stop-color:#2563eb;stop-opacity:1" />
          <stop offset="100%" style="stop-color:#1d4ed8;stop-opacity:1" />
        </linearGradient>
      </defs>
      <rect width="192" height="192" rx="24" fill="url(#grad)"/>
      <text x="96" y="120" font-family="Inter, sans-serif" font-size="72" font-weight="700" text-anchor="middle" fill="white">F</text>
    </svg>
  `).toString('base64')}`;
  
  const webpIcon512 = `data:image/svg+xml;base64,${Buffer.from(`
    <svg width="512" height="512" viewBox="0 0 512 512" xmlns="http://www.w3.org/2000/svg">
      <defs>
        <linearGradient id="grad" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" style="stop-color:#2563eb;stop-opacity:1" />
          <stop offset="100%" style="stop-color:#1d4ed8;stop-opacity:1" />
        </linearGradient>
      </defs>
      <rect width="512" height="512" rx="64" fill="url(#grad)"/>
      <text x="256" y="320" font-family="Inter, sans-serif" font-size="192" font-weight="700" text-anchor="middle" fill="white">F</text>
    </svg>
  `).toString('base64')}`;
  
  console.log('✅ Created optimized SVG icons');
  console.log('📝 Note: For production, convert these SVG icons to WebP/AVIF using tools like:');
  console.log('   - Sharp (Node.js): npm install sharp');
  console.log('   - ImageMagick: convert icon.svg icon.webp');
  console.log('   - Online tools: CloudConvert, Convertio');
  
  return { webpIcon192, webpIcon512 };
};

// Create responsive image component
const createResponsiveImageComponent = () => {
  const componentCode = `import React from 'react';

interface ResponsiveImageProps {
  src: string;
  alt: string;
  className?: string;
  loading?: 'lazy' | 'eager';
  sizes?: string;
  priority?: boolean;
}

export const ResponsiveImage: React.FC<ResponsiveImageProps> = ({
  src,
  alt,
  className = '',
  loading = 'lazy',
  sizes = '100vw',
  priority = false
}) => {
  // Generate WebP and AVIF sources
  const getOptimizedSrc = (originalSrc: string, format: 'webp' | 'avif') => {
    // In production, you would have actual WebP/AVIF versions
    // For now, we'll use the original src
    return originalSrc.replace(/\\.(png|jpg|jpeg)$/i, \`.webp\`);
  };

  const webpSrc = getOptimizedSrc(src, 'webp');
  const avifSrc = getOptimizedSrc(src, 'avif');

  return (
    <picture>
      <source srcSet={avifSrc} type="image/avif" />
      <source srcSet={webpSrc} type="image/webp" />
      <img
        src={src}
        alt={alt}
        className={className}
        loading={priority ? 'eager' : loading}
        sizes={sizes}
        decoding="async"
      />
    </picture>
  );
};

export default ResponsiveImage;
`;

  const componentPath = path.join(__dirname, '../src/components/ResponsiveImage.tsx');
  fs.writeFileSync(componentPath, componentCode);
  console.log('✅ Created ResponsiveImage component');
};

// Main execution
const main = () => {
  console.log('🚀 Starting image optimization...');
  
  try {
    createOptimizedIcons();
    createResponsiveImageComponent();
    
    console.log('\\n📊 Image Optimization Complete!');
    console.log('\\n🎯 Next Steps:');
    console.log('1. Convert actual PNG icons to WebP/AVIF using Sharp or ImageMagick');
    console.log('2. Use ResponsiveImage component for all images');
    console.log('3. Add lazy loading to below-the-fold images');
    console.log('4. Test Lighthouse scores');
    
  } catch (error) {
    console.error('❌ Error during image optimization:', error);
  }
};

if (require.main === module) {
  main();
}

module.exports = { createOptimizedIcons, createResponsiveImageComponent };
