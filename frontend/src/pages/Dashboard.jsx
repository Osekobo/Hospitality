import { Link } from 'react-router-dom'
import { getBookings, getChats, getStats } from '../lib/api'
import { formatDate, formatMoney, formatRelative } from '../lib/format'
import { useI18n } from '../lib/i18nCore'
import { useApiResource } from '../lib/resource'
import { Badge, Card, EmptyState, ErrorState, LoadingState, PageHeader, StatCard } from '../components/ui'

const loadDashboard = async () => {
  const [stats, bookings, chats] = await Promise.all([getStats(), getBookings(), getChats()])
  return { stats, bookings, chats }
}

export default function Dashboard() {
  const { t, locale } = useI18n()
  const { data, status, error, refresh } = useApiResource('dashboard', loadDashboard)

  if (status === 'error') return <ErrorState message={error} onRetry={refresh} retryLabel={t('common.retry')} />
  if (!data || status === 'loading') return <LoadingState label={t('common.loading')} />

  const stats = data.stats || {}
  const bookings = data.bookings || []
  const chats = data.chats || []
  const trend = stats.revenue_by_day || []
  const maxRevenue = Math.max(...trend.map((item) => Number(item.revenue) || 0), 1)
  const pendingCount = (stats.bookings_by_status || []).find((item) => item.status === 'Pending')?.count || 0

  return (
    <>
      <PageHeader
        title={t('dashboard.title')}
        description={t('dashboard.description')}
        action={
          <Link className="app-button" to="/chats">
            {t('dashboard.openChats')}
          </Link>
        }
      />

      <div className="app-stat-grid">
        <StatCard label={t('dashboard.revenue')} value={formatMoney(stats.total_revenue, locale)} hint={t('dashboard.deposits', { count: stats.successful_payments || 0 })} />
        <StatCard label={t('dashboard.active')} value={stats.active_bookings || 0} hint={`${pendingCount} ${t('dashboard.awaiting')}`} />
        <StatCard label={t('dashboard.users')} value={stats.total_users || 0} hint={`${stats.total_chats || 0} ${t('dashboard.messages')}`} />
        <StatCard label={t('dashboard.conversion')} value={`${stats.conversion_rate || 0}%`} hint={t('dashboard.paidBookings')} />
      </div>

      <div className="app-two-column">
        <Card>
          <div className="app-card-heading">
            <h2>{t('dashboard.trend')}</h2>
            <p>{t('dashboard.trendHint')}</p>
          </div>
          <div className="app-chart" role="img" aria-label={t('dashboard.trendHint')}>
            {trend.map((item) => (
              <div className="app-chart-row" key={item.date}>
                <span className="app-chart-label">{formatDate(item.date, locale)}</span>
                <span className="app-chart-track">
                  <span className="app-chart-bar" style={{ width: `${Math.max(2, ((Number(item.revenue) || 0) / maxRevenue) * 100)}%` }} />
                </span>
                <span className="app-chart-value">{formatMoney(item.revenue, locale)}</span>
              </div>
            ))}
            {!trend.length && <EmptyState message={t('common.noData')} />}
          </div>
          <table className="app-sr-only">
            <caption>{t('dashboard.trend')}</caption>
            <thead><tr><th>{t('common.date')}</th><th>{t('common.amount')}</th></tr></thead>
            <tbody>
              {trend.map((item) => (
                <tr key={item.date}><td>{item.date}</td><td>{formatMoney(item.revenue, locale)}</td></tr>
              ))}
            </tbody>
          </table>
        </Card>

        <Card>
          <div className="app-card-heading">
            <h2>{t('dashboard.channels')}</h2>
            <p>{t('dashboard.channelsHint')}</p>
          </div>
          <div className="app-channel-list">
            {(stats.users_by_platform || []).map((item) => {
              const width = stats.total_users ? Math.max(4, (item.count / stats.total_users) * 100) : 0
              return (
                <div className="app-channel-row" key={item.platform}>
                  <div className="app-channel-meta">
                    <span>{item.platform}</span>
                    <span>{item.count}</span>
                  </div>
                  <div className="app-progress" role="progressbar" aria-label={item.platform} aria-valuenow={item.count} aria-valuemin={0} aria-valuemax={stats.total_users || 0}>
                    <span style={{ width: `${width}%` }} />
                  </div>
                </div>
              )
            })}
            {!stats.users_by_platform?.length && <EmptyState message={t('common.noData')} />}
          </div>
          <div className="app-badge-row">
            {(stats.bookings_by_status || []).map((item) => (
              <Badge key={item.status} value={item.status} label={`${item.status} (${item.count})`} />
            ))}
          </div>
        </Card>
      </div>

      <div className="app-two-column app-section-gap">
        <Card>
          <div className="app-card-heading app-card-heading-inline">
            <div>
              <h2>{t('dashboard.recentBookings')}</h2>
            </div>
            <Link className="app-text-link" to="/bookings">{t('dashboard.viewAll')}</Link>
          </div>
          {bookings.length ? (
            <div className="app-table-wrap">
              <table className="app-table">
                <caption className="app-sr-only">{t('dashboard.recentBookings')}</caption>
                <thead>
                  <tr>
                    <th>{t('common.guest')}</th>
                    <th>{t('common.property')}</th>
                    <th>{t('dashboard.dates')}</th>
                    <th>{t('common.amount')}</th>
                    <th>{t('common.status')}</th>
                  </tr>
                </thead>
                <tbody>
                  {bookings.slice(0, 5).map((booking) => (
                    <tr key={booking.id}>
                      <td>{booking.guest_name}</td>
                      <td>{booking.property_name}</td>
                      <td>{formatDate(booking.check_in, locale)} {t('common.to')} {formatDate(booking.check_out, locale)}</td>
                      <td>{formatMoney(booking.total_amount, locale)}</td>
                      <td><Badge value={booking.status} /></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <EmptyState message={t('dashboard.noBookings')} />
          )}
        </Card>

        <Card>
          <div className="app-card-heading">
            <h2>{t('dashboard.recentChats')}</h2>
          </div>
          {chats.length ? (
            <ul className="app-recent-chats">
              {chats.slice(0, 5).map((chat) => (
                <li key={chat.id}>
                  <p className="app-recent-content">{chat.content}</p>
                  <p className="app-recent-meta">
                    <Badge value={chat.direction} label={t(`common.${chat.direction}`)} />
                    <span>{chat.guest_name}</span>
                    <span>{chat.platform}</span>
                    <time dateTime={chat.created_at}>{formatRelative(chat.created_at, locale)}</time>
                  </p>
                </li>
              ))}
            </ul>
          ) : (
            <EmptyState message={t('dashboard.noChats')} />
          )}
        </Card>
      </div>
    </>
  )
}
