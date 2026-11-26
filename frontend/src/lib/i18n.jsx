import { useCallback, useEffect, useState } from 'react'
import { LocaleContext, normalizeLocale, STORAGE_KEY, translate } from './i18nCore'

export function I18nProvider({ children }) {
  const [locale, setLocaleState] = useState(() => {
    const stored = globalThis.localStorage?.getItem(STORAGE_KEY)
    return normalizeLocale(stored || import.meta.env.VITE_DEFAULT_LOCALE || 'en')
  })

  useEffect(() => {
    document.documentElement.lang = locale
    globalThis.localStorage?.setItem(STORAGE_KEY, locale)
  }, [locale])

  const setLocale = useCallback((next) => setLocaleState(normalizeLocale(next)), [])
  const t = useCallback((key, variables) => translate(locale, key, variables), [locale])

  return <LocaleContext.Provider value={{ locale, setLocale, t }}>{children}</LocaleContext.Provider>
}
