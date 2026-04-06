import { useState, useCallback } from 'react'

interface UseApiReturn<T> {
  data: T | null
  loading: boolean
  error: string | null
  execute: (...args: unknown[]) => Promise<T | null>
}

export function useApi<T>(apiFunc: (...args: unknown[]) => Promise<T>): UseApiReturn<T> {
  const [data, setData] = useState<T | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const execute = useCallback(async (...args: unknown[]) => {
    setLoading(true)
    setError(null)
    try {
      const result = await apiFunc(...args)
      setData(result)
      return result
    } catch (e) {
      const message = e instanceof Error ? e.message : 'An error occurred'
      setError(message)
      return null
    } finally {
      setLoading(false)
    }
  }, [apiFunc])

  return { data, loading, error, execute }
}
