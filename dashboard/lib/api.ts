const API  = process.env.NEXT_PUBLIC_API_URL  ?? 'http://localhost:8000'
const KEY  = process.env.NEXT_PUBLIC_API_KEY  ?? ''

/** Construit une URL absolue vers l'API à partir d'un chemin relatif. */
export function apiUrl(path: string): string {
  return path.startsWith('http') ? path : `${API}${path}`
}

export function apiHeaders(): HeadersInit {
  return KEY ? { 'Content-Type': 'application/json', 'X-API-Key': KEY }
             : { 'Content-Type': 'application/json' }
}

export async function apiFetch(path: string, init?: RequestInit) {
  return fetch(`${API}${path}`, {
    ...init,
    headers: { ...apiHeaders(), ...(init?.headers ?? {}) },
  })
}

export interface SessionSummary {
  id: string
  created_at: string
  title: string | null
  message_count: number
}

export interface HistoryMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  agent: string | null
  created_at: string
}

export async function fetchSessions(): Promise<SessionSummary[]> {
  const r = await apiFetch('/api/sessions')
  if (!r.ok) return []
  return r.json()
}

export async function fetchSession(id: string): Promise<HistoryMessage[]> {
  const r = await apiFetch(`/api/sessions/${id}`)
  if (!r.ok) return []
  return r.json()
}

export interface NextcloudStatus {
  configured: boolean
  sync_enabled: boolean
  sync_interval: number
  root: string
  running: boolean
  files: number
  chunks: number
  last_sync: string | null
  last_result: Record<string, unknown> | null
}

export async function fetchNextcloudStatus(): Promise<NextcloudStatus | null> {
  const r = await apiFetch('/api/nextcloud/status')
  if (!r.ok) return null
  return r.json()
}

export async function triggerNextcloudSync(): Promise<boolean> {
  const r = await apiFetch('/api/nextcloud/sync?background=true', { method: 'POST' })
  return r.ok
}

export async function triggerReembed(): Promise<{ ok: boolean; updated?: number; error?: string }> {
  const r = await apiFetch('/api/docs/reembed', { method: 'POST' })
  if (!r.ok) return { ok: false, error: `HTTP ${r.status}` }
  return r.json()
}

export interface MemoryFact {
  id: string
  text: string
  kind: string
  created_at: string
}

export async function fetchMemory(): Promise<MemoryFact[]> {
  const r = await apiFetch('/api/memory')
  if (!r.ok) return []
  return (await r.json()).facts
}

export async function deleteMemory(id: string): Promise<boolean> {
  const r = await apiFetch(`/api/memory/${id}`, { method: 'DELETE' })
  return r.ok
}

export async function clearMemory(): Promise<boolean> {
  const r = await apiFetch('/api/memory', { method: 'DELETE' })
  return r.ok
}

export interface GenJob {
  id: string
  kind: string
  prompt: string
  state: 'running' | 'done' | 'error'
  created_at: number
  view_url: string | null
  error: string | null
}

export async function fetchJobs(): Promise<{ jobs: GenJob[]; running: number }> {
  const r = await apiFetch('/api/jobs')
  if (!r.ok) return { jobs: [], running: 0 }
  return r.json()
}

/** Transcrit un blob audio en texte via Whisper (Kubuntu). */
export async function transcribeAudio(blob: Blob): Promise<string> {
  const form = new FormData()
  form.append('file', blob, 'audio.webm')
  const headers: HeadersInit = KEY ? { 'X-API-Key': KEY } : {}
  const r = await fetch(`${API}/api/voice/transcribe`, { method: 'POST', headers, body: form })
  if (!r.ok) throw new Error(`transcribe HTTP ${r.status}`)
  const data = await r.json()
  return data.text as string
}

/** Synthèse vocale (Piper). Retourne une URL d'objet audio jouable, ou null. */
export async function speak(text: string): Promise<string | null> {
  try {
    const r = await apiFetch('/api/voice/speak', {
      method: 'POST',
      body: JSON.stringify({ text }),
    })
    if (!r.ok) return null
    const blob = await r.blob()
    return URL.createObjectURL(blob)
  } catch {
    return null
  }
}
