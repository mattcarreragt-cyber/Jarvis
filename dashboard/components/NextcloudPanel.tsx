'use client'

import { useCallback, useEffect, useState } from 'react'
import { motion } from 'framer-motion'
import { Cloud, CloudOff, X, RefreshCw, FileStack, Clock, Sparkles } from 'lucide-react'
import { fetchNextcloudStatus, triggerNextcloudSync, triggerReembed, NextcloudStatus } from '@/lib/api'

interface Props { onClose: () => void }

export default function NextcloudPanel({ onClose }: Props) {
  const [status, setStatus] = useState<NextcloudStatus | null>(null)
  const [loading, setLoading] = useState(true)
  const [syncing, setSyncing] = useState(false)
  const [reembedding, setReembedding] = useState(false)
  const [reembedMsg, setReembedMsg] = useState('')

  const load = useCallback(async () => {
    const s = await fetchNextcloudStatus()
    setStatus(s)
    setLoading(false)
    setSyncing(s?.running ?? false)
  }, [])

  useEffect(() => {
    load()
    const id = setInterval(load, 5000)   // rafraîchit pendant la sync
    return () => clearInterval(id)
  }, [load])

  const onSync = async () => {
    setSyncing(true)
    await triggerNextcloudSync()
    setTimeout(load, 1500)
  }

  const onReembed = async () => {
    setReembedding(true)
    setReembedMsg('')
    const res = await triggerReembed()
    setReembedMsg(res.ok
      ? `${res.updated ?? 0} extraits ré-indexés (sémantique activée)`
      : `Indisponible : ${res.error ?? 'Kubuntu éteint ?'}`)
    setReembedding(false)
  }

  const fmtDate = (iso: string | null) =>
    iso ? new Date(iso).toLocaleString('fr-FR') : 'jamais'

  return (
    <motion.div
      className="absolute inset-0 z-20 flex flex-col panel"
      initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: 20 }} transition={{ duration: 0.2 }}
    >
      <div className="flex items-center justify-between px-4 py-3 border-b border-[rgba(0,212,255,0.15)]">
        <div className="flex items-center gap-2">
          <Cloud size={14} className="text-[var(--cyan)]" />
          <span className="text-xs tracking-widest text-[var(--cyan)] glow-sm">NEXTCLOUD — RAG LOCAL</span>
        </div>
        <button onClick={onClose} className="text-[var(--text-dim)] hover:text-[var(--cyan)]">
          <X size={16} />
        </button>
      </div>

      <div className="flex-1 flex flex-col gap-5 px-6 py-6 overflow-y-auto">
        {loading ? (
          <p className="text-xs text-[var(--text-dim)] tracking-widest">CHARGEMENT…</p>
        ) : !status?.configured ? (
          <div className="flex flex-col items-center justify-center gap-3 flex-1 text-center">
            <CloudOff size={32} className="text-[var(--text-dim)]" />
            <p className="text-sm text-[var(--text-dim)]">Nextcloud non configuré</p>
            <p className="text-[10px] text-[var(--text-dim)] opacity-70 max-w-xs">
              Renseigne NEXTCLOUD_URL / USER / PASSWORD dans le fichier <code>.env</code> sur Unraid,
              puis redémarre l'API.
            </p>
          </div>
        ) : (
          <>
            {/* Stats */}
            <div className="grid grid-cols-2 gap-3">
              <Stat icon={<FileStack size={16} />} label="FICHIERS INDEXÉS" value={String(status.files)} />
              <Stat icon={<FileStack size={16} />} label="EXTRAITS (CHUNKS)" value={String(status.chunks)} />
            </div>

            <div className="flex flex-col gap-2 text-[11px] text-[var(--text-dim)]">
              <Row label="Racine surveillée" value={status.root} />
              <Row label="Sync périodique" value={status.sync_enabled
                ? `activée (${Math.round(status.sync_interval / 60)} min)` : 'désactivée'} />
              <Row label="Dernière sync" value={fmtDate(status.last_sync)} />
            </div>

            {/* Last result */}
            {status.last_result && (
              <div className="text-[10px] text-[var(--text-dim)] bg-[rgba(0,212,255,0.05)] rounded px-3 py-2 font-mono">
                {JSON.stringify(status.last_result)}
              </div>
            )}

            {/* Sync button */}
            <button
              onClick={onSync}
              disabled={syncing}
              className="flex items-center justify-center gap-2 px-4 py-2.5 rounded
                         border border-[var(--cyan)] text-[var(--cyan)] text-xs tracking-widest
                         hover:bg-[rgba(0,212,255,0.1)] transition-colors disabled:opacity-50"
            >
              <RefreshCw size={14} className={syncing ? 'animate-spin' : ''} />
              {syncing ? 'SYNCHRONISATION…' : 'SYNCHRONISER MAINTENANT'}
            </button>

            <p className="flex items-center gap-1.5 text-[10px] text-[var(--text-dim)] opacity-70">
              <Clock size={11} />
              La sync incrémentale n'ingère que les fichiers nouveaux ou modifiés.
            </p>

            {/* Ré-embedding (active la recherche sémantique une fois Kubuntu en ligne) */}
            <div className="border-t border-[rgba(0,212,255,0.1)] pt-4 mt-1 flex flex-col gap-2">
              <button
                onClick={onReembed}
                disabled={reembedding}
                className="flex items-center justify-center gap-2 px-4 py-2 rounded
                           border border-[rgba(0,212,255,0.3)] text-[var(--text-dim)] text-[11px] tracking-widest
                           hover:text-[var(--cyan)] hover:border-[var(--cyan)] transition-colors disabled:opacity-50"
              >
                <Sparkles size={13} className={reembedding ? 'animate-pulse' : ''} />
                {reembedding ? 'RÉ-INDEXATION…' : 'RÉ-INDEXER (EMBEDDINGS)'}
              </button>
              {reembedMsg && (
                <p className="text-[10px] text-[var(--text-dim)] text-center">{reembedMsg}</p>
              )}
              <p className="text-[10px] text-[var(--text-dim)] opacity-60 text-center">
                Encode les documents ajoutés pendant que Kubuntu dormait.
              </p>
            </div>
          </>
        )}
      </div>
    </motion.div>
  )
}

function Stat({ icon, label, value }: { icon: React.ReactNode; label: string; value: string }) {
  return (
    <div className="flex flex-col gap-1 border border-[rgba(0,212,255,0.15)] rounded px-3 py-3">
      <span className="flex items-center gap-1.5 text-[9px] tracking-widest text-[var(--text-dim)]">
        {icon}{label}
      </span>
      <span className="text-2xl text-[var(--cyan)] glow-sm">{value}</span>
    </div>
  )
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between">
      <span>{label}</span>
      <span className="text-[var(--text)]">{value}</span>
    </div>
  )
}
