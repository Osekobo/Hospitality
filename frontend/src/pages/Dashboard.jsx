import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { ArrowUpRight, CalendarCheck2, MessageCircleMore, TrendingUp, UsersRound, Wallet } from 'lucide-react'
import { getBookings, getChats, getStats } from '../lib/api'
import { Badge, Card, ErrorState, LoadingState, PageHeader, StatCard, formatKes, timeAgo } from '../components/ui'

export default function Dashboard() {
  const [data, setData] = useState(null)
  const [error, setError] = useState('')

  const load = useCallback(async () => {
    try {
      setError('')
      const [stats, bookings, chats] = await Promise.all([getStats(), getBookings(), getChats()])
      setData({ stats, bookings, chats })
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Could not reach the API')
    }
  }, [])

  useEffect(() => {
    load()
  }, [load])

  if (error && !data) return <ErrorState message={`Backend unavailable: ${error}`} onRetry={load} />
  if (!data) return <LoadingState />

  const { stats, bookings, chats } = data
  const chartData = stats.revenue_by_day.map((item) => ({
    ...item,
    label: new Date(item.date).toLocaleDateString('en-GB', { day: 'numeric', month: 'short' }),
  }))

  return (
    <>
      <PageHeader
        eyebrow="Command center"
        title="Good morning, team"
        description="Live overview of bookings, conversations and M-Pesa revenue across every channel."
        action={
          <Link
            to="/chats"
            className="inline-flex items-center gap-2 rounded-xl bg-emerald-500 px-4 py-2.5 text-sm font-semibold text-slate-950 transition hover:bg-emerald-400"
          >
            Open live chats <ArrowUpRight className="size-4" />
          </Link>
        }
      />

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <StatCard label="Total revenue" value={formatKes(stats.total_revenue)} hint={`${stats.successful_payments} successful M-Pesa payments`} icon={Wallet} />
        <StatCard label="Active bookings" value={stats.active_bookings} hint={`${stats.bookings_by_status.find((b) => b.status === 'Pending')?.count || 0} awaiting payment`} icon={CalendarCheck2} tone="amber" />
        <StatCard label="Total users" value={stats.total_users} hint={`${stats.total_chats} messages exchanged`} icon={UsersRound} tone="violet" />
        <StatCard label="Conversion rate" value={`${stats.conversion_rate}%`} hint="Bookings marked as paid" icon={TrendingUp} tone="sky" />
      </div>

      <div className="mt-5 grid gap-5 xl:grid-cols-3">
        <Card className="xl:col-span-2">
          <div className="mb-6 flex items-center justify-between">
            <div>
              <h2 className="text-base font-semibold text-white">Revenue trend</h2>
              <p className="mt-1 text-xs text-slate-500">Last 7 days · paid bookings</p>
            </div>
            <span className="rounded-lg bg-emerald-500/10 px-2.5 py-1 text-xs font-medium text-emerald-300">KES</span>
          </div>
          <div className="h-64 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={chartData} margin={{ top: 10, right: 10, left: -10, bottom: 0 }}>
                <defs>
                  <linearGradient id="revenue" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#34d399" stopOpacity={0.45} />
                    <stop offset="100%" stopColor="#34d399" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid stroke="#1e293b" vertical={false} />
                <XAxis dataKey="label" tick={{ fill: '#64748b', fontSize: 11 }} axisLine={false} tickLine={false} />
                <YAxis tick={{ fill: '#64748b', fontSize: 11 }} axisLine={false} tickLine={false} tickFormatter={(v) => `${Math.round(v / 1000)}k`} />
                <Tooltip
                  contentStyle={{ background: '#0f172a', border: '1px solid #334155', borderRadius: 12, color: '#f8fafc' }}
                  formatter={(value) => [formatKes(value), 'Revenue']}
                />
                <Area type="monotone" dataKey="revenue" stroke="#34d399" strokeWidth={2.5} fill="url(#revenue)" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </Card>

        <Card>
          <h2 className="text-base font-semibold text-white">Channels & status</h2>
          <p className="mt-1 text-xs text-slate-500">Where travelers reach you</p>
          <div className="mt-6 space-y-5">
            {stats.users_by_platform.map((item) => {
              const width = stats.total_users ? Math.max(8, (item.count / stats.total_users) * 100) : 0
              return (
                <div key={item.platform}>
                  <div className="mb-2 flex items-center justify-between text-sm">
                    <span className="text-slate-300">{item.platform}</span>
                    <span className="text-slate-500">{item.count}</span>
                  </div>
                  <div className="h-2 overflow-hidden rounded-full bg-slate-800">
                    <div className="h-full rounded-full bg-gradient-to-r from-emerald-500 to-teal-400" style={{ width: `${width}%` }} />
                  </div>
                </div>
              )
            })}
          </div>
          <div className="mt-7 flex flex-wrap gap-2">
            {stats.bookings_by_status.map((item) => (
              <Badge key={item.status} value={item.status} />
            ))}
          </div>
        </Card>
      </div>

      <div className="mt-5 grid gap-5 xl:grid-cols-3">
        <Card className="xl:col-span-2">
          <div className="mb-5 flex items-center justify-between">
            <h2 className="text-base font-semibold text-white">Recent bookings</h2>
            <Link to="/bookings" className="text-xs font-medium text-emerald-400 hover:text-emerald-300">View all</Link>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full min-w-[620px] text-left text-sm">
              <thead className="text-xs uppercase tracking-wider text-slate-500">
                <tr>
                  <th className="pb-3">Guest</th>
                  <th className="pb-3">Property</th>
                  <th className="pb-3">Dates</th>
                  <th className="pb-3">Amount</th>
                  <th className="pb-3">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/80">
                {bookings.slice(0, 5).map((booking) => (
                  <tr key={booking.id} className="text-slate-300">
                    <td className="py-3 font-medium text-white">{booking.guest_name}</td>
                    <td className="py-3">{booking.property_name}</td>
                    <td className="py-3 text-slate-400">{booking.check_in} → {booking.check_out}</td>
                    <td className="py-3">{formatKes(booking.total_amount)}</td>
                    <td className="py-3"><Badge value={booking.status} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>

        <Card>
          <div className="mb-5 flex items-center gap-2">
            <MessageCircleMore className="size-4 text-violet-400" />
            <h2 className="text-base font-semibold text-white">Recent conversations</h2>
          </div>
          <div className="space-y-4">
            {chats.slice(0, 5).map((chat) => (
              <div key={chat.id} className="flex gap-3">
                <span className={`mt-1 size-2 shrink-0 rounded-full ${chat.direction === 'in' ? 'bg-sky-400' : 'bg-violet-400'}`} />
                <div className="min-w-0">
                  <p className="truncate text-sm text-slate-300">{chat.content}</p>
                  <p className="mt-1 text-xs text-slate-500">{chat.guest_name} · {chat.platform} · {timeAgo(chat.created_at)}</p>
                </div>
              </div>
            ))}
          </div>
        </Card>
      </div>
    </>
  )
}
