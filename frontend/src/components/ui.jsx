export function Card({ children, className = '', ...props }) {
  return (
    <section className={`app-card ${className}`} {...props}>
      {children}
    </section>
  )
}

export function PageHeader({ title, description, action }) {
  return (
    <div className="app-page-header">
      <div>
        <h1>{title}</h1>
        {description && <p>{description}</p>}
      </div>
      {action}
    </div>
  )
}

export function StatCard({ label, value, hint }) {
  return (
    <Card className="app-stat-card">
      <p className="app-stat-label">{label}</p>
      <p className="app-stat-value">{value}</p>
      {hint && <p className="app-stat-hint">{hint}</p>}
    </Card>
  )
}

const statusClasses = {
  Paid: 'app-badge-positive',
  Success: 'app-badge-positive',
  in: 'app-badge-info',
  Pending: 'app-badge-warning',
  Cancelled: 'app-badge-negative',
  Failed: 'app-badge-negative',
  out: 'app-badge-neutral',
}

export function Badge({ value, label }) {
  return <span className={`app-badge ${statusClasses[value] || 'app-badge-neutral'}`}>{label ?? value}</span>
}

export function LoadingState({ label = 'Loading' }) {
  return (
    <div className="app-state" role="status">
      <span className="app-spinner" aria-hidden="true" />
      <p>{label}</p>
    </div>
  )
}

export function ErrorState({ message, onRetry, retryLabel = 'Retry' }) {
  return (
    <Card className="app-state">
      <p className="app-state-title">The data could not be loaded</p>
      <p>{message}</p>
      {onRetry && (
        <button type="button" className="app-button" onClick={onRetry}>
          {retryLabel}
        </button>
      )}
    </Card>
  )
}

export function EmptyState({ message }) {
  return <p className="app-empty-state">{message}</p>
}
