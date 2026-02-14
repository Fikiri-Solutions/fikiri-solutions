import { useLocation } from 'react-router-dom'
import { Disclosure, DisclosureButton, DisclosurePanel } from '@headlessui/react'
import { Bars2Icon } from '@heroicons/react/24/solid'
import { motion } from 'framer-motion'
import { RadiantLink } from './RadiantLink'
import { FikiriLogo } from '@/components/FikiriLogo'
import { PlusGrid, PlusGridItem, PlusGridRow } from './PlusGrid'

const links = [
  { to: '/pricing', label: 'Pricing' },
  { to: '/about', label: 'About' },
  { to: '/login', label: 'Login' },
]

function DesktopNav() {
  return (
    <nav className="relative hidden lg:flex">
      {links.map(({ to, label }) => (
        <PlusGridItem key={to} className="relative flex">
          <RadiantLink
            to={to}
            className="flex items-center min-h-[44px] px-4 py-3 text-base font-medium text-foreground hover:bg-black/5 rounded-lg touch-manipulation"
          >
            {label}
          </RadiantLink>
        </PlusGridItem>
      ))}
    </nav>
  )
}

function MobileNavButton() {
  return (
    <DisclosureButton
      className="flex size-12 items-center justify-center self-center rounded-lg hover:bg-black/5 lg:hidden text-foreground"
      aria-label="Open main menu"
    >
      <Bars2Icon className="size-6" />
    </DisclosureButton>
  )
}

function MobileNav() {
  return (
    <DisclosurePanel className="lg:hidden">
      <div className="flex flex-col gap-6 py-4">
        {links.map(({ to, label }, linkIndex) => (
          <motion.div
            key={to}
            initial={{ opacity: 0, rotateX: -90 }}
            animate={{ opacity: 1, rotateX: 0 }}
            transition={{
              duration: 0.15,
              ease: 'easeInOut',
              rotateX: { duration: 0.3, delay: linkIndex * 0.1 },
            }}
          >
            <RadiantLink to={to} className="flex items-center min-h-[44px] py-3 text-base font-medium text-foreground">
              {label}
            </RadiantLink>
          </motion.div>
        ))}
      </div>
      <div className="absolute left-1/2 w-screen -translate-x-1/2">
        <div className="absolute inset-x-0 top-0 border-t border-border" />
        <div className="absolute inset-x-0 top-2 border-t border-border" />
      </div>
    </DisclosurePanel>
  )
}

export function Navbar({ banner }: { banner?: React.ReactNode }) {
  const { pathname } = useLocation()
  return (
    <Disclosure as="header" className="pt-12 sm:pt-16" key={pathname}>
      <PlusGrid>
        <PlusGridRow className="grid grid-cols-3 items-center gap-4">
          <div className="flex items-center gap-6">
            <PlusGridItem className="py-3">
              <RadiantLink to="/" title="Home" className="inline-flex">
                <FikiriLogo size="md" variant="full" className="h-12 w-auto sm:h-14" />
              </RadiantLink>
            </PlusGridItem>
            {banner && (
              <div className="relative hidden items-center py-3 lg:flex">
                {banner}
              </div>
            )}
          </div>
          <div className="hidden lg:flex justify-center">
            <DesktopNav />
          </div>
          <div className="flex justify-end">
            <MobileNavButton />
          </div>
        </PlusGridRow>
      </PlusGrid>
      <MobileNav />
    </Disclosure>
  )
}
