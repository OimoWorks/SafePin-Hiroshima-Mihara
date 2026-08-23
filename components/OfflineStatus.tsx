'use client'

import { useEffect, useState } from 'react'
export default function OfflineStatus() {
  const [isOffline, setIsOffline] = useState(false)
  const [lastUpdated, setLastUpdated] = useState<string | null>(null)

  useEffect(() => {
    setIsOffline(!navigator.onLine)
    setLastUpdated(localStorage.getItem('lastUpdated'))

    const handleOffline = () => setIsOffline(true)
    const handleOnline = () => setIsOffline(false)

    window.addEventListener('offline', handleOffline)
    window.addEventListener('online', handleOnline)

    return () => {
      window.removeEventListener('offline', handleOffline)
      window.removeEventListener('online', handleOnline)
    }
  }, [])

  if (!isOffline) return null

  return (
    <div className="fixed top-0 left-0 right-0 z-[2000] bg-orange-500 text-white text-center py-2 px-4 text-sm font-bold shadow-md">
      オフライン表示中
      {lastUpdated && <span className="font-normal ml-2">・最終更新：{lastUpdated}</span>}
    </div>
  )
}
