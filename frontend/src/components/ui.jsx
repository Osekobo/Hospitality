import { AlertTriangle, LoaderCircle } from 'lucide-react'

export function Card({ children, className = '' }) {
  return (
    <div className={`rounded-2xl border border-slate-800/80 bg-slate-900/60 p-5 shadow-xl shadow-black/10 ${className}`}>
      {children}
    </div>
  )
}

export function PageHeader({ eyebrow, title, description, action }) {
  return (
    <div className="mb-8 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
      <div>
        {eyebrow && <p className="mb-2 text-xs font-semibold uppercase tracking-[0.2em] text-emerald-400">{eyebrow}</p>}
        <h1 className="text-2xl font-bold tracking-tight text-white sm:text-3xl">{title}</h1>
        {description && <p className="mt-2 max-w-2xl text-sm text-slate-400">{description}</p>}
      </div>
      {action}
    </div>
  )
}

export function StatCard({ label, value, hint, icon: Icon, tone = 'emerald' }) {
  const tones = {
    emerald: 'bg-emerald-500/10 text-emerald-400 ring-emerald-500/20',
    sky: 'bg-sky-500/10 text-sky-400 ring-sky-500/20',
    violet: 'bg-violet-500/10 text-violet-400 ring-violet-500/20',
    amber: 'bg-amber-500/10 text-amber-400 ring-amber-500/20',
  }
  return (
    <Card className="relative overflow-hidden">
      <div className="flex items-start justify-between">
        <div>
          <p className="text-sm text-slate-400">{label}</p>
          <p className="mt-3 text-3xl font-semibold tracking-tight text-white">{value}</p>
        </div>
        <span className={`grid size-11 place-items-center rounded-xl ring-1 ${tones[tone]}`}>
          <Icon className="size-5" />
        </span>
      </div>
      {hint && <p className="mt-3 text-xs text-slate-500">{hint}</p>}
    </Card>
  )
}

const statusStyles = {
  Paid: 'bg-emerald-500/10 text-emerald-300 ring-emerald-500/30',
  Pending: 'bg-amber-500/10 text-amber-300 ring-amber-500/30',
  Cancelled: 'bg-rose-500/10 text-rose-300 ring-rose-500/30',
  Success: 'bg-emerald-500/10 text-emerald-300 ring-emerald-500/30',
  Failed: 'bg-rose-500/10 text-rose-300 ring-rose-500/30',
  in: 'bg-sky-500/10 text-sky-300 ring-sky-500/30',
  out: 'bg-violet-500/10 text-violet-300 ring-violet-500/30',
}

export function Badge({ value }) {
  return (
    <span className={`inline-flex rounded-full px-2.5 py-1 text-xs font-medium ring-1 ring-inset ${statusStyles[value] || 'bg-slate-700/40 text-slate-300 ring-slate-600/40'}`}>
      {value}
    </span>
  )
}

export function LoadingState({ label = 'Loading data...' }) {
  return (
    <div className="flex min-h-64 items-center justify-center gap-3 text-sm text-slate-400">
      <LoaderCircle className="size-5 animate-spin text-emerald-400" />
      {label}
    </div>
  )
}

export function ErrorState({ message, onRetry }) {
  return (
    <Card className="flex min-h-64 flex-col items-center justify-center gap-3 text-center">
      <AlertTriangle className="size-8 text-amber-400" />
      <p className="text-sm text-slate-300">{message}</p>
      {onRetry && (
        <button onClick={onRetry} className="rounded-lg bg-emerald-500 px-4 py-2 text-sm font-semibold text-slate-950 hover:bg-emerald-400">
          Retry
        </button>
      )}
    </Card>
  )
}

export function formatKes(value) {
  return `KES ${Number(value || 0).toLocaleString('en-KE', { maximumFractionDigits: 0 })}`
}

export function formatDate(value) {
  if (!value) return '—'
  const parsed = new Date(value)
  if (Number.isNaN(parsed.getTime())) return value
  return parsed.toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' })
}

export function timeAgo(value) {
  if (!value) return '—'
  const diff = Date.now() - new Date(value).getTime()
  if (Number.isNaN(diff)) return value
  const minutes = Math.floor(diff / 60000)
  if (minutes < 1) return 'just now'
  if (minutes < 60) return `${minutes}m ago`
  const hours = Math.floor(minutes / 60)
  if (hours < 24) return `${hours}h ago`
  return `${Math.floor(hours / 24)}d ago`
}
