'use client'

import { Pin, CATEGORIES, ShelterDetail, EvacuationSiteDetail, ToiletDetail, WaterDetail, AedDetail } from '@/lib/types'

type Props = {
  pin: Pin
  onClose: () => void
}

export default function PinDetail({ pin, onClose }: Props) {
  const cat = CATEGORIES[pin.category]

  function renderDetail() {
    switch (pin.category) {
      case 'shelter': {
        const d = pin.detail as ShelterDetail
        return (
          <>
            <div className="flex justify-between py-2 border-b border-gray-100">
              <span className="text-gray-500 text-sm">収容人数</span>
              <span className="font-bold">{d.capacity.toLocaleString()}人</span>
            </div>
            <div className="flex justify-between py-2 border-b border-gray-100">
              <span className="text-gray-500 text-sm">備考</span>
              <span className="font-medium">{d.notes}</span>
            </div>
          </>
        )
      }
      case 'evacuation_site': {
        const d = pin.detail as EvacuationSiteDetail
        return (
          <>
            <div className="flex justify-between py-2 border-b border-gray-100">
              <span className="text-gray-500 text-sm">収容人数</span>
              <span className="font-bold">{d.capacity > 0 ? `${d.capacity.toLocaleString()}人` : '—'}</span>
            </div>
            <div className="flex justify-between py-2 border-b border-gray-100">
              <span className="text-gray-500 text-sm">備考</span>
              <span className="font-medium">{d.notes}</span>
            </div>
          </>
        )
      }
      case 'toilet': {
        const d = pin.detail as ToiletDetail
        return (
          <>
            <div className="flex justify-between py-2 border-b border-gray-100">
              <span className="text-gray-500 text-sm">使用可能人数</span>
              <span className="font-bold">{d.capacity}人</span>
            </div>
            <div className="flex justify-between py-2 border-b border-gray-100">
              <span className="text-gray-500 text-sm">備考</span>
              <span className="font-medium">{d.notes}</span>
            </div>
          </>
        )
      }
      case 'water': {
        const d = pin.detail as WaterDetail
        return (
          <>
            <div className="flex justify-between py-2 border-b border-gray-100">
              <span className="text-gray-500 text-sm">供給量目安</span>
              <span className="font-bold">{d.supplyAmount}</span>
            </div>
            <div className="flex justify-between py-2 border-b border-gray-100">
              <span className="text-gray-500 text-sm">備考</span>
              <span className="font-medium">{d.notes}</span>
            </div>
          </>
        )
      }
      case 'aed': {
        const d = pin.detail as AedDetail
        return (
          <>
            <div className="flex justify-between py-2 border-b border-gray-100">
              <span className="text-gray-500 text-sm">設置施設</span>
              <span className="font-bold">{d.facilityName}</span>
            </div>
            <div className="flex justify-between py-2 border-b border-gray-100">
              <span className="text-gray-500 text-sm">備考</span>
              <span className="font-medium">{d.notes}</span>
            </div>
          </>
        )
      }
    }
  }

  return (
    <div className="absolute bottom-0 left-0 right-0 z-[1000] bg-white rounded-t-2xl shadow-2xl p-5 pb-8 max-h-[50vh] overflow-y-auto">
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center gap-2">
          <span
            className="text-xs font-bold px-2 py-1 rounded-full text-white"
            style={{ backgroundColor: cat.color }}
          >
            {cat.icon} {cat.label}
          </span>
        </div>
        <button
          onClick={onClose}
          className="text-gray-400 hover:text-gray-700 text-2xl leading-none"
          aria-label="閉じる"
        >
          ×
        </button>
      </div>

      <h2 className="text-lg font-bold text-gray-900 mb-1">{pin.name}</h2>
      <p className="text-sm text-gray-500 mb-4">{pin.address}</p>

      <div className="space-y-0">
        {renderDetail()}
        <div className="flex justify-between py-2">
          <span className="text-gray-500 text-sm">最終更新</span>
          <span className="text-sm text-gray-600">{pin.updatedAt}</span>
        </div>
      </div>
    </div>
  )
}
