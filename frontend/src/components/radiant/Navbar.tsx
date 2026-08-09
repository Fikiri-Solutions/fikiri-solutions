import { useLocation } from 'react-router-dom'
import { Disclosure, DisclosureButton, DisclosurePanel } from '@headlessui/react'
import { Bars2Icon } from '@heroicons/react/24/solid'
import { clsx } from 'clsx'
import { RadiantLink } from './RadiantLink'
import { FikiriLogo } from '@/components/FikiriLogo'
import { PlusGrid, PlusGridItem, PlusGridRow } from './PlusGrid'
import { Container } from './Container'
import { useAuth } from '@/contexts/AuthContext'

function buildNavLinks(
  isAuthenticated: boolean,
  onboardingCompleted: boolean | undefined
): { to: string; label: string }[] {
  if (!isAuthenticated) {
    return [
      { to: '/pricing', label: 'Pricing' },
      { to: '/about', label: 'About' },
      { to: '/login', label: 'Login' },
      { to: '/signup', label: 'Sign up' },
    ]
  }
  return [
    { to: '/pricing', label: 'Pricing' },
    { to: '/about', label: 'About' },
    onboardingCompleted
      ? { to: '/dashboard', label: 'Dashboard' }
      : { to: '/onboarding', label: 'Continue setup' },
  ]
}

const onDarkLinkClass =
  'flex min-h-[44px] items-center rounded-lg px-4 py-3 text-base font-medium !text-white hover:bg-white/15 touch-manipulation'
const onLightLinkClass =
  'flex min-h-[44px] items-center rounded-lg px-4 py-3 text-base font-medium !text-foreground hover:bg-black/5 touch-manipulation'

function DesktopNav({
  links,
  onDark,
}: {
  links: { to: string; label: string }[]
  onDark?: boolean
}) {
  return (
    <nav className="relative hidden lg:flex">
      {links.map(({ to, label }) => (
        <PlusGridItem key={to} className="relative flex">
          <RadiantLink to={to} className={onDark ? onDarkLinkClass : onLightLinkClass}>
            {label}
          </RadiantLink>
        </PlusGridItem>
      ))}
    </nav>
  )
}

function MobileNavButton({ onDark }: { onDark?: boolean }) {
  return (
    <DisclosureButton
      className={
        onDark
          ? 'flex size-11 items-center justify-center self-center rounded-lg !text-white hover:bg-white/10 sm:size-12 lg:hidden'
          : 'flex size-12 items-center justify-center self-center rounded-lg !text-foreground hover:bg-black/5 lg:hidden'
      }
      aria-label="Open main menu"
    >
      <Bars2Icon className="size-6" />
    </DisclosureButton>
  )
}

function MobileNav({
  links,
  onDark,
  marketing,
}: {
  links: { to: string; label: string }[]
  onDark?: boolean
  marketing?: boolean
}) {
  return (
    <DisclosurePanel
      className={clsx(
        'lg:hidden',
        marketing && onDark && 'rounded-b-xl bg-black/85 px-2 backdrop-blur-md ring-1 ring-white/10',
        marketing && !onDark && 'rounded-b-xl bg-background/90 px-2 backdrop-blur-md ring-1 ring-black/10'
      )}
    >
      {/*
        Avoid rotateX / 3D menu reveals — on iOS Chrome and in-app browsers they
        often stick at near-zero opacity and look like missing/dark links.
      */}
      <div className="flex flex-col gap-1 py-3">
        {links.map(({ to, label }) => (
          <RadiantLink
            key={to}
            to={to}
            className={
              onDark
                ? 'flex min-h-[44px] items-center px-3 py-3 text-base font-medium !text-white touch-manipulation'
                : 'flex min-h-[44px] items-center px-3 py-3 text-base font-medium !text-foreground touch-manipulation'
            }
          >
            {label}
          </RadiantLink>
        ))}
      </div>
    </DisclosurePanel>
  )
}

export function Navbar({
  banner,
  tone = 'default',
  variant = 'marketing',
  /**
   * Home hero mode: float over artwork with no opaque bar / hard bottom edge
   * so the baobab canopy continues behind the logo + menu.
   */
  overlay = false,
}: {
  banner?: React.ReactNode
  /** Dark hero shell — light nav text without changing global theme */
  tone?: 'default' | 'onDark'
  /**
   * marketing: transparent / light blur over page wash (public pages).
   * app: solid structured chrome (reserved; not used by RadiantLayout marketing pages).
   */
  variant?: 'marketing' | 'app'
  overlay?: boolean
}) {
  const { pathname } = useLocation()
  const { isAuthenticated, user } = useAuth()
  const homeTo = isAuthenticated && user?.onboarding_completed ? '/dashboard' : '/'
  const links = buildNavLinks(isAuthenticated, user?.onboarding_completed)
  const onDark = tone === 'onDark'
  const isMarketing = variant === 'marketing'
  const heroOverlay = overlay && onDark && isMarketing

  return (
    <Disclosure
      as="header"
      key={pathname}
      className={clsx(
        heroOverlay
          ? 'absolute inset-x-0 top-0 z-50 bg-gradient-to-b from-[#140f0c]/55 via-[#140f0c]/20 to-transparent pt-[max(0.35rem,env(safe-area-inset-top))] sm:bg-transparent sm:from-transparent sm:via-transparent sm:pt-4'
          : clsx(
              'pt-3 sm:pt-4',
              isMarketing && onDark && 'bg-black/25 backdrop-blur-md',
              isMarketing && !onDark && 'bg-transparent',
              !isMarketing && 'bg-background'
            )
      )}
    >
      {heroOverlay ? (
        <Container>
          <PlusGrid>
            <PlusGridRow
              dense
              className="flex items-center justify-between gap-4 border-b-0 lg:grid lg:grid-cols-3"
            >
              <div className="flex min-w-0 flex-1 items-center gap-4 sm:gap-6 lg:flex-initial">
                <PlusGridItem className="py-1.5 sm:py-2.5">
                  <RadiantLink
                    to={homeTo}
                    title="Home"
                    aria-label="Fikiri Solutions — Home"
                    className="inline-flex max-w-[min(100%,20rem)] items-center sm:max-w-none"
                  >
                    <FikiriLogo
                      size="xl"
                      variant="white"
                      className="!h-12 w-auto sm:!h-16 md:!h-[4.5rem]"
                    />
                  </RadiantLink>
                </PlusGridItem>
                {banner && (
                  <div className="relative hidden items-center py-1.5 lg:flex">
                    {banner}
                  </div>
                )}
              </div>
              <div className="hidden justify-center lg:flex">
                <DesktopNav links={links} onDark={onDark} />
              </div>
              <div className="flex shrink-0 justify-end">
                <MobileNavButton onDark={onDark} />
              </div>
            </PlusGridRow>
          </PlusGrid>
          <MobileNav links={links} onDark={onDark} marketing={isMarketing} />
        </Container>
      ) : (
        <>
          <PlusGrid>
            <PlusGridRow
              dense
              className={clsx(
                'flex items-center justify-between gap-4 lg:grid lg:grid-cols-3',
                onDark ? 'border-b border-white/10' : 'border-b border-border/40'
              )}
            >
              <div className="flex min-w-0 flex-1 items-center gap-4 sm:gap-6 lg:flex-initial">
                <PlusGridItem className="py-2 sm:py-2.5">
                  <RadiantLink
                    to={homeTo}
                    title="Home"
                    aria-label="Fikiri Solutions — Home"
                    className="inline-flex max-w-[min(100%,20rem)] items-center sm:max-w-none"
                  >
                    <FikiriLogo
                      size="xl"
                      variant={onDark ? 'white' : 'full'}
                      className="!h-14 w-auto sm:!h-16 md:!h-[4.5rem]"
                    />
                  </RadiantLink>
                </PlusGridItem>
                {banner && (
                  <div className="relative hidden items-center py-1.5 lg:flex">
                    {banner}
                  </div>
                )}
              </div>
              <div className="hidden justify-center lg:flex">
                <DesktopNav links={links} onDark={onDark} />
              </div>
              <div className="flex shrink-0 justify-end">
                <MobileNavButton onDark={onDark} />
              </div>
            </PlusGridRow>
          </PlusGrid>
          <MobileNav links={links} onDark={onDark} marketing={isMarketing} />
        </>
      )}
    </Disclosure>
  )
}
