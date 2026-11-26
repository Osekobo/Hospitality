import { useState } from 'react'
import { NavLink, Outlet } from 'react-router-dom'
import {
  CalendarCheck2,
  LayoutDashboard,
  Menu,
  MessageCircleMore,
  RadioTower,
  ReceiptText,
  Sparkles,
  X,
} from 'lucide-react'

const navigation = [
  { to: '/', label: 'Overview', icon: LayoutDashboard, end: true },
  { to: '/bookings', label: 'Bookings', icon: CalendarCheck2 },
  { to: '/chats', label: 'Live Chats', icon: MessageCircleMore },
  { to: '/transactions', label: 'Payments', icon: ReceiptText },
]

export default function Layout() {
  const [open, setOpen] = useState(false)

  return (
    <div className="min-h-screen bg-[#080d18]">
      <div className="pointer-events-none fixed inset-0 bg-[radial-gradient(circle_at_20%_-10%,rgba(16,185,129,0.12),transparent_35%),radial-gradient(circle_at_85%_10%,rgba(139,92,246,0.10),transparent_30%)]" />

      <div className="relative flex min-h-screen">
        <aside
          className={`fixed inset-y-0 left-0 z-40 flex w-64 flex-col border-r border-slate-800/80 bg-[#0b1120]/95 p-5 backdrop-blur transition-transform lg:translate-x-0 ${open ? 'translate-x-0' : '-translate-x-full'}`}
        >
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <span className="grid size-10 place-items-center rounded-xl bg-gradient-to-br from-emerald-400 to-teal-600 text-slate-950">
                <Sparkles className="size-5" />
              </span>
              <div>
                <p className="text-sm font-semibold text-white">Social Concierge</p>
                <p className="text-xs text-slate-500">Hospitality & Tourism</p>
              </div>
            </div>
            <button onClick={() => setOpen(false)} className="text-slate-400 lg:hidden" aria-label="Close menu">
              <X className="size-5" />
            </button>
          </div>

          <nav className="mt-10 space-y-1">
            {navigation.map(({ to, label, icon: Icon, end }) => (
              <NavLink
                key={to}
                to={to}
                end={end}
                onClick={() => setOpen(false)}
                className={({ isActive }) =>
                  `flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition ${
                    isActive
                      ? 'bg-emerald-500/10 text-emerald-300 ring-1 ring-emerald-500/20'
                      : 'text-slate-400 hover:bg-slate-800/60 hover:text-white'
                  }`
                }
              >
                <Icon className="size-4" />
                {label}
              </NavLink>
            ))}
          </nav>

          <div className="mt-auto rounded-2xl border border-emerald-500/20 bg-emerald-500/5 p-4">
            <div className="flex items-center gap-2 text-sm font-semibold text-emerald-300">
              <RadioTower className="size-4" />
              Connected channels
            </div>
            <p className="mt-2 text-xs leading-relaxed text-slate-400">
              WhatsApp · Instagram · SMS · USSD · Voice · M-Pesa
            </p>
          </div>
        </aside>

        {open && <button className="fixed inset-0 z-30 bg-black/60 lg:hidden" onClick={() => setOpen(false)} aria-label="Close sidebar" />}

        <div className="flex min-w-0 flex-1 flex-col lg:pl-64">
          <header className="sticky top-0 z-20 flex items-center justify-between border-b border-slate-800/70 bg-[#080d18]/85 px-5 py-4 backdrop-blur sm:px-8">
            <div className="flex items-center gap-3">
              <button onClick={() => setOpen(true)} className="text-slate-300 lg:hidden" aria-label="Open menu">
                <Menu className="size-6" />
              </button>
              <div>
                <p className="text-sm font-medium text-white">Operations dashboard</p>
                <p className="text-xs text-slate-500">Nairobi, Kenya · East Africa Time</p>
              </div>
            </div>
            <div className="flex items-center gap-2 rounded-full border border-slate-800 bg-slate-900/70 px-3 py-1.5 text-xs text-slate-300">
              <span className="size-2 animate-pulse rounded-full bg-emerald-400" />
              Live
            </div>
          </header>

          <main className="mx-auto w-full max-w-7xl flex-1 px-5 py-8 sm:px-8">
            <Outlet />
          </main>
        </div>
      </div>
    </div>
  )
}
