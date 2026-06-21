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

/** Télécharge l'export d'une conversation (md|json) via le navigateur. */
export async function exportSession(id: string, format: 'md' | 'json'): Promise<boolean> {
  const r = await apiFetch(`/api/sessions/${id}/export?format=${format}`)
  if (!r.ok) return false
  const blob = await r.blob()
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `jarvis_${id.slice(0, 8)}.${format}`
  document.body.appendChild(a)
  a.click()
  a.remove()
  URL.revokeObjectURL(url)
  return true
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

export interface Webhook {
  id: string
  token: string
  label: string
  message: string
  enabled: boolean
  run_count: number
  last_triggered: string | null
}

export async function fetchHooks(): Promise<Webhook[]> {
  const r = await apiFetch('/api/hooks')
  if (!r.ok) return []
  return (await r.json()).hooks
}

export async function createHook(label: string, message: string): Promise<Webhook | null> {
  const r = await apiFetch('/api/hooks', {
    method: 'POST', body: JSON.stringify({ label, message }),
  })
  if (!r.ok) return null
  return r.json()
}

export async function deleteHook(id: string): Promise<boolean> {
  const r = await apiFetch(`/api/hooks/${id}`, { method: 'DELETE' })
  return r.ok
}

export function hookUrl(token: string): string {
  return `${API}/api/hooks/${token}`
}

export interface CyberHost {
  id: string
  label: string
  hostname: string
  port: number
  username: string
}

export interface CyberFinding {
  check: string
  severity: 'critical' | 'high' | 'medium' | 'low' | 'info'
  title: string
  detail: string | null
  recommendation: string | null
  remediation: string | null
}

export async function fetchCyberHosts(): Promise<CyberHost[]> {
  const r = await apiFetch('/api/cyber/hosts')
  if (!r.ok) return []
  return (await r.json()).hosts
}

export async function addCyberHost(label: string, hostname: string, username: string, port: number): Promise<boolean> {
  const r = await apiFetch('/api/cyber/hosts', {
    method: 'POST', body: JSON.stringify({ label, hostname, username, port }),
  })
  return r.ok
}

export async function deleteCyberHost(id: string): Promise<boolean> {
  const r = await apiFetch(`/api/cyber/hosts/${id}`, { method: 'DELETE' })
  return r.ok
}

export async function runCyberAudit(id: string): Promise<{ ok: boolean; findings?: CyberFinding[]; summary?: Record<string, number>; score?: number; grade?: string; error?: string }> {
  const r = await apiFetch(`/api/cyber/hosts/${id}/audit`, { method: 'POST' })
  if (!r.ok) return { ok: false, error: `HTTP ${r.status}` }
  return r.json()
}

export async function fetchCyberScores(id: string): Promise<{ score: number; grade: string; created_at: string }[]> {
  const r = await apiFetch(`/api/cyber/hosts/${id}/scores`)
  if (!r.ok) return []
  return (await r.json()).history
}

export async function remediateCyber(id: string, command: string): Promise<{ ok: boolean; output?: string; error?: string }> {
  const r = await apiFetch(`/api/cyber/hosts/${id}/remediate`, {
    method: 'POST', body: JSON.stringify({ command }),
  })
  const d = await r.json().catch(() => ({}))
  if (!r.ok) return { ok: false, error: d.detail || `HTTP ${r.status}` }
  return { ok: true, output: d.output }
}

export interface UsageStats {
  totals: { sessions: number; messages: number; facts: number; tasks: number; media: number }
  agent_usage: { agent: string; count: number }[]
  method_breakdown: { method: string; count: number }[]
  messages_per_day: { day: string; count: number }[]
  tools: { ok: number; error: number; top: { tool: string; count: number }[] }
}

export async function fetchStats(): Promise<UsageStats | null> {
  const r = await apiFetch('/api/stats')
  if (!r.ok) return null
  return r.json()
}

export interface SystemInfo {
  paliers: { name: string; role: string; status: string }[]
  capabilities: { name: string; machine: string; model: string; vram_gb: number | null; description: string }[]
  agents: { name: string; description: string }[]
  unrestricted_mode?: boolean
}

export async function fetchSystem(): Promise<SystemInfo | null> {
  const r = await apiFetch('/api/system')
  if (!r.ok) return null
  return r.json()
}

/** Télécharge une sauvegarde JSON du « cerveau » de JARVIS. */
export async function downloadBackup(): Promise<boolean> {
  const r = await apiFetch('/api/backup')
  if (!r.ok) return false
  const blob = await r.blob()
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `jarvis_backup_${new Date().toISOString().slice(0, 10)}.json`
  document.body.appendChild(a); a.click(); a.remove()
  URL.revokeObjectURL(url)
  return true
}

/** Restaure depuis un fichier de sauvegarde. */
export async function restoreBackup(file: File, mode: 'merge' | 'replace'): Promise<{ ok: boolean; imported?: Record<string, unknown>; error?: string }> {
  const form = new FormData()
  form.append('file', file)
  const headers: HeadersInit = KEY ? { 'X-API-Key': KEY } : {}
  const r = await fetch(`${API}/api/backup/restore?mode=${mode}`, { method: 'POST', headers, body: form })
  const data = await r.json().catch(() => ({}))
  if (!r.ok) return { ok: false, error: data.detail || `HTTP ${r.status}` }
  return data
}

export interface MediaAsset {
  id: string
  kind: 'image' | 'video' | 'audio'
  prompt: string | null
  created_at: string
  view_url: string
}

export async function fetchMedia(): Promise<MediaAsset[]> {
  const r = await apiFetch('/api/media')
  if (!r.ok) return []
  return (await r.json()).assets
}

export async function deleteMedia(id: string): Promise<boolean> {
  const r = await apiFetch(`/api/media/${id}`, { method: 'DELETE' })
  return r.ok
}

export interface Notification {
  id: string
  text: string
  source: string | null
  read: boolean
  created_at: string
}

export interface AgendaTask {
  id: string
  label: string
  kind: string
  payload: string
  schedule_kind: string
  time_of_day: string | null
  interval_sec: number | null
  next_run: string
  enabled: boolean
  last_run: string | null
}

export async function fetchNotifications(): Promise<{ notifications: Notification[]; unread: number }> {
  const r = await apiFetch('/api/agenda/notifications')
  if (!r.ok) return { notifications: [], unread: 0 }
  return r.json()
}

export async function markNotificationsRead(): Promise<void> {
  await apiFetch('/api/agenda/notifications/read', { method: 'POST' })
}

export async function fetchAgendaTasks(): Promise<AgendaTask[]> {
  const r = await apiFetch('/api/agenda/tasks')
  if (!r.ok) return []
  return (await r.json()).tasks
}

export async function deleteAgendaTask(id: string): Promise<boolean> {
  const r = await apiFetch(`/api/agenda/tasks/${id}`, { method: 'DELETE' })
  return r.ok
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

/** Anime une image (image→vidéo). Retourne le job_id, ou lève une erreur. */
export async function animateImage(file: File, seconds: number): Promise<string> {
  const form = new FormData()
  form.append('file', file)
  form.append('seconds', String(seconds))
  const headers: HeadersInit = KEY ? { 'X-API-Key': KEY } : {}
  const r = await fetch(`${API}/api/video/animate`, { method: 'POST', headers, body: form })
  if (!r.ok) {
    const d = await r.json().catch(() => ({}))
    throw new Error(d.detail || `HTTP ${r.status}`)
  }
  return (await r.json()).job_id as string
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
