import { useCallback, useEffect, useState } from 'react'

type UseFetchOptions = {
  pollIntervalMs?: number
}

export function useFetch<T>(
  fetcher: () => Promise<T>,
  deps: unknown[] = [],
  options?: UseFetchOptions,
) {
  const [data, setData] = useState<T | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const refetch = useCallback(async (silent = false) => {
    if (!silent) {
      setLoading(true)
      setError(null)
    }
    try {
      const result = await fetcher()
      setData(result)
      if (silent) setError(null)
    } catch (e) {
      if (!silent) {
        setError(e instanceof Error ? e.message : 'Failed to load data')
      }
    } finally {
      if (!silent) setLoading(false)
    }
  }, deps)

  useEffect(() => {
    refetch()
  }, [refetch])

  useEffect(() => {
    const interval = options?.pollIntervalMs
    if (!interval || interval <= 0) return
    const id = setInterval(() => refetch(true), interval)
    return () => clearInterval(id)
  }, [refetch, options?.pollIntervalMs])

  return { data, loading, error, refetch }
}
