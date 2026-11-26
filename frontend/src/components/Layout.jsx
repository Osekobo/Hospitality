import { useEffect, useState } from 'react'
import { NavLink, Outlet } from 'react-router-dom'
import { CalendarCheck2, LayoutDashboard, Menu, MessageSquare, ReceiptText, X } from 'lucide-react'
import { getHealth } from '../lib/api'
import { useI18n } from '../lib/i18nCore'
import { useApiResource } from '../lib/resource'

const navigation = [
  { to: '/', key: 'nav.overview', icon: LayoutDashboard, end: true },
  { to: '/bookings', key: 'nav.bookings', icon: CalendarCheck2 },
  { to: '/chats', key: 'nav.chats', icon: MessageSquare },
  { to: '/transactions', key: 'nav.payments', icon: ReceiptText },
]

function Sidebar({ onNavigate }) {
  const { t } = useI18n()

  return (
    <div className="app-sidebar-inner">
      <div className="app-brand">
        <span className="app-brand-mark" aria-hidden="true">SC</span>
        <span>
          <strong>{t('app.name')}</strong>
          <small>{t('app.subtitle')}</small>
        </span>
      </div>
      <nav className="app-nav" aria-label={t('app.name')}>
        {navigation.map(({ to, key, icon: Icon, end }) => (
          <NavLink
            key={to}
            to={to}
            end={end}
            onClick={onNavigate}
            className={({ isActive }) => `app-nav-link${isActive ? ' is-active' : ''}`}
          >
            <Icon size={18} aria-hidden="true" />
            <span>{t(key)}</span>
          </NavLink>
        ))}
      </nav>
      <div className="app-sidebar-footer">
        <span>{t('common.region')}</span>
      </div>
    </div>
  )
}

export default function Layout() {
  const [open, setOpen] = useState(false)
  const { setLocale, t } = useI18n()
  const { data: healthData, status: healthStatus, refresh } = useApiResource('health', getHealth)

  useEffect(() => {
    const timer = setInterval(() => refresh(), 30000)
    return () => clearInterval(timer)
  }, [refresh])

  useEffect(() => {
    const onKeyDown = (event) => {
      if (event.key === 'Escape') setOpen(false)
    }
    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [])

  const apiState = healthStatus === 'success' && healthData?.status === 'ok' ? t('api.online') : healthStatus === 'error' ? t('api.offline') : t('api.checking')

  return (
    <div className="app-shell">
      <a className="app-skip-link" href="#main">{t('common.skip')}</a>

      <aside className="app-sidebar app-sidebar-desktop">
        <Sidebar />
      </aside>

      {open && (
        <>
          <button className="app-overlay" type="button" aria-label={t('nav.overview')} onClick={() => setOpen(false)} />
          <aside className="app-sidebar app-sidebar-mobile" id="mobile-sidebar">
            <button className="app-icon-button app-sidebar-close" type="button" onClick={() => setOpen(false)} aria-label={t('common.closeMenu')}>
              <X size={20} aria-hidden="true" />
            </button>
            <Sidebar onNavigate={() => setOpen(false)} />
          </aside>
        </>
      )}

      <div className="app-content-wrap">
        <header className="app-header">
          <div className="app-header-left">
            <button
              className="app-icon-button app-menu-button"
              type="button"
              aria-label={t('common.openMenu')}
              aria-expanded={open}
              aria-controls="mobile-sidebar"
              onClick={() => setOpen(true)}
            >
              <Menu size={22} aria-hidden="true" />
            </button>
            <div>
              <strong>{t('app.subtitle')}</strong>
              <small>{t('common.region')}</small>
            </div>
          </div>
          <div className="app-header-actions">
            <span className={`app-api-status${apiState === t('api.online') ? ' is-online' : ''}`} role="status">
              {t('api.status')}: {apiState}
            </span>
            <label className="app-locale-label">
              <span className="app-sr-only">{t('common.language')}</span>
              <select value={locale} onChange={(event) => setLocale(event.target.value)}>
                <option value="en">EN</option>
                <option value="sw">SW</option>
              </select>
            </label>
          </div>
        </header>

        <main className="app-main" id="main" tabIndex={-1}>
          <Outlet />
        </main>
      </div>
    </div>
  )
}
