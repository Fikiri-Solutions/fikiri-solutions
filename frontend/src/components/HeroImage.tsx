import React from 'react';

export function HeroImage() {
  return (
    <picture>
      <source srcSet="/optimized/img/hero.avif" type="image/avif" />
      <source srcSet="/optimized/img/hero.webp" type="image/webp" />
      <img
        src="/img/hero.png"             // final fallback
        alt="Fikiri Solutions automation preview"
        width={1600}
        height={900}
        loading="eager"                  // above the fold
        fetchPriority="high"             // Chrome: prioritize for LCP
        style={{ width: "100%", height: "auto" }}
      />
    </picture>
  );
}
