import { useCallback, useSyncExternalStore } from 'react'

const cache = new Map()
const listeners = new Map()

function notify(key) {
  listeners.get(key)?.forEach((listener) => listener())
}

function errorMessage(error) {
  return error?.response?.data?.detail || error?.message || 'The request could not be completed'
}

async function load(key, loader) {
  const current = cache.get(key) || { status: 'loading', data: undefined, error: '', updatedAt: 0 }
  cache.set(key, { ...current, status: 'loading', error: '' })
  notify(key)
  try {
    const data = await loader()
    cache.set(key, { status: 'success', data, error: '', updatedAt: Date.now() })
  } catch (error) {
    cache.set(key, { ...cache.get(key), status: 'error', error: errorMessage(error) })
  }
  notify(key)
}

function ensure(key, loader) {
  let entry = cache.get(key)
  if (!entry) {
    entry = { status: 'loading', data: undefined, error: '', updatedAt: 0 }
    cache.set(key, entry)
    queueMicrotask(() => load(key, loader))
  }
  return entry
}

export function useApiResource(key, loader) {
  const subscribe = useCallback(
    (listener) => {
      const group = listeners.get(key) || new Set()
      group.add(listener)
      listeners.set(key, group)
      return () => group.delete(listener)
    },
    [key],
  )

  const getSnapshot = useCallback(() => ensure(key, loader), [key, loader])
  const snapshot = useSyncExternalStore(subscribe, getSnapshot, getSnapshot)
  const refresh = useCallback(() => load(key, loader), [key, loader])

  return { ...snapshot, refresh }
}
