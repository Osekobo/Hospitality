import { getTransactions } from '../lib/api'
import { formatDate, formatMoney } from '../lib/format'
import { useI18n } from '../lib/i18nCore'
import { useApiResource } from '../lib/resource'
import { Badge, Card, EmptyState, ErrorState, LoadingState, PageHeader } from '../components/ui'

const loadTransactions = () => getTransactions()

export default function Transactions() {
  const { t, locale } = useI18n()
  const { data, status, error, refresh } = useApiResource('transactions', loadTransactions)
  const rows = data || []
  const collected = rows
    .filter((row) => row.status === 'Success')
    .reduce((sum, row) => sum + (Number(row.amount) || 0), 0)

  if (status === 'error') return <ErrorState message={error} onRetry={refresh} retryLabel={t('common.retry')} />
  if (!data || status === 'loading') return <LoadingState label={t('common.loading')} />

  return (
    <>
      <PageHeader
        title={t('transactions.title')}
        description={t('transactions.description')}
        action={
          <div className="app-count-chip">
            <strong>{formatMoney(collected, locale)}</strong> {t('transactions.collected')}
          </div>
        }
      />

      <Card className="app-card-flush">
        <div className="app-toolbar app-toolbar-end">
          <button type="button" className="app-button app-button-secondary" onClick={refresh}>
            {t('common.refresh')}
          </button>
        </div>
        {rows.length ? (
          <div className="app-table-wrap">
            <table className="app-table">
              <caption className="app-sr-only">{t('transactions.title')}</caption>
              <thead>
                <tr>
                  <th>{t('transactions.receipt')}</th>
                  <th>{t('transactions.booking')}</th>
                  <th>{t('common.phone')}</th>
                  <th>{t('transactions.checkout')}</th>
                  <th>{t('common.amount')}</th>
                  <th>{t('common.date')}</th>
                  <th>{t('common.status')}</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((row) => (
                  <tr key={row.id}>
                    <td><strong>{row.mpesa_receipt_number || '—'}</strong></td>
                    <td>{row.booking_id ? `#${row.booking_id}` : '—'}</td>
                    <td>{row.phone_number}</td>
                    <td className="app-truncate">{row.checkout_request_id}</td>
                    <td>{formatMoney(row.amount, locale)}</td>
                    <td><time dateTime={row.created_at}>{formatDate(row.created_at, locale)}</time></td>
                    <td><Badge value={row.status} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <EmptyState message={t('transactions.empty')} />
        )}
      </Card>
    </>
  )
}
