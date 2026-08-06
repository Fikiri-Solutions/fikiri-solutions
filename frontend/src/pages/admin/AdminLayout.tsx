import { useEffect } from 'react'
import { NavLink, Outlet, useLocation } from 'react-router-dom'
import { Building2, ClipboardList, LayoutDashboard, Shield, KeyRound } from 'lucide-react'

const navItems = [
  { to: '/admin', label: 'Overview', icon: LayoutDashboard, end: true },
  { to: '/admin/tenants', label: 'Tenants', icon: Building2 },
  { to: '/admin/security', label: 'MFA Security', icon: KeyRound },
  { to: '/admin/audit', label: 'Audit Log', icon: ClipboardList },
]

export function AdminLayout() {
  const location = useLocation()

  // Shared layout keeps scroll position across Outlet swaps; reset so sticky
  // header / first paint never starts clipped under the viewport top.
  useEffect(() => {
    window.scrollTo(0, 0)
  }, [location.pathname])

  return (
    <div className="min-h-screen bg-zinc-100 text-zinc-900 dark:bg-zinc-950 dark:text-zinc-100">
      <header className="sticky top-0 z-40 border-b border-zinc-200/90 bg-white/95 backdrop-blur dark:border-zinc-800 dark:bg-zinc-900/95">
        <div className="mx-auto flex max-w-7xl items-center justify-between gap-4 px-4 py-3.5">
          <div className="flex min-w-0 items-center gap-2.5">
            <Shield className="h-5 w-5 shrink-0 text-teal-700 dark:text-teal-400" aria-hidden />
            <div className="min-w-0">
              <p className="text-[11px] font-medium uppercase tracking-wider text-zinc-500">
                Fikiri
              </p>
              <h1 className="text-lg font-semibold tracking-tight">Platform Admin</h1>
            </div>
          </div>
          <NavLink
            to="/dashboard"
            className="shrink-0 text-sm font-medium text-teal-700 underline-offset-2 hover:underline focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-teal-600 dark:text-teal-400"
          >
            Back to app
          </NavLink>
        </div>
      </header>

      <div className="mx-auto grid max-w-7xl gap-6 px-4 py-6 lg:grid-cols-[220px_1fr]">
        <aside className="h-fit rounded-xl border border-zinc-200/90 bg-white p-2.5 dark:border-zinc-800 dark:bg-zinc-900 lg:sticky lg:top-[4.25rem]">
          <nav className="space-y-0.5" aria-label="Platform admin">
            {navItems.map((item) => {
              const Icon = item.icon
              return (
                <NavLink
                  key={item.to}
                  to={item.to}
                  end={item.end}
                  className={({ isActive }) =>
                    [
                      'flex items-center gap-2 rounded-lg px-3 py-2 text-sm transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-teal-600',
                      isActive
                        ? 'bg-teal-50 font-medium text-teal-900 dark:bg-teal-950/60 dark:text-teal-100'
                        : 'text-zinc-600 hover:bg-zinc-100 dark:text-zinc-300 dark:hover:bg-zinc-800',
                    ].join(' ')
                  }
                >
                  <Icon className="h-4 w-4 shrink-0" aria-hidden />
                  {item.label}
                </NavLink>
              )
            })}
          </nav>
        </aside>

        <main id="main-content" className="min-w-0" tabIndex={-1}>
          <Outlet />
        </main>
      </div>
    </div>
  )
}
