/**
 * Image Optimization Utilities
 * WebP/AVIF support, lazy loading, and responsive images
 */

import React from 'react'

interface OptimizedImageProps {
  src: string
  alt: string
  width?: number
  height?: number
  className?: string
  priority?: boolean
  sizes?: string
  quality?: number
  style?: React.CSSProperties
  onClick?: () => void
}

export const OptimizedImage: React.FC<OptimizedImageProps> = ({
  src,
  alt,
  width,
  height,
  className = '',
  priority = false,
  sizes = '100vw',
  quality = 75,
  style,
  onClick
}) => {
  const [isLoaded, setIsLoaded] = React.useState(false)
  const [isInView, setIsInView] = React.useState(priority)
  const imgRef = React.useRef<HTMLImageElement>(null)

  // Intersection Observer for lazy loading
  React.useEffect(() => {
    if (priority) return

    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setIsInView(true)
          observer.disconnect()
        }
      },
      { threshold: 0.1 }
    )

    if (imgRef.current) {
      observer.observe(imgRef.current)
    }

    return () => observer.disconnect()
  }, [priority])

  // Generate optimized image sources
  const generateSrcSet = (baseSrc: string) => {
    const baseName = baseSrc.replace(/\.[^/.]+$/, '')
    
    return {
      webp: `${baseName}.webp`,
      avif: `${baseName}.avif`,
      fallback: baseSrc
    }
  }

  const imageSources = generateSrcSet(src)

  return (
    <div ref={imgRef} className={`relative overflow-hidden ${className}`}>
      {isInView && (
        <picture>
          {/* AVIF format for modern browsers */}
          <source
            srcSet={imageSources.avif}
            type="image/avif"
            sizes={sizes}
          />
          {/* WebP format for good browser support */}
          <source
            srcSet={imageSources.webp}
            type="image/webp"
            sizes={sizes}
          />
          {/* Fallback for older browsers */}
          <img
            src={imageSources.fallback}
            alt={alt}
            width={width}
            height={height}
            sizes={sizes}
            loading={priority ? 'eager' : 'lazy'}
            decoding="async"
            onLoad={() => setIsLoaded(true)}
            onClick={onClick}
            className={`transition-opacity duration-300 ${
              isLoaded ? 'opacity-100' : 'opacity-0'
            }`}
            style={{
              width: width ? `${width}px` : '100%',
              height: height ? `${height}px` : 'auto',
              ...style
            }}
          />
        </picture>
      )}
      
      {/* Loading placeholder */}
      {!isLoaded && isInView && (
        <div
          className="absolute inset-0 bg-gray-200 animate-pulse"
          style={{
            width: width ? `${width}px` : '100%',
            height: height ? `${height}px` : '200px'
          }}
        />
      )}
    </div>
  )
}

// Responsive image component
export const ResponsiveImage: React.FC<{
  src: string
  alt: string
  className?: string
  breakpoints?: { [key: string]: string }
}> = ({ src, alt, className = '', breakpoints = {} }) => {
  const defaultBreakpoints = {
    mobile: '480w',
    tablet: '768w',
    desktop: '1024w',
    large: '1920w'
  }

  const mergedBreakpoints = { ...defaultBreakpoints, ...breakpoints }
  const srcSet = Object.entries(mergedBreakpoints)
    .map(([size, width]) => `${src}?w=${width} ${width}`)
    .join(', ')

  return (
    <OptimizedImage
      src={src}
      alt={alt}
      className={className}
      sizes="(max-width: 480px) 100vw, (max-width: 768px) 50vw, (max-width: 1024px) 33vw, 25vw"
    />
  )
}

// Hero image with parallax effect
export const HeroImage: React.FC<{
  src: string
  alt: string
  className?: string
  overlay?: boolean
}> = ({ src, alt, className = '', overlay = true }) => {
  const [scrollY, setScrollY] = React.useState(0)

  React.useEffect(() => {
    const handleScroll = () => setScrollY(window.scrollY)
    window.addEventListener('scroll', handleScroll)
    return () => window.removeEventListener('scroll', handleScroll)
  }, [])

  return (
    <div className={`relative overflow-hidden ${className}`}>
      <OptimizedImage
        src={src}
        alt={alt}
        className="w-full h-full object-cover"
        style={{
          transform: `translateY(${scrollY * 0.5}px)`,
          height: '100vh'
        }}
      />
      {overlay && (
        <div className="absolute inset-0 bg-black bg-opacity-40" />
      )}
    </div>
  )
}

// Image gallery with lazy loading
export const ImageGallery: React.FC<{
  images: Array<{
    src: string
    alt: string
    thumbnail?: string
  }>
  className?: string
}> = ({ images, className = '' }) => {
  const [selectedImage, setSelectedImage] = React.useState<number | null>(null)

  return (
    <div className={`grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4 ${className}`}>
      {images.map((image, index) => (
        <OptimizedImage
          key={index}
          src={image.thumbnail || image.src}
          alt={image.alt}
          className="cursor-pointer hover:opacity-80 transition-opacity"
          onClick={() => setSelectedImage(index)}
          sizes="(max-width: 768px) 50vw, (max-width: 1024px) 33vw, 25vw"
        />
      ))}
      
      {/* Lightbox modal */}
      {selectedImage !== null && (
        <div
          className="fixed inset-0 bg-black bg-opacity-90 z-50 flex items-center justify-center p-4"
          onClick={() => setSelectedImage(null)}
        >
          <OptimizedImage
            src={images[selectedImage].src}
            alt={images[selectedImage].alt}
            className="max-w-full max-h-full object-contain"
            priority
          />
        </div>
      )}
    </div>
  )
}
