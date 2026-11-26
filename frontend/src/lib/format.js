import { localeTag } from './i18nCore'

export function formatMoney(value, locale = 'en') {
  const amount = Number.isFinite(Number(value)) ? Number(value) : 0
  return new Intl.NumberFormat(localeTag(locale), {
    style: 'currency',
    currency: 'KES',
    maximumFractionDigits: 2,
    minimumFractionDigits: 0,
  }).format(amount)
}

export function formatDate(value, locale = 'en') {
  if (!value) return '—'
  const parsed = new Date(value)
  if (Number.isNaN(parsed.getTime())) return value
  return new Intl.DateTimeFormat(localeTag(locale), {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
    timeZone: 'Africa/Nairobi',
  }).format(parsed)
}

export function formatRelative(value, locale = 'en') {
  if (!value) return '—'
  const parsed = new Date(value)
  if (Number.isNaN(parsed.getTime())) return value
  const minutes = Math.round((parsed.getTime() - Date.now()) / 60000)
  const formatter = new Intl.RelativeTimeFormat(localeTag(locale), { numeric: 'auto' })
  if (Math.abs(minutes) < 60) return formatter.format(minutes, 'minute')
  const hours = Math.round(minutes / 60)
  if (Math.abs(hours) < 24) return formatter.format(hours, 'hour')
  return formatter.format(Math.round(hours / 24), 'day')
}

export function initials(name) {
  return String(name || '?')
    .trim()
    .split(/\s+/)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase() || '')
    .join('')
}
