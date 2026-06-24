'use client'

import { useEffect, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Clock, ChevronLeft, MessageSquare, Download, FileJson, Trash2 } from 'lucide-react'
import { fetchSessions, fetchSession, exportSession, deleteSession, SessionSummary, HistoryMessage } from '@/lib/api'

interface Props {
  onRestore: (messages: { role: 'user' | 'assistant'; content: string; agent?: string }[]) => void
  onClose: () => void
}

export default function HistoryPanel({ onRestore, onClose }: Props) {
  const [sessions, setSessions]   = useState<SessionSummary[]>([])
  const [selected, setSelected]   = useState<string | null>(null)
  const [messages, setMessages]   = useState<HistoryMessage[]>([])
  const [loading, setLoading]     = useState(false)

  useEffect(() => {
    fetchSessions().then(setSessions)
  }, [])

  const open = async (id: string) => {
    setLoading(true)
    setSelected(id)
    const msgs = await fetchSession(id)
    setMessages(msgs)
    setLoading(false)
  }

  const remove = async (id: string, e: React.MouseEvent) => {
    e.stopPropagation()
    if (!confirm('Supprimer définitivement cette conversation ?')) return
    const ok = await deleteSession(id)
    if (!ok) return
    setSessions(prev => prev.filter(s => s.id !== id))
    if (selected === id) { setSelected(null); setMessages([]) }
  }

  const restore = () => {
    onRestore(messages.map(m => ({
      role: m.role as 'user' | 'assistant',
      content: m.content,
      agent: m.agent ?? undefined,
    })))
    onClose()
  }

  return (
    <motion.div
      className="absolute inset-0 z-20 flex flex-col panel"
      initial={{ opacity: 0, x: 40 }}
      animate={{ opacity: 1, x: 0 }}
      exit={{ opacity: 0, x: 40 }}
      transition={{ duration: 0.2 }}
    >
      {/* Header */}
      <div className="flex items-center gap-3 px-4 py-3 border-b border-[rgba(0,212,255,0.15)]">
        <button onClick={onClose} className="text-[var(--text-dim)] hover:text-[var(--cyan)]">
          <ChevronLeft size={18} />
        </button>
        <Clock size={14} className="text-[var(--cyan)]" />
        <span className="text-xs tracking-widest text-[var(--cyan)] glow-sm">HISTORIQUE</span>
        <span className="ml-auto text-[10px] text-[var(--text-dim)]">{sessions.length} sessions</span>
      </div>

      <div className="flex flex-1 min-h-0">
        {/* Sessions list */}
        <div className="w-48 shrink-0 border-r border-[rgba(0,212,255,0.1)] overflow-y-auto py-2">
          {sessions.length === 0 && (
            <p className="text-[10px] text-[var(--text-dim)] text-center mt-4 tracking-widest">
              AUCUNE SESSION
            </p>
          )}
          {sessions.map(s => (
            <div
              key={s.id}
              onClick={() => open(s.id)}
              className={`group relative w-full cursor-pointer px-3 py-2 text-[11px] transition-colors hover:bg-[rgba(0,212,255,0.05)] ${
                selected === s.id ? 'bg-[rgba(0,212,255,0.08)] text-[var(--cyan)]' : 'text-[var(--text-dim)]'
              }`}
            >
              <div className="flex items-center gap-1 mb-0.5 pr-5">
                <MessageSquare size={10} />
                <span className="font-mono">{s.id.slice(0, 8).toUpperCase()}</span>
              </div>
              <div className="text-[9px] opacity-60">
                {new Date(s.created_at).toLocaleDateString('fr-FR')} · {s.message_count} msgs
              </div>
              <button
                onClick={(e) => remove(s.id, e)}
                title="Supprimer cette conversation"
                className="absolute top-1.5 right-1.5 p-1 rounded text-[var(--text-dim)] opacity-0
                           group-hover:opacity-100 hover:text-red-400 hover:bg-[rgba(255,0,0,0.08)] transition"
              >
                <Trash2 size={12} />
              </button>
            </div>
          ))}
        </div>

        {/* Messages preview */}
        <div className="flex-1 overflow-y-auto px-4 py-3 space-y-2">
          {loading && (
            <p className="text-[var(--text-dim)] text-xs text-center mt-8 tracking-widest">
              CHARGEMENT…
            </p>
          )}
          {!loading && messages.map(m => (
            <div key={m.id} className={`text-xs leading-relaxed ${
              m.role === 'user' ? 'text-[var(--text)] text-right' : 'text-[var(--cyan)]'
            }`}>
              {m.role === 'assistant' && (
                <span className="text-[9px] text-[var(--text-dim)] block tracking-widest mb-0.5">
                  [{m.agent?.toUpperCase() ?? 'JARVIS'}]
                </span>
              )}
              <span className="whitespace-pre-wrap line-clamp-3">{m.content}</span>
            </div>
          ))}
          {!loading && messages.length > 0 && (
            <div className="mt-4 flex flex-col gap-2">
              <button
                onClick={restore}
                className="w-full py-2 text-[10px] tracking-widest text-[var(--cyan)]
                           border border-[rgba(0,212,255,0.3)] rounded hover:bg-[rgba(0,212,255,0.08)]"
              >
                RESTAURER CETTE SESSION
              </button>
              <div className="flex gap-2">
                <button
                  onClick={() => selected && exportSession(selected, 'md')}
                  className="flex-1 flex items-center justify-center gap-1.5 py-1.5 text-[10px] tracking-widest
                             text-[var(--text-dim)] border border-[rgba(0,212,255,0.2)] rounded
                             hover:text-[var(--cyan)] hover:border-[var(--cyan)] transition-colors"
                >
                  <Download size={11} /> MARKDOWN
                </button>
                <button
                  onClick={() => selected && exportSession(selected, 'json')}
                  className="flex-1 flex items-center justify-center gap-1.5 py-1.5 text-[10px] tracking-widest
                             text-[var(--text-dim)] border border-[rgba(0,212,255,0.2)] rounded
                             hover:text-[var(--cyan)] hover:border-[var(--cyan)] transition-colors"
                >
                  <FileJson size={11} /> JSON
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </motion.div>
  )
}
