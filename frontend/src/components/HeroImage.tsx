import React from 'react';
import { publicAsset } from '../lib/publicAsset';

export function HeroImage() {
  return (
    <picture>
      <source srcSet={publicAsset('optimized/img/hero.avif')} type="image/avif" />
      <source srcSet={publicAsset('optimized/img/hero.webp')} type="image/webp" />
      <img
        src={publicAsset('img/hero.png')}
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
