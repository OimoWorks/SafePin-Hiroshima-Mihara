import dynamic from 'next/dynamic'
import OfflineStatus from '@/components/OfflineStatus'

const Map = dynamic(() => import('@/components/Map'), { ssr: false })

export default function Home() {
  return (
    <main className="relative w-screen h-screen overflow-hidden">
      <OfflineStatus />
      <Map />
    </main>
  )
}
