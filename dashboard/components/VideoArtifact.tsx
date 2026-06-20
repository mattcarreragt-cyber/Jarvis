'use client'

import { useEffect, useRef, useState } from 'react'
import { Film, AlertCircle, Loader2 } from 'lucide-react'
import { apiFetch, apiUrl } from '@/lib/api'

interface Props { statusUrl: string }

type State = 'running' | 'done' | 'error'

export default function VideoArtifact({ statusUrl }: Props) {
  const [state, setState] = useState<State>('running')
  const [viewUrl, setViewUrl] = useState<string>('')
  const [error, setError] = useState<string>('')
  const timer = useRef<ReturnType<typeof setInterval> | null>(null)
  const elapsed = useRef(0)
  const [secs, setSecs] = useState(0)

  useEffect(() => {
    const poll = async () => {
      try {
        const r = await apiFetch(statusUrl)
        if (!r.ok) return
        const data = await r.json()
        if (data.state === 'done' && data.view_url) {
          setViewUrl(apiUrl(data.view_url))
          setState('done')
          if (timer.current) clearInterval(timer.current)
        } else if (data.state === 'error') {
          setError(data.error || 'Échec de la génération')
          setState('error')
          if (timer.current) clearInterval(timer.current)
        }
      } catch { /* on retente au prochain tick */ }
    }
    timer.current = setInterval(() => {
      elapsed.current += 5
      setSecs(elapsed.current)
      poll()
    }, 5000)
    poll()
    return () => { if (timer.current) clearInterval(timer.current) }
  }, [statusUrl])

  if (state === 'done') {
    return (
      <video
        controls autoPlay loop muted
        src={viewUrl}
        className="mt-2 rounded-lg border border-[rgba(0,212,255,0.25)] max-w-full"
        style={{ maxHeight: 420 }}
      />
    )
  }

  if (state === 'error') {
    return (
      <div className="mt-2 flex items-center gap-2 text-xs text-red-400 bg-[rgba(239,68,68,0.08)] rounded px-3 py-2">
        <AlertCircle size={14} /> {error}
      </div>
    )
  }

  const mm = Math.floor(secs / 60)
  const ss = secs % 60
  return (
    <div className="mt-2 flex items-center gap-3 text-xs text-[var(--cyan)] border border-dashed border-[rgba(0,212,255,0.3)] rounded px-3 py-3">
      <Film size={16} />
      <Loader2 size={14} className="animate-spin" />
      <span>Génération vidéo en cours… {mm}:{ss.toString().padStart(2, '0')}</span>
    </div>
  )
}
