import { useCallback, useEffect, useMemo, useState } from 'react'
import { Search, SlidersHorizontal } from 'lucide-react'
import { getBookings } from '../lib/api'
import { Badge, Card, ErrorState, LoadingState, PageHeader, formatKes } from '../components/ui'

const filters = ['All', 'Pending', 'Paid', 'Cancelled']

export default function Bookings() {
  const [bookings, setBookings] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [query, setQuery] = useState('')
  const [status, setStatus] = useState('All')

  const load = useCallback(async () => {
    try {
      setLoading(true)
      setError('')
      setBookings(await getBookings())
    } catch (err) {
      setError(err.message || 'Could not load bookings')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    load()
  }, [load])

  const rows = useMemo(() => {
    const needle = query.toLowerCase()
    return bookings.filter((booking) => {
      const matchesStatus = status === 'All' || booking.status === status
      const matchesQuery =
        !needle ||
        `${booking.guest_name} ${booking.property_name} ${booking.phone_number} ${booking.location}`.toLowerCase().includes(needle)
      return matchesStatus && matchesQuery
    })
  }, [bookings, query, status])

  if (error) return <ErrorState message={error} onRetry={load} />
  if (loading) return <LoadingState label="Loading bookings..." />

  return (
    <>
      <PageHeader
        eyebrow="Reservations"
        title="Bookings"
        description="Every reservation created from WhatsApp, Instagram, SMS and USSD in one place."
        action={
          <div className="rounded-xl border border-slate-800 bg-slate-900/60 px-4 py-2 text-sm text-slate-400">
            <span className="font-semibold text-white">{rows.length}</span> records
          </div>
        }
      />

      <Card className="p-0">
        <div className="flex flex-col gap-3 border-b border-slate-800/80 p-4 sm:flex-row sm:items-center sm:justify-between">
          <label className="flex w-full items-center gap-2 rounded-xl border border-slate-800 bg-slate-950/60 px-3 py-2 sm:max-w-sm">
            <Search className="size-4 text-slate-500" />
            <input
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Search guest, property or phone"
              className="w-full bg-transparent text-sm text-white outline-none placeholder:text-slate-600"
            />
          </label>
          <div className="flex items-center gap-2 overflow-x-auto">
            <SlidersHorizontal className="size-4 shrink-0 text-slate-500" />
            {filters.map((item) => (
              <button
                key={item}
                onClick={() => setStatus(item)}
                className={`shrink-0 rounded-lg px-3 py-1.5 text-xs font-medium transition ${
                  status === item ? 'bg-emerald-500 text-slate-950' : 'bg-slate-800/70 text-slate-400 hover:text-white'
                }`}
              >
                {item}
              </button>
            ))}
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full min-w-[900px] text-left text-sm">
            <thead className="bg-slate-950/40 text-xs uppercase tracking-wider text-slate-500">
              <tr>
                <th className="px-5 py-3">Guest</th>
                <th className="px-5 py-3">Property</th>
                <th className="px-5 py-3">Channel</th>
                <th className="px-5 py-3">Check-in / out</th>
                <th className="px-5 py-3">Guests</th>
                <th className="px-5 py-3">Amount</th>
                <th className="px-5 py-3">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/70">
              {rows.map((booking) => (
                <tr key={booking.id} className="transition hover:bg-slate-800/30">
                  <td className="px-5 py-4">
                    <p className="font-medium text-white">{booking.guest_name}</p>
                    <p className="text-xs text-slate-500">{booking.phone_number}</p>
                  </td>
                  <td className="px-5 py-4">
                    <p className="text-slate-200">{booking.property_name}</p>
                    <p className="text-xs text-slate-500">{booking.location}</p>
                  </td>
                  <td className="px-5 py-4 text-slate-400">{booking.platform}</td>
                  <td className="px-5 py-4 text-slate-400">{booking.check_in} <span className="text-slate-600">→</span> {booking.check_out}</td>
                  <td className="px-5 py-4 text-slate-400">{booking.guests}</td>
                  <td className="px-5 py-4 font-medium text-white">{formatKes(booking.total_amount)}</td>
                  <td className="px-5 py-4"><Badge value={booking.status} /></td>
                </tr>
              ))}
              {rows.length === 0 && (
                <tr>
                  <td colSpan={7} className="px-5 py-12 text-center text-sm text-slate-500">No bookings match your filters.</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </Card>
    </>
  )
}
