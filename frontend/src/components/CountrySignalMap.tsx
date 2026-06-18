import { useEffect, useRef } from 'react'
import L, { type LayerGroup, type Map as LeafletMap } from 'leaflet'

import 'leaflet/dist/leaflet.css'

type SignalRegion = {
  key: string
  label: string
  count: number
  percentage: number
}

type CountrySignalMapProps = {
  country: string
  regions: SignalRegion[]
}

type MapView = {
  center: [number, number]
  zoom: number
}

const countryViews: Record<string, MapView> = {
  Austria: { center: [47.6, 14.1], zoom: 7 },
  Belgium: { center: [50.65, 4.65], zoom: 8 },
  Bulgaria: { center: [42.75, 25.35], zoom: 7 },
  Croatia: { center: [45.2, 16.4], zoom: 7 },
  Cyprus: { center: [35.13, 33.38], zoom: 9 },
  Czechia: { center: [49.8, 15.5], zoom: 7 },
  Denmark: { center: [56.1, 9.4], zoom: 7 },
  Estonia: { center: [58.6, 25.4], zoom: 7 },
  Finland: { center: [64.7, 26.0], zoom: 5 },
  France: { center: [46.5, 2.4], zoom: 6 },
  Germany: { center: [51.1, 10.4], zoom: 6 },
  Greece: { center: [39.1, 22.0], zoom: 6 },
  Hungary: { center: [47.15, 19.5], zoom: 7 },
  Ireland: { center: [53.25, -8.1], zoom: 7 },
  Italy: { center: [42.8, 12.6], zoom: 6 },
  Latvia: { center: [56.9, 24.6], zoom: 7 },
  Lithuania: { center: [55.2, 23.9], zoom: 7 },
  Luxembourg: { center: [49.81, 6.13], zoom: 10 },
  Malta: { center: [35.9, 14.44], zoom: 11 },
  Netherlands: { center: [52.2, 5.4], zoom: 8 },
  Poland: { center: [52.1, 19.4], zoom: 6 },
  Portugal: { center: [39.6, -8.0], zoom: 7 },
  Romania: { center: [45.85, 24.95], zoom: 6 },
  Slovakia: { center: [48.7, 19.6], zoom: 7 },
  Slovenia: { center: [46.15, 14.9], zoom: 8 },
  Spain: { center: [40.2, -3.5], zoom: 6 },
  Sweden: { center: [62.2, 16.6], zoom: 5 },
}

const europeView: MapView = {
  center: [52.0, 13.0],
  zoom: 4,
}

const regionCoordinates: Record<string, Record<string, [number, number]>> = {
  Cyprus: {
    Nicosia: [35.1856, 33.3823],
    Limassol: [34.6786, 33.0413],
    Larnaca: [34.9182, 33.6232],
    Paphos: [34.7754, 32.4245],
    'Famagusta area': [35.1174, 33.9385],
  },
}

function escapeHtml(value: string): string {
  return value
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#039;')
}

function CountrySignalMap({ country, regions }: CountrySignalMapProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const mapRef = useRef<LeafletMap | null>(null)
  const signalLayerRef = useRef<LayerGroup | null>(null)

  useEffect(() => {
    if (!containerRef.current || mapRef.current) return

    const map = L.map(containerRef.current, {
      center: europeView.center,
      zoom: europeView.zoom,
      minZoom: 3,
      maxZoom: 13,
      scrollWheelZoom: false,
    })

    L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution:
        '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
      maxZoom: 19,
    }).addTo(map)

    mapRef.current = map
    signalLayerRef.current = L.layerGroup().addTo(map)

    return () => {
      map.remove()
      mapRef.current = null
      signalLayerRef.current = null
    }
  }, [])

  useEffect(() => {
    const map = mapRef.current
    const signalLayer = signalLayerRef.current
    if (!map || !signalLayer) return

    const view = countryViews[country] ?? europeView
    map.setView(view.center, view.zoom, { animate: true })
    signalLayer.clearLayers()

    const coordinates = regionCoordinates[country] ?? {}
    const maxCount = Math.max(1, ...regions.map((region) => region.count))

    for (const region of regions) {
      const point = coordinates[region.label]
      if (!point) continue

      const marker = L.circleMarker(point, {
        radius: 7 + (region.count / maxCount) * 13,
        color: '#ffffff',
        weight: 2,
        fillColor: '#e96d4e',
        fillOpacity: 0.78,
      })
      marker.bindPopup(
        `<strong>${escapeHtml(region.label)}</strong><br>` +
          `${region.count.toLocaleString()} signals (${region.percentage}%)`,
      )
      marker.addTo(signalLayer)
    }

    window.setTimeout(() => map.invalidateSize(), 0)
  }, [country, regions])

  return (
    <div
      aria-label={`Interactive geographic map for ${country || 'Europe'}`}
      className="country-signal-map"
      ref={containerRef}
      role="region"
    />
  )
}

export default CountrySignalMap
