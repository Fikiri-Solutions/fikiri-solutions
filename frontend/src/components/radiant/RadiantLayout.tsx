import { Navbar } from './Navbar'
import { Footer } from './Footer'

/**
 * Wraps public/marketing pages with Radiant-style Navbar + Footer for continuity
 * with the landing template. Use for: pricing, about, login, signup, terms, privacy, etc.
 */
export function RadiantLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen flex flex-col bg-background text-foreground">
      <Navbar />
      <main className="flex-1">{children}</main>
      <Footer />
    </div>
  )
}
