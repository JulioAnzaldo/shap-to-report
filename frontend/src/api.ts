import type { EventMeta, SituationalReport, SourceBody, BackendType } from './types'

const BASE = '/api'

export async function fetchEvents(): Promise<EventMeta[]> {
  const res = await fetch(`${BASE}/events`)
  if (!res.ok) throw new Error(`Failed to fetch events: ${res.status}`)
  const data = await res.json()
  return data.events as EventMeta[]
}

export async function fetchReport(
  event_id: string,
  source_bodies: SourceBody[],
  backend: BackendType,
  force_refresh = false,
): Promise<{ report: SituationalReport; cached: boolean }> {
  const res = await fetch(`${BASE}/explain`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ event_id, source_bodies, backend, force_refresh }),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Unknown error' }))
    throw new Error(err.detail ?? `Request failed: ${res.status}`)
  }
  const data = await res.json()
  return { report: data.report as SituationalReport, cached: data.cached ?? false }
}
