import { useCallback, useEffect, useState } from 'react'
import { api, ApiError } from './api'

export type Me = { stage: 'mfa' | 'enroll' | 'full'; email: string; role: 'investor' | 'admin'; display_name: string }

export function useMe() {
  const [me, setMe] = useState<Me | null | undefined>(undefined) // undefined = loading, null = signed out
  const refresh = useCallback(async () => {
    try {
      setMe(await api<Me>('/auth/me'))
    } catch (e) {
      if (e instanceof ApiError && e.status === 401) setMe(null)
      else throw e
    }
  }, [])
  useEffect(() => { void refresh() }, [refresh])
  return { me, refresh }
}

export const homeFor = (role: Me['role']) => (role === 'admin' ? '/admin' : '/portal')

export async function logout() {
  await api('/auth/logout', { method: 'POST' })
}
