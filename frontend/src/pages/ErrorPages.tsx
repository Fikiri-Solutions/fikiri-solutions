import React from 'react'
import { Helmet } from 'react-helmet-async'
import { Home, RefreshCw, AlertTriangle, Search } from 'lucide-react'
import { RadiantLayout, Container } from '../components/radiant'
import { Button } from '../components/radiant/Button'

export const NotFoundPage: React.FC = () => {
  return (
    <RadiantLayout showFooterCta={false}>
      <Helmet>
        <title>Page not found - Fikiri Solutions</title>
        <meta
          name="description"
          content="The page you requested could not be found on Fikiri Solutions."
        />
        <meta name="robots" content="noindex" />
      </Helmet>
      <div className="flex flex-1 flex-col justify-center py-16 sm:py-24">
        <Container>
          <div className="mx-auto max-w-lg text-center">
            <Search className="mx-auto h-16 w-16 text-white/40" aria-hidden />
            <p className="mt-6 text-sm font-semibold uppercase tracking-[0.18em] text-orange-300">
              404
            </p>
            <h1 className="mt-3 font-serif text-3xl font-bold text-white sm:text-4xl">
              Page not found
            </h1>
            <p className="mt-3 font-serif text-base text-white/70">
              Sorry, we couldn&apos;t find the page you&apos;re looking for.
            </p>
            <div className="mt-8 flex flex-col items-stretch justify-center gap-3 sm:flex-row sm:items-center">
              <Button to="/" className="w-full sm:w-auto">
                <Home className="mr-2 h-4 w-4" aria-hidden />
                Back to home
              </Button>
              <Button
                to="/contact"
                variant="secondary"
                className="w-full border-white/20 bg-white/10 !text-white ring-white/20 hover:bg-white/15 sm:w-auto"
              >
                Contact us
              </Button>
            </div>
          </div>
        </Container>
      </div>
    </RadiantLayout>
  )
}

export const ErrorPage: React.FC = () => {
  return (
    <RadiantLayout showFooterCta={false}>
      <Helmet>
        <title>Something went wrong - Fikiri Solutions</title>
        <meta name="robots" content="noindex" />
      </Helmet>
      <div className="flex flex-1 flex-col justify-center py-16 sm:py-24">
        <Container>
          <div className="mx-auto max-w-lg text-center">
            <AlertTriangle className="mx-auto h-16 w-16 text-red-400" aria-hidden />
            <h1 className="mt-6 font-serif text-3xl font-bold text-white sm:text-4xl">
              Something went wrong
            </h1>
            <p className="mt-3 font-serif text-base text-white/70">
              We&apos;re experiencing some technical difficulties. Please try again.
            </p>
            <div className="mt-8 flex flex-col items-stretch justify-center gap-3 sm:flex-row sm:items-center">
              <Button className="w-full sm:w-auto" onClick={() => window.location.reload()}>
                <RefreshCw className="mr-2 h-4 w-4" aria-hidden />
                Try again
              </Button>
              <Button
                to="/"
                variant="secondary"
                className="w-full border-white/20 bg-white/10 !text-white ring-white/20 hover:bg-white/15 sm:w-auto"
              >
                <Home className="mr-2 h-4 w-4" aria-hidden />
                Back to home
              </Button>
            </div>
          </div>
        </Container>
      </div>
    </RadiantLayout>
  )
}
