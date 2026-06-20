const API  = process.env.NEXT_PUBLIC_API_URL  ?? 'http://localhost:8000'
const KEY  = process.env.NEXT_PUBLIC_API_KEY  ?? ''

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
