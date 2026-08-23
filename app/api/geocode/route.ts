import { NextRequest, NextResponse } from 'next/server'

const ACCEPTED_TYPES = new Set(['street_address', 'premise', 'subpremise'])

export async function GET(req: NextRequest) {
  const address = req.nextUrl.searchParams.get('address')
  if (!address) {
    return NextResponse.json({ error: 'address is required' }, { status: 400 })
  }

  const apiKey = process.env.GOOGLE_MAPS_API_KEY
  if (!apiKey) {
    return NextResponse.json({ error: 'geocoding unavailable' }, { status: 503 })
  }

  const url = `https://maps.googleapis.com/maps/api/geocode/json?address=${encodeURIComponent(address)}&key=${apiKey}&language=ja&region=JP`
  const res = await fetch(url)
  if (!res.ok) {
    return NextResponse.json({ error: 'upstream error' }, { status: 502 })
  }

  const data = await res.json()
  if (data.status !== 'OK' || !data.results?.length) {
    return NextResponse.json({ result: null })
  }

  // street_address / premise レベルのみ採用
  const match = data.results.find((r: { types: string[] }) =>
    r.types.some((t: string) => ACCEPTED_TYPES.has(t))
  )
  if (!match) {
    return NextResponse.json({ result: null })
  }

  return NextResponse.json({
    result: {
      lat: match.geometry.location.lat,
      lng: match.geometry.location.lng,
      displayName: match.formatted_address,
    },
  })
}
