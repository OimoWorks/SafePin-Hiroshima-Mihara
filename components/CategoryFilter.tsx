'use client'

import { useState, useEffect, useRef } from 'react'
import { PinCategory, CATEGORIES } from '@/lib/types'
import { DUMMY_PINS } from '@/lib/pins'
import { trackEvent } from '@/lib/analytics'

type Props = {
  activeCategories: Set<PinCategory>
  onToggle: (category: PinCategory) => void
}

// データが1件も存在しないカテゴリはフィルターに表示しない
// (例: 三原市版では給水ポイントデータが未整備のため非表示になる)
const CATEGORIES_WITH_DATA = new Set(DUMMY_PINS.map((p) => p.category))

export default function CategoryFilter({ activeCategories, onToggle }: Props) {
  const [open, setOpen] = useState(false)
  const containerRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!open) return
    function handleClick(e: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClick)
    return () => document.removeEventListener('mousedown', handleClick)
  }, [open])

  return (
    <div ref={containerRef} className="absolute top-4 left-4 z-[1000] flex flex-col gap-2">
      {/* ハンバーガーボタン */}
      <button
        onClick={() => setOpen((v) => !v)}
        className="w-12 h-12 bg-white rounded-full shadow-md flex items-center justify-center text-gray-700 hover:bg-gray-50 active:bg-gray-100"
        aria-label={open ? 'フィルターを閉じる' : 'フィルターを開く'}
      >
        {open ? (
          <svg width="20" height="20" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
            <line x1="4" y1="4" x2="16" y2="16" />
            <line x1="16" y1="4" x2="4" y2="16" />
          </svg>
        ) : (
          <svg width="20" height="20" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
            <line x1="3" y1="5" x2="17" y2="5" />
            <circle cx="14" cy="5" r="2" fill="currentColor" stroke="none" />
            <line x1="3" y1="10" x2="17" y2="10" />
            <circle cx="7" cy="10" r="2" fill="currentColor" stroke="none" />
            <line x1="3" y1="15" x2="17" y2="15" />
            <circle cx="12" cy="15" r="2" fill="currentColor" stroke="none" />
          </svg>
        )}
      </button>

      {/* カテゴリ一覧（展開時） */}
      <div
        className={`flex flex-col gap-2 transition-all duration-200 origin-top ${
          open ? 'opacity-100 scale-y-100' : 'opacity-0 scale-y-0 pointer-events-none'
        }`}
      >
        {(Object.entries(CATEGORIES) as [PinCategory, typeof CATEGORIES[PinCategory]][])
          .filter(([key]) => CATEGORIES_WITH_DATA.has(key))
          .map(([key, cat]) => {
          const isActive = activeCategories.has(key)
          return (
            <button
              key={key}
              onClick={() => {
                const next = !isActive
                trackEvent('category_filter_toggle', { category: key, action: next ? 'on' : 'off' })
                onToggle(key)
              }}
              className="flex items-center gap-2 px-3 py-2 rounded-lg shadow-md text-sm font-bold transition-all"
              style={{
                backgroundColor: isActive ? cat.color : '#e5e7eb',
                color: isActive ? '#fff' : '#6b7280',
                border: `2px solid ${isActive ? cat.color : '#d1d5db'}`,
              }}
            >
              <span>{cat.icon}</span>
              <span>{cat.label}</span>
            </button>
          )
        })}
      </div>
    </div>
  )
}
