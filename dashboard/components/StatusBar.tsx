'use client'

import { useEffect, useState } from 'react'

interface ServiceStatus {
  status: 'ok' | 'error' | 'unavailable'
  detail?: string
}

interface Health {
  status: 'ok' | 'error'
  core: { postgres: ServiceStatus; redis: ServiceStatus; qdrant: ServiceStatus }
  compute: { ollama: ServiceStatus; comfyui: ServiceStatus; whisper: ServiceStatus; piper: ServiceStatus }
}

const DOT: Record<string, string> = {
  ok:          'bg-[var(--cyan)] shadow-[0_0_6px_var(--cyan)]',
  unavailable: 'bg-yellow-500 shadow-[0_0_6px_#ca8a04]',
  error:       'bg-red-500 shadow-[0_0_6px_#ef4444]',
}

function Dot({ s }: { s: ServiceStatus }) {
  return <span className={`inline-block w-2 h-2 rounded-full ${DOT[s.status] ?? DOT.error}`} />
}

const API = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'

export default function StatusBar() {
  const [health, setHealth] = useState<Health | null>(null)

  useEffect(() => {
    const fetch_ = () =>
      fetch(`${API}/api/health`)
        .then(r => r.json())
        .then(setHealth)
        .catch(() => setHealth(null))

    fetch_()
    const id = setInterval(fetch_, 15_000)
    return () => clearInterval(id)
  }, [])

  if (!health) {
    return (
      <div className="flex justify-center pb-2">
        <span className="text-[var(--text-dim)] text-[10px] tracking-widest">
          API INDISPONIBLE
        </span>
      </div>
    )
  }

  const services: [string, ServiceStatus][] = [
    ['PG',     health.core.postgres],
    ['REDIS',  health.core.redis],
    ['QDRANT', health.core.qdrant],
    ['OLLAMA', health.compute.ollama],
    ['COMFY',  health.compute.comfyui],
    ['STT',    health.compute.whisper],
    ['TTS',    health.compute.piper],
  ]

  return (
    <div className="flex justify-center gap-4 pb-3 px-4">
      {services.map(([name, s]) => (
        <span key={name} className="flex items-center gap-1">
          <Dot s={s} />
          <span className="text-[9px] tracking-widest text-[var(--text-dim)]">{name}</span>
        </span>
      ))}
    </div>
  )
}
