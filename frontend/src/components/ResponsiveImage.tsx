import React from 'react';

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
    return originalSrc.replace(/\.(png|jpg|jpeg)$/i, `.webp`);
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
