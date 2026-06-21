'use client'

import { useCallback, useEffect, useState } from 'react'
import { motion } from 'framer-motion'
import { Bell, X, Trash2, Clock, Repeat, CalendarClock } from 'lucide-react'
import {
  fetchNotifications, markNotificationsRead, fetchAgendaTasks, deleteAgendaTask,
  Notification, AgendaTask,
} from '@/lib/api'

interface Props { onClose: () => void }

export default function AgendaPanel({ onClose }: Props) {
  const [notifs, setNotifs] = useState<Notification[]>([])
  const [tasks, setTasks] = useState<AgendaTask[]>([])
  const [tab, setTab] = useState<'notifs' | 'tasks'>('notifs')

  const load = useCallback(async () => {
    const [n, t] = await Promise.all([fetchNotifications(), fetchAgendaTasks()])
    setNotifs(n.notifications); setTasks(t)
  }, [])

  useEffect(() => {
    load()
    markNotificationsRead()   // ouvrir = marquer lu
    const id = setInterval(load, 8000)
    return () => clearInterval(id)
  }, [load])

  const removeTask = async (id: string) => {
    if (await deleteAgendaTask(id)) setTasks(t => t.filter(x => x.id !== id))
  }

  const describe = (t: AgendaTask) => {
    if (t.schedule_kind === 'daily') return `chaque jour à ${t.time_of_day}`
    if (t.schedule_kind === 'interval') return `toutes les ${Math.round((t.interval_sec || 0) / 60)} min`
    return `le ${t.next_run.slice(0, 16).replace('T', ' à ')}`
  }
  const icon = (t: AgendaTask) =>
    t.schedule_kind === 'interval' ? <Repeat size={12} />
    : t.schedule_kind === 'daily' ? <Repeat size={12} />
    : <Clock size={12} />

  return (
    <motion.div
      className="absolute inset-0 z-20 flex flex-col panel"
      initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: 20 }} transition={{ duration: 0.2 }}
    >
      <div className="flex items-center justify-between px-4 py-3 border-b border-[rgba(0,212,255,0.15)]">
        <div className="flex items-center gap-2">
          <Bell size={14} className="text-[var(--cyan)]" />
          <span className="text-xs tracking-widest text-[var(--cyan)] glow-sm">AGENDA & NOTIFICATIONS</span>
        </div>
        <button onClick={onClose} className="text-[var(--text-dim)] hover:text-[var(--cyan)]">
          <X size={16} />
        </button>
      </div>

      <div className="flex border-b border-[rgba(0,212,255,0.1)] text-[10px] tracking-widest">
        {(['notifs', 'tasks'] as const).map(t => (
          <button key={t} onClick={() => setTab(t)}
            className={`flex-1 py-2 transition-colors ${
              tab === t ? 'text-[var(--cyan)] border-b border-[var(--cyan)]' : 'text-[var(--text-dim)]'}`}>
            {t === 'notifs' ? `NOTIFICATIONS (${notifs.length})` : `TÂCHES (${tasks.length})`}
          </button>
        ))}
      </div>

      <div className="flex-1 overflow-y-auto px-4 py-4 flex flex-col gap-2">
        {tab === 'notifs' ? (
          notifs.length === 0 ? (
            <Empty icon={<Bell size={28} />} text="Aucune notification."
              hint="Tes rappels apparaîtront ici." />
          ) : notifs.map(n => (
            <div key={n.id}
              className="border border-[rgba(0,212,255,0.12)] rounded px-3 py-2 flex flex-col gap-1">
              <span className="text-xs text-[var(--text)] whitespace-pre-wrap">{n.text}</span>
              <span className="text-[9px] text-[var(--text-dim)]">
                {n.source ? `${n.source} · ` : ''}{n.created_at.slice(0, 16).replace('T', ' ')}
              </span>
            </div>
          ))
        ) : (
          tasks.length === 0 ? (
            <Empty icon={<CalendarClock size={28} />} text="Aucune tâche planifiée."
              hint="Dis « rappelle-moi… » ou « chaque jour à 8h… »." />
          ) : tasks.map(t => (
            <div key={t.id}
              className="group flex items-start justify-between gap-2 border border-[rgba(0,212,255,0.12)] rounded px-3 py-2">
              <div className="flex flex-col gap-0.5">
                <span className="text-xs text-[var(--text)]">{t.payload}</span>
                <span className="flex items-center gap-1 text-[9px] text-[var(--text-dim)]">
                  {icon(t)} {describe(t)} · {t.kind === 'prompt' ? '🤖 auto' : '⏰ rappel'}
                  {!t.enabled && ' · terminé'}
                </span>
              </div>
              <button onClick={() => removeTask(t.id)}
                className="text-[var(--text-dim)] hover:text-red-400 opacity-0 group-hover:opacity-100 transition-opacity shrink-0">
                <Trash2 size={13} />
              </button>
            </div>
          ))
        )}
      </div>
    </motion.div>
  )
}

function Empty({ icon, text, hint }: { icon: React.ReactNode; text: string; hint: string }) {
  return (
    <div className="flex-1 flex flex-col items-center justify-center gap-2 text-center text-[var(--text-dim)]">
      {icon}
      <p className="text-xs">{text}</p>
      <p className="text-[10px] opacity-60">{hint}</p>
    </div>
  )
}
