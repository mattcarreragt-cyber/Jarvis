'use client'

import { useCallback, useEffect, useState } from 'react'
import { motion } from 'framer-motion'
import { Film, X, Loader2, CheckCircle, AlertCircle } from 'lucide-react'
import { fetchJobs, apiUrl, GenJob } from '@/lib/api'

interface Props { onClose: () => void }

export default function JobsPanel({ onClose }: Props) {
  const [jobs, setJobs] = useState<GenJob[]>([])
  const [loading, setLoading] = useState(true)

  const load = useCallback(async () => {
    const data = await fetchJobs()
    setJobs(data.jobs)
    setLoading(false)
  }, [])

  useEffect(() => {
    load()
    const id = setInterval(load, 5000)
    return () => clearInterval(id)
  }, [load])

  const fmt = (ts: number) => new Date(ts * 1000).toLocaleTimeString('fr-FR')

  return (
    <motion.div
      className="absolute inset-0 z-20 flex flex-col panel"
      initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: 20 }} transition={{ duration: 0.2 }}
    >
      <div className="flex items-center justify-between px-4 py-3 border-b border-[rgba(0,212,255,0.15)]">
        <div className="flex items-center gap-2">
          <Film size={14} className="text-[var(--cyan)]" />
          <span className="text-xs tracking-widest text-[var(--cyan)] glow-sm">JOBS DE GÉNÉRATION</span>
        </div>
        <button onClick={onClose} className="text-[var(--text-dim)] hover:text-[var(--cyan)]">
          <X size={16} />
        </button>
      </div>

      <div className="flex-1 overflow-y-auto px-4 py-4 flex flex-col gap-3">
        {loading ? (
          <p className="text-xs text-[var(--text-dim)] tracking-widest">CHARGEMENT…</p>
        ) : jobs.length === 0 ? (
          <div className="flex-1 flex flex-col items-center justify-center gap-2 text-center">
            <Film size={28} className="text-[var(--text-dim)]" />
            <p className="text-xs text-[var(--text-dim)]">Aucune génération lancée.</p>
            <p className="text-[10px] text-[var(--text-dim)] opacity-60">
              Demande une vidéo dans le chat pour la voir apparaître ici.
            </p>
          </div>
        ) : jobs.map(job => (
          <div key={job.id}
            className="border border-[rgba(0,212,255,0.15)] rounded px-3 py-2 flex flex-col gap-2">
            <div className="flex items-start justify-between gap-2">
              <span className="text-xs text-[var(--text)] line-clamp-2">{job.prompt}</span>
              <StateBadge state={job.state} />
            </div>
            <div className="flex items-center justify-between text-[10px] text-[var(--text-dim)]">
              <span>{job.kind.toUpperCase()} · {fmt(job.created_at)}</span>
            </div>
            {job.state === 'done' && job.view_url && (
              <video controls loop muted src={apiUrl(job.view_url)}
                className="rounded border border-[rgba(0,212,255,0.2)] max-w-full"
                style={{ maxHeight: 220 }} />
            )}
            {job.state === 'error' && (
              <span className="text-[10px] text-red-400">{job.error}</span>
            )}
          </div>
        ))}
      </div>
    </motion.div>
  )
}

function StateBadge({ state }: { state: GenJob['state'] }) {
  if (state === 'running')
    return <span className="flex items-center gap-1 text-[10px] text-[var(--cyan)] shrink-0">
      <Loader2 size={11} className="animate-spin" /> EN COURS</span>
  if (state === 'done')
    return <span className="flex items-center gap-1 text-[10px] text-[#00ffcc] shrink-0">
      <CheckCircle size={11} /> TERMINÉ</span>
  return <span className="flex items-center gap-1 text-[10px] text-red-400 shrink-0">
    <AlertCircle size={11} /> ERREUR</span>
}
