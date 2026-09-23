import { Helmet } from 'react-helmet-async'
import {
  absoluteUrl,
  DEFAULT_OG_IMAGE,
  getPublicPageSeo,
  type PublicPageSeo,
} from '../lib/publicPageSeo'

type PageMetaProps =
  | { route: string; title?: undefined; description?: undefined; path?: undefined }
  | {
      route?: undefined
      title: string
      description: string
      path: string
      robots?: string
    }

/**
 * Per-route document meta for SPA navigation (title, description, canonical, OG/Twitter).
 * Prefer `route` keys from publicPageSeo so sitemap and Helmet stay aligned.
 */
export function PageMeta(props: PageMetaProps) {
  const seo: PublicPageSeo | undefined =
    props.route !== undefined
      ? getPublicPageSeo(props.route)
      : {
          path: props.path,
          title: props.title,
          description: props.description,
          robots: props.robots,
        }

  if (!seo) return null

  const url = absoluteUrl(seo.path)
  const image = DEFAULT_OG_IMAGE

  return (
    <Helmet>
      <title>{seo.title}</title>
      <meta name="description" content={seo.description} />
      {seo.robots ? <meta name="robots" content={seo.robots} /> : null}
      <link rel="canonical" href={url} />
      <meta property="og:type" content="website" />
      <meta property="og:url" content={url} />
      <meta property="og:title" content={seo.title} />
      <meta property="og:description" content={seo.description} />
      <meta property="og:image" content={image} />
      <meta property="og:image:secure_url" content={image} />
      <meta property="og:site_name" content="Fikiri Solutions" />
      <meta property="twitter:card" content="summary_large_image" />
      <meta property="twitter:url" content={url} />
      <meta property="twitter:title" content={seo.title} />
      <meta property="twitter:description" content={seo.description} />
      <meta property="twitter:image" content={image} />
    </Helmet>
  )
}
