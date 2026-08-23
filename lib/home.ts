const KEY = 'safepin_home_location'

export type HomeLocation = { lat: number; lng: number; address: string }

export function getHome(): HomeLocation | null {
  if (typeof window === 'undefined') return null
  try {
    const raw = localStorage.getItem(KEY)
    return raw ? (JSON.parse(raw) as HomeLocation) : null
  } catch {
    return null
  }
}

export function setHome(h: HomeLocation): void {
  localStorage.setItem(KEY, JSON.stringify(h))
}

export function deleteHome(): void {
  localStorage.removeItem(KEY)
}
