import { useMemo, useState } from 'react'
import { Search } from 'lucide-react'
import { getBookings } from '../lib/api'
import { formatDate, formatMoney } from '../lib/format'
import { useI18n } from '../lib/i18nCore'
import { useApiResource } from '../lib/resource'
import { Badge, Card, EmptyState, ErrorState, LoadingState, PageHeader } from '../components/ui'

const filters = ['All', 'Pending', 'Paid', 'Cancelled']

export default function Bookings() {
  const { t, locale } = useI18n()
  const { data, status, error, refresh } = useApiResource('bookings', getBookings)
  const [query, setQuery] = useState('')
  const [statusFilter, setStatusFilter] = useState('All')

  const rows = useMemo(() => {
    const bookings = data || []
    const needle = query.trim().toLowerCase()
    return bookings.filter((booking) => {
      const matchesStatus = statusFilter === 'All' || booking.status === statusFilter
      const haystack = `${booking.guest_name || ''} ${booking.property_name || ''} ${booking.phone_number || ''} ${booking.location || ''}`.toLowerCase()
      return matchesStatus && (!needle || haystack.includes(needle))
    })
  }, [data, query, statusFilter])

  if (status === 'error') return <ErrorState message={error} onRetry={refresh} retryLabel={t('common.retry')} />
  if (!data || status === 'loading') return <LoadingState label={t('common.loading')} />

  return (
    <>
      <PageHeader
        title={t('bookings.title')}
        description={t('bookings.description')}
        action={
          <div className="app-count-chip">
            <strong>{rows.length}</strong> {t('common.records')}
          </div>
        }
      />

      <Card className="app-card-flush">
        <div className="app-toolbar">
          <label className="app-search">
            <Search size={18} aria-hidden="true" />
            <span className="app-sr-only">{t('bookings.search')}</span>
            <input
              type="search"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder={t('bookings.search')}
            />
          </label>
          <div className="app-toolbar-actions">
            <div className="app-filter-group" role="group" aria-label={t('bookings.filterLabel')}>
              {filters.map((item) => (
                <button
                  key={item}
                  type="button"
                  aria-pressed={statusFilter === item}
                  className="app-filter-button"
                  onClick={() => setStatusFilter(item)}
                >
                  {item === 'All' ? t('common.all') : t(`common.${item.toLowerCase()}`)}
                </button>
              ))}
            </div>
            <button type="button" className="app-button app-button-secondary" onClick={refresh}>
              {t('common.refresh')}
            </button>
          </div>
        </div>

        {rows.length ? (
          <div className="app-table-wrap">
            <table className="app-table">
              <caption className="app-sr-only">{t('bookings.title')}</caption>
              <thead>
                <tr>
                  <th>{t('common.guest')}</th>
                  <th>{t('common.property')}</th>
                  <th>{t('bookings.channel')}</th>
                  <th>{t('bookings.dates')}</th>
                  <th>{t('bookings.guests')}</th>
                  <th>{t('common.amount')}</th>
                  <th>{t('common.status')}</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((booking) => (
                  <tr key={booking.id}>
                    <td>
                      <strong>{booking.guest_name}</strong>
                      <small>{booking.phone_number}</small>
                    </td>
                    <td>
                      <span>{booking.property_name}</span>
                      <small>{booking.location}</small>
                    </td>
                    <td>{booking.platform}</td>
                    <td>
                      {formatDate(booking.check_in, locale)} {t('common.to')} {formatDate(booking.check_out, locale)}
                    </td>
                    <td>{booking.guests}</td>
                    <td>{formatMoney(booking.total_amount, locale)}</td>
                    <td><Badge value={booking.status} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <EmptyState message={query || statusFilter !== 'All' ? t('bookings.empty') : t('bookings.none')} />
        )}
      </Card>
    </>
  )
}
