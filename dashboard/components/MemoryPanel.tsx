'use client'

import { useCallback, useEffect, useState } from 'react'
import { motion } from 'framer-motion'
import { Brain, X, Trash2 } from 'lucide-react'
import { fetchMemory, deleteMemory, clearMemory, MemoryFact } from '@/lib/api'

interface Props { onClose: () => void }

export default function MemoryPanel({ onClose }: Props) {
  const [facts, setFacts] = useState<MemoryFact[]>([])
  const [loading, setLoading] = useState(true)

  const load = useCallback(async () => {
    setFacts(await fetchMemory())
    setLoading(false)
  }, [])

  useEffect(() => { load() }, [load])

  const remove = async (id: string) => {
    if (await deleteMemory(id)) setFacts(f => f.filter(x => x.id !== id))
  }
  const wipe = async () => {
    if (await clearMemory()) setFacts([])
  }

  return (
    <motion.div
      className="absolute inset-0 z-20 flex flex-col panel"
      initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: 20 }} transition={{ duration: 0.2 }}
    >
      <div className="flex items-center justify-between px-4 py-3 border-b border-[rgba(0,212,255,0.15)]">
        <div className="flex items-center gap-2">
          <Brain size={14} className="text-[var(--cyan)]" />
          <span className="text-xs tracking-widest text-[var(--cyan)] glow-sm">MÉMOIRE LONG TERME</span>
        </div>
        <button onClick={onClose} className="text-[var(--text-dim)] hover:text-[var(--cyan)]">
          <X size={16} />
        </button>
      </div>

      <div className="flex-1 overflow-y-auto px-4 py-4 flex flex-col gap-2">
        {loading ? (
          <p className="text-xs text-[var(--text-dim)] tracking-widest">CHARGEMENT…</p>
        ) : facts.length === 0 ? (
          <div className="flex-1 flex flex-col items-center justify-center gap-2 text-center">
            <Brain size={28} className="text-[var(--text-dim)]" />
            <p className="text-xs text-[var(--text-dim)]">Aucun souvenir enregistré.</p>
            <p className="text-[10px] text-[var(--text-dim)] opacity-60">
              Dis « souviens-toi que… » dans le chat.
            </p>
          </div>
        ) : facts.map(f => (
          <div key={f.id}
            className="group flex items-start justify-between gap-2 border border-[rgba(0,212,255,0.12)]
                       rounded px-3 py-2">
            <span className="text-xs text-[var(--text)]">{f.text}</span>
            <button onClick={() => remove(f.id)}
              className="text-[var(--text-dim)] hover:text-red-400 opacity-0 group-hover:opacity-100 transition-opacity shrink-0">
              <Trash2 size={13} />
            </button>
          </div>
        ))}
      </div>

      {facts.length > 0 && (
        <div className="px-4 py-3 border-t border-[rgba(0,212,255,0.1)]">
          <button onClick={wipe}
            className="flex items-center gap-2 text-[10px] tracking-widest text-red-400/80 hover:text-red-400">
            <Trash2 size={12} /> TOUT OUBLIER
          </button>
        </div>
      )}
    </motion.div>
  )
}
