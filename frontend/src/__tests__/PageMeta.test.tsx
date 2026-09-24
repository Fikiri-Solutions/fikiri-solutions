import { describe, expect, it } from 'vitest'
import { render, waitFor } from '@testing-library/react'
import { HelmetProvider } from 'react-helmet-async'
import { PageMeta } from '../components/PageMeta'

describe('PageMeta', () => {
  it('sets document title and description for a known public route', async () => {
    render(
      <HelmetProvider>
        <PageMeta route="/contact" />
      </HelmetProvider>
    )
    await waitFor(() => {
      expect(document.title).toMatch(/Contact Fikiri Solutions/)
    })
    const description = document.querySelector('meta[name="description"]')
    expect(description?.getAttribute('content')).toMatch(/Contact Fikiri/i)
    const canonical = document.querySelector('link[rel="canonical"]')
    expect(canonical?.getAttribute('href')).toBe('https://fikirisolutions.com/contact')
    const ogUrl = document.querySelector('meta[property="og:url"]')
    expect(ogUrl?.getAttribute('content')).toBe('https://fikirisolutions.com/contact')
  })

  it('renders nothing for an unknown route key', () => {
    const { container } = render(
      <HelmetProvider>
        <PageMeta route="/not-a-real-route" />
      </HelmetProvider>
    )
    expect(container.innerHTML).toBe('')
  })
})
