export type PinCategory = 'shelter' | 'evacuation_site' | 'toilet' | 'water' | 'aed'

export type ShelterDetail = {
  capacity: number
  notes: string
}

export type EvacuationSiteDetail = {
  capacity: number
  notes: string
}

export type ToiletDetail = {
  capacity: number
  notes: string
}

export type WaterDetail = {
  supplyAmount: string
  notes: string
}

export type AedDetail = {
  facilityName: string
  notes: string
}

export type Pin = {
  id: string
  category: PinCategory
  name: string
  address: string
  lat: number
  lng: number
  detail: ShelterDetail | EvacuationSiteDetail | ToiletDetail | WaterDetail | AedDetail
  updatedAt: string
}

export const CATEGORIES: Record<PinCategory, { label: string; color: string; icon: string }> = {
  shelter: {
    label: '指定避難所',
    color: '#E53E3E',
    icon: '🏠',
  },
  evacuation_site: {
    label: '緊急避難場所',
    color: '#805AD5',
    icon: '⛺',
  },
  toilet: {
    label: '公衆トイレ',
    color: '#38A169',
    icon: '🚻',
  },
  water: {
    label: '給水ポイント',
    color: '#3182CE',
    icon: '💧',
  },
  aed: {
    label: 'AED',
    color: '#D69E2E',
    icon: '❤️',
  },
}
