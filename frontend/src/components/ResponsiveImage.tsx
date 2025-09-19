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
  // For now, just return the original image until WebP files are created
  // TODO: Implement WebP/AVIF conversion and use picture element
  return (
    <img
      src={src}
      alt={alt}
      className={className}
      loading={priority ? 'eager' : loading}
      sizes={sizes}
      decoding="async"
    />
  );
};

export default ResponsiveImage;
