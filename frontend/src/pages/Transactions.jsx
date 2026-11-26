import { useCallback, useEffect, useState } from 'react'
import { getTransactions } from '../lib/api'
import { Badge, Card, ErrorState, LoadingState, PageHeader, formatKes, formatDate } from '../components/ui'

export default function Transactions() {
  const [rows, setRows] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const load = useCallback(async () => {
    try {
      setLoading(true)
      setError('')
      setRows(await getTransactions())
    } catch (err) {
      setError(err.message || 'Could not load payments')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    load()
  }, [load])

  if (error) return <ErrorState message={error} onRetry={load} />
  if (loading) return <LoadingState label="Loading payments..." />

  const successful = rows.filter((row) => row.status === 'Success')

  return (
    <>
      <PageHeader
        eyebrow="M-Pesa Daraja"
        title="Payments"
        description="STK Push requests and their callbacks, reconciled against bookings in real time."
        action={
          <div className="rounded-xl border border-slate-800 bg-slate-900/60 px-4 py-2 text-sm text-slate-400">
            <span className="font-semibold text-white">{formatKes(successful.reduce((sum, row) => sum + row.amount, 0))}</span> collected
          </div>
        }
      />

      <Card className="p-0">
        <div className="overflow-x-auto">
          <table className="w-full min-w-[850px] text-left text-sm">
            <thead className="bg-slate-950/40 text-xs uppercase tracking-wider text-slate-500">
              <tr>
                <th className="px-5 py-3">Receipt</th>
                <th className="px-5 py-3">Booking</th>
                <th className="px-5 py-3">Phone</th>
                <th className="px-5 py-3">Checkout ID</th>
                <th className="px-5 py-3">Amount</th>
                <th className="px-5 py-3">Date</th>
                <th className="px-5 py-3">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/70">
              {rows.map((row) => (
                <tr key={row.id} className="hover:bg-slate-800/30">
                  <td className="px-5 py-4 font-medium text-white">{row.mpesa_receipt_number || 'Pending'}</td>
                  <td className="px-5 py-4 text-slate-400">{row.booking_id ? `#${row.booking_id}` : '—'}</td>
                  <td className="px-5 py-4 text-slate-400">{row.phone_number}</td>
                  <td className="max-w-56 truncate px-5 py-4 text-xs text-slate-500">{row.checkout_request_id}</td>
                  <td className="px-5 py-4 font-medium text-white">{formatKes(row.amount)}</td>
                  <td className="px-5 py-4 text-slate-400">{formatDate(row.created_at)}</td>
                  <td className="px-5 py-4"><Badge value={row.status} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
    </>
  )
}
