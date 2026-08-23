'use client'

import { useEffect, useRef, useState } from 'react'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import 'leaflet.markercluster'
import 'leaflet.markercluster/dist/MarkerCluster.css'
import 'leaflet.markercluster/dist/MarkerCluster.Default.css'
import { Pin, PinCategory, CATEGORIES } from '@/lib/types'
import { DUMMY_PINS } from '@/lib/pins'
import { trackEvent } from '@/lib/analytics'
import { getHome, setHome, deleteHome, HomeLocation } from '@/lib/home'
import CategoryFilter from './CategoryFilter'
import PinDetail from './PinDetail'
import Attribution from './Attribution'

const ALL_CATEGORIES = new Set<PinCategory>(['shelter', 'evacuation_site', 'toilet', 'water', 'aed'])
const DEFAULT_CENTER: [number, number] = [34.3968, 133.0782] // 三原市役所付近
const DEFAULT_ZOOM = 15
const LOCATE_ZOOM = 16

function createPinIcon(category: PinCategory) {
  const cat = CATEGORIES[category]
  return L.divIcon({
    html: `<div style="
      background:${cat.color};
      width:36px;height:36px;
      border-radius:50% 50% 50% 0;
      transform:rotate(-45deg);
      border:3px solid white;
      box-shadow:0 2px 6px rgba(0,0,0,0.4);
      display:flex;align-items:center;justify-content:center;
    "><span style="transform:rotate(45deg);font-size:16px;line-height:1;">${cat.icon}</span></div>`,
    className: '',
    iconSize: [36, 36],
    iconAnchor: [18, 36],
    popupAnchor: [0, -36],
  })
}

function createHomeIcon() {
  return L.divIcon({
    html: `<div style="
      background:#1D4ED8;
      width:40px;height:40px;
      border-radius:8px;
      border:3px solid white;
      box-shadow:0 2px 8px rgba(0,0,0,0.4);
      display:flex;align-items:center;justify-content:center;
      font-size:22px;line-height:1;
    ">🏠</div>`,
    className: '',
    iconSize: [40, 40],
    iconAnchor: [20, 20],
  })
}

function createUserIcon() {
  return L.divIcon({
    html: `<div style="
      width:20px;height:20px;
      border-radius:50%;
      background:#2563EB;
      border:3px solid white;
      box-shadow:0 0 0 4px rgba(37,99,235,0.3);
    "></div>`,
    className: '',
    iconSize: [20, 20],
    iconAnchor: [10, 10],
  })
}

function createPreviewIcon() {
  return L.divIcon({
    html: `<div style="
      background:#7C3AED;
      width:40px;height:40px;
      border-radius:8px;
      border:3px solid white;
      box-shadow:0 2px 8px rgba(0,0,0,0.5);
      display:flex;align-items:center;justify-content:center;
      font-size:22px;line-height:1;
    ">🏠</div>`,
    className: '',
    iconSize: [40, 40],
    iconAnchor: [20, 20],
  })
}

async function geocodeAddress(address: string): Promise<{ lat: number; lng: number; displayName: string } | null> {
  // 1st: Nominatim（APIキー不要）
  try {
    const url = `https://nominatim.openstreetmap.org/search?q=${encodeURIComponent(address)}&format=json&limit=1&countrycodes=jp`
    const res = await fetch(url, { headers: { 'Accept-Language': 'ja' } })
    if (res.ok) {
      const data = await res.json()
      if (data.length) {
        return { lat: parseFloat(data[0].lat), lng: parseFloat(data[0].lon), displayName: data[0].display_name }
      }
    }
  } catch { /* fall through */ }

  // 2nd: Google Geocoding API（サーバー経由でAPIキーを隠蔽）
  try {
    const res = await fetch(`/api/geocode?address=${encodeURIComponent(address)}`)
    if (res.ok) {
      const data = await res.json()
      if (data.result) return data.result
    }
  } catch { /* fall through */ }

  return null
}

type HomeModalStage = 'menu' | 'input' | 'confirm'

export default function Map() {
  const mapRef = useRef<HTMLDivElement>(null)
  const leafletMap = useRef<L.Map | null>(null)
  const markersRef = useRef<globalThis.Map<string, L.Marker>>(new globalThis.Map())
  const clusterGroupRef = useRef<L.MarkerClusterGroup | null>(null)
  const homeMarkerRef = useRef<L.Marker | null>(null)
  const previewMarkerRef = useRef<L.Marker | null>(null)
  const userMarkerRef = useRef<L.Marker | null>(null)

  const [activeCategories, setActiveCategories] = useState<Set<PinCategory>>(new Set(ALL_CATEGORIES))
  const [selectedPin, setSelectedPin] = useState<Pin | null>(null)
  const [locating, setLocating] = useState(true)
  const [homeLocation, setHomeLocation] = useState<HomeLocation | null>(null)

  // Home modal state
  const [modalStage, setModalStage] = useState<HomeModalStage | null>(null)
  const [addressInput, setAddressInput] = useState('')
  const [geocoding, setGeocoding] = useState(false)
  const [geocodeError, setGeocodeError] = useState('')
  const [pendingHome, setPendingHome] = useState<{ lat: number; lng: number; address: string } | null>(null)

  // ホームマーカーの追加/削除
  function syncHomeMarker(loc: HomeLocation | null) {
    const map = leafletMap.current
    if (!map) return
    if (homeMarkerRef.current) {
      homeMarkerRef.current.remove()
      homeMarkerRef.current = null
    }
    if (loc) {
      homeMarkerRef.current = L.marker([loc.lat, loc.lng], { icon: createHomeIcon(), zIndexOffset: 500 }).addTo(map)
    }
  }

  function clearPreviewMarker() {
    if (previewMarkerRef.current) {
      previewMarkerRef.current.remove()
      previewMarkerRef.current = null
    }
  }

  useEffect(() => {
    if (!mapRef.current || leafletMap.current) return

    const map = L.map(mapRef.current, {
      center: DEFAULT_CENTER,
      zoom: DEFAULT_ZOOM,
      zoomControl: false,
    })

    L.control.zoom({ position: 'bottomright' }).addTo(map)

    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
      maxZoom: 19,
    }).addTo(map)

    leafletMap.current = map
    localStorage.setItem('lastUpdated', new Date().toLocaleDateString('ja-JP'))

    const clusterGroup = L.markerClusterGroup({
      maxClusterRadius: 60,
      spiderfyOnMaxZoom: true,
      showCoverageOnHover: false,
    })

    for (const pin of DUMMY_PINS) {
      const marker = L.marker([pin.lat, pin.lng], { icon: createPinIcon(pin.category) })
      marker.on('click', () => {
        setSelectedPin(pin)
        trackEvent('pin_detail_view', { category: pin.category })
      })
      clusterGroup.addLayer(marker)
      markersRef.current.set(pin.id, marker)
    }

    clusterGroup.addTo(map)
    clusterGroupRef.current = clusterGroup

    // 現在地ボタン（locate）の結果で現在地マーカーを更新
    map.on('locationfound', (e) => {
      userMarkerRef.current
        ? userMarkerRef.current.setLatLng(e.latlng)
        : (userMarkerRef.current = L.marker(e.latlng, { icon: createUserIcon(), zIndexOffset: 400 }).addTo(map))
      setLocating(false)
    })
    map.on('locationerror', () => {
      setLocating(false)
    })

    // 自宅登録 → 現在地 → 固定座標の優先順位で初期表示
    const saved = getHome()
    if (saved) {
      setHomeLocation(saved)
      map.setView([saved.lat, saved.lng], LOCATE_ZOOM)
      homeMarkerRef.current = L.marker([saved.lat, saved.lng], { icon: createHomeIcon(), zIndexOffset: 500 }).addTo(map)
      setLocating(false)
      // 自宅表示の場合でもバックグラウンドで現在地マーカーを取得しておく
      if (navigator.geolocation) {
        navigator.geolocation.getCurrentPosition(
          (pos) => {
            userMarkerRef.current = L.marker(
              [pos.coords.latitude, pos.coords.longitude],
              { icon: createUserIcon(), zIndexOffset: 400 }
            ).addTo(map)
          },
          () => {},
          { timeout: 10000, maximumAge: 60000 }
        )
      }
    } else if (navigator.geolocation) {
      navigator.geolocation.getCurrentPosition(
        (pos) => {
          map.setView([pos.coords.latitude, pos.coords.longitude], LOCATE_ZOOM)
          userMarkerRef.current = L.marker(
            [pos.coords.latitude, pos.coords.longitude],
            { icon: createUserIcon(), zIndexOffset: 400 }
          ).addTo(map)
          setLocating(false)
          trackEvent('auto_geolocation_result', { result: 'success' })
        },
        (err) => {
          setLocating(false)
          trackEvent('auto_geolocation_result', { result: err.code === err.TIMEOUT ? 'timeout' : 'denied' })
        },
        { timeout: 5000, maximumAge: 60000 }
      )
    } else {
      setLocating(false)
    }

    return () => {
      map.remove()
      leafletMap.current = null
      clusterGroupRef.current = null
      homeMarkerRef.current = null
      previewMarkerRef.current = null
      userMarkerRef.current = null
    }
  }, [])

  useEffect(() => {
    const clusterGroup = clusterGroupRef.current
    if (!clusterGroup) return
    for (const pin of DUMMY_PINS) {
      const marker = markersRef.current.get(pin.id)
      if (!marker) continue
      if (activeCategories.has(pin.category)) {
        clusterGroup.addLayer(marker)
      } else {
        clusterGroup.removeLayer(marker)
      }
    }
  }, [activeCategories])

  function toggleCategory(category: PinCategory) {
    setActiveCategories((prev) => {
      const next = new Set(prev)
      if (next.has(category)) next.delete(category)
      else next.add(category)
      return next
    })
    if (selectedPin?.category === category) setSelectedPin(null)
  }

  function locateUser() {
    if (!leafletMap.current || locating) return
    setLocating(true)
    leafletMap.current.locate({ setView: true, maxZoom: LOCATE_ZOOM })
    trackEvent('locate_button_click')
  }

  function openHomeModal() {
    if (homeLocation) {
      setModalStage('menu')
    } else {
      setAddressInput('')
      setGeocodeError('')
      setModalStage('input')
    }
  }

  function closeModal() {
    setModalStage(null)
    clearPreviewMarker()
    setPendingHome(null)
    setAddressInput('')
    setGeocodeError('')
  }

  async function handleGeocode() {
    if (!addressInput.trim()) return
    setGeocoding(true)
    setGeocodeError('')
    try {
      const result = await geocodeAddress(addressInput.trim())
      if (!result) {
        setGeocodeError('住所が見つかりませんでした。もう少し詳しく入力してください。')
        setGeocoding(false)
        return
      }
      const pending = { lat: result.lat, lng: result.lng, address: result.displayName }
      setPendingHome(pending)
      clearPreviewMarker()
      const map = leafletMap.current
      if (map) {
        previewMarkerRef.current = L.marker([pending.lat, pending.lng], {
          icon: createPreviewIcon(),
          zIndexOffset: 600,
        }).addTo(map)
        map.setView([pending.lat, pending.lng], LOCATE_ZOOM)
      }
      setModalStage('confirm')
    } catch {
      setGeocodeError('通信エラーが発生しました。')
    }
    setGeocoding(false)
  }

  function handleConfirmHome() {
    if (!pendingHome) return
    setHome(pendingHome)
    setHomeLocation(pendingHome)
    syncHomeMarker(pendingHome)
    clearPreviewMarker()
    closeModal()
    trackEvent('home_registered')
  }

  function handleDeleteHome() {
    deleteHome()
    setHomeLocation(null)
    syncHomeMarker(null)
    closeModal()
    trackEvent('home_deleted')
  }

  function handleChangeHome() {
    setAddressInput('')
    setGeocodeError('')
    setModalStage('input')
  }

  return (
    <div className="relative w-full h-full">
      <div ref={mapRef} className="w-full h-full" />

      {locating && (
        <div className="absolute inset-0 z-[2000] flex items-center justify-center bg-white/70 backdrop-blur-sm">
          <div className="bg-white rounded-2xl px-8 py-6 flex flex-col items-center gap-4 shadow-lg">
            <svg className="animate-spin w-10 h-10 text-red-500" viewBox="0 0 24 24" fill="none">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z" />
            </svg>
            <p className="text-sm font-medium text-gray-700">現在地を取得しています…</p>
          </div>
        </div>
      )}

      <CategoryFilter activeCategories={activeCategories} onToggle={toggleCategory} />

      {/* 自宅ボタン */}
      <button
        onClick={openHomeModal}
        className="absolute bottom-36 right-4 z-[1000] rounded-full w-12 h-12 shadow-md flex items-center justify-center text-2xl hover:opacity-90 active:opacity-80 transition-opacity"
        style={{
          backgroundColor: homeLocation ? '#1D4ED8' : '#fff',
          border: homeLocation ? 'none' : '2px solid #d1d5db',
        }}
        aria-label="自宅を登録"
      >
        🏠
      </button>

      {/* 現在地ボタン */}
      <button
        onClick={locateUser}
        disabled={locating}
        className="absolute bottom-20 right-4 z-[1000] bg-white rounded-full w-12 h-12 shadow-md flex items-center justify-center text-2xl hover:bg-gray-50 active:bg-gray-100 disabled:opacity-40 disabled:cursor-not-allowed"
        aria-label="現在地"
      >
        📍
      </button>

      <Attribution />

      {selectedPin && (
        <PinDetail pin={selectedPin} onClose={() => setSelectedPin(null)} />
      )}

      {/* 自宅モーダル */}
      {modalStage && (
        <div className="absolute inset-0 z-[1500] flex items-end justify-center pb-8 px-4">
          <div className="bg-white rounded-2xl shadow-xl w-full max-w-sm p-5">

            {modalStage === 'menu' && (
              <>
                <h2 className="text-base font-bold text-gray-800 mb-1">自宅</h2>
                <p className="text-xs text-gray-500 mb-4 truncate">{homeLocation?.address}</p>
                <div className="flex flex-col gap-2">
                  <button
                    onClick={handleChangeHome}
                    className="w-full py-3 rounded-xl bg-blue-600 text-white font-bold text-sm hover:bg-blue-700"
                  >
                    自宅を変更する
                  </button>
                  <button
                    onClick={handleDeleteHome}
                    className="w-full py-3 rounded-xl bg-red-50 text-red-600 font-bold text-sm hover:bg-red-100"
                  >
                    自宅を削除する
                  </button>
                  <button
                    onClick={closeModal}
                    className="w-full py-3 rounded-xl bg-gray-100 text-gray-600 font-bold text-sm hover:bg-gray-200"
                  >
                    キャンセル
                  </button>
                </div>
              </>
            )}

            {modalStage === 'input' && (
              <>
                <h2 className="text-base font-bold text-gray-800 mb-3">自宅を登録</h2>
                <input
                  type="text"
                  value={addressInput}
                  onChange={(e) => setAddressInput(e.target.value)}
                  onKeyDown={(e) => { if (e.key === 'Enter') handleGeocode() }}
                  placeholder="例：松山市二番町4丁目7"
                  className="w-full border border-gray-300 rounded-xl px-4 py-3 text-sm mb-2 outline-none focus:border-blue-500"
                  autoFocus
                />
                {geocodeError && <p className="text-xs text-red-500 mb-2">{geocodeError}</p>}
                <div className="flex gap-2">
                  <button
                    onClick={closeModal}
                    className="flex-1 py-3 rounded-xl bg-gray-100 text-gray-600 font-bold text-sm"
                  >
                    キャンセル
                  </button>
                  <button
                    onClick={handleGeocode}
                    disabled={geocoding || !addressInput.trim()}
                    className="flex-1 py-3 rounded-xl bg-blue-600 text-white font-bold text-sm disabled:opacity-50"
                  >
                    {geocoding ? '検索中…' : '住所を検索'}
                  </button>
                </div>
              </>
            )}

            {modalStage === 'confirm' && pendingHome && (
              <>
                <h2 className="text-base font-bold text-gray-800 mb-1">この場所でよろしいですか？</h2>
                <p className="text-xs text-gray-500 mb-4 leading-relaxed">{pendingHome.address}</p>
                <div className="flex gap-2">
                  <button
                    onClick={() => {
                      clearPreviewMarker()
                      setModalStage('input')
                    }}
                    className="flex-1 py-3 rounded-xl bg-gray-100 text-gray-600 font-bold text-sm"
                  >
                    戻る
                  </button>
                  <button
                    onClick={handleConfirmHome}
                    className="flex-1 py-3 rounded-xl bg-blue-600 text-white font-bold text-sm"
                  >
                    登録する
                  </button>
                </div>
              </>
            )}

          </div>
        </div>
      )}
    </div>
  )
}
